import asyncio
import base64
import configparser
import json
import logging
import os
import traceback
from typing import Any, AsyncGenerator, Optional

import websockets
from elevenlabs.client import ElevenLabs

from utils.env_loader import load_env_variables


def setup_elevenlabs_client() -> ElevenLabs:
    env_vars = load_env_variables()
    api_key = env_vars.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEYが未設定です")
    return ElevenLabs(api_key=api_key)


def validate_audio_file(file_path: str) -> tuple[bool, Optional[str]]:
    """音声ファイルの存在と有効性を検証

    Returns:
        tuple[bool, Optional[str]]: (検証成功, エラーメッセージ)
    """
    if not file_path:
        return False, "音声ファイルパスが未指定です"

    if not os.path.exists(file_path):
        return False, f"音声ファイルが存在しません: {file_path}"

    file_size = os.path.getsize(file_path)
    if file_size == 0:
        return False, "音声ファイルサイズが0バイトです"

    return True, None


def convert_response_to_text(response) -> Optional[str]:
    """APIレスポンスをテキストに変換"""
    if response is None:
        logging.error("APIからのレスポンスが空です")
        return None

    try:
        if isinstance(response, str):
            return response
        elif hasattr(response, 'text') and response.text is not None:
            return str(response.text)
        elif hasattr(response, '__str__'):
            return str(response)
        else:
            logging.error(f"予期しないレスポンス形式: {type(response)}")
            return None
    except Exception as e:
        logging.error(f"レスポンス変換中の予期しないエラー: {str(e)}")
        logging.debug(f"レスポンス変換エラー詳細: {traceback.format_exc()}")
        return None


def transcribe_audio(
        audio_file_path: str,
        config: configparser.ConfigParser,
        client: ElevenLabs
) -> Optional[str]:
    is_valid, error_msg = validate_audio_file(audio_file_path)
    if not is_valid:
        if error_msg and "未指定" in error_msg:
            logging.warning(error_msg)
        elif error_msg:
            logging.error(error_msg)
        return None

    try:
        logging.info("ファイル読み込み開始")
        with open(audio_file_path, "rb") as file:
            file_content = file.read()
            logging.info(f"ファイル読み込み完了: {len(file_content)} bytes")

            transcription = client.speech_to_text.convert(
                file=(os.path.basename(audio_file_path), file_content),
                model_id=config['ELEVENLABS']['MODEL'],
                language_code=config['ELEVENLABS']['LANGUAGE']
            )

        text_result = convert_response_to_text(transcription)
        if text_result is None:
            return None

        if len(text_result) == 0:
            logging.warning("文字起こし結果が空です")
            return ""

        logging.info(f"文字起こし完了: {len(text_result)}文字")
        return text_result

    except FileNotFoundError as e:
        logging.error(f"ファイルが見つかりません: {str(e)}")
        logging.debug(f"詳細: {traceback.format_exc()}")
        return None
    except PermissionError as e:
        logging.error(f"ファイルアクセス権限エラー: {str(e)}")
        logging.debug(f"詳細: {traceback.format_exc()}")
        return None
    except OSError as e:
        logging.error(f"OS関連エラー: {str(e)}")
        logging.debug(f"詳細: {traceback.format_exc()}")
        return None

    except Exception as e:
        logging.error(f"文字起こしエラー: {str(e)}")
        logging.error(f"エラーのタイプ: {type(e).__name__}")
        logging.debug(f"詳細: {traceback.format_exc()}")
        return None


class ElevenLabsRealtimeClient:
    """ElevenLabs Scribe V2 リアルタイムAPI用WebSocketクライアント

    修正版: 正しいエンドポイントURLとメッセージ形式を使用
    """

    # 正しいWebSocketエンドポイント
    WEBSOCKET_BASE_URL = "wss://api.elevenlabs.io/v1/speech-to-text/realtime"

    def __init__(self, api_key: str, model: str = "scribe_v2_realtime", language: str = "jpn"):
        self.api_key = api_key
        self.model = model
        self.language = language
        self.websocket: Any = None
        self._is_connected = False
        self._audio_queue: asyncio.Queue = asyncio.Queue()
        self._stop_flag = False

    def _build_websocket_url(self) -> str:
        """クエリパラメータを含むWebSocket URLを構築"""
        # クエリパラメータで設定を指定
        params = [
            f"model_id={self.model}",
            f"language_code={self.language}",
            "encoding=pcm_s16le",  # 16bit PCM Little Endian
            "sample_rate=16000",  # AudioRecorderの設定に合わせる
            "commit_strategy=vad",  # Voice Activity Detection
            "vad_silence_threshold_secs=0.5",  # 無音検出しきい値
        ]
        return f"{self.WEBSOCKET_BASE_URL}?{'&'.join(params)}"

    async def connect(self) -> bool:
        """WebSocket接続を確立"""
        try:
            # APIキーの簡易チェック（ログにはマスクして出力）
            masked_key = f"{self.api_key[:4]}****{self.api_key[-4:]}" if self.api_key and len(
                self.api_key) > 8 else "INVALID"

            websocket_url = self._build_websocket_url()
            logging.info(f"WebSocket接続開始: URL={websocket_url}, API_KEY={masked_key}")

            # xi-api-keyヘッダーで認証
            self.websocket = await websockets.connect(
                websocket_url,
                additional_headers={
                    "xi-api-key": self.api_key
                },
                ping_interval=20,
                ping_timeout=10
            )

            if not self.websocket:
                raise ConnectionError("WebSocket接続の確立に失敗しました")

            logging.info("WebSocket接続成功")

            # session_started イベントを待機
            try:
                initial_response = await asyncio.wait_for(
                    self.websocket.recv(),
                    timeout=10.0
                )
                data = json.loads(initial_response)
                message_type = data.get("message_type")

                if message_type == "session_started":
                    session_id = data.get("session_id", "unknown")
                    logging.info(f"セッション開始: session_id={session_id}")
                else:
                    logging.warning(f"予期しない初期メッセージ: {message_type}")

            except asyncio.TimeoutError:
                logging.warning("セッション開始メッセージのタイムアウト（続行します）")

            self._is_connected = True
            return True

        except websockets.exceptions.InvalidStatus as e:
            # 403 ForbiddenなどのHTTPエラー処理
            status_code = getattr(e.response, 'status_code', 'unknown')
            logging.error(f"WebSocket接続拒否 (HTTP {status_code}): {str(e)}")
            if status_code == 403:
                logging.error("認証エラー: APIキーが無効か、Scribe V2 Realtimeへのアクセス権限がありません。")
                logging.error("注意: Scribe V2 Realtimeは有料プランが必要な場合があります。")
            return False
        except Exception as e:
            logging.error(f"WebSocket接続エラー: {str(e)}")
            logging.debug(f"詳細: {traceback.format_exc()}")
            return False

    async def disconnect(self):
        """WebSocket接続を切断"""
        self._stop_flag = True
        if self.websocket:
            try:
                await self.websocket.close()
                logging.info("WebSocket接続を切断しました")
            except Exception as e:
                logging.error(f"WebSocket切断エラー: {str(e)}")
            finally:
                self._is_connected = False
                self.websocket = None

    def is_connected(self) -> bool:
        """接続状態を確認"""
        return self._is_connected and self.websocket is not None

    async def send_audio_chunk(self, audio_data: bytes, commit: bool = False):
        """音声チャンクを送信

        Args:
            audio_data: PCM音声データ（16bit, 16kHz, mono）
            commit: Trueの場合、このチャンクで音声入力を確定
        """
        if not self.is_connected() or not self.websocket:
            # 接続切れの場合はログを出してスキップ
            return

        try:
            # 音声データをBase64エンコード
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')

            # input_audio_chunk メッセージ形式
            message = {
                "message_type": "input_audio_chunk",
                "audio_base_64": audio_base64,
            }

            # commit フラグが True の場合、音声入力を確定
            if commit:
                message["commit"] = True

            await self.websocket.send(json.dumps(message))

        except Exception as e:
            logging.error(f"音声チャンク送信エラー: {str(e)}")
            self._is_connected = False

    async def send_commit(self):
        """手動でトランスクリプトをコミット（確定）する"""
        if not self.is_connected() or not self.websocket:
            return

        try:
            message = {
                "message_type": "commit"
            }
            await self.websocket.send(json.dumps(message))
            logging.debug("コミットメッセージを送信しました")
        except Exception as e:
            logging.error(f"コミット送信エラー: {str(e)}")

    async def receive_text(self) -> AsyncGenerator[tuple[str, bool], None]:
        """テキスト結果を受信

        Yields:
            tuple[str, bool]: (テキスト, is_final)
                - is_final=False: 部分的なトランスクリプト（partial_transcript）
                - is_final=True: 確定したトランスクリプト（committed_transcript）
        """
        if not self.is_connected() or not self.websocket:
            logging.error("WebSocketが接続されていません")
            return

        try:
            async for message in self.websocket:
                if self._stop_flag:
                    break

                try:
                    data = json.loads(message)

                    message_type = data.get("message_type")

                    if message_type == "partial_transcript":
                        # 部分的なトランスクリプト
                        text = data.get("text", "")
                        if text:
                            logging.debug(f"部分結果: {text}")
                            yield (text, False)

                    elif message_type == "committed_transcript":
                        # 確定したトランスクリプト
                        text = data.get("text", "")
                        if text:
                            logging.info(f"確定結果: {text}")
                            yield (text, True)

                    elif message_type == "committed_transcript_with_timestamps":
                        # タイムスタンプ付き確定トランスクリプト
                        text = data.get("text", "")
                        if text:
                            logging.info(f"確定結果(タイムスタンプ付き): {text}")
                            yield (text, True)

                    elif message_type == "error":
                        error_code = data.get("error_code", "unknown")
                        error_message = data.get("error_message", "Unknown error")
                        logging.error(f"APIエラー [{error_code}]: {error_message}")

                    elif message_type == "session_started":
                        # セッション開始（接続時に既に処理済みの場合もある）
                        session_id = data.get("session_id", "unknown")
                        logging.debug(f"セッション開始イベント: {session_id}")

                    else:
                        logging.debug(f"未処理のメッセージタイプ: {message_type}")

                except json.JSONDecodeError as e:
                    logging.error(f"JSONデコードエラー: {str(e)}")
                    continue

        except websockets.exceptions.ConnectionClosed as e:
            logging.info(f"WebSocket接続が閉じられました: {e.code} - {e.reason}")
            self._is_connected = False
        except Exception as e:
            logging.error(f"テキスト受信エラー: {str(e)}")
            logging.debug(f"詳細: {traceback.format_exc()}")
            self._is_connected = False