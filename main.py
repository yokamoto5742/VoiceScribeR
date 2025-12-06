import asyncio
import logging
import sys
from datetime import datetime, timedelta
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

import qasync
from PyQt6.QtWidgets import QApplication, QMessageBox

from application.clipboard_manager import ClipboardManager
from application.orchestrator import TranscriptionOrchestrator
from application.text_processor import TextPostProcessor
from config.settings import AppSettings
from infrastructure.audio_recorder import AudioRecorderWorker
from infrastructure.keyboard_listener import GlobalHotkeyManager
from infrastructure.realtime_client import RealtimeTranscriptionClient
from presentation.dialogs.settings_dialog import SettingsDialog
from presentation.main_window import MainWindow
from presentation.widgets.control_panel import ControlPanel
from presentation.widgets.status_bar import VoiceScribeStatusBar
from presentation.widgets.transcript_view import TranscriptView
from utils.error_handler import setup_exception_handler


def setup_logging(settings: AppSettings):
    """ログシステムをセットアップ（ファイル出力とローテーション機能付き）"""
    log_level = getattr(logging, settings.logging.log_level.upper(), logging.INFO)

    # ログディレクトリ作成
    log_dir = settings.paths.log_dir
    log_dir.mkdir(parents=True, exist_ok=True)

    # ログファイルパス
    log_file = log_dir / "VoiceScribe.log"

    # TimedRotatingFileHandlerでログローテーション
    file_handler = TimedRotatingFileHandler(
        filename=str(log_file),
        when='midnight',
        backupCount=settings.logging.log_retention_days,
        encoding='utf-8'
    )
    file_handler.suffix = "%Y-%m-%d.log"

    # フォーマッター設定
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    # コンソールハンドラー
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.WARNING)  # WARNING以上のみコンソール出力

    # ルートロガー設定
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # デバッグモード時は全てのログをコンソール出力
    if settings.logging.debug_mode:
        console_handler.setLevel(logging.DEBUG)
        root_logger.setLevel(logging.DEBUG)

    # 古いログファイルをクリーンアップ
    _cleanup_old_logs(log_dir, settings.logging.log_retention_days)

    logger = logging.getLogger(__name__)
    logger.info(f"ログシステムが初期化されました: {log_file}")
    logger.info("VoiceScribe v2.0 起動")
    return logger


def _cleanup_old_logs(log_dir: Path, retention_days: int):
    """古いログファイルを削除"""
    try:
        now = datetime.now()
        main_log_file = "VoiceScribe.log"
        rotated_log_pattern = r"VoiceScribe\.log\.\d{4}-\d{2}-\d{2}\.log$"

        import re
        deleted_count = 0
        for log_file in log_dir.glob("*.log"):
            if log_file.name != main_log_file and re.match(rotated_log_pattern, log_file.name):
                try:
                    file_modified = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if now - file_modified >= timedelta(days=retention_days):
                        log_file.unlink()
                        logging.info(f"古いログファイルを削除しました: {log_file.name}")
                        deleted_count += 1
                except OSError as e:
                    logging.error(f"ログファイルの削除中にエラーが発生しました {log_file.name}: {str(e)}")

        if deleted_count > 0:
            logging.info(f"合計 {deleted_count} 個の古いログファイルを削除しました")

    except Exception as e:
        logging.error(f"ログクリーンアップ処理中にエラーが発生しました: {str(e)}")


def load_stylesheet() -> str:
    """スタイルシートを読み込み"""
    style_path = Path(__file__).parent / "presentation" / "styles" / "theme.qss"
    if style_path.exists():
        with open(style_path, encoding="utf-8") as f:
            return f.read()
    return ""


def main():
    """アプリケーションのメインエントリポイント"""
    # QApplication 作成
    app = QApplication(sys.argv)
    app.setApplicationName("VoiceScribe v2.0")

    # qasyncイベントループ設定
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    try:
        # 1. 設定読み込み
        settings = AppSettings.load()
        logger = setup_logging(settings)

        # グローバル例外ハンドラ設定
        setup_exception_handler(app)

        # スタイルシート適用
        stylesheet = load_stylesheet()
        if stylesheet:
            app.setStyleSheet(stylesheet)
            logger.info("スタイルシート適用完了")

        # 2. インフラ層初期化
        logger.info("インフラ層初期化開始")
        audio_recorder = AudioRecorderWorker(settings=settings.audio)
        realtime_client = RealtimeTranscriptionClient(
            api_key=settings.elevenlabs_api_key,
            settings=settings.realtime_api,
        )
        hotkey_manager = GlobalHotkeyManager(settings=settings.hotkeys)

        # 3. アプリケーション層初期化
        logger.info("アプリケーション層初期化開始")
        text_processor = TextPostProcessor(settings=settings)
        clipboard_manager = ClipboardManager(settings=settings)

        orchestrator = TranscriptionOrchestrator(
            recorder=audio_recorder,
            client=realtime_client,
            text_processor=text_processor,
            settings=settings,
        )

        # 4. プレゼンテーション層初期化
        logger.info("プレゼンテーション層初期化開始")
        main_window = MainWindow(settings=settings)

        transcript_view = TranscriptView(max_lines=settings.ui.max_transcript_lines)
        control_panel = ControlPanel()
        status_bar = VoiceScribeStatusBar()

        main_window.set_transcript_view(transcript_view)
        main_window.set_control_panel(control_panel)
        main_window.set_status_bar_widget(status_bar)

        # 5. Signal/Slot接続
        logger.info("Signal/Slot接続開始")

        # オーケストレーター → UI
        orchestrator.state_changed.connect(control_panel.update_recording_state)
        orchestrator.state_changed.connect(status_bar.update_recording_state)
        orchestrator.partial_text_ready.connect(transcript_view.show_partial)
        orchestrator.committed_text_ready.connect(transcript_view.show_committed)
        orchestrator.processed_text_ready.connect(clipboard_manager.copy_and_paste)
        orchestrator.error_occurred.connect(
            lambda title, msg: QMessageBox.critical(main_window, title, msg)
        )

        # WebSocketクライアント → ステータスバー
        realtime_client.connection_state_changed.connect(
            status_bar.update_connection_state
        )

        # コントロールパネル → オーケストレーター
        control_panel.recording_toggled.connect(orchestrator.toggle_recording)
        control_panel.punctuation_toggled.connect(orchestrator.toggle_punctuation)
        control_panel.clear_clicked.connect(transcript_view.clear_all)
        control_panel.settings_clicked.connect(
            lambda: SettingsDialog(settings, main_window).exec()
        )

        # ホットキー → オーケストレーター
        hotkey_manager.toggle_recording_pressed.connect(orchestrator.toggle_recording)
        hotkey_manager.toggle_punctuation_pressed.connect(
            orchestrator.toggle_punctuation
        )
        hotkey_manager.exit_app_pressed.connect(app.quit)
        hotkey_manager.reload_replacements_pressed.connect(
            text_processor.reload_replacements
        )

        # クリップボード → ステータスバー
        clipboard_manager.paste_completed.connect(
            lambda: status_bar.show_message_timed("貼り付け完了")
        )
        clipboard_manager.paste_failed.connect(
            lambda msg: status_bar.show_message_timed(f"貼り付け失敗: {msg}")
        )

        # ホットキー登録
        try:
            hotkey_manager.register_hotkeys()
            logger.info("ホットキー登録完了")
        except Exception as e:
            logger.warning(f"ホットキー登録失敗: {e}")

        # メインウィンドウ表示
        if not settings.ui.start_minimized:
            main_window.show()

        logger.info("VoiceScribe v2.0 起動完了")

        # アプリケーション終了時の処理
        def cleanup():
            logger.info("アプリケーション終了処理開始")
            hotkey_manager.unregister_all()

        app.aboutToQuit.connect(cleanup)

        # イベントループ開始 (qasyncで統合されたイベントループ)
        with loop:
            loop.run_forever()

        return 0

    except Exception as e:
        logger.error(f"起動エラー: {e}", exc_info=True)
        QMessageBox.critical(None, "起動エラー", f"アプリケーションの起動に失敗しました:\n{e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
