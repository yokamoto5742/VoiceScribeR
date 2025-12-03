import configparser
import logging
import os
import tkinter as tk
from tkinter import messagebox, ttk
from unittest.mock import Mock, MagicMock, patch, mock_open

import pytest

from service.replacements_editor import ReplacementsEditor


def create_mock_text_widget():
    """辞書のように動作するMockTextWidgetを作成するヘルパー関数"""
    mock_widget = MagicMock()
    return mock_widget


class TestReplacementsEditorInit:
    """ReplacementsEditor初期化のテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.mock_parent = Mock(spec=tk.Tk)
        self.mock_config = {
            'PATHS': {
                'replacements_file': 'C:/test/replacements.txt'
            },
            'EDITOR': {
                'width': '500',
                'height': '800',
                'font_name': 'MS Gothic',
                'font_size': '12'
            }
        }

    @patch('service.replacements_editor.tk.Toplevel')
    @patch('service.replacements_editor.tk.Text')
    @patch('service.replacements_editor.ttk.Scrollbar')
    @patch('service.replacements_editor.ttk.Frame')
    @patch('service.replacements_editor.ttk.Button')
    @patch.object(ReplacementsEditor, 'load_file')
    def test_replacements_editor_init_success(
        self, mock_load_file, mock_button, mock_frame, mock_scrollbar,
        mock_text, mock_toplevel
    ):
        """正常系: ReplacementsEditor正常初期化"""
        # Arrange
        mock_window = Mock()
        mock_toplevel.return_value = mock_window
        mock_text_widget = create_mock_text_widget()
        mock_text.return_value = mock_text_widget

        # Act
        editor = ReplacementsEditor(self.mock_parent, self.mock_config)

        # Assert
        mock_toplevel.assert_called_once_with(self.mock_parent)
        mock_window.title.assert_called_once_with('テキスト置換登録( 置換前 , 置換後 )')
        mock_window.geometry.assert_called_once_with('500x800')
        mock_load_file.assert_called_once()
        mock_window.transient.assert_called_once_with(self.mock_parent)
        mock_window.grab_set.assert_called_once()
        assert editor.config == self.mock_config

    def test_replacements_editor_init_missing_paths_section(self):
        """異常系: PATHS設定が存在しない"""
        # Arrange
        invalid_config = {
            'EDITOR': {
                'width': '500',
                'height': '800'
            }
        }

        # Act & Assert
        with pytest.raises(ValueError, match='設定ファイルにreplacements_fileのパスがありません'):
            ReplacementsEditor(self.mock_parent, invalid_config)

    def test_replacements_editor_init_missing_replacements_file(self):
        """異常系: replacements_fileが存在しない"""
        # Arrange
        invalid_config = {
            'PATHS': {},
            'EDITOR': {
                'width': '500',
                'height': '800'
            }
        }

        # Act & Assert
        with pytest.raises(ValueError, match='設定ファイルにreplacements_fileのパスがありません'):
            ReplacementsEditor(self.mock_parent, invalid_config)

    @patch('service.replacements_editor.tk.Toplevel')
    @patch('service.replacements_editor.tk.Text')
    @patch('service.replacements_editor.ttk.Scrollbar')
    @patch('service.replacements_editor.ttk.Frame')
    @patch('service.replacements_editor.ttk.Button')
    @patch.object(ReplacementsEditor, 'load_file')
    def test_replacements_editor_init_custom_size(
        self, mock_load_file, mock_button, mock_frame, mock_scrollbar,
        mock_text, mock_toplevel
    ):
        """正常系: カスタムサイズでの初期化"""
        # Arrange
        custom_config = {
            'PATHS': {
                'replacements_file': 'C:/test/replacements.txt'
            },
            'EDITOR': {
                'width': '600',
                'height': '900',
                'font_name': 'Arial',
                'font_size': '14'
            }
        }

        mock_window = Mock()
        mock_toplevel.return_value = mock_window
        mock_text_widget = create_mock_text_widget()
        mock_text.return_value = mock_text_widget

        # Act
        editor = ReplacementsEditor(self.mock_parent, custom_config)

        # Assert
        mock_window.geometry.assert_called_once_with('600x900')


class TestLoadFile:
    """ファイル読み込みのテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.mock_parent = Mock(spec=tk.Tk)
        self.mock_config = {
            'PATHS': {
                'replacements_file': 'C:/test/replacements.txt'
            },
            'EDITOR': {
                'width': '500',
                'height': '800',
                'font_name': 'MS Gothic',
                'font_size': '12'
            }
        }

    @patch('service.replacements_editor.tk.Toplevel')
    @patch('service.replacements_editor.tk.Text')
    @patch('service.replacements_editor.ttk.Scrollbar')
    @patch('service.replacements_editor.ttk.Frame')
    @patch('service.replacements_editor.ttk.Button')
    @patch('service.replacements_editor.os.path.exists')
    def test_load_file_success(
        self, mock_exists, mock_button, mock_frame, mock_scrollbar,
        mock_text, mock_toplevel
    ):
        """正常系: ファイル読み込み成功"""
        # Arrange
        mock_window = Mock()
        mock_toplevel.return_value = mock_window
        mock_text_widget = create_mock_text_widget()
        mock_text.return_value = mock_text_widget

        mock_exists.return_value = True
        file_content = "旧単語,新単語\n古い表現,新しい表現\n"

        with patch('builtins.open', mock_open(read_data=file_content)):
            # Act
            editor = ReplacementsEditor(self.mock_parent, self.mock_config)

            # Assert
            mock_text_widget.insert.assert_called_once_with('1.0', file_content)

    @patch('service.replacements_editor.tk.Toplevel')
    @patch('service.replacements_editor.tk.Text')
    @patch('service.replacements_editor.ttk.Scrollbar')
    @patch('service.replacements_editor.ttk.Frame')
    @patch('service.replacements_editor.ttk.Button')
    @patch('service.replacements_editor.os.path.exists')
    @patch('service.replacements_editor.messagebox.showwarning')
    def test_load_file_not_found(
        self, mock_showwarning, mock_exists, mock_button, mock_frame,
        mock_scrollbar, mock_text, mock_toplevel, caplog
    ):
        """異常系: ファイルが存在しない"""
        # Arrange
        caplog.set_level(logging.WARNING)
        mock_window = Mock()
        mock_toplevel.return_value = mock_window
        mock_text_widget = create_mock_text_widget()
        mock_text.return_value = mock_text_widget

        mock_exists.return_value = False

        # Act
        editor = ReplacementsEditor(self.mock_parent, self.mock_config)

        # Assert
        assert "置換設定ファイルが見つかりません" in caplog.text
        mock_showwarning.assert_called_once()
        call_args = mock_showwarning.call_args
        assert call_args[0][0] == '警告'

    @patch('service.replacements_editor.tk.Toplevel')
    @patch('service.replacements_editor.tk.Text')
    @patch('service.replacements_editor.ttk.Scrollbar')
    @patch('service.replacements_editor.ttk.Frame')
    @patch('service.replacements_editor.ttk.Button')
    @patch('service.replacements_editor.os.path.exists')
    @patch('service.replacements_editor.messagebox.showerror')
    def test_load_file_read_error(
        self, mock_showerror, mock_exists, mock_button, mock_frame,
        mock_scrollbar, mock_text, mock_toplevel, caplog
    ):
        """異常系: ファイル読み込みエラー"""
        # Arrange
        caplog.set_level(logging.ERROR)
        mock_window = Mock()
        mock_toplevel.return_value = mock_window
        mock_text_widget = create_mock_text_widget()
        mock_text.return_value = mock_text_widget

        mock_exists.return_value = True

        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            # Act
            editor = ReplacementsEditor(self.mock_parent, self.mock_config)

            # Assert
            assert "ファイルの読み込みに失敗しました" in caplog.text
            mock_showerror.assert_called_once()
            call_args = mock_showerror.call_args
            assert call_args[0][0] == 'エラー'

    @patch('service.replacements_editor.tk.Toplevel')
    @patch('service.replacements_editor.tk.Text')
    @patch('service.replacements_editor.ttk.Scrollbar')
    @patch('service.replacements_editor.ttk.Frame')
    @patch('service.replacements_editor.ttk.Button')
    @patch('service.replacements_editor.os.path.exists')
    def test_load_file_empty_file(
        self, mock_exists, mock_button, mock_frame, mock_scrollbar,
        mock_text, mock_toplevel
    ):
        """境界値: 空のファイル"""
        # Arrange
        mock_window = Mock()
        mock_toplevel.return_value = mock_window
        mock_text_widget = create_mock_text_widget()
        mock_text.return_value = mock_text_widget

        mock_exists.return_value = True
        file_content = ""

        with patch('builtins.open', mock_open(read_data=file_content)):
            # Act
            editor = ReplacementsEditor(self.mock_parent, self.mock_config)

            # Assert
            mock_text_widget.insert.assert_called_once_with('1.0', file_content)

    @patch('service.replacements_editor.tk.Toplevel')
    @patch('service.replacements_editor.tk.Text')
    @patch('service.replacements_editor.ttk.Scrollbar')
    @patch('service.replacements_editor.ttk.Frame')
    @patch('service.replacements_editor.ttk.Button')
    @patch('service.replacements_editor.os.path.exists')
    def test_load_file_large_content(
        self, mock_exists, mock_button, mock_frame, mock_scrollbar,
        mock_text, mock_toplevel
    ):
        """境界値: 大きなファイル"""
        # Arrange
        mock_window = Mock()
        mock_toplevel.return_value = mock_window
        mock_text_widget = create_mock_text_widget()
        mock_text.return_value = mock_text_widget

        mock_exists.return_value = True
        large_content = "置換ルール,結果\n" * 1000

        with patch('builtins.open', mock_open(read_data=large_content)):
            # Act
            editor = ReplacementsEditor(self.mock_parent, self.mock_config)

            # Assert
            mock_text_widget.insert.assert_called_once_with('1.0', large_content)


class TestSaveFile:
    """ファイル保存のテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.mock_parent = Mock(spec=tk.Tk)
        self.mock_config = {
            'PATHS': {
                'replacements_file': 'C:/test/replacements.txt'
            },
            'EDITOR': {
                'width': '500',
                'height': '800',
                'font_name': 'MS Gothic',
                'font_size': '12'
            }
        }

    @patch('service.replacements_editor.tk.Toplevel')
    @patch('service.replacements_editor.tk.Text')
    @patch('service.replacements_editor.ttk.Scrollbar')
    @patch('service.replacements_editor.ttk.Frame')
    @patch('service.replacements_editor.ttk.Button')
    @patch('service.replacements_editor.os.path.exists')
    @patch('service.replacements_editor.os.makedirs')
    @patch('service.replacements_editor.os.path.dirname')
    @patch('service.replacements_editor.messagebox.showinfo')
    def test_save_file_success(
        self, mock_showinfo, mock_dirname, mock_makedirs, mock_exists,
        mock_button, mock_frame, mock_scrollbar, mock_text, mock_toplevel
    ):
        """正常系: ファイル保存成功"""
        # Arrange
        mock_window = Mock()
        mock_toplevel.return_value = mock_window
        mock_text_widget = create_mock_text_widget()
        mock_text_widget.get.return_value = "新しい置換ルール,結果"
        mock_text.return_value = mock_text_widget

        mock_exists.return_value = True
        mock_dirname.return_value = 'C:/test'

        with patch('builtins.open', mock_open()):
            # Act
            editor = ReplacementsEditor(self.mock_parent, self.mock_config)
            editor.save_file()

            # Assert
            mock_showinfo.assert_called_once_with('保存完了', 'ファイルを保存しました')
            mock_window.destroy.assert_called_once()

    @patch('service.replacements_editor.tk.Toplevel')
    @patch('service.replacements_editor.tk.Text')
    @patch('service.replacements_editor.ttk.Scrollbar')
    @patch('service.replacements_editor.ttk.Frame')
    @patch('service.replacements_editor.ttk.Button')
    @patch('service.replacements_editor.os.path.exists')
    @patch('service.replacements_editor.os.makedirs')
    @patch('service.replacements_editor.os.path.dirname')
    def test_save_file_creates_directory(
        self, mock_dirname, mock_makedirs, mock_exists, mock_button,
        mock_frame, mock_scrollbar, mock_text, mock_toplevel
    ):
        """正常系: ディレクトリ作成してから保存"""
        # Arrange
        mock_window = Mock()
        mock_toplevel.return_value = mock_window
        mock_text_widget = create_mock_text_widget()
        mock_text_widget.get.return_value = "置換ルール,結果"
        mock_text.return_value = mock_text_widget

        mock_exists.return_value = True
        mock_dirname.return_value = 'C:/test/new_dir'

        with patch('builtins.open', mock_open()), \
             patch('service.replacements_editor.messagebox.showinfo'):
            # Act
            editor = ReplacementsEditor(self.mock_parent, self.mock_config)
            editor.save_file()

            # Assert
            mock_makedirs.assert_called_once_with('C:/test/new_dir', exist_ok=True)

    @patch('service.replacements_editor.tk.Toplevel')
    @patch('service.replacements_editor.tk.Text')
    @patch('service.replacements_editor.ttk.Scrollbar')
    @patch('service.replacements_editor.ttk.Frame')
    @patch('service.replacements_editor.ttk.Button')
    @patch('service.replacements_editor.os.path.exists')
    @patch('service.replacements_editor.os.makedirs')
    @patch('service.replacements_editor.os.path.dirname')
    @patch('service.replacements_editor.messagebox.showerror')
    def test_save_file_write_error(
        self, mock_showerror, mock_dirname, mock_makedirs, mock_exists,
        mock_button, mock_frame, mock_scrollbar, mock_text, mock_toplevel, caplog
    ):
        """異常系: ファイル書き込みエラー"""
        # Arrange
        caplog.set_level(logging.ERROR)
        mock_window = Mock()
        mock_toplevel.return_value = mock_window
        mock_text_widget = create_mock_text_widget()
        mock_text_widget.get.return_value = "置換ルール,結果"
        mock_text.return_value = mock_text_widget

        mock_exists.return_value = True
        mock_dirname.return_value = 'C:/test'

        # 初期化時は成功、保存時は失敗
        open_mocks = [mock_open(read_data="")(), None]

        with patch('builtins.open', side_effect=[mock_open(read_data="")(), PermissionError("Permission denied")]):
            # Act
            editor = ReplacementsEditor(self.mock_parent, self.mock_config)
            editor.save_file()

            # Assert
            assert "ファイルの保存に失敗しました" in caplog.text
            # showerrorは保存時の1回のみ呼ばれる
            mock_showerror.assert_called_once()
            call_args = mock_showerror.call_args
            assert call_args[0][0] == 'エラー'
            assert "保存" in call_args[0][1]
            mock_window.destroy.assert_not_called()

    @patch('service.replacements_editor.tk.Toplevel')
    @patch('service.replacements_editor.tk.Text')
    @patch('service.replacements_editor.ttk.Scrollbar')
    @patch('service.replacements_editor.ttk.Frame')
    @patch('service.replacements_editor.ttk.Button')
    @patch('service.replacements_editor.os.path.exists')
    @patch('service.replacements_editor.os.makedirs')
    @patch('service.replacements_editor.os.path.dirname')
    @patch('service.replacements_editor.messagebox.showinfo')
    def test_save_file_empty_content(
        self, mock_showinfo, mock_dirname, mock_makedirs, mock_exists,
        mock_button, mock_frame, mock_scrollbar, mock_text, mock_toplevel
    ):
        """境界値: 空の内容を保存"""
        # Arrange
        mock_window = Mock()
        mock_toplevel.return_value = mock_window
        mock_text_widget = create_mock_text_widget()
        mock_text_widget.get.return_value = ""
        mock_text.return_value = mock_text_widget

        mock_exists.return_value = True
        mock_dirname.return_value = 'C:/test'

        with patch('builtins.open', mock_open()) as m:
            # Act
            editor = ReplacementsEditor(self.mock_parent, self.mock_config)
            editor.save_file()

            # Assert
            m().write.assert_called_once_with("")
            mock_showinfo.assert_called_once()

    @patch('service.replacements_editor.tk.Toplevel')
    @patch('service.replacements_editor.tk.Text')
    @patch('service.replacements_editor.ttk.Scrollbar')
    @patch('service.replacements_editor.ttk.Frame')
    @patch('service.replacements_editor.ttk.Button')
    @patch('service.replacements_editor.os.path.exists')
    @patch('service.replacements_editor.os.makedirs')
    @patch('service.replacements_editor.os.path.dirname')
    @patch('service.replacements_editor.messagebox.showinfo')
    def test_save_file_large_content(
        self, mock_showinfo, mock_dirname, mock_makedirs, mock_exists,
        mock_button, mock_frame, mock_scrollbar, mock_text, mock_toplevel
    ):
        """境界値: 大きな内容を保存"""
        # Arrange
        mock_window = Mock()
        mock_toplevel.return_value = mock_window
        mock_text_widget = create_mock_text_widget()
        large_content = "置換ルール,結果\n" * 1000
        mock_text_widget.get.return_value = large_content
        mock_text.return_value = mock_text_widget

        mock_exists.return_value = True
        mock_dirname.return_value = 'C:/test'

        with patch('builtins.open', mock_open()) as m:
            # Act
            editor = ReplacementsEditor(self.mock_parent, self.mock_config)
            editor.save_file()

            # Assert
            m().write.assert_called_once_with(large_content)


class TestIntegrationScenarios:
    """統合シナリオテスト"""

    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.mock_parent = Mock(spec=tk.Tk)
        self.mock_config = {
            'PATHS': {
                'replacements_file': 'C:/test/replacements.txt'
            },
            'EDITOR': {
                'width': '500',
                'height': '800',
                'font_name': 'MS Gothic',
                'font_size': '12'
            }
        }

    @patch('service.replacements_editor.tk.Toplevel')
    @patch('service.replacements_editor.tk.Text')
    @patch('service.replacements_editor.ttk.Scrollbar')
    @patch('service.replacements_editor.ttk.Frame')
    @patch('service.replacements_editor.ttk.Button')
    @patch('service.replacements_editor.os.path.exists')
    @patch('service.replacements_editor.os.makedirs')
    @patch('service.replacements_editor.os.path.dirname')
    @patch('service.replacements_editor.messagebox.showinfo')
    def test_full_edit_workflow(
        self, mock_showinfo, mock_dirname, mock_makedirs, mock_exists,
        mock_button, mock_frame, mock_scrollbar, mock_text, mock_toplevel
    ):
        """統合テスト: ファイル読み込み→編集→保存の完全なワークフロー"""
        # Arrange
        mock_window = Mock()
        mock_toplevel.return_value = mock_window
        mock_text_widget = create_mock_text_widget()
        mock_text.return_value = mock_text_widget

        mock_exists.return_value = True
        mock_dirname.return_value = 'C:/test'

        original_content = "旧単語,新単語\n"
        edited_content = "旧単語,新単語\n追加,された\n"

        # ファイル読み込み
        with patch('builtins.open', mock_open(read_data=original_content)):
            # Act
            editor = ReplacementsEditor(self.mock_parent, self.mock_config)

            # Assert - 読み込み確認
            mock_text_widget.insert.assert_called_once_with('1.0', original_content)

        # 編集をシミュレート
        mock_text_widget.get.return_value = edited_content

        # ファイル保存
        with patch('builtins.open', mock_open()) as m:
            editor.save_file()

            # Assert - 保存確認
            m().write.assert_called_once_with(edited_content)
            mock_showinfo.assert_called_once()

    @patch('service.replacements_editor.tk.Toplevel')
    @patch('service.replacements_editor.tk.Text')
    @patch('service.replacements_editor.ttk.Scrollbar')
    @patch('service.replacements_editor.ttk.Frame')
    @patch('service.replacements_editor.ttk.Button')
    @patch('service.replacements_editor.os.path.exists')
    @patch('service.replacements_editor.messagebox.showwarning')
    def test_create_new_file_workflow(
        self, mock_showwarning, mock_exists, mock_button, mock_frame,
        mock_scrollbar, mock_text, mock_toplevel
    ):
        """統合テスト: 新規ファイル作成ワークフロー"""
        # Arrange
        mock_window = Mock()
        mock_toplevel.return_value = mock_window
        mock_text_widget = create_mock_text_widget()
        mock_text_widget.get.return_value = "新規,ルール\n"
        mock_text.return_value = mock_text_widget

        mock_exists.return_value = False  # ファイルが存在しない

        # Act
        editor = ReplacementsEditor(self.mock_parent, self.mock_config)

        # Assert - 警告表示
        mock_showwarning.assert_called_once()

        # 新規内容を入力して保存
        with patch('service.replacements_editor.os.makedirs'), \
             patch('service.replacements_editor.os.path.dirname', return_value='C:/test'), \
             patch('builtins.open', mock_open()) as m, \
             patch('service.replacements_editor.messagebox.showinfo') as mock_showinfo:

            editor.save_file()

            # Assert - 保存成功
            m().write.assert_called_once_with("新規,ルール\n")
            mock_showinfo.assert_called_once()


class TestEdgeCases:
    """エッジケーステスト"""

    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.mock_parent = Mock(spec=tk.Tk)
        self.mock_config = {
            'PATHS': {
                'replacements_file': 'C:/test/replacements.txt'
            },
            'EDITOR': {
                'width': '500',
                'height': '800',
                'font_name': 'MS Gothic',
                'font_size': '12'
            }
        }

    @patch('service.replacements_editor.tk.Toplevel')
    @patch('service.replacements_editor.tk.Text')
    @patch('service.replacements_editor.ttk.Scrollbar')
    @patch('service.replacements_editor.ttk.Frame')
    @patch('service.replacements_editor.ttk.Button')
    @patch('service.replacements_editor.os.path.exists')
    def test_special_characters_in_content(
        self, mock_exists, mock_button, mock_frame, mock_scrollbar,
        mock_text, mock_toplevel
    ):
        """エッジケース: 特殊文字を含む内容"""
        # Arrange
        mock_window = Mock()
        mock_toplevel.return_value = mock_window
        mock_text_widget = create_mock_text_widget()
        mock_text.return_value = mock_text_widget

        mock_exists.return_value = True
        special_content = "改行\n含む,内容\nタブ\t,も\n"

        with patch('builtins.open', mock_open(read_data=special_content)):
            # Act
            editor = ReplacementsEditor(self.mock_parent, self.mock_config)

            # Assert
            mock_text_widget.insert.assert_called_once_with('1.0', special_content)

    @patch('service.replacements_editor.tk.Toplevel')
    @patch('service.replacements_editor.tk.Text')
    @patch('service.replacements_editor.ttk.Scrollbar')
    @patch('service.replacements_editor.ttk.Frame')
    @patch('service.replacements_editor.ttk.Button')
    @patch('service.replacements_editor.os.path.exists')
    def test_unicode_characters_in_content(
        self, mock_exists, mock_button, mock_frame, mock_scrollbar,
        mock_text, mock_toplevel
    ):
        """エッジケース: Unicode文字を含む内容"""
        # Arrange
        mock_window = Mock()
        mock_toplevel.return_value = mock_window
        mock_text_widget = create_mock_text_widget()
        mock_text.return_value = mock_text_widget

        mock_exists.return_value = True
        unicode_content = "日本語🎉,한글\nÉmojis,テスト\n"

        with patch('builtins.open', mock_open(read_data=unicode_content)):
            # Act
            editor = ReplacementsEditor(self.mock_parent, self.mock_config)

            # Assert
            mock_text_widget.insert.assert_called_once_with('1.0', unicode_content)

    @patch('service.replacements_editor.tk.Toplevel')
    @patch('service.replacements_editor.tk.Text')
    @patch('service.replacements_editor.ttk.Scrollbar')
    @patch('service.replacements_editor.ttk.Frame')
    @patch('service.replacements_editor.ttk.Button')
    @patch('service.replacements_editor.os.path.exists')
    def test_very_long_lines(
        self, mock_exists, mock_button, mock_frame, mock_scrollbar,
        mock_text, mock_toplevel
    ):
        """エッジケース: 非常に長い行"""
        # Arrange
        mock_window = Mock()
        mock_toplevel.return_value = mock_window
        mock_text_widget = create_mock_text_widget()
        mock_text.return_value = mock_text_widget

        mock_exists.return_value = True
        long_line = "a" * 10000 + "," + "b" * 10000 + "\n"

        with patch('builtins.open', mock_open(read_data=long_line)):
            # Act
            editor = ReplacementsEditor(self.mock_parent, self.mock_config)

            # Assert
            mock_text_widget.insert.assert_called_once_with('1.0', long_line)


class TestErrorHandling:
    """エラーハンドリングの詳細テスト"""

    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.mock_parent = Mock(spec=tk.Tk)
        self.mock_config = {
            'PATHS': {
                'replacements_file': 'C:/test/replacements.txt'
            },
            'EDITOR': {
                'width': '500',
                'height': '800',
                'font_name': 'MS Gothic',
                'font_size': '12'
            }
        }

    @patch('service.replacements_editor.tk.Toplevel')
    @patch('service.replacements_editor.tk.Text')
    @patch('service.replacements_editor.ttk.Scrollbar')
    @patch('service.replacements_editor.ttk.Frame')
    @patch('service.replacements_editor.ttk.Button')
    @patch('service.replacements_editor.os.path.exists')
    @patch('service.replacements_editor.messagebox.showerror')
    def test_unicode_decode_error(
        self, mock_showerror, mock_exists, mock_button, mock_frame,
        mock_scrollbar, mock_text, mock_toplevel, caplog
    ):
        """異常系: Unicode デコードエラー"""
        # Arrange
        caplog.set_level(logging.ERROR)
        mock_window = Mock()
        mock_toplevel.return_value = mock_window
        mock_text_widget = create_mock_text_widget()
        mock_text.return_value = mock_text_widget

        mock_exists.return_value = True

        with patch('builtins.open', side_effect=UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid')):
            # Act
            editor = ReplacementsEditor(self.mock_parent, self.mock_config)

            # Assert
            assert "ファイルの読み込みに失敗しました" in caplog.text
            mock_showerror.assert_called_once()

    @patch('service.replacements_editor.tk.Toplevel')
    @patch('service.replacements_editor.tk.Text')
    @patch('service.replacements_editor.ttk.Scrollbar')
    @patch('service.replacements_editor.ttk.Frame')
    @patch('service.replacements_editor.ttk.Button')
    @patch('service.replacements_editor.os.path.exists')
    @patch('service.replacements_editor.os.makedirs')
    @patch('service.replacements_editor.os.path.dirname')
    @patch('service.replacements_editor.messagebox.showerror')
    def test_directory_creation_error(
        self, mock_showerror, mock_dirname, mock_makedirs, mock_exists,
        mock_button, mock_frame, mock_scrollbar, mock_text, mock_toplevel, caplog
    ):
        """異常系: ディレクトリ作成エラー"""
        # Arrange
        caplog.set_level(logging.ERROR)
        mock_window = Mock()
        mock_toplevel.return_value = mock_window
        mock_text_widget = create_mock_text_widget()
        mock_text_widget.get.return_value = "置換ルール,結果"
        mock_text.return_value = mock_text_widget

        mock_dirname.return_value = 'C:/test'

        # 初期化時は成功、ディレクトリ作成時は失敗
        with patch('builtins.open', mock_open(read_data="")):
            mock_exists.return_value = True
            mock_makedirs.side_effect = PermissionError("Cannot create directory")

            # Act
            editor = ReplacementsEditor(self.mock_parent, self.mock_config)
            editor.save_file()

            # Assert
            assert "ファイルの保存に失敗しました" in caplog.text
            # showerrorは保存時の1回のみ呼ばれる
            mock_showerror.assert_called_once()
            call_args = mock_showerror.call_args
            assert call_args[0][0] == 'エラー'
            assert "保存" in call_args[0][1]
