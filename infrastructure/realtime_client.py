"""ElevenLabs Realtime API WebSocketクライアント"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

import websockets
from websockets.asyncio.client import ClientConnection
from PyQt6.QtCore import QObject, pyqtSignal

from config.settings import RealtimeApiSettings
from domain.exceptions import (
    TranscriptionError,
    WebSocketAuthenticationError,
    WebSocketConnectionError,
)
from domain.models import ConnectionState, Transcript, TranscriptType

logger = logging.getLogger(__name__)


class RealtimeTranscriptionClient(QObject):
    """ElevenLabs Realtime API WebSocketクライアント"""

    # Signal定義
    partial_transcript_received = pyqtSignal(Transcript)
    committed_transcript_received = pyqtSignal(Transcript)
    connection_state_changed = pyqtSignal(ConnectionState)
    error_occurred = pyqtSignal(Exception)

    def __init__(self, api_key: str, settings: RealtimeApiSettings):
        super().__init__()
        self._api_key = api_key
        self._settings = settings
        self._websocket: Optional[ClientConnection] = None
        self._connection_state = ConnectionState.DISCONNECTED
        self._reconnect_count = 0
        self._is_running = False
        self._audio_queue: asyncio.Queue = asyncio.Queue(maxsize=10)

    def _check_connected(self) -> bool:
        """接続状態を確認するヘルパーメソッド"""
        if self._websocket is None:
            return False
        
        if self._connection_state != ConnectionState.CONNECTED:
            return False

        try:
            # websockets 15.x: state プロパティで接続状態を確認
            state = self._websocket.state
            # State列挙型の値をチェック（OPEN = 1）
            is_open = state.value == 1 or str(state.name) == "OPEN"
            return is_open
        except Exception as e:
            logger.debug(f"接続状態チェック中のエラー: {e}")
            return False

    @property
    def is_connected(self) -> bool:
        """接続状態を返す"""
        return self._check_connected()

    @property
    def connection_state(self) -> ConnectionState:
        """現在の接続状態"""
        return self._connection_state

    def _set_connection_state(self, state: ConnectionState):
        """接続状態を更新してSignalを発火"""
        if self._connection_state != state:
            self._connection_state = state
            self.connection_state_changed.emit(state)
            logger.info(f"接続状態変更: {state.name}")

    async def connect(self) -> bool:
        """WebSocket接続を確立"""
        if self._check_connected():
            logger.warning("既に接続されています")
            return True

        self._set_connection_state(ConnectionState.CONNECTING)

        try:
            url = self._build_websocket_url()
            headers = {"xi-api-key": self._api_key}

            logger.info(f"WebSocket接続開始: {self._settings.model}")
            self._websocket = await websockets.connect(url, additional_headers=headers)

            self._set_connection_state(ConnectionState.CONNECTED)
            self._reconnect_count = 0
            logger.info("WebSocket接続成功")
            return True

        except websockets.InvalidStatusCode as e:
            if e.status_code == 401:
                error = WebSocketAuthenticationError("APIキーが無効です")
                self.error_occurred.emit(error)
                self._set_connection_state(ConnectionState.FAILED)
                raise error
            else:
                error = WebSocketConnectionError(f"接続エラー: HTTP {e.status_code}")
                self.error_occurred.emit(error)
                self._set_connection_state(ConnectionState.FAILED)
                raise error

        except Exception as e:
            error = WebSocketConnectionError(f"予期しないエラー: {e}")
            logger.error(f"接続失敗: {e}", exc_info=True)
            self.error_occurred.emit(error)
            self._set_connection_state(ConnectionState.FAILED)
            return False

    async def disconnect(self):
        """WebSocket接続を切断"""
        self._is_running = False
        if self._websocket:
            try:
                await self._websocket.close()
                logger.info("WebSocket接続を切断しました")
            except Exception as e:
                logger.error(f"切断エラー: {e}")
            finally:
                self._websocket = None
                self._set_connection_state(ConnectionState.DISCONNECTED)

    async def send_audio(self, data: bytes):
        """音声データを送信（未接続時はスキップ）"""
        # 未接続時は例外を投げずにスキップ
        if not self._check_connected():
            logger.debug("WebSocket未接続のため音声データをスキップ")
            return

        try:
            # バックプレッシャー制御
            if self._audio_queue.full():
                logger.warning("音声キューが満杯 - 古いデータを破棄")
                try:
                    self._audio_queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass

            await self._audio_queue.put(data)

        except Exception as e:
            logger.error(f"音声データキューイングエラー: {e}")

    async def _send_loop(self):
        """音声データ送信ループ"""
        logger.debug("送信ループ開始")
        while self._is_running:
            try:
                # キューからデータを取得
                data = await asyncio.wait_for(
                    self._audio_queue.get(), timeout=0.1
                )

                # 接続確認してから送信
                if self._websocket and self._check_connected():
                    await self._websocket.send(data)
                else:
                    logger.debug("送信時にWebSocket未接続")

            except asyncio.TimeoutError:
                continue
            except websockets.ConnectionClosed:
                logger.warning("送信中に接続が閉じられました")
                break
            except Exception as e:
                logger.error(f"送信ループエラー: {e}")
                # エラーでも継続
                continue

        logger.debug("送信ループ終了")

    async def receive_loop(self):
        """文字起こし結果受信ループ"""
        if not self._check_connected():
            logger.error("receive_loop: WebSocketが接続されていません")
            return

        self._is_running = True
        logger.info("受信ループ開始")

        # 送信ループを別タスクで起動
        send_task = asyncio.create_task(self._send_loop())

        try:
            async for message in self._websocket:
                if not self._is_running:
                    break

                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"JSONパースエラー: {e}")
                except Exception as e:
                    logger.error(f"メッセージ処理エラー: {e}")

        except websockets.ConnectionClosed as e:
            logger.warning(f"WebSocket接続が切断されました: {e}")
            if self._is_running:
                await self._handle_reconnect()

        except Exception as e:
            logger.error(f"受信ループエラー: {e}", exc_info=True)
            self.error_occurred.emit(TranscriptionError(str(e)))

        finally:
            self._is_running = False
            send_task.cancel()
            try:
                await send_task
            except asyncio.CancelledError:
                pass
            logger.info("受信ループ終了")

    async def _handle_message(self, data: dict):
        """受信メッセージを処理"""
        message_type = data.get("type")

        if message_type == "partial":
            # 部分結果
            text = data.get("text", "")
            transcript = Transcript(
                text=text,
                type=TranscriptType.PARTIAL,
                timestamp=datetime.now(),
            )
            self.partial_transcript_received.emit(transcript)
            logger.debug(f"部分結果: {text}")

        elif message_type == "committed":
            # 確定結果
            text = data.get("text", "")
            transcript = Transcript(
                text=text,
                type=TranscriptType.COMMITTED,
                timestamp=datetime.now(),
            )
            self.committed_transcript_received.emit(transcript)
            logger.debug(f"確定結果: {text}")

        else:
            logger.debug(f"未知のメッセージタイプ: {message_type}")

    async def _handle_reconnect(self):
        """再接続処理"""
        if self._reconnect_count >= self._settings.max_reconnect_attempts:
            logger.error(
                f"再接続試行回数上限 ({self._settings.max_reconnect_attempts}) に達しました"
            )
            error = WebSocketConnectionError("再接続失敗")
            self.error_occurred.emit(error)
            self._set_connection_state(ConnectionState.FAILED)
            return

        self._reconnect_count += 1
        delay = self._calculate_backoff_delay()

        logger.info(
            f"再接続試行 {self._reconnect_count}/{self._settings.max_reconnect_attempts} - {delay}秒後"
        )
        self._set_connection_state(ConnectionState.RECONNECTING)

        await asyncio.sleep(delay)

        try:
            success = await self.connect()
            if success:
                logger.info("再接続成功")
                # 受信ループを再開
                asyncio.create_task(self.receive_loop())
        except Exception as e:
            logger.error(f"再接続失敗: {e}")
            await self._handle_reconnect()

    def _calculate_backoff_delay(self) -> float:
        """エクスポネンシャルバックオフの遅延時間を計算"""
        base_delay = self._settings.initial_reconnect_delay
        max_delay = 16.0
        delay = min(base_delay * (2 ** (self._reconnect_count - 1)), max_delay)
        return delay

    def _build_websocket_url(self) -> str:
        """WebSocket URL を構築"""
        base_url = "wss://api.elevenlabs.io/v1/speech-to-text/realtime"
        params = [
            f"model_id={self._settings.model}",
            f"audio_format={self._settings.audio_format}",
            f"language_code={self._settings.language}",
        ]
        return f"{base_url}?{'&'.join(params)}"