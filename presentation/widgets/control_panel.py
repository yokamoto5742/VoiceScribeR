"""操作パネルウィジェット"""

import logging

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QWidget,
)

from domain.models import RecordingState

logger = logging.getLogger(__name__)


class ControlPanel(QWidget):
    """操作パネル"""

    # Signal定義
    recording_toggled = pyqtSignal()
    punctuation_toggled = pyqtSignal()
    settings_clicked = pyqtSignal()
    clear_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_recording = False
        self._use_punctuation = True

        self._setup_ui()

        logger.info("ControlPanel 初期化完了")

    def _setup_ui(self):
        """UI設定"""
        layout = QHBoxLayout()
        self.setLayout(layout)

        # 録音ボタン
        self._record_button = QPushButton("🎤 録音開始")
        self._record_button.setMinimumHeight(40)
        self._record_button.clicked.connect(self._on_record_clicked)
        layout.addWidget(self._record_button)

        # 句読点トグルボタン
        self._punctuation_button = QPushButton("句読点: ON")
        self._punctuation_button.setCheckable(True)
        self._punctuation_button.setChecked(True)
        self._punctuation_button.clicked.connect(self._on_punctuation_clicked)
        layout.addWidget(self._punctuation_button)

        # クリアボタン
        self._clear_button = QPushButton("クリア")
        self._clear_button.clicked.connect(self._on_clear_clicked)
        layout.addWidget(self._clear_button)

        # 設定ボタン
        self._settings_button = QPushButton("設定")
        self._settings_button.clicked.connect(self._on_settings_clicked)
        layout.addWidget(self._settings_button)

        logger.debug("ControlPanel UI設定完了")

    def _on_record_clicked(self):
        """録音ボタンクリック"""
        self.recording_toggled.emit()
        logger.debug("録音トグルSignal発火")

    def _on_punctuation_clicked(self):
        """句読点ボタンクリック"""
        self._use_punctuation = self._punctuation_button.isChecked()
        self.punctuation_toggled.emit()
        logger.debug(f"句読点トグルSignal発火: {self._use_punctuation}")

    def _on_settings_clicked(self):
        """設定ボタンクリック"""
        self.settings_clicked.emit()
        logger.debug("設定Signal発火")

    def _on_clear_clicked(self):
        """クリアボタンクリック"""
        self.clear_clicked.emit()
        logger.debug("クリアSignal発火")

    def update_recording_state(self, state: RecordingState):
        """録音状態に応じてUIを更新"""
        if state == RecordingState.IDLE:
            self._record_button.setText("🎤 録音開始")
            self._record_button.setEnabled(True)
            self._is_recording = False
        elif state == RecordingState.CONNECTING:
            self._record_button.setText("接続中...")
            self._record_button.setEnabled(False)
        elif state == RecordingState.READY:
            self._record_button.setText("準備完了")
            self._record_button.setEnabled(True)
        elif state == RecordingState.RECORDING:
            self._record_button.setText("⏹ 録音停止")
            self._record_button.setEnabled(True)
            self._is_recording = True
        elif state == RecordingState.PROCESSING:
            self._record_button.setText("処理中...")
            self._record_button.setEnabled(False)
        elif state == RecordingState.ERROR:
            self._record_button.setText("❌ エラー")
            self._record_button.setEnabled(True)

        logger.debug(f"録音状態更新: {state.name}")

    def update_punctuation_state(self, enabled: bool):
        """句読点トグル状態を更新"""
        self._use_punctuation = enabled
        self._punctuation_button.setChecked(enabled)
        button_text = "句読点: ON" if enabled else "句読点: OFF"
        self._punctuation_button.setText(button_text)
        logger.debug(f"句読点状態更新: {enabled}")

    @property
    def is_recording(self) -> bool:
        """録音中かどうか"""
        return self._is_recording

    @property
    def use_punctuation(self) -> bool:
        """句読点を使用するか"""
        return self._use_punctuation
