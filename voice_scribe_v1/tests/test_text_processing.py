import logging
import os
import time
from unittest.mock import Mock, patch, mock_open, call

import pytest

from service.text_processing import (
    process_punctuation,
    get_replacements_path,
    load_replacements,
    replace_text,
    copy_and_paste_transcription,
    emergency_clipboard_recovery,
    initialize_text_processing
)


class TestProcessPunctuation:
    """句読点処理のテストクラス"""

    def test_process_punctuation_with_punctuation_true(self):
        """正常系: use_punctuation=Trueの場合、句読点をそのまま保持"""
        # Arrange
        text = "これは。テスト、です。"
        use_punctuation = True

        # Act
        result = process_punctuation(text, use_punctuation)

        # Assert
        assert result == "これは。テスト、です。"
        assert "。" in result
        assert "、" in result

    def test_process_punctuation_with_punctuation_false(self):
        """正常系: use_punctuation=Falseの場合、句読点を削除"""
        # Arrange
        text = "これは。テスト、です。"
        use_punctuation = False

        # Act
        result = process_punctuation(text, use_punctuation)

        # Assert
        assert result == "これはテストです"
        assert "。" not in result
        assert "、" not in result

    def test_process_punctuation_empty_text(self):
        """境界値: 空文字列"""
        # Arrange
        text = ""
        use_punctuation = False

        # Act
        result = process_punctuation(text, use_punctuation)

        # Assert
        assert result == ""

    def test_process_punctuation_only_punctuation(self):
        """境界値: 句読点のみの文字列"""
        # Arrange
        text = "。、。、"
        use_punctuation = False

        # Act
        result = process_punctuation(text, use_punctuation)

        # Assert
        assert result == ""

    def test_process_punctuation_no_punctuation(self):
        """正常系: 句読点を含まない文字列"""
        # Arrange
        text = "これはテストです"
        use_punctuation = False

        # Act
        result = process_punctuation(text, use_punctuation)

        # Assert
        assert result == "これはテストです"

    def test_process_punctuation_multiple_types(self):
        """正常系: 複数の句読点を含む"""
        # Arrange
        text = "一つ目。二つ目、三つ目。最後、です。"
        use_punctuation = False

        # Act
        result = process_punctuation(text, use_punctuation)

        # Assert
        assert result == "一つ目二つ目三つ目最後です"

    def test_process_punctuation_none_text(self, caplog):
        """異常系: Noneが渡された場合"""
        # Arrange
        caplog.set_level(logging.ERROR)
        text = None
        use_punctuation = False

        # Act
        result = process_punctuation(text, use_punctuation)

        # Assert
        assert result is None
        assert "句読点処理中にタイプエラー" in caplog.text

    @pytest.mark.parametrize("use_punctuation,input_text,expected", [
        (True, "テスト。文字、起こし", "テスト。文字、起こし"),
        (False, "テスト。文字、起こし", "テスト文字起こし"),
        (False, "。、。、", ""),
        (True, "", ""),
        (False, "句読点なし", "句読点なし"),
    ])
    def test_process_punctuation_parametrized(self, use_punctuation, input_text, expected):
        """パラメータ化テスト: 句読点処理の組み合わせ"""
        # Act
        result = process_punctuation(input_text, use_punctuation)

        # Assert
        assert result == expected


class TestGetReplacementsPath:
    """置換ルールファイルパス取得のテストクラス"""

    @patch('service.text_processing.sys.frozen', True, create=True)
    @patch('service.text_processing.sys._MEIPASS', '/mocked/meipass', create=True)
    def test_get_replacements_path_frozen_executable(self):
        """正常系: PyInstallerでビルドされた実行ファイルの場合"""
        # Act
        result = get_replacements_path()

        # Assert
        expected_path = os.path.join('/mocked/meipass', 'replacements.txt')
        assert result == expected_path

    @patch('service.text_processing.sys.frozen', False, create=True)
    @patch('service.text_processing.os.path.dirname')
    def test_get_replacements_path_script_mode(self, mock_dirname):
        """正常系: 通常のPythonスクリプトとして実行される場合"""
        # Arrange
        mock_dirname.return_value = '/script/directory'

        # Act
        result = get_replacements_path()

        # Assert
        expected_path = os.path.join('/script/directory', 'replacements.txt')
        assert result == expected_path
        mock_dirname.assert_called_once()

    @patch('service.text_processing.sys.frozen', None, create=True)
    @patch('service.text_processing.os.path.dirname')
    def test_get_replacements_path_no_frozen_attribute(self, mock_dirname):
        """境界値: frozenアトリビュートが存在しない場合"""
        # Arrange
        mock_dirname.return_value = '/fallback/directory'

        # Act
        result = get_replacements_path()

        # Assert
        expected_path = os.path.join('/fallback/directory', 'replacements.txt')
        assert result == expected_path


class TestLoadReplacements:
    """置換ルール読み込みのテストクラス"""

    @patch('service.text_processing.get_replacements_path')
    def test_load_replacements_success_normal_format(self, mock_get_path):
        """正常系: 標準フォーマットの置換ルールファイル"""
        # Arrange
        mock_get_path.return_value = 'test_replacements.txt'
        file_content = "旧文字列1,新文字列1\n旧文字列2,新文字列2\n\n有効行,値\n"

        with patch('builtins.open', mock_open(read_data=file_content)):
            # Act
            result = load_replacements()

            # Assert
            expected = {
                '旧文字列1': '新文字列1',
                '旧文字列2': '新文字列2',
                '有効行': '値'
            }
            assert result == expected

    @patch('service.text_processing.get_replacements_path')
    def test_load_replacements_success_with_whitespace(self, mock_get_path):
        """正常系: 空白を含む置換ルール"""
        # Arrange
        mock_get_path.return_value = 'test_replacements.txt'
        file_content = "  旧文字列  ,  新文字列  \n前後空白,削除される\n"
        
        with patch('builtins.open', mock_open(read_data=file_content)):
            # Act
            result = load_replacements()

            # Assert
            expected = {
                '旧文字列': '新文字列',
                '前後空白': '削除される'
            }
            assert result == expected

    @patch('service.text_processing.get_replacements_path')
    def test_load_replacements_empty_file(self, mock_get_path):
        """境界値: 空ファイル"""
        # Arrange
        mock_get_path.return_value = 'empty_replacements.txt'
        
        with patch('builtins.open', mock_open()):
            # Act
            result = load_replacements()

            # Assert
            assert result == {}

    @patch('service.text_processing.get_replacements_path')
    def test_load_replacements_only_empty_lines(self, mock_get_path):
        """境界値: 空行のみのファイル"""
        # Arrange
        mock_get_path.return_value = 'empty_lines.txt'
        file_content = "\n\n   \n\t\n"
        
        with patch('builtins.open', mock_open(read_data=file_content)):
            # Act
            result = load_replacements()

            # Assert
            assert result == {}

    @patch('service.text_processing.get_replacements_path')
    def test_load_replacements_invalid_format_lines(self, mock_get_path, caplog):
        """異常系: 無効なフォーマットの行を含む"""
        # Arrange
        caplog.set_level(logging.ERROR)
        mock_get_path.return_value = 'invalid_replacements.txt'
        file_content = "正常,置換\n無効な行\nカンマなし\n正常2,置換2\n"
        
        with patch('builtins.open', mock_open(read_data=file_content)):
            # Act
            result = load_replacements()

            # Assert
            expected = {
                '正常': '置換',
                '正常2': '置換2'
            }
            assert result == expected
            assert "無効な行があります" in caplog.text

    @patch('service.text_processing.get_replacements_path')
    def test_load_replacements_simple_comma_pair(self, mock_get_path):
        """正常系: 単純なカンマペア"""
        # Arrange
        mock_get_path.return_value = 'simple_comma.txt'
        file_content = "旧,新\n"

        with patch('builtins.open', mock_open(read_data=file_content)):
            # Act
            result = load_replacements()

            # Assert
            expected = {'旧': '新'}
            assert result == expected

    @patch('service.text_processing.get_replacements_path')
    def test_load_replacements_file_not_found(self, mock_get_path, caplog):
        """異常系: ファイルが存在しない"""
        # Arrange
        caplog.set_level(logging.ERROR)
        mock_get_path.return_value = 'nonexistent.txt'
        
        with patch('builtins.open', side_effect=FileNotFoundError("File not found")):
            # Act
            result = load_replacements()

            # Assert
            assert result == {}
            assert "置換ファイルの読み込み中にエラーが発生しました" in caplog.text

    @patch('service.text_processing.get_replacements_path')
    def test_load_replacements_permission_error(self, mock_get_path, caplog):
        """異常系: ファイルアクセス権限エラー"""
        # Arrange
        caplog.set_level(logging.ERROR)
        mock_get_path.return_value = 'protected.txt'
        
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            # Act
            result = load_replacements()

            # Assert
            assert result == {}
            assert "置換ファイルの読み込み中にエラーが発生しました" in caplog.text

    @patch('service.text_processing.get_replacements_path')
    def test_load_replacements_unexpected_error(self, mock_get_path, caplog):
        """異常系: 予期しないエラー"""
        # Arrange
        caplog.set_level(logging.ERROR)
        mock_get_path.return_value = 'problem.txt'
        
        with patch('builtins.open', side_effect=RuntimeError("Unexpected error")):
            # Act
            result = load_replacements()

            # Assert
            assert result == {}
            assert "予期せぬエラーが発生しました" in caplog.text

    @patch('service.text_processing.get_replacements_path')
    def test_load_replacements_unicode_content(self, mock_get_path):
        """正常系: Unicode文字を含む置換ルール"""
        # Arrange
        mock_get_path.return_value = 'unicode_replacements.txt'
        file_content = "😀,😊\n漢字,ひらがな\n한글,カタカナ\n"
        
        with patch('builtins.open', mock_open(read_data=file_content)):
            # Act
            result = load_replacements()

            # Assert
            expected = {
                '😀': '😊',
                '漢字': 'ひらがな',
                '한글': 'カタカナ'
            }
            assert result == expected

    @patch('service.text_processing.get_replacements_path')
    def test_load_replacements_logging_verification(self, mock_get_path, caplog):
        """ログ出力の確認"""
        # Arrange
        caplog.set_level(logging.INFO)
        mock_get_path.return_value = 'test.txt'
        file_content = "テスト1,結果1\nテスト2,結果2\n"
        
        with patch('builtins.open', mock_open(read_data=file_content)):
            # Act
            result = load_replacements()

            # Assert
            assert len(result) == 2
            assert "置換ルールの総数: 2" in caplog.text


class TestReplaceText:
    """テキスト置換のテストクラス"""

    def test_replace_text_success_single_replacement(self):
        """正常系: 単一の置換処理"""
        # Arrange
        text = "これはテストです"
        replacements = {"テスト": "試験"}

        # Act
        result = replace_text(text, replacements)

        # Assert
        assert result == "これは試験です"

    def test_replace_text_success_multiple_replacements(self):
        """正常系: 複数の置換処理"""
        # Arrange
        text = "テストとサンプルを実行"
        replacements = {
            "テスト": "試験",
            "サンプル": "例",
            "実行": "処理"
        }

        # Act
        result = replace_text(text, replacements)

        # Assert
        assert result == "試験と例を処理"

    def test_replace_text_success_multiple_occurrences(self):
        """正常系: 同じ単語の複数回置換"""
        # Arrange
        text = "テストとテストのテスト"
        replacements = {"テスト": "試験"}

        # Act
        result = replace_text(text, replacements)

        # Assert
        assert result == "試験と試験の試験"

    def test_replace_text_no_matches(self):
        """正常系: 置換対象が見つからない場合"""
        # Arrange
        text = "置換されないテキスト"
        replacements = {"存在しない": "置換"}

        # Act
        result = replace_text(text, replacements)

        # Assert
        assert result == "置換されないテキスト"

    def test_replace_text_empty_text(self):
        """境界値: 空文字列のテキスト"""
        # Arrange
        text = ""
        replacements = {"何か": "置換"}

        # Act
        result = replace_text(text, replacements)

        # Assert
        assert result == ""

    def test_replace_text_none_text(self):
        """異常系: Noneのテキスト"""
        # Arrange
        replacements = {"何か": "置換"}

        # Act
        result = replace_text(None, replacements)

        # Assert
        assert result == ""

    def test_replace_text_empty_replacements(self):
        """境界値: 空の置換辞書"""
        # Arrange
        text = "置換ルールがないテキスト"
        replacements = {}

        # Act
        result = replace_text(text, replacements)

        # Assert
        assert result == "置換ルールがないテキスト"

    def test_replace_text_none_replacements(self):
        """異常系: Noneの置換辞書"""
        # Arrange
        text = "テストテキスト"

        # Act
        result = replace_text(text, None)

        # Assert
        assert result == "テストテキスト"

    def test_replace_text_overlapping_replacements(self):
        """正常系: 重複する置換パターン"""
        # Arrange
        text = "ABCABC"
        replacements = {
            "ABC": "XYZ",
            "BC": "YZ"
        }

        # Act
        result = replace_text(text, replacements)

        # Assert
        # Pythonの辞書は順序を保持するので、最初のルールが適用される
        assert result == "XYZXYZ"

    def test_replace_text_case_sensitive(self):
        """正常系: 大文字小文字の区別"""
        # Arrange
        text = "testとTESTとTest"
        replacements = {"test": "試験"}

        # Act
        result = replace_text(text, replacements)

        # Assert
        assert result == "試験とTESTとTest"

    def test_replace_text_special_characters(self):
        """正常系: 特殊文字の置換"""
        # Arrange
        text = "記号!@#$%と数字123"
        replacements = {
            "!@#$%": "特殊文字",
            "123": "数値"
        }

        # Act
        result = replace_text(text, replacements)

        # Assert
        assert result == "記号特殊文字と数字数値"

    def test_replace_text_unicode_characters(self):
        """正常系: Unicode文字の置換"""
        # Arrange
        text = "絵文字😀と韓国語한글"
        replacements = {
            "😀": "😊",
            "한글": "ハングル"
        }

        # Act
        result = replace_text(text, replacements)

        # Assert
        assert result == "絵文字😊と韓国語ハングル"

    def test_replace_text_exception_handling(self, caplog):
        """異常系: 置換処理中の例外"""
        # Arrange
        caplog.set_level(logging.ERROR)
        text = "テストテキスト"
        
        # 置換処理でエラーを発生させるためのモック
        mock_replacements = Mock()
        mock_replacements.items.side_effect = Exception("置換処理エラー")

        # Act
        result = replace_text(text, mock_replacements)

        # Assert
        assert result == "テストテキスト"  # 元のテキストが返される
        assert "テキスト置換中にエラーが発生" in caplog.text

    @pytest.mark.parametrize("text,replacements,expected", [
        ("", {}, ""),
        ("a", {"a": "b"}, "b"),
        ("abc", {"b": "x"}, "axc"),
        ("aaaa", {"aa": "x"}, "xx"),
        ("テスト", {"テスト": ""}, ""),
        ("前置換後", {"置換": "REPLACE"}, "前REPLACE後"),
    ])
    def test_replace_text_parametrized(self, text, replacements, expected):
        """パラメータ化テスト: 様々な置換パターン"""
        # Act
        result = replace_text(text, replacements)

        # Assert
        assert result == expected


class TestCopyAndPasteTranscription:
    """コピー&ペースト処理のテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.mock_config = {
            'CLIPBOARD': {
                'PASTE_DELAY': 0.1
            }
        }
        self.mock_replacements = {
            "テスト": "試験",
            "サンプル": "例"
        }

    @patch('service.text_processing.replace_text')
    @patch('service.text_processing.safe_clipboard_copy')
    @patch('service.text_processing.safe_paste_text')
    @patch('service.text_processing.threading.Thread')
    def test_copy_and_paste_transcription_success(
        self, mock_thread, mock_paste, mock_copy, mock_replace
    ):
        """正常系: 正常なコピー&ペースト処理"""
        # Arrange
        text = "テストテキスト"
        replaced_text = "試験テキスト"
        
        mock_replace.return_value = replaced_text
        mock_copy.return_value = True
        mock_paste.return_value = True
        
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance

        # Act
        copy_and_paste_transcription(text, self.mock_replacements, self.mock_config)

        # Assert
        mock_replace.assert_called_once_with(text, self.mock_replacements)
        mock_copy.assert_called_once_with(replaced_text)
        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()

    @patch('service.text_processing.replace_text')
    def test_copy_and_paste_transcription_empty_text(self, mock_replace):
        """境界値: 空のテキスト"""
        # Act & Assert
        copy_and_paste_transcription("", self.mock_replacements, self.mock_config)
        
        # replace_textが呼ばれないことを確認
        mock_replace.assert_not_called()

    @patch('service.text_processing.replace_text')
    def test_copy_and_paste_transcription_none_text(self, mock_replace):
        """異常系: Noneのテキスト"""
        # Act & Assert
        copy_and_paste_transcription(None, self.mock_replacements, self.mock_config)
        
        # replace_textが呼ばれないことを確認
        mock_replace.assert_not_called()

    @patch('service.text_processing.replace_text')
    @patch('service.text_processing.safe_clipboard_copy')
    def test_copy_and_paste_transcription_clipboard_copy_failure(
        self, mock_copy, mock_replace
    ):
        """異常系: クリップボードコピー失敗"""
        # Arrange
        text = "テストテキスト"
        replaced_text = "試験テキスト"
        
        mock_replace.return_value = replaced_text
        mock_copy.return_value = False

        # Act & Assert
        with pytest.raises(Exception, match="クリップボードへのコピーに失敗しました"):
            copy_and_paste_transcription(text, self.mock_replacements, self.mock_config)

    @patch('service.text_processing.replace_text')
    @patch('service.text_processing.safe_clipboard_copy')
    def test_copy_and_paste_transcription_empty_replaced_text(
            self, mock_copy, mock_replace
    ):
        """境界値: 置換結果が空文字列（正常終了する）"""
        # Arrange
        text = "テストテキスト"

        mock_replace.return_value = ""
        mock_copy.return_value = True

        # Act
        copy_and_paste_transcription(text, self.mock_replacements, self.mock_config)

        # Assert
        mock_replace.assert_called_once_with(text, self.mock_replacements)
        mock_copy.assert_not_called()

    @patch('service.text_processing.replace_text')
    @patch('service.text_processing.safe_clipboard_copy')
    @patch('service.text_processing.safe_paste_text')
    @patch('service.text_processing.time.sleep')
    def test_copy_and_paste_transcription_delayed_paste_execution(
        self, mock_sleep, mock_paste, mock_copy, mock_replace
    ):
        """正常系: 遅延ペースト処理の実行確認"""
        # Arrange
        text = "テストテキスト"
        replaced_text = "試験テキスト"
        
        mock_replace.return_value = replaced_text
        mock_copy.return_value = True
        mock_paste.return_value = True

        # threading.Threadの代わりに直接実行する
        with patch('service.text_processing.threading.Thread') as mock_thread:
            def immediate_execute(target=None, **kwargs):
                # スレッドの代わりに即座に実行
                target()
                thread_mock = Mock()
                return thread_mock
            
            mock_thread.side_effect = immediate_execute

            # Act
            copy_and_paste_transcription(text, self.mock_replacements, self.mock_config)

            # Assert
            mock_sleep.assert_called_once_with(0.2)
            mock_paste.assert_called_once()

    @patch('service.text_processing.replace_text')
    @patch('service.text_processing.safe_clipboard_copy')
    def test_copy_and_paste_transcription_general_exception(
        self, mock_copy, mock_replace, caplog
    ):
        """異常系: 一般的な例外処理"""
        # Arrange
        caplog.set_level(logging.ERROR)
        text = "テストテキスト"
        
        mock_replace.side_effect = Exception("予期しないエラー")

        # Act & Assert
        with pytest.raises(Exception):
            copy_and_paste_transcription(text, self.mock_replacements, self.mock_config)

        assert "コピー&ペースト処理でエラー" in caplog.text


class TestEmergencyClipboardRecovery:
    """クリップボード復旧のテストクラス"""

    @patch('service.text_processing.pyperclip.copy')
    @patch('service.text_processing.pyperclip.paste')
    @patch('service.text_processing.time.sleep')
    def test_emergency_clipboard_recovery_success(self, mock_sleep, mock_paste, mock_copy):
        """正常系: クリップボード復旧成功"""
        # Arrange
        mock_paste.return_value = "test"

        # Act
        result = emergency_clipboard_recovery()

        # Assert
        assert result is True
        assert mock_copy.call_count == 2  # 空文字とテスト文字で2回
        mock_copy.assert_has_calls([call(""), call("test")])
        mock_paste.assert_called_once()
        assert mock_sleep.call_count == 2  # 各コピー後にsleep

    @patch('service.text_processing.pyperclip.copy')
    @patch('service.text_processing.pyperclip.paste')
    def test_emergency_clipboard_recovery_paste_mismatch(self, mock_paste, mock_copy):
        """異常系: ペースト結果が期待値と異なる"""
        # Arrange
        mock_paste.return_value = "unexpected"  # "test"ではない値

        # Act
        result = emergency_clipboard_recovery()

        # Assert
        assert result is False

    @patch('service.text_processing.pyperclip.copy')
    def test_emergency_clipboard_recovery_exception(self, mock_copy, caplog):
        """異常系: クリップボード操作での例外"""
        # Arrange
        caplog.set_level(logging.ERROR)
        mock_copy.side_effect = Exception("クリップボードエラー")

        # Act
        result = emergency_clipboard_recovery()

        # Assert
        assert result is False
        assert "クリップボード復旧中にエラー" in caplog.text


class TestInitializeModule:
    """モジュール初期化のテストクラス"""

    @patch('service.text_processing.is_paste_available')
    @patch('service.text_processing.emergency_clipboard_recovery')
    def test_initialize_module_success(self, mock_recovery, mock_paste_available):
        """正常系: モジュール初期化成功"""
        # Arrange
        mock_paste_available.return_value = True
        mock_recovery.return_value = True

        # Act
        initialize_text_processing()

        # Assert
        mock_paste_available.assert_called_once()
        mock_recovery.assert_called_once()

    @patch('service.text_processing.is_paste_available')
    @patch('service.text_processing.emergency_clipboard_recovery')
    def test_initialize_module_paste_unavailable(
        self, mock_recovery, mock_paste_available, caplog
    ):
        """異常系: ペースト機能が利用不可"""
        # Arrange
        caplog.set_level(logging.ERROR)
        mock_paste_available.return_value = False
        mock_recovery.return_value = True

        # Act
        initialize_text_processing()

        # Assert
        assert "貼り付け機能初期化失敗" in caplog.text

    @patch('service.text_processing.is_paste_available')
    @patch('service.text_processing.emergency_clipboard_recovery')
    def test_initialize_module_recovery_failure(
        self, mock_recovery, mock_paste_available, caplog
    ):
        """異常系: クリップボード復旧失敗"""
        # Arrange
        caplog.set_level(logging.WARNING)
        mock_paste_available.return_value = True
        mock_recovery.return_value = False

        # Act
        initialize_text_processing()

        # Assert
        assert "クリップボード初期化テストに失敗しました" in caplog.text

    @patch('service.text_processing.is_paste_available')
    def test_initialize_module_exception(self, mock_paste_available, caplog):
        """異常系: モジュール初期化での例外"""
        # Arrange
        caplog.set_level(logging.ERROR)
        mock_paste_available.side_effect = Exception("初期化エラー")

        # Act
        initialize_text_processing()

        # Assert
        assert "モジュール初期化中にエラー" in caplog.text


class TestIntegrationScenarios:
    """統合シナリオテスト"""

    def test_full_text_processing_workflow(self):
        """正常系: テキスト処理の完全なワークフロー"""
        # Arrange
        original_text = "これはテストとサンプルです"
        replacements = {
            "テスト": "試験",
            "サンプル": "例"
        }
        config = {
            'CLIPBOARD': {
                'PASTE_DELAY': 0.05
            }
        }

        # 置換処理のテスト
        replaced_text = replace_text(original_text, replacements)
        assert replaced_text == "これは試験と例です"

        # クリップボード操作のモック化
        with patch('service.text_processing.safe_clipboard_copy') as mock_copy, \
             patch('service.text_processing.safe_paste_text') as mock_paste, \
             patch('service.text_processing.threading.Thread') as mock_thread:
            
            mock_copy.return_value = True
            mock_paste.return_value = True
            mock_thread_instance = Mock()
            mock_thread.return_value = mock_thread_instance

            # Act
            copy_and_paste_transcription(original_text, replacements, config)

            # Assert
            mock_copy.assert_called_once_with("これは試験と例です")
            mock_thread.assert_called_once()
            mock_thread_instance.start.assert_called_once()

    @patch('service.text_processing.get_replacements_path')
    def test_load_and_apply_replacements_workflow(self, mock_get_path):
        """統合テスト: 置換ルール読み込みから適用まで"""
        # Arrange
        mock_get_path.return_value = 'test.txt'
        file_content = "旧単語,新単語\n古い表現,新しい表現\n"
        test_text = "旧単語と古い表現を含むテキスト"

        with patch('builtins.open', mock_open(read_data=file_content)):
            # Act
            replacements = load_replacements()
            result = replace_text(test_text, replacements)

            # Assert
            assert len(replacements) == 2
            assert result == "新単語と新しい表現を含むテキスト"

    def test_error_resilience_workflow(self, caplog):
        """異常系: エラー耐性のテスト"""
        # Arrange
        caplog.set_level(logging.ERROR)

        # 置換ルール読み込みエラー
        with patch('service.text_processing.get_replacements_path') as mock_path:
            mock_path.return_value = 'nonexistent.txt'
            with patch('builtins.open', side_effect=FileNotFoundError()):
                replacements = load_replacements()
                assert replacements == {}

        # テキスト置換でエラーが発生した場合でも元のテキストを返す
        problematic_replacements = Mock()
        problematic_replacements.items.side_effect = Exception("置換エラー")
        
        result = replace_text("テストテキスト", problematic_replacements)
        assert result == "テストテキスト"

        # ログにエラーが記録されていることを確認
        assert "置換ファイルの読み込み中にエラーが発生しました" in caplog.text
        assert "テキスト置換中にエラーが発生" in caplog.text


# パフォーマンステスト
class TestPerformance:
    """パフォーマンステスト"""

    def test_large_text_replacement_performance(self):
        """大きなテキストの置換処理性能"""
        # Arrange
        large_text = "テスト " * 10000  # 10,000回繰り返し
        replacements = {"テスト": "試験"}

        # Act
        start_time = time.time()
        result = replace_text(large_text, replacements)
        end_time = time.time()

        # Assert
        assert "試験" in result
        assert "テスト" not in result
        assert (end_time - start_time) < 1.0  # 1秒以内で完了

    def test_many_replacements_performance(self):
        """多数の置換ルールの処理性能"""
        # Arrange
        text = "文字列1 文字列2 文字列3 " * 100
        replacements = {f"文字列{i}": f"置換{i}" for i in range(1, 101)}  # 100個の置換ルール

        # Act
        start_time = time.time()
        result = replace_text(text, replacements)
        end_time = time.time()

        # Assert
        assert "置換1" in result
        assert "文字列1" not in result
        assert (end_time - start_time) < 1.0  # 1秒以内で完了


# モックとスレッドのテスト
class TestThreadingSafety:
    """スレッドセーフティのテスト"""

    @patch('service.text_processing.threading.Thread')
    def test_concurrent_copy_paste_operations(self, mock_thread):
        """並行コピー&ペースト操作のテスト"""
        # Arrange
        config = {'CLIPBOARD': {'PASTE_DELAY': 0.01}}
        replacements = {"テスト": "試験"}
        
        # スレッドの動作をシミュレート
        threads_created = []
        
        def capture_thread(*args, **kwargs):
            thread_mock = Mock()
            threads_created.append((args, kwargs))
            return thread_mock
        
        mock_thread.side_effect = capture_thread

        with patch('service.text_processing.safe_clipboard_copy', return_value=True):
            # Act
            copy_and_paste_transcription("テスト1", replacements, config)
            copy_and_paste_transcription("テスト2", replacements, config)

            # Assert
            assert len(threads_created) == 2
            assert mock_thread.call_count == 2
