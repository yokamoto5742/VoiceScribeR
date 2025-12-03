import logging
import time
from unittest.mock import Mock, patch, call

import pytest

from service.safe_paste_sendinput import (
    safe_clipboard_copy,
    safe_paste_text,
    is_paste_available
)


class TestSafeClipboardCopy:
    """クリップボードコピー機能のテストクラス"""

    @patch('service.safe_paste_sendinput.pyperclip.paste')
    @patch('service.safe_paste_sendinput.pyperclip.copy')
    @patch('service.safe_paste_sendinput.time.sleep')
    def test_safe_clipboard_copy_success_first_attempt(self, mock_sleep, mock_copy, mock_paste):
        """正常系: 1回目の試行で成功"""
        # Arrange
        test_text = "テストテキスト"
        mock_paste.return_value = test_text

        # Act
        result = safe_clipboard_copy(test_text)

        # Assert
        assert result is True
        mock_copy.assert_called_once_with(test_text)
        mock_paste.assert_called_once()
        mock_sleep.assert_called_once_with(0.05)

    @patch('service.safe_paste_sendinput.pyperclip.paste')
    @patch('service.safe_paste_sendinput.pyperclip.copy')
    @patch('service.safe_paste_sendinput.time.sleep')
    def test_safe_clipboard_copy_success_after_retry(self, mock_sleep, mock_copy, mock_paste):
        """正常系: 2回目の試行で成功"""
        # Arrange
        test_text = "テストテキスト"
        # 1回目は検証失敗、2回目は成功
        mock_paste.side_effect = ["違うテキスト", test_text]

        # Act
        result = safe_clipboard_copy(test_text)

        # Assert
        assert result is True
        assert mock_copy.call_count == 2
        assert mock_paste.call_count == 2
        # 初回のsleep + リトライ前のsleep + 成功後のsleep
        assert mock_sleep.call_count == 3

    @patch('service.safe_paste_sendinput.pyperclip.paste')
    @patch('service.safe_paste_sendinput.pyperclip.copy')
    @patch('service.safe_paste_sendinput.time.sleep')
    def test_safe_clipboard_copy_failure_max_retries(
        self, mock_sleep, mock_copy, mock_paste, caplog
    ):
        """異常系: 最大リトライ回数で失敗"""
        # Arrange
        caplog.set_level(logging.ERROR)
        test_text = "テストテキスト"
        mock_paste.return_value = "常に異なるテキスト"

        # Act
        result = safe_clipboard_copy(test_text)

        # Assert
        assert result is False
        assert mock_copy.call_count == 2  # max_retries = 2
        assert "クリップボードコピーが最大試行回数後に失敗しました" in caplog.text

    def test_safe_clipboard_copy_empty_text(self):
        """境界値: 空文字列のテキスト"""
        # Act
        result = safe_clipboard_copy("")

        # Assert
        assert result is False

    def test_safe_clipboard_copy_none_text(self):
        """異常系: Noneのテキスト"""
        # Act
        result = safe_clipboard_copy(None)

        # Assert
        assert result is False

    @patch('service.safe_paste_sendinput.pyperclip.paste')
    @patch('service.safe_paste_sendinput.pyperclip.copy')
    @patch('service.safe_paste_sendinput.time.sleep')
    def test_safe_clipboard_copy_exception_on_copy(
        self, mock_sleep, mock_copy, mock_paste, caplog
    ):
        """異常系: コピー時に例外発生"""
        # Arrange
        caplog.set_level(logging.ERROR)
        test_text = "テストテキスト"
        mock_copy.side_effect = Exception("コピーエラー")

        # Act
        result = safe_clipboard_copy(test_text)

        # Assert
        assert result is False
        assert "クリップボードコピー中にエラー" in caplog.text

    @patch('service.safe_paste_sendinput.pyperclip.paste')
    @patch('service.safe_paste_sendinput.pyperclip.copy')
    @patch('service.safe_paste_sendinput.time.sleep')
    def test_safe_clipboard_copy_exception_on_paste(
        self, mock_sleep, mock_copy, mock_paste, caplog
    ):
        """異常系: 検証ペースト時に例外発生"""
        # Arrange
        caplog.set_level(logging.ERROR)
        test_text = "テストテキスト"
        mock_paste.side_effect = Exception("ペーストエラー")

        # Act
        result = safe_clipboard_copy(test_text)

        # Assert
        assert result is False
        assert "クリップボードコピー中にエラー" in caplog.text

    @patch('service.safe_paste_sendinput.pyperclip.paste')
    @patch('service.safe_paste_sendinput.pyperclip.copy')
    @patch('service.safe_paste_sendinput.time.sleep')
    def test_safe_clipboard_copy_whitespace_text(self, mock_sleep, mock_copy, mock_paste):
        """境界値: 空白のみのテキスト"""
        # Arrange
        test_text = "   "
        mock_paste.return_value = test_text

        # Act
        result = safe_clipboard_copy(test_text)

        # Assert
        assert result is True
        mock_copy.assert_called_once_with(test_text)

    @patch('service.safe_paste_sendinput.pyperclip.paste')
    @patch('service.safe_paste_sendinput.pyperclip.copy')
    @patch('service.safe_paste_sendinput.time.sleep')
    def test_safe_clipboard_copy_large_text(self, mock_sleep, mock_copy, mock_paste):
        """境界値: 大きなテキスト"""
        # Arrange
        test_text = "あ" * 10000
        mock_paste.return_value = test_text

        # Act
        result = safe_clipboard_copy(test_text)

        # Assert
        assert result is True
        mock_copy.assert_called_once_with(test_text)

    @patch('service.safe_paste_sendinput.pyperclip.paste')
    @patch('service.safe_paste_sendinput.pyperclip.copy')
    @patch('service.safe_paste_sendinput.time.sleep')
    def test_safe_clipboard_copy_special_characters(self, mock_sleep, mock_copy, mock_paste):
        """正常系: 特殊文字を含むテキスト"""
        # Arrange
        test_text = "改行\n\tタブ\r\n特殊文字!@#$%^&*()"
        mock_paste.return_value = test_text

        # Act
        result = safe_clipboard_copy(test_text)

        # Assert
        assert result is True
        mock_copy.assert_called_once_with(test_text)

    @patch('service.safe_paste_sendinput.pyperclip.paste')
    @patch('service.safe_paste_sendinput.pyperclip.copy')
    @patch('service.safe_paste_sendinput.time.sleep')
    def test_safe_clipboard_copy_unicode_characters(self, mock_sleep, mock_copy, mock_paste):
        """正常系: Unicode文字を含むテキスト"""
        # Arrange
        test_text = "日本語🎉한글Émojis"
        mock_paste.return_value = test_text

        # Act
        result = safe_clipboard_copy(test_text)

        # Assert
        assert result is True
        mock_copy.assert_called_once_with(test_text)

    @patch('service.safe_paste_sendinput.pyperclip.paste')
    @patch('service.safe_paste_sendinput.pyperclip.copy')
    @patch('service.safe_paste_sendinput.time.sleep')
    def test_safe_clipboard_copy_logging_on_retry(self, mock_sleep, mock_copy, mock_paste, caplog):
        """ログ検証: リトライ時の警告ログ"""
        # Arrange
        caplog.set_level(logging.WARNING)
        test_text = "テストテキスト"
        mock_paste.side_effect = ["違うテキスト", test_text]

        # Act
        result = safe_clipboard_copy(test_text)

        # Assert
        assert result is True
        assert "クリップボードコピー検証失敗" in caplog.text

    @patch('service.safe_paste_sendinput.pyperclip.paste')
    @patch('service.safe_paste_sendinput.pyperclip.copy')
    @patch('service.safe_paste_sendinput.time.sleep')
    def test_safe_clipboard_copy_logging_on_success(self, mock_sleep, mock_copy, mock_paste, caplog):
        """ログ検証: 成功時の情報ログ"""
        # Arrange
        caplog.set_level(logging.INFO)
        test_text = "テストテキスト"
        mock_paste.return_value = test_text

        # Act
        result = safe_clipboard_copy(test_text)

        # Assert
        assert result is True
        assert "クリップボードコピー完了" in caplog.text

    @pytest.mark.parametrize("text,expected", [
        ("", False),
        (None, False),
        ("a", True),
        ("あいうえお", True),
        ("123456", True),
        ("\n\t", True),
    ])
    @patch('service.safe_paste_sendinput.pyperclip.paste')
    @patch('service.safe_paste_sendinput.pyperclip.copy')
    @patch('service.safe_paste_sendinput.time.sleep')
    def test_safe_clipboard_copy_parametrized(
        self, mock_sleep, mock_copy, mock_paste, text, expected
    ):
        """パラメータ化テスト: 様々なテキストパターン"""
        # Arrange
        mock_paste.return_value = text

        # Act
        result = safe_clipboard_copy(text)

        # Assert
        assert result is expected


class TestSafePasteText:
    """テキスト貼り付け機能のテストクラス"""

    @patch('service.safe_paste_sendinput.keyboard.send')
    @patch('service.safe_paste_sendinput.pyperclip.paste')
    @patch('service.safe_paste_sendinput.time.sleep')
    def test_safe_paste_text_success(self, mock_sleep, mock_paste, mock_send):
        """正常系: 貼り付け成功"""
        # Arrange
        mock_paste.return_value = "テストテキスト"

        # Act
        result = safe_paste_text()

        # Assert
        assert result is True
        mock_paste.assert_called_once()
        mock_send.assert_called_once_with('ctrl+v')
        mock_sleep.assert_called_once_with(0.1)

    @patch('service.safe_paste_sendinput.pyperclip.paste')
    def test_safe_paste_text_empty_clipboard(self, mock_paste, caplog):
        """異常系: クリップボードが空"""
        # Arrange
        caplog.set_level(logging.WARNING)
        mock_paste.return_value = ""

        # Act
        result = safe_paste_text()

        # Assert
        assert result is False
        assert "クリップボードが空です" in caplog.text

    @patch('service.safe_paste_sendinput.pyperclip.paste')
    def test_safe_paste_text_none_clipboard(self, mock_paste, caplog):
        """異常系: クリップボードがNone"""
        # Arrange
        caplog.set_level(logging.WARNING)
        mock_paste.return_value = None

        # Act
        result = safe_paste_text()

        # Assert
        assert result is False
        assert "クリップボードが空です" in caplog.text

    @patch('service.safe_paste_sendinput.keyboard.send')
    @patch('service.safe_paste_sendinput.pyperclip.paste')
    @patch('service.safe_paste_sendinput.time.sleep')
    def test_safe_paste_text_keyboard_exception(
        self, mock_sleep, mock_paste, mock_send, caplog
    ):
        """異常系: keyboard.sendで例外発生"""
        # Arrange
        caplog.set_level(logging.ERROR)
        mock_paste.return_value = "テストテキスト"
        mock_send.side_effect = Exception("キーボードエラー")

        # Act
        result = safe_paste_text()

        # Assert
        assert result is False
        assert "貼り付け操作に失敗" in caplog.text

    @patch('service.safe_paste_sendinput.pyperclip.paste')
    def test_safe_paste_text_paste_exception(self, mock_paste, caplog):
        """異常系: pyperclip.pasteで例外発生"""
        # Arrange
        caplog.set_level(logging.ERROR)
        mock_paste.side_effect = Exception("クリップボード読み取りエラー")

        # Act
        result = safe_paste_text()

        # Assert
        assert result is False
        assert "貼り付け操作に失敗" in caplog.text

    @patch('service.safe_paste_sendinput.keyboard.send')
    @patch('service.safe_paste_sendinput.pyperclip.paste')
    @patch('service.safe_paste_sendinput.time.sleep')
    def test_safe_paste_text_whitespace_content(self, mock_sleep, mock_paste, mock_send):
        """境界値: 空白のみのクリップボード内容"""
        # Arrange
        mock_paste.return_value = "   "

        # Act
        result = safe_paste_text()

        # Assert
        assert result is True
        mock_send.assert_called_once_with('ctrl+v')

    @patch('service.safe_paste_sendinput.keyboard.send')
    @patch('service.safe_paste_sendinput.pyperclip.paste')
    @patch('service.safe_paste_sendinput.time.sleep')
    def test_safe_paste_text_large_content(self, mock_sleep, mock_paste, mock_send):
        """境界値: 大きなクリップボード内容"""
        # Arrange
        mock_paste.return_value = "テスト" * 10000

        # Act
        result = safe_paste_text()

        # Assert
        assert result is True
        mock_send.assert_called_once_with('ctrl+v')

    @patch('service.safe_paste_sendinput.keyboard.send')
    @patch('service.safe_paste_sendinput.pyperclip.paste')
    @patch('service.safe_paste_sendinput.time.sleep')
    def test_safe_paste_text_special_characters(self, mock_sleep, mock_paste, mock_send):
        """正常系: 特殊文字を含む内容"""
        # Arrange
        mock_paste.return_value = "改行\n\tタブ\r\n特殊!@#"

        # Act
        result = safe_paste_text()

        # Assert
        assert result is True
        mock_send.assert_called_once_with('ctrl+v')

    @pytest.mark.parametrize("clipboard_content,expected", [
        ("テスト", True),
        ("", False),
        (None, False),
        ("あいうえお", True),
        ("   ", True),
        ("123", True),
    ])
    @patch('service.safe_paste_sendinput.keyboard.send')
    @patch('service.safe_paste_sendinput.pyperclip.paste')
    @patch('service.safe_paste_sendinput.time.sleep')
    def test_safe_paste_text_parametrized(
        self, mock_sleep, mock_paste, mock_send, clipboard_content, expected
    ):
        """パラメータ化テスト: 様々なクリップボード内容"""
        # Arrange
        mock_paste.return_value = clipboard_content

        # Act
        result = safe_paste_text()

        # Assert
        assert result is expected


class TestIsPasteAvailable:
    """貼り付け機能利用可否チェックのテストクラス"""

    def test_is_paste_available_success(self):
        """正常系: 常にTrueを返す"""
        # Act
        result = is_paste_available()

        # Assert
        assert result is True

    def test_is_paste_available_always_true(self):
        """正常系: keyboardライブラリが利用可能"""
        # Act
        # keyboardライブラリがインポートされていれば常にTrue
        result = is_paste_available()

        # Assert
        assert result is True

    def test_is_paste_available_multiple_calls(self):
        """正常系: 複数回呼び出しても常にTrue"""
        # Act
        results = [is_paste_available() for _ in range(5)]

        # Assert
        assert all(results)

    @patch('service.safe_paste_sendinput.logger.error')
    def test_is_paste_available_exception_handling(self, mock_logger_error):
        """異常系: 例外が発生した場合（現実的にはまれ）"""
        # Note: 現在の実装では常にTrueを返すため、
        # この関数内で例外が発生するシナリオは実際には存在しないが、
        # 将来の拡張性のためテストケースを用意

        # Act
        result = is_paste_available()

        # Assert
        assert result is True
        mock_logger_error.assert_not_called()


class TestIntegrationScenarios:
    """統合シナリオテスト"""

    @patch('service.safe_paste_sendinput.keyboard.send')
    @patch('service.safe_paste_sendinput.pyperclip.paste')
    @patch('service.safe_paste_sendinput.pyperclip.copy')
    @patch('service.safe_paste_sendinput.time.sleep')
    def test_full_copy_paste_workflow(self, mock_sleep, mock_copy, mock_paste, mock_send):
        """正常系: コピーから貼り付けまでの完全なワークフロー"""
        # Arrange
        test_text = "統合テストテキスト"
        mock_paste.side_effect = [test_text, test_text]  # コピー検証用とペースト前チェック用

        # Act - コピー
        copy_result = safe_clipboard_copy(test_text)

        # Assert - コピー成功
        assert copy_result is True
        mock_copy.assert_called_once_with(test_text)

        # Act - 貼り付け
        paste_result = safe_paste_text()

        # Assert - 貼り付け成功
        assert paste_result is True
        mock_send.assert_called_once_with('ctrl+v')

    @patch('service.safe_paste_sendinput.keyboard.send')
    @patch('service.safe_paste_sendinput.pyperclip.paste')
    @patch('service.safe_paste_sendinput.pyperclip.copy')
    @patch('service.safe_paste_sendinput.time.sleep')
    def test_copy_failure_prevents_paste(self, mock_sleep, mock_copy, mock_paste, mock_send):
        """異常系: コピー失敗時は貼り付けを実行しない"""
        # Arrange
        test_text = "テストテキスト"
        mock_copy.side_effect = Exception("コピー失敗")

        # Act - コピー失敗
        copy_result = safe_clipboard_copy(test_text)

        # Assert - コピー失敗
        assert copy_result is False

        # このシナリオでは貼り付けは実行されない
        # （実際のアプリケーションではコピー成功を確認してから貼り付けを呼ぶ）
        mock_send.assert_not_called()

    def test_paste_availability_check_workflow(self):
        """正常系: 貼り付け機能の利用可否確認ワークフロー"""
        # Act
        is_available = is_paste_available()

        # Assert
        assert is_available is True

        # 利用可能な場合のみ実際の操作に進む
        if is_available:
            with patch('service.safe_paste_sendinput.keyboard.send'), \
                 patch('service.safe_paste_sendinput.pyperclip.paste', return_value="test"), \
                 patch('service.safe_paste_sendinput.time.sleep'):
                result = safe_paste_text()
                assert result is True

    @patch('service.safe_paste_sendinput.keyboard.send')
    @patch('service.safe_paste_sendinput.pyperclip.paste')
    @patch('service.safe_paste_sendinput.pyperclip.copy')
    @patch('service.safe_paste_sendinput.time.sleep')
    def test_error_recovery_workflow(self, mock_sleep, mock_copy, mock_paste, mock_send, caplog):
        """異常系: エラーからの回復ワークフロー"""
        # Arrange
        caplog.set_level(logging.ERROR)
        test_text = "テストテキスト"

        # 1回目のコピーは2回とも失敗
        mock_copy.side_effect = [Exception("一時的なエラー"), Exception("一時的なエラー"), None]
        mock_paste.side_effect = [test_text]

        # Act - 1回目のコピー失敗（2回試行して両方失敗）
        result1 = safe_clipboard_copy(test_text)
        assert result1 is False

        # リトライ（2回目のコピー成功）
        mock_paste.side_effect = [test_text, test_text]
        result2 = safe_clipboard_copy(test_text)

        # Assert - リトライ後成功
        assert result2 is True
        assert mock_copy.call_count == 3  # 1回目失敗(2回試行) + 2回目成功(1回)


class TestPerformance:
    """パフォーマンステスト"""

    @patch('service.safe_paste_sendinput.pyperclip.paste')
    @patch('service.safe_paste_sendinput.pyperclip.copy')
    @patch('service.safe_paste_sendinput.time.sleep')
    def test_large_text_copy_performance(self, mock_sleep, mock_copy, mock_paste):
        """パフォーマンス: 大きなテキストのコピー"""
        # Arrange
        large_text = "あ" * 100000  # 100,000文字
        mock_paste.return_value = large_text

        # Act
        start_time = time.time()
        result = safe_clipboard_copy(large_text)
        end_time = time.time()

        # Assert
        assert result is True
        # モック使用時は実際のクリップボード操作がないため、非常に高速
        assert (end_time - start_time) < 1.0

    @patch('service.safe_paste_sendinput.keyboard.send')
    @patch('service.safe_paste_sendinput.pyperclip.paste')
    @patch('service.safe_paste_sendinput.time.sleep')
    def test_paste_operation_timing(self, mock_sleep, mock_paste, mock_send):
        """パフォーマンス: 貼り付け操作のタイミング"""
        # Arrange
        mock_paste.return_value = "テストテキスト"

        # Act
        start_time = time.time()
        result = safe_paste_text()
        end_time = time.time()

        # Assert
        assert result is True
        # sleep(0.1)が呼ばれることを確認
        mock_sleep.assert_called_once_with(0.1)
        assert (end_time - start_time) < 1.0


class TestEdgeCases:
    """エッジケーステスト"""

    @patch('service.safe_paste_sendinput.pyperclip.paste')
    @patch('service.safe_paste_sendinput.pyperclip.copy')
    @patch('service.safe_paste_sendinput.time.sleep')
    def test_copy_with_zero_length_string(self, mock_sleep, mock_copy, mock_paste):
        """エッジケース: 長さ0の文字列"""
        # Act
        result = safe_clipboard_copy("")

        # Assert
        assert result is False
        mock_copy.assert_not_called()

    @patch('service.safe_paste_sendinput.pyperclip.paste')
    @patch('service.safe_paste_sendinput.pyperclip.copy')
    @patch('service.safe_paste_sendinput.time.sleep')
    def test_copy_with_newlines_only(self, mock_sleep, mock_copy, mock_paste):
        """エッジケース: 改行のみのテキスト"""
        # Arrange
        text = "\n\n\n"
        mock_paste.return_value = text

        # Act
        result = safe_clipboard_copy(text)

        # Assert
        assert result is True
        mock_copy.assert_called_once_with(text)

    @patch('service.safe_paste_sendinput.keyboard.send')
    @patch('service.safe_paste_sendinput.pyperclip.paste')
    @patch('service.safe_paste_sendinput.time.sleep')
    def test_paste_with_newline_content(self, mock_sleep, mock_paste, mock_send):
        """エッジケース: 改行を含むクリップボード内容"""
        # Arrange
        mock_paste.return_value = "行1\n行2\n行3"

        # Act
        result = safe_paste_text()

        # Assert
        assert result is True
        mock_send.assert_called_once_with('ctrl+v')

    @patch('service.safe_paste_sendinput.pyperclip.paste')
    @patch('service.safe_paste_sendinput.pyperclip.copy')
    @patch('service.safe_paste_sendinput.time.sleep')
    def test_copy_with_mixed_encoding(self, mock_sleep, mock_copy, mock_paste):
        """エッジケース: 混合エンコーディングの文字列"""
        # Arrange
        text = "ASCII文字と日本語と한글とÉmojis🎉が混在"
        mock_paste.return_value = text

        # Act
        result = safe_clipboard_copy(text)

        # Assert
        assert result is True
        mock_copy.assert_called_once_with(text)
