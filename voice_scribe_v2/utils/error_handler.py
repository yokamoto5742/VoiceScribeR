"""グローバルエラーハンドラ"""

import logging
import sys
import traceback

from PyQt6.QtWidgets import QMessageBox

logger = logging.getLogger(__name__)


def setup_exception_handler(app):
    """グローバル例外ハンドラを設定"""

    def handle_exception(exc_type, exc_value, exc_traceback):
        """未処理例外のハンドラ"""
        if issubclass(exc_type, KeyboardInterrupt):
            # Ctrl+C は通常通り処理
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        # エラーログ出力
        error_msg = "".join(
            traceback.format_exception(exc_type, exc_value, exc_traceback)
        )
        logger.critical(f"未処理例外が発生しました:\n{error_msg}")

        # ユーザーへのエラー通知
        QMessageBox.critical(
            None,
            "予期しないエラー",
            f"予期しないエラーが発生しました:\n\n{exc_type.__name__}: {exc_value}\n\n"
            f"詳細はログファイルを確認してください。",
        )

    # グローバル例外ハンドラを設定
    sys.excepthook = handle_exception
    logger.info("グローバル例外ハンドラ設定完了")
