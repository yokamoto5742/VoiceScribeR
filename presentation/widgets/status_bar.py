"""ステータスバーウィジェット"""

import logging

from PyQt6.QtWidgets import QLabel, QStatusBar

from domain.models import ConnectionState, RecordingState

logger = logging.getLogger(__name__)


class VoiceScribeStatusBar(QStatusBar):
    """VoiceScribe ステータスバー"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

        logger.info("VoiceScribeStatusBar 初期化完了")

    def _setup_ui(self):
        """UI設定"""
        # 接続状態インジケーター
        self._connection_label = QLabel("● 切断")
        self._connection_label.setStyleSheet("color: red;")
        self.addWidget(self._connection_label)

        # 録音時間表示
        self._duration_label = QLabel("録音時間: 0秒")
        self.addWidget(self._duration_label)

        # ホットキーヒント
        self._hotkey_label = QLabel(
            "| Pause: 録音 | F9: 句読点 | Esc: 終了"
        )
        self.addPermanentWidget(self._hotkey_label)

        logger.debug("StatusBar UI設定完了")

    def update_connection_state(self, state: ConnectionState):
        """接続状態を更新"""
        state_map = {
            ConnectionState.DISCONNECTED: ("● 切断", "red"),
            ConnectionState.CONNECTING: ("● 接続中", "orange"),
            ConnectionState.CONNECTED: ("● 接続", "green"),
            ConnectionState.RECONNECTING: ("● 再接続中", "orange"),
            ConnectionState.FAILED: ("● 失敗", "red"),
        }

        text, color = state_map.get(state, ("● 不明", "gray"))
        self._connection_label.setText(text)
        self._connection_label.setStyleSheet(f"color: {color};")

        logger.debug(f"接続状態更新: {state.name}")

    def update_recording_state(self, state: RecordingState):
        """録音状態を更新"""
        state_map = {
            RecordingState.IDLE: "待機中",
            RecordingState.CONNECTING: "接続中",
            RecordingState.READY: "準備完了",
            RecordingState.RECORDING: "録音中",
            RecordingState.PROCESSING: "処理中",
            RecordingState.ERROR: "エラー",
        }

        status_text = state_map.get(state, "不明")
        self.showMessage(status_text)

        logger.debug(f"録音状態更新: {state.name}")

    def update_duration(self, seconds: int):
        """録音時間を更新"""
        if seconds < 60:
            text = f"録音時間: {seconds}秒"
        else:
            minutes = seconds // 60
            secs = seconds % 60
            text = f"録音時間: {minutes}分{secs}秒"

        self._duration_label.setText(text)

    def update_hotkey_hint(self, hints: str):
        """ホットキーヒントを更新"""
        self._hotkey_label.setText(f"| {hints}")
        logger.debug(f"ホットキーヒント更新: {hints}")

    def show_message_timed(self, message: str, timeout: int = 3000):
        """一時的なメッセージを表示"""
        self.showMessage(message, timeout)
        logger.debug(f"メッセージ表示: {message}")
