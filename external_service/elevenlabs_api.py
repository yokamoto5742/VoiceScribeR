import asyncio
import configparser
import json
import logging
import os
import traceback
import base64
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
    """ElevenLabs Scribe V2 リアルタイムAPI用WebSocketクライアント"""

    WEBSOCKET_URL = "wss://api.elevenlabs.io/v1/speech-to-text/scribe-v2/real-time"

    def __init__(self, api_key: str, model: str = "scribe_v2", language: str = "jpn"):
        self.api_key = api_key
        self.model = model
        self.language = language
        self.websocket: Any = None
        self._is_connected = False
        self._audio_queue: asyncio.Queue = asyncio.Queue()
        self._stop_flag = False

    async def connect(self) -> bool:
        """WebSocket接続を確立"""
        try:
            # APIキーの簡易チェック（ログにはマスクして出力）
            masked_key = f"{self.api_key[:4]}****{self.api_key[-4:]}" if self.api_key and len(
                self.api_key) > 8 else "INVALID"
            logging.info(f"WebSocket接続開始: URL={self.WEBSOCKET_URL}, API_KEY={masked_key}")

            # 修正: extra_headers -> additional_headers に変更
            self.websocket = await websockets.connect(
                self.WEBSOCKET_URL,
                additional_headers={
                    "xi-api-key": self.api_key
                },
                ping_interval=20,
                ping_timeout=10
            )

            if not self.websocket:
                raise ConnectionError("WebSocket接続の確立に失敗しました")

            logging.info("WebSocket接続成功")

            # 初期設定を送信
            # Scribe V2用の初期化メッセージ
            config_message = {
                "type": "start",
                "model": "scribe_v2",  # config.iniの値に関わらず正しいモデルIDを指定
                "language": self.language,
                # AudioRecorderの設定(16kHz, 1ch, 16bit PCM)に合わせる
                "audio_encoding": "pcm_s16le",
                "sample_rate": 16000
            }
            await self.websocket.send(json.dumps(config_message))
            logging.info(f"初期設定送信完了: {config_message}")

            self._is_connected = True
            return True

        except websockets.exceptions.InvalidStatus as e:
            # 403 ForbiddenなどのHTTPエラー処理
            logging.error(f"WebSocket接続拒否 (HTTP {e.response.status_code}): {str(e)}")
            if e.response.status_code == 403:
                logging.error("認証エラー: APIキーが無効か、Scribe V2へのアクセス権限がありません。")
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

    async def send_audio_chunk(self, audio_data: bytes):
        """音声チャンクを送信"""
        if not self.is_connected() or not self.websocket:
            # 接続切れの場合はログを出してスキップ
            return

        try:
            # 音声データはJSON形式でBase64エンコードして送信
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')

            message = {
                "audio_event": {
                    "audio_base_64": audio_base64,
                }
            }
            await self.websocket.send(json.dumps(message))

        except Exception as e:
            logging.error(f"音声チャンク送信エラー: {str(e)}")
            self._is_connected = False

    async def receive_text(self) -> AsyncGenerator[tuple[str, bool], None]:
        """テキスト結果を受信

        Yields:
            tuple[str, bool]: (テキスト, is_final)
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

                    event_type = data.get("type")

                    if event_type == "transcription":
                        transcription = data.get("transcription_event", {})
                        text = transcription.get("text", "")
                        result_type = transcription.get("type", "")

                        # 空文字は無視
                        if not text:
                            continue

                        if result_type == "partial":
                            # 部分結果はデバッグログのみ
                            logging.debug(f"部分結果: {text}")
                            yield (text, False)
                        elif result_type == "final":
                            logging.info(f"確定結果: {text}")
                            yield (text, True)

                    elif event_type == "error":
                        error_msg = data.get("description", "Unknown error")
                        logging.error(f"APIエラー: {error_msg}")

                except json.JSONDecodeError as e:
                    logging.error(f"JSONデコードエラー: {str(e)}")
                    continue

        except Exception as e:
            logging.error(f"テキスト受信エラー: {str(e)}")
            logging.debug(f"詳細: {traceback.format_exc()}")
            self._is_connected = False
