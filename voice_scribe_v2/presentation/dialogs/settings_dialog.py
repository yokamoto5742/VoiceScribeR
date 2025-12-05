"""設定ダイアログ"""

import logging

from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)

from config.settings import AppSettings

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """設定ダイアログ"""

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__(parent)
        self._settings = settings

        self._setup_ui()
        self._load_settings()

        logger.info("SettingsDialog 初期化完了")

    def _setup_ui(self):
        """UI設定"""
        self.setWindowTitle("設定")
        self.setMinimumWidth(400)

        layout = QVBoxLayout()
        self.setLayout(layout)

        # フォームレイアウト
        form_layout = QFormLayout()
        layout.addLayout(form_layout)

        # 一般設定
        form_layout.addRow(QLabel("<b>一般設定</b>"))

        self._start_minimized_check = QCheckBox()
        form_layout.addRow("最小化で起動:", self._start_minimized_check)

        # 音声設定
        form_layout.addRow(QLabel("<b>音声設定</b>"))

        self._sample_rate_spin = QSpinBox()
        self._sample_rate_spin.setRange(8000, 48000)
        self._sample_rate_spin.setSingleStep(8000)
        form_layout.addRow("サンプリングレート:", self._sample_rate_spin)

        self._chunk_size_spin = QSpinBox()
        self._chunk_size_spin.setRange(128, 2048)
        self._chunk_size_spin.setSingleStep(128)
        form_layout.addRow("チャンクサイズ:", self._chunk_size_spin)

        # 録音設定
        form_layout.addRow(QLabel("<b>録音設定</b>"))

        self._auto_stop_spin = QSpinBox()
        self._auto_stop_spin.setRange(10, 300)
        self._auto_stop_spin.setSuffix(" 秒")
        form_layout.addRow("自動停止時間:", self._auto_stop_spin)

        self._use_punctuation_check = QCheckBox()
        form_layout.addRow("句読点を使用:", self._use_punctuation_check)

        # ホットキー設定
        form_layout.addRow(QLabel("<b>ホットキー設定</b>"))

        self._toggle_key_edit = QLineEdit()
        form_layout.addRow("録音トグル:", self._toggle_key_edit)

        self._exit_key_edit = QLineEdit()
        form_layout.addRow("終了キー:", self._exit_key_edit)

        # ボタン
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        logger.debug("SettingsDialog UI設定完了")

    def _load_settings(self):
        """現在の設定を読み込み"""
        # 一般設定
        self._start_minimized_check.setChecked(self._settings.ui.start_minimized)

        # 音声設定
        self._sample_rate_spin.setValue(self._settings.audio.sample_rate)
        self._chunk_size_spin.setValue(self._settings.audio.chunk_size)

        # 録音設定
        self._auto_stop_spin.setValue(self._settings.recording.auto_stop_timer)
        self._use_punctuation_check.setChecked(
            self._settings.recording.use_punctuation
        )

        # ホットキー設定
        self._toggle_key_edit.setText(self._settings.hotkeys.toggle_recording)
        self._exit_key_edit.setText(self._settings.hotkeys.exit_app)

        logger.debug("設定読み込み完了")

    def get_settings(self) -> dict:
        """変更された設定を取得"""
        return {
            "ui": {
                "start_minimized": self._start_minimized_check.isChecked(),
            },
            "audio": {
                "sample_rate": self._sample_rate_spin.value(),
                "chunk_size": self._chunk_size_spin.value(),
            },
            "recording": {
                "auto_stop_timer": self._auto_stop_spin.value(),
                "use_punctuation": self._use_punctuation_check.isChecked(),
            },
            "hotkeys": {
                "toggle_recording": self._toggle_key_edit.text(),
                "exit_app": self._exit_key_edit.text(),
            },
        }
