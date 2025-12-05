"""PyQt6 メインウィンドウ"""

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCloseEvent, QIcon
from PyQt6.QtWidgets import (
    QMainWindow,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from config.settings import AppSettings

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """VoiceScribe v2.0 メインウィンドウ"""

    def __init__(self, settings: AppSettings):
        super().__init__()
        self._settings = settings
        self._tray_icon = None

        self._setup_window()
        self._setup_ui()
        self._setup_tray_icon()

        logger.info("MainWindow 初期化完了")

    def _setup_window(self):
        """ウィンドウ設定"""
        self.setWindowTitle("VoiceScribe v2.0")
        self.resize(
            self._settings.ui.window_width,
            self._settings.ui.window_height,
        )

        # 最小化で起動
        if self._settings.ui.start_minimized:
            self.showMinimized()
        else:
            self.show()

    def _setup_ui(self):
        """UIレイアウト設定"""
        # 中央ウィジェット
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # メインレイアウト
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # TODO: Phase 4 で各ウィジェットを追加
        # - TranscriptView
        # - ControlPanel
        # - StatusBar

        logger.debug("UI レイアウト設定完了")

    def _setup_tray_icon(self):
        """システムトレイアイコン設定"""
        try:
            self._tray_icon = QSystemTrayIcon(self)
            # TODO: アイコン設定
            # self._tray_icon.setIcon(QIcon("icon.png"))
            self._tray_icon.setToolTip("VoiceScribe v2.0")
            self._tray_icon.activated.connect(self._on_tray_activated)
            self._tray_icon.show()
            logger.debug("システムトレイアイコン設定完了")
        except Exception as e:
            logger.warning(f"システムトレイアイコン設定失敗: {e}")

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason):
        """トレイアイコンクリック時の処理"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.activateWindow()

    def closeEvent(self, event: QCloseEvent):
        """ウィンドウクローズイベント"""
        # 最小化してトレイに格納
        if self._tray_icon and self._tray_icon.isVisible():
            self.hide()
            event.ignore()
            logger.debug("ウィンドウをトレイに最小化")
        else:
            event.accept()
            logger.info("アプリケーション終了")

    def set_transcript_view(self, view):
        """TranscriptView を設定"""
        layout = self.centralWidget().layout()
        layout.addWidget(view, stretch=3)
        logger.debug("TranscriptView 追加")

    def set_control_panel(self, panel):
        """ControlPanel を設定"""
        layout = self.centralWidget().layout()
        layout.addWidget(panel, stretch=1)
        logger.debug("ControlPanel 追加")

    def set_status_bar_widget(self, status_bar):
        """StatusBar を設定"""
        self.setStatusBar(status_bar)
        logger.debug("StatusBar 追加")
