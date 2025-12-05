"""リアルタイム文字起こし表示ウィジェット"""

import logging

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import QTextEdit

logger = logging.getLogger(__name__)


class TranscriptView(QTextEdit):
    """リアルタイム文字起こし表示ウィジェット"""

    def __init__(self, max_lines: int = 1000, parent=None):
        super().__init__(parent)
        self._max_lines = max_lines
        self._partial_text_length = 0

        self._setup_widget()
        self._setup_formats()

        logger.info("TranscriptView 初期化完了")

    def _setup_widget(self):
        """ウィジェット設定"""
        self.setReadOnly(True)
        self.setPlaceholderText("文字起こし結果がここに表示されます...")

        # フォント設定
        font = QFont("Yu Gothic UI", 11)
        self.setFont(font)

        logger.debug("TranscriptView ウィジェット設定完了")

    def _setup_formats(self):
        """テキストフォーマット設定"""
        # 部分結果フォーマット（グレー・イタリック）
        self._partial_format = QTextCharFormat()
        self._partial_format.setForeground(QColor("#888888"))
        self._partial_format.setFontItalic(True)

        # 確定結果フォーマット（黒・通常）
        self._committed_format = QTextCharFormat()
        self._committed_format.setForeground(QColor("#000000"))
        self._committed_format.setFontItalic(False)

        logger.debug("テキストフォーマット設定完了")

    @pyqtSlot(str)
    def show_partial(self, text: str):
        """部分結果を表示（グレー、イタリック）"""
        if not text:
            return

        # 前回の部分結果をクリア
        self.clear_partial()

        # カーソルを末尾に移動
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        # 部分結果を追加（末尾に "..." を付ける）
        cursor.insertText(text + "...", self._partial_format)
        self._partial_text_length = len(text) + 3

        # スクロールを末尾に
        self.ensureCursorVisible()

        logger.debug(f"部分結果表示: {text[:50]}...")

    @pyqtSlot(str)
    def show_committed(self, text: str):
        """確定結果を表示（黒、通常）"""
        if not text:
            return

        # 部分結果をクリア
        self.clear_partial()

        # カーソルを末尾に移動
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        # 確定結果を追加
        cursor.insertText(text, self._committed_format)

        # スクロールを末尾に
        self.ensureCursorVisible()

        # 最大行数制限
        self._limit_lines()

        logger.debug(f"確定結果表示: {text[:50]}...")

    def clear_partial(self):
        """部分結果のみをクリア"""
        if self._partial_text_length == 0:
            return

        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        # 部分結果の文字数分削除
        for _ in range(self._partial_text_length):
            cursor.deletePreviousChar()

        self._partial_text_length = 0
        logger.debug("部分結果クリア")

    def clear_all(self):
        """全てクリア"""
        self.clear()
        self._partial_text_length = 0
        logger.debug("全テキストクリア")

    def _limit_lines(self):
        """最大行数制限を適用"""
        document = self.document()
        if document.lineCount() > self._max_lines:
            # 古い行を削除
            cursor = QTextCursor(document)
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(
                QTextCursor.MoveOperation.Down,
                QTextCursor.MoveMode.KeepAnchor,
                document.lineCount() - self._max_lines,
            )
            cursor.removeSelectedText()
            logger.debug(f"古い行を削除: {self._max_lines}行に制限")

    def get_all_text(self) -> str:
        """全テキストを取得"""
        return self.toPlainText()

    def set_max_lines(self, max_lines: int):
        """最大行数を設定"""
        self._max_lines = max_lines
        self._limit_lines()
        logger.info(f"最大行数設定: {max_lines}")
