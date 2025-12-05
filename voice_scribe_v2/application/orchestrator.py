"""文字起こしオーケストレーター - 全体制御"""

import logging
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal

from config.settings import AppSettings
from domain.exceptions import StateTransitionError
from domain.models import RecordingState, Transcript, TranscriptType

logger = logging.getLogger(__name__)


class TranscriptionOrchestrator(QObject):
    """文字起こし全体の制御と状態管理"""

    # 状態変更Signal
    state_changed = pyqtSignal(RecordingState)

    # テキスト関連Signal
    partial_text_ready = pyqtSignal(str)  # UI表示用（グレー）
    committed_text_ready = pyqtSignal(str)  # UI表示用（黒）
    processed_text_ready = pyqtSignal(str)  # 後処理済み（貼り付け用）

    # エラーSignal
    error_occurred = pyqtSignal(str, str)  # (title, message)

    # 録音時間Signal
    recording_duration_changed = pyqtSignal(int)  # 秒数

    def __init__(
        self,
        recorder,  # AudioRecorderWorker
        client,  # RealtimeTranscriptionClient
        text_processor,  # TextPostProcessor
        settings: AppSettings,
    ):
        super().__init__()
        self._recorder = recorder
        self._client = client
        self._text_processor = text_processor
        self._settings = settings

        self._current_state = RecordingState.IDLE
        self._use_punctuation = settings.recording.use_punctuation

        # Signal/Slot接続
        self._connect_signals()

        logger.info("TranscriptionOrchestrator 初期化完了")

    def _connect_signals(self):
        """各コンポーネントのSignal/Slotを接続"""
        # AudioRecorder Signal
        self._recorder.audio_chunk_ready.connect(self._on_audio_chunk)
        self._recorder.recording_started.connect(self._on_recording_started)
        self._recorder.recording_stopped.connect(self._on_recording_stopped)
        self._recorder.error_occurred.connect(self._on_recorder_error)

        # RealtimeTranscriptionClient Signal
        self._client.partial_transcript_received.connect(
            self._on_partial_transcript
        )
        self._client.committed_transcript_received.connect(
            self._on_committed_transcript
        )
        self._client.connection_state_changed.connect(
            self._on_connection_state_changed
        )
        self._client.error_occurred.connect(self._on_client_error)

        logger.debug("Signal/Slot接続完了")

    @property
    def current_state(self) -> RecordingState:
        """現在の状態"""
        return self._current_state

    @property
    def use_punctuation(self) -> bool:
        """句読点を使用するか"""
        return self._use_punctuation

    def start_recording(self):
        """録音を開始"""
        logger.info("録音開始要求")

        if self._current_state != RecordingState.IDLE:
            logger.warning(f"録音開始不可: 現在の状態={self._current_state}")
            self.error_occurred.emit(
                "録音開始エラー", f"現在の状態で録音を開始できません ({self._current_state.name})"
            )
            return

        # 状態遷移: IDLE → CONNECTING
        self._set_state(RecordingState.CONNECTING)

        # WebSocket接続を非同期で開始
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        asyncio.create_task(self._async_start_recording())

    async def _async_start_recording(self):
        """非同期で録音を開始"""
        try:
            # WebSocket接続
            success = await self._client.connect()
            if not success:
                logger.error("WebSocket接続失敗")
                self._set_state(RecordingState.ERROR)
                return

            # 状態遷移: CONNECTING → READY
            self._set_state(RecordingState.READY)

            # 受信ループを開始
            import asyncio

            asyncio.create_task(self._client.receive_loop())

            # 録音開始
            self._recorder.start_recording()

            # 状態遷移: READY → RECORDING
            self._set_state(RecordingState.RECORDING)

        except Exception as e:
            logger.error(f"録音開始エラー: {e}", exc_info=True)
            self._set_state(RecordingState.ERROR)
            self.error_occurred.emit("録音開始エラー", str(e))

    def stop_recording(self):
        """録音を停止"""
        logger.info("録音停止要求")

        if self._current_state != RecordingState.RECORDING:
            logger.warning(f"録音停止不可: 現在の状態={self._current_state}")
            return

        # 状態遷移: RECORDING → PROCESSING
        self._set_state(RecordingState.PROCESSING)

        # 録音停止
        self._recorder.stop_recording()

        # WebSocket切断
        import asyncio

        asyncio.create_task(self._async_stop_recording())

    async def _async_stop_recording(self):
        """非同期で録音を停止"""
        try:
            await self._client.disconnect()

            # 状態遷移: PROCESSING → IDLE
            self._set_state(RecordingState.IDLE)

            logger.info("録音停止完了")

        except Exception as e:
            logger.error(f"録音停止エラー: {e}", exc_info=True)
            self.error_occurred.emit("録音停止エラー", str(e))
            self._set_state(RecordingState.ERROR)

    def toggle_recording(self):
        """録音のトグル"""
        if self._current_state == RecordingState.IDLE:
            self.start_recording()
        elif self._current_state == RecordingState.RECORDING:
            self.stop_recording()
        else:
            logger.warning(f"トグル不可: 現在の状態={self._current_state}")

    def toggle_punctuation(self):
        """句読点使用のトグル"""
        self._use_punctuation = not self._use_punctuation
        self._text_processor.set_punctuation_enabled(self._use_punctuation)
        logger.info(f"句読点使用: {self._use_punctuation}")

    def _set_state(self, new_state: RecordingState):
        """状態を更新してSignalを発火"""
        if self._current_state != new_state:
            old_state = self._current_state
            self._current_state = new_state
            self.state_changed.emit(new_state)
            logger.info(f"状態遷移: {old_state.name} → {new_state.name}")

    def _on_audio_chunk(self, data: bytes):
        """音声チャンク受信時の処理"""
        if self._current_state != RecordingState.RECORDING:
            return

        # WebSocketに音声を送信
        import asyncio

        asyncio.create_task(self._client.send_audio(data))

    def _on_partial_transcript(self, transcript: Transcript):
        """部分結果受信時の処理"""
        logger.debug(f"部分結果: {transcript.text}")
        self.partial_text_ready.emit(transcript.text)

    def _on_committed_transcript(self, transcript: Transcript):
        """確定結果受信時の処理"""
        logger.debug(f"確定結果: {transcript.text}")

        # UI表示用
        self.committed_text_ready.emit(transcript.text)

        # 後処理を適用
        processed_text = self._text_processor.process(transcript.text)

        # 後処理済みテキスト（貼り付け用）
        self.processed_text_ready.emit(processed_text)

        logger.info(f"処理済みテキスト: {processed_text}")

    def _on_recording_started(self):
        """録音開始時の処理"""
        logger.debug("録音開始Signal受信")

    def _on_recording_stopped(self):
        """録音停止時の処理"""
        logger.debug("録音停止Signal受信")

    def _on_connection_state_changed(self, state):
        """接続状態変更時の処理"""
        logger.debug(f"接続状態変更: {state}")

    def _on_recorder_error(self, error: Exception):
        """録音エラー時の処理"""
        logger.error(f"録音エラー: {error}")
        self.error_occurred.emit("録音エラー", str(error))
        self._set_state(RecordingState.ERROR)

    def _on_client_error(self, error: Exception):
        """クライアントエラー時の処理"""
        logger.error(f"クライアントエラー: {error}")
        self.error_occurred.emit("接続エラー", str(error))
        self._set_state(RecordingState.ERROR)
