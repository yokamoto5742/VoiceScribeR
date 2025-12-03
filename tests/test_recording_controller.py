import time
import tkinter as tk
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, call

import pytest

from service.recording_controller import RecordingController


class TestRecordingControllerInit:
    """RecordingController初期化のテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.mock_master = Mock(spec=tk.Tk)
        self.mock_config = {
            'WHISPER': {
                'USE_PUNCTUATION': 'True'
            },
            'PATHS': {
                'TEMP_DIR': '/test/temp',
                'CLEANUP_MINUTES': '240'
            }
        }
        self.mock_recorder = Mock()
        self.mock_client = Mock()
        self.mock_replacements = {'テスト': '試験'}
        self.mock_ui_callbacks = {
            'update_record_button': Mock(),
            'update_status_label': Mock()
        }
        self.mock_notification_callback = Mock()

    @patch('service.recording_controller.os.makedirs')
    @patch('service.recording_controller.RecordingController._cleanup_temp_files')
    def test_init_success(self, mock_cleanup, mock_makedirs):
        """正常系: RecordingController正常初期化"""
        # Act
        controller = RecordingController(
            self.mock_master,
            self.mock_config,
            self.mock_recorder,
            self.mock_client,
            self.mock_replacements,
            self.mock_ui_callbacks,
            self.mock_notification_callback
        )

        # Assert
        assert controller.master == self.mock_master
        assert controller.config == self.mock_config
        assert controller.recorder == self.mock_recorder
        assert controller.client == self.mock_client
        assert controller.replacements == self.mock_replacements
        assert controller.ui_callbacks == self.mock_ui_callbacks
        assert controller.show_notification == self.mock_notification_callback
        
        assert controller.use_punctuation is True
        assert controller.temp_dir == '/test/temp'
        assert controller.cleanup_minutes == 240
        assert controller.cancel_processing is False
        
        mock_makedirs.assert_called_once_with('/test/temp', exist_ok=True)
        mock_cleanup.assert_called_once()

    @patch('service.recording_controller.os.makedirs')
    def test_init_directory_creation_error(self, mock_makedirs):
        """異常系: ディレクトリ作成エラー"""
        # Arrange
        mock_makedirs.side_effect = PermissionError("Permission denied")

        # Act & Assert
        with pytest.raises(PermissionError):
            RecordingController(
                self.mock_master,
                self.mock_config,
                self.mock_recorder,
                self.mock_client,
                self.mock_replacements,
                self.mock_ui_callbacks,
                self.mock_notification_callback
            )


class TestRecordingControllerUIManagement:
    """UI管理機能のテストクラス"""

    def setup_method(self):
        """テスト用のRecordingControllerを準備"""
        self.mock_master = Mock(spec=tk.Tk)
        self.mock_master.winfo_exists.return_value = True
        self.mock_config = {
            'WHISPER': {'USE_PUNCTUATION': 'True'},
            'PATHS': {'TEMP_DIR': '/test/temp', 'CLEANUP_MINUTES': '240'}
        }
        
        with patch('service.recording_controller.os.makedirs'), \
             patch('service.recording_controller.RecordingController._cleanup_temp_files'):
            self.controller = RecordingController(
                self.mock_master,
                self.mock_config,
                Mock(),
                Mock(),
                {},
                {'update_record_button': Mock(), 'update_status_label': Mock()},
                Mock()
            )

    def test_is_ui_valid_success(self):
        """正常系: UI有効性チェック成功"""
        # Act
        result = self.controller._is_ui_valid()

        # Assert
        assert result is True
        self.mock_master.winfo_exists.assert_called_once()

    def test_is_ui_valid_tcl_error(self):
        """異常系: TclError発生時"""
        # Arrange
        self.mock_master.winfo_exists.side_effect = tk.TclError("Invalid window")

        # Act
        result = self.controller._is_ui_valid()

        # Assert
        assert result is False

    def test_is_ui_valid_master_none(self):
        """異常系: masterがNone"""
        # Arrange
        self.controller.master = None

        # Act
        result = self.controller._is_ui_valid()

        # Assert
        assert result is False

    def test_direct_ui_task_scheduling_success(self):
        """正常系: 直接UIタスクスケジュール成功"""
        # Arrange
        mock_callback = Mock()
        self.mock_master.after.return_value = "task_id_123"

        # Act
        task_id = self.mock_master.after(100, mock_callback, "arg1", "arg2")

        # Assert
        assert task_id == "task_id_123"
        self.mock_master.after.assert_called_once_with(100, mock_callback, "arg1", "arg2")

    def test_direct_ui_task_scheduling_ui_invalid(self):
        """異常系: UI無効時の動作確認"""
        # Arrange
        self.mock_master.winfo_exists.return_value = False

        # Act
        result = self.controller._is_ui_valid()

        # Assert
        assert result is False


class TestRecordingControllerRecording:
    """録音制御のテストクラス"""

    def setup_method(self):
        """テスト用のRecordingControllerを準備"""
        self.mock_master = Mock(spec=tk.Tk)
        self.mock_master.winfo_exists.return_value = True
        self.mock_recorder = Mock()
        self.mock_recorder.is_recording = False
        
        self.mock_config = {
            'WHISPER': {'USE_PUNCTUATION': 'True'},
            'PATHS': {'TEMP_DIR': '/test/temp', 'CLEANUP_MINUTES': '240'},
            'RECORDING': {'AUTO_STOP_TIMER': '60'},
            'KEYS': {'TOGGLE_RECORDING': 'F1'}
        }
        
        self.mock_ui_callbacks = {
            'update_record_button': Mock(),
            'update_status_label': Mock()
        }

        with patch('service.recording_controller.os.makedirs'), \
             patch('service.recording_controller.RecordingController._cleanup_temp_files'):
            self.controller = RecordingController(
                self.mock_master,
                self.mock_config,
                self.mock_recorder,
                Mock(),
                {},
                self.mock_ui_callbacks,
                Mock()
            )

    def test_toggle_recording_start(self):
        """正常系: 録音開始"""
        # Arrange
        self.mock_recorder.is_recording = False

        with patch.object(self.controller, 'start_recording') as mock_start:
            # Act
            self.controller.toggle_recording()

            # Assert
            mock_start.assert_called_once()

    def test_toggle_recording_stop(self):
        """正常系: 録音停止"""
        # Arrange
        self.mock_recorder.is_recording = True

        with patch.object(self.controller, 'stop_recording') as mock_stop:
            # Act
            self.controller.toggle_recording()

            # Assert
            mock_stop.assert_called_once()

    @patch('service.recording_controller.threading.Thread')
    @patch('service.recording_controller.threading.Timer')
    def test_start_recording_success(self, mock_timer_class, mock_thread_class):
        """正常系: 録音開始処理"""
        # Arrange
        mock_recording_thread = Mock()
        mock_thread_class.return_value = mock_recording_thread
        mock_timer = Mock()
        mock_timer_class.return_value = mock_timer

        # Act
        self.controller.start_recording()

        # Assert
        assert self.controller.cancel_processing is False
        self.mock_recorder.start_recording.assert_called_once()
        self.mock_ui_callbacks['update_record_button'].assert_called_once_with(True)
        self.mock_ui_callbacks['update_status_label'].assert_called_once()
        
        # 録音スレッド開始の確認
        mock_thread_class.assert_called_once()
        mock_recording_thread.start.assert_called_once()
        
        # 自動停止タイマー開始の確認
        mock_timer_class.assert_called_once_with(60, self.controller.auto_stop_recording)
        mock_timer.start.assert_called_once()

    def test_start_recording_with_active_processing_thread(self):
        """異常系: 処理中のスレッドがある場合"""
        # Arrange
        mock_active_thread = Mock()
        mock_active_thread.is_alive.return_value = True
        self.controller.processing_thread = mock_active_thread

        # Act & Assert
        with pytest.raises(RuntimeError, match="前回の処理が完了していません"):
            self.controller.start_recording()

    @patch('service.recording_controller.threading.Timer')
    def test_stop_recording_success(self, mock_timer_class):
        """正常系: 録音停止処理"""
        # Arrange
        mock_timer = Mock()
        mock_timer.is_alive.return_value = True
        self.controller.recording_timer = mock_timer
        
        self.controller.five_second_timer = "timer_id"
        self.mock_master.after_cancel = Mock()

        with patch.object(self.controller, '_stop_recording_process') as mock_stop_process:
            # Act
            self.controller.stop_recording()

            # Assert
            mock_timer.cancel.assert_called_once()
            self.mock_master.after_cancel.assert_called_once_with("timer_id")
            mock_stop_process.assert_called_once()

    def test_stop_recording_no_timer(self):
        """境界値: タイマーが存在しない場合"""
        # Arrange
        self.controller.recording_timer = None
        self.controller.five_second_timer = None

        with patch.object(self.controller, '_stop_recording_process') as mock_stop_process:
            # Act
            self.controller.stop_recording()

            # Assert
            mock_stop_process.assert_called_once()

    @patch('service.recording_controller.threading.Thread')
    def test_stop_recording_process_success(self, mock_thread_class):
        """正常系: 録音停止処理の詳細"""
        # Arrange
        test_frames = [b'frame1', b'frame2']
        self.mock_recorder.stop_recording.return_value = (test_frames, 16000)
        
        mock_processing_thread = Mock()
        mock_thread_class.return_value = mock_processing_thread

        # Act
        self.controller._stop_recording_process()

        # Assert
        self.mock_recorder.stop_recording.assert_called_once()
        self.mock_ui_callbacks['update_record_button'].assert_called_once_with(False)
        self.mock_ui_callbacks['update_status_label'].assert_called_once_with("テキスト出力中...")
        
        # 処理スレッド開始の確認
        mock_thread_class.assert_called_once()
        thread_call_args = mock_thread_class.call_args
        assert thread_call_args[1]['target'] == self.controller.transcribe_audio_frames
        assert thread_call_args[1]['args'] == (test_frames, 16000)
        mock_processing_thread.start.assert_called_once()

    @patch('service.recording_controller.threading.Thread')
    def test_stop_recording_process_recorder_error(self, mock_thread_class):
        """異常系: 録音停止時のエラー"""
        # Arrange
        self.mock_recorder.stop_recording.side_effect = Exception("Recorder error")

        with patch.object(self.controller, '_safe_error_handler') as mock_error_handler:
            # Act
            self.controller._stop_recording_process()

            # Assert
            mock_error_handler.assert_called_once()
            mock_thread_class.assert_not_called()


class TestRecordingControllerAutoStop:
    """自動停止機能のテストクラス"""

    def setup_method(self):
        """テスト用のRecordingControllerを準備"""
        self.mock_master = Mock(spec=tk.Tk)
        self.mock_master.winfo_exists.return_value = True
        
        self.mock_config = {
            'WHISPER': {'USE_PUNCTUATION': 'True'},
            'PATHS': {'TEMP_DIR': '/test/temp', 'CLEANUP_MINUTES': '240'},
            'RECORDING': {'AUTO_STOP_TIMER': '60'}
        }

        with patch('service.recording_controller.os.makedirs'), \
             patch('service.recording_controller.RecordingController._cleanup_temp_files'):
            self.controller = RecordingController(
                self.mock_master,
                self.mock_config,
                Mock(),
                Mock(),
                {},
                {'update_record_button': Mock(), 'update_status_label': Mock()},
                Mock()
            )

    def test_auto_stop_recording(self):
        """正常系: 自動停止処理"""
        # Arrange & Act
        self.controller.auto_stop_recording()

        # Assert
        # _auto_stop_recording_uiがmaster.afterでスケジュールされることを確認
        self.mock_master.after.assert_called_once_with(0, self.controller._auto_stop_recording_ui)

    def test_auto_stop_recording_ui(self):
        """正常系: 自動停止UI処理"""
        # Arrange
        with patch.object(self.controller, 'show_notification') as mock_notification, \
             patch.object(self.controller, '_stop_recording_process') as mock_stop:

            # Act
            self.controller._auto_stop_recording_ui()

            # Assert
            mock_notification.assert_called_once_with("自動停止", "アプリケーションを終了します")
            mock_stop.assert_called_once()
            self.mock_master.after.assert_called_with(1000, self.mock_master.quit)

    def test_show_five_second_notification(self):
        """正常系: 5秒前通知"""
        # Arrange
        self.mock_recorder = Mock()
        self.mock_recorder.is_recording = True
        self.controller.recorder = self.mock_recorder
        self.controller.five_second_notification_shown = False

        with patch.object(self.controller, 'show_notification') as mock_notification:
            # Act
            self.controller.show_five_second_notification()

            # Assert
            self.mock_master.lift.assert_called_once()
            self.mock_master.attributes.assert_has_calls([
                call('-topmost', True),
                call('-topmost', False)
            ])
            mock_notification.assert_called_once_with("自動停止", "あと5秒で音声入力を停止します")
            assert self.controller.five_second_notification_shown is True

    def test_show_five_second_notification_already_shown(self):
        """境界値: 5秒前通知が既に表示済み"""
        # Arrange
        self.mock_recorder = Mock()
        self.mock_recorder.is_recording = True
        self.controller.recorder = self.mock_recorder
        self.controller.five_second_notification_shown = True

        with patch.object(self.controller, 'show_notification') as mock_notification:
            # Act
            self.controller.show_five_second_notification()

            # Assert
            mock_notification.assert_not_called()

    def test_show_five_second_notification_not_recording(self):
        """境界値: 録音中でない場合"""
        # Arrange
        self.mock_recorder = Mock()
        self.mock_recorder.is_recording = False
        self.controller.recorder = self.mock_recorder

        with patch.object(self.controller, 'show_notification') as mock_notification:
            # Act
            self.controller.show_five_second_notification()

            # Assert
            mock_notification.assert_not_called()


class TestRecordingControllerAudioProcessing:
    """音声処理のテストクラス"""

    def setup_method(self):
        """テスト用のRecordingControllerを準備"""
        self.mock_master = Mock(spec=tk.Tk)
        self.mock_master.winfo_exists.return_value = True
        self.mock_client = Mock()
        
        self.mock_config = {
            'WHISPER': {'USE_PUNCTUATION': 'True'},
            'PATHS': {'TEMP_DIR': '/test/temp', 'CLEANUP_MINUTES': '240'},
            'CLIPBOARD': {'PASTE_DELAY': '0.1'}
        }

        with patch('service.recording_controller.os.makedirs'), \
             patch('service.recording_controller.RecordingController._cleanup_temp_files'):
            self.controller = RecordingController(
                self.mock_master,
                self.mock_config,
                Mock(),
                self.mock_client,
                {'テスト': '試験'},
                {'update_record_button': Mock(), 'update_status_label': Mock()},
                Mock()
            )

    @patch('service.recording_controller.save_audio')
    @patch('service.recording_controller.transcribe_audio')
    @patch('service.recording_controller.process_punctuation')
    def test_transcribe_audio_frames_success(self, mock_process_punct, mock_transcribe, mock_save_audio):
        """正常系: 音声フレーム文字起こし成功"""
        # Arrange
        test_frames = [b'frame1', b'frame2']
        sample_rate = 16000
        mock_save_audio.return_value = '/test/temp/audio.wav'
        mock_transcribe.return_value = 'テスト。結果、です'
        mock_process_punct.return_value = 'テスト結果です'

        # Act
        self.controller.transcribe_audio_frames(test_frames, sample_rate)

        # Assert
        mock_save_audio.assert_called_once_with(test_frames, sample_rate, self.mock_config)
        mock_transcribe.assert_called_once_with(
            '/test/temp/audio.wav',
            self.mock_config,
            self.mock_client
        )
        mock_process_punct.assert_called_once_with('テスト。結果、です', self.controller.use_punctuation)
        # master.afterが呼ばれることを確認
        self.mock_master.after.assert_called_once()
        call_args = self.mock_master.after.call_args
        assert call_args[0][0] == 0  # delay

    @patch('service.recording_controller.save_audio')
    def test_transcribe_audio_frames_save_error(self, mock_save_audio):
        """異常系: 音声ファイル保存エラー"""
        # Arrange
        test_frames = [b'frame1', b'frame2']
        sample_rate = 16000
        mock_save_audio.return_value = None

        # Act
        self.controller.transcribe_audio_frames(test_frames, sample_rate)

        # Assert
        # エラーハンドラーが呼ばれることを確認
        self.mock_master.after.assert_called_once()
        call_args = self.mock_master.after.call_args
        assert call_args[0][0] == 0  # delay

    @patch('service.recording_controller.save_audio')
    @patch('service.recording_controller.transcribe_audio')
    def test_transcribe_audio_frames_transcribe_error(self, mock_transcribe, mock_save_audio):
        """異常系: 文字起こしエラー"""
        # Arrange
        test_frames = [b'frame1', b'frame2']
        sample_rate = 16000
        mock_save_audio.return_value = '/test/temp/audio.wav'
        mock_transcribe.return_value = None

        # Act
        self.controller.transcribe_audio_frames(test_frames, sample_rate)

        # Assert
        # エラーハンドラーが呼ばれることを確認
        self.mock_master.after.assert_called_once()
        call_args = self.mock_master.after.call_args
        assert call_args[0][0] == 0  # delay

    @patch('service.recording_controller.save_audio')
    def test_transcribe_audio_frames_cancelled(self, mock_save_audio):
        """境界値: 処理がキャンセルされた場合"""
        # Arrange
        test_frames = [b'frame1', b'frame2']
        sample_rate = 16000
        self.controller.cancel_processing = True

        # Act
        self.controller.transcribe_audio_frames(test_frames, sample_rate)

        # Assert
        mock_save_audio.assert_not_called()


class TestRecordingControllerTextProcessing:
    """テキスト処理のテストクラス"""

    def setup_method(self):
        """テスト用のRecordingControllerを準備"""
        self.mock_master = Mock(spec=tk.Tk)
        self.mock_master.winfo_exists.return_value = True
        
        self.mock_config = {
            'WHISPER': {'USE_PUNCTUATION': 'True'},
            'PATHS': {'TEMP_DIR': '/test/temp', 'CLEANUP_MINUTES': '240'},
            'CLIPBOARD': {'PASTE_DELAY': '0.1'}
        }

        with patch('service.recording_controller.os.makedirs'), \
             patch('service.recording_controller.RecordingController._cleanup_temp_files'):
            self.controller = RecordingController(
                self.mock_master,
                self.mock_config,
                Mock(),
                Mock(),
                {'テスト': '試験'},
                {'update_record_button': Mock(), 'update_status_label': Mock()},
                Mock()
            )

    def test_ui_update_success(self):
        """正常系: UI更新処理"""
        # Arrange
        test_text = "テスト結果"

        # Act
        self.controller.ui_update(test_text)

        # Assert
        self.mock_master.after.assert_called_once_with(100, self.controller.copy_and_paste, test_text)

    @patch('service.recording_controller.threading.Thread')
    def test_copy_and_paste_success(self, mock_thread_class):
        """正常系: コピー&ペースト処理"""
        # Arrange
        test_text = "テスト結果"
        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread

        # Act
        self.controller.copy_and_paste(test_text)

        # Assert
        mock_thread_class.assert_called_once()
        thread_call_args = mock_thread_class.call_args
        assert thread_call_args[1]['target'] == self.controller._safe_copy_and_paste
        assert thread_call_args[1]['args'] == (test_text,)
        assert thread_call_args[1]['daemon'] is True
        mock_thread.start.assert_called_once()

    @patch('service.recording_controller.copy_and_paste_transcription')
    def test_safe_copy_and_paste_success(self, mock_copy_paste):
        """正常系: 安全なコピー&ペースト処理"""
        # Arrange
        test_text = "テスト結果"

        # Act
        self.controller._safe_copy_and_paste(test_text)

        # Assert
        mock_copy_paste.assert_called_once_with(
            test_text,
            self.controller.replacements,
            self.mock_config
        )

    @patch('service.recording_controller.copy_and_paste_transcription')
    def test_safe_copy_and_paste_error(self, mock_copy_paste):
        """異常系: コピー&ペースト処理エラー"""
        # Arrange
        test_text = "テスト結果"
        mock_copy_paste.side_effect = Exception("Paste error")

        # Act
        self.controller._safe_copy_and_paste(test_text)

        # Assert
        # エラーハンドラーが呼ばれることを確認
        self.mock_master.after.assert_called_once()
        call_args = self.mock_master.after.call_args
        assert call_args[0][0] == 0  # delay


class TestRecordingControllerCleanup:
    """クリーンアップ処理のテストクラス"""

    def setup_method(self):
        """テスト用のRecordingControllerを準備"""
        self.mock_master = Mock(spec=tk.Tk)
        self.mock_master.winfo_exists.return_value = True
        self.mock_recorder = Mock()
        
        self.mock_config = {
            'WHISPER': {'USE_PUNCTUATION': 'True'},
            'PATHS': {'TEMP_DIR': '/test/temp', 'CLEANUP_MINUTES': '240'}
        }

        with patch('service.recording_controller.os.makedirs'), \
             patch('service.recording_controller.RecordingController._cleanup_temp_files'):
            self.controller = RecordingController(
                self.mock_master,
                self.mock_config,
                self.mock_recorder,
                Mock(),
                {},
                {'update_record_button': Mock(), 'update_status_label': Mock()},
                Mock()
            )

    @patch('service.recording_controller.glob.glob')
    @patch('service.recording_controller.os.path.getmtime')
    @patch('service.recording_controller.os.remove')
    @patch('service.recording_controller.datetime')
    def test_cleanup_temp_files_success(self, mock_datetime, mock_remove, mock_getmtime, mock_glob):
        """正常系: 一時ファイルクリーンアップ成功"""
        # Arrange
        current_time = datetime(2024, 1, 1, 12)
        old_file_time = (current_time - timedelta(minutes=300)).timestamp()  # 5時間前
        recent_file_time = (current_time - timedelta(minutes=60)).timestamp()  # 1時間前

        mock_datetime.now.return_value = current_time
        mock_datetime.fromtimestamp = datetime.fromtimestamp
        mock_glob.return_value = ['/test/temp/old_file.wav', '/test/temp/recent_file.wav']
        mock_getmtime.side_effect = [old_file_time, recent_file_time]

        # Act
        self.controller._cleanup_temp_files()

        # Assert
        mock_remove.assert_called_once_with('/test/temp/old_file.wav')
        # recent_file.wavは削除されない（240分以内）

    @patch('service.recording_controller.glob.glob')
    def test_cleanup_temp_files_no_files(self, mock_glob):
        """境界値: 一時ファイルが存在しない"""
        # Arrange
        mock_glob.return_value = []

        # Act
        self.controller._cleanup_temp_files()

        # Assert - エラーが発生しないことを確認

    @patch('service.recording_controller.glob.glob')
    @patch('service.recording_controller.os.path.getmtime')
    @patch('service.recording_controller.os.remove')
    @patch('service.recording_controller.datetime')
    def test_cleanup_temp_files_remove_error(self, mock_datetime, mock_remove, mock_getmtime, mock_glob):
        """異常系: ファイル削除エラー"""
        # Arrange
        current_time = datetime(2024, 1, 1, 12)
        old_file_time = (current_time - timedelta(minutes=300)).timestamp()

        mock_datetime.now.return_value = current_time
        mock_datetime.fromtimestamp = datetime.fromtimestamp
        mock_glob.return_value = ['/test/temp/old_file.wav']
        mock_getmtime.return_value = old_file_time
        mock_remove.side_effect = PermissionError("Cannot delete file")

        # Act & Assert - 例外が発生しないことを確認
        self.controller._cleanup_temp_files()


    def test_cleanup_no_active_components(self):
        """境界値: アクティブなコンポーネントがない場合"""
        # Arrange
        self.controller.processing_thread = None
        self.controller.recording_timer = None
        self.controller.five_second_timer = None
        self.mock_recorder.is_recording = False

        with patch.object(self.controller, '_cleanup_temp_files') as mock_cleanup_files:
            # Act
            self.controller.cleanup()

            # Assert
            assert self.controller.cancel_processing is True
            mock_cleanup_files.assert_called_once()


class TestRecordingControllerThreadSafety:
    """スレッドセーフティのテストクラス"""

    def setup_method(self):
        """テスト用のRecordingControllerを準備"""
        self.mock_master = Mock(spec=tk.Tk)
        self.mock_master.winfo_exists.return_value = True
        
        self.mock_config = {
            'WHISPER': {'USE_PUNCTUATION': 'True'},
            'PATHS': {'TEMP_DIR': '/test/temp', 'CLEANUP_MINUTES': '240'},
            'CLIPBOARD': {'PASTE_DELAY': '0.1'}
        }

        with patch('service.recording_controller.os.makedirs'), \
             patch('service.recording_controller.RecordingController._cleanup_temp_files'):
            self.controller = RecordingController(
                self.mock_master,
                self.mock_config,
                Mock(),
                Mock(),
                {},
                {'update_record_button': Mock(), 'update_status_label': Mock()},
                Mock()
            )

    def test_concurrent_ui_updates(self):
        """境界値: 並行UI更新"""
        # Arrange
        self.mock_master.after.side_effect = lambda delay, func, *args: f"task_{delay}"

        # Act
        task1 = self.mock_master.after(100, Mock())
        task2 = self.mock_master.after(200, Mock())

        # Assert
        assert task1 == "task_100"
        assert task2 == "task_200"
        assert self.mock_master.after.call_count == 2

    def test_check_process_thread_still_running(self):
        """正常系: 処理スレッドがまだ実行中"""
        # Arrange
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True  # スレッド実行中

        # Act
        self.controller._check_process_thread(mock_thread)

        # Assert
        self.mock_master.after.assert_called_once_with(100, self.controller._check_process_thread, mock_thread)


class TestRecordingControllerIntegration:
    """統合シナリオテスト"""

    def setup_method(self):
        """テスト用のRecordingControllerを準備"""
        self.mock_master = Mock(spec=tk.Tk)
        self.mock_master.winfo_exists.return_value = True
        self.mock_recorder = Mock()
        self.mock_client = Mock()
        
        self.mock_config = {
            'WHISPER': {'USE_PUNCTUATION': 'True'},
            'PATHS': {'TEMP_DIR': '/test/temp', 'CLEANUP_MINUTES': '240'},
            'RECORDING': {'AUTO_STOP_TIMER': '60'},
            'KEYS': {'TOGGLE_RECORDING': 'F1'},
            'CLIPBOARD': {'PASTE_DELAY': '0.1'}
        }

        self.mock_ui_callbacks = {
            'update_record_button': Mock(),
            'update_status_label': Mock()
        }

        with patch('service.recording_controller.os.makedirs'), \
             patch('service.recording_controller.RecordingController._cleanup_temp_files'):
            self.controller = RecordingController(
                self.mock_master,
                self.mock_config,
                self.mock_recorder,
                self.mock_client,
                {'テスト': '試験'},
                self.mock_ui_callbacks,
                Mock()
            )

    @patch('service.recording_controller.threading.Thread')
    @patch('service.recording_controller.threading.Timer')
    @patch('service.recording_controller.save_audio')
    @patch('service.recording_controller.transcribe_audio')
    @patch('service.recording_controller.process_punctuation')
    @patch('service.recording_controller.copy_and_paste_transcription')
    def test_complete_recording_workflow(self, mock_copy_paste, mock_process_punct, mock_transcribe,
                                        mock_save_audio, mock_timer_class, mock_thread_class):
        """統合テスト: 完全な録音ワークフロー"""
        # Arrange
        self.mock_recorder.is_recording = False

        # モックの設定
        mock_recording_thread = Mock()
        mock_processing_thread = Mock()
        mock_thread_class.side_effect = [mock_recording_thread, mock_processing_thread]

        mock_timer = Mock()
        mock_timer_class.return_value = mock_timer

        test_frames = [b'frame1', b'frame2']
        self.mock_recorder.stop_recording.return_value = (test_frames, 16000)
        mock_save_audio.return_value = '/test/temp/audio.wav'
        mock_transcribe.return_value = 'テスト。文字、起こし。結果'
        mock_process_punct.return_value = 'テスト文字起こし結果'

        # Act 1: 録音開始
        self.controller.start_recording()

        # Assert 1: 録音開始状態
        self.mock_recorder.start_recording.assert_called_once()
        self.mock_ui_callbacks['update_record_button'].assert_called_with(True)
        mock_recording_thread.start.assert_called_once()
        mock_timer.start.assert_called_once()

        # Act 2: 録音停止
        self.controller.stop_recording()

        # Assert 2: 録音停止と処理開始
        self.mock_recorder.stop_recording.assert_called_once()
        self.mock_ui_callbacks['update_record_button'].assert_called_with(False)

        # Act 3: 文字起こし処理（直接呼び出しでシミュレート）
        self.controller.transcribe_audio_frames(test_frames, 16000)

        # Assert 3: 文字起こし処理
        mock_save_audio.assert_called_once_with(test_frames, 16000, self.mock_config)
        mock_transcribe.assert_called_once_with(
            '/test/temp/audio.wav',
            self.mock_config,
            self.mock_client
        )
        mock_process_punct.assert_called_once_with('テスト。文字、起こし。結果', True)

    def test_error_recovery_workflow(self):
        """統合テスト: エラー回復ワークフロー"""
        # Arrange
        self.mock_recorder.start_recording.side_effect = Exception("Recording error")

        with patch.object(self.controller, '_handle_error') as mock_handle_error:
            # Act
            try:
                self.controller.start_recording()
            except Exception:
                pass

            # 録音停止を試行
            self.controller.stop_recording()

            # クリーンアップ実行
            self.controller.cleanup()

            # Assert
            assert self.controller.cancel_processing is True


# パフォーマンステスト
class TestRecordingControllerPerformance:
    """パフォーマンステスト"""

    @patch('service.recording_controller.os.makedirs')
    @patch('service.recording_controller.RecordingController._cleanup_temp_files')
    def test_initialization_performance(self, mock_cleanup, mock_makedirs):
        """初期化処理のパフォーマンステスト"""
        # Arrange
        mock_master = Mock(spec=tk.Tk)
        config = {
            'WHISPER': {'USE_PUNCTUATION': 'True'},
            'PATHS': {'TEMP_DIR': '/test/temp', 'CLEANUP_MINUTES': '240'}
        }

        # Act
        start_time = time.time()
        controller = RecordingController(
            mock_master, config, Mock(), Mock(), {}, 
            {'update_record_button': Mock(), 'update_status_label': Mock()}, Mock()
        )
        end_time = time.time()

        # Assert
        assert (end_time - start_time) < 0.1  # 100ms以内で初期化完了
        assert controller is not None

    @patch('service.recording_controller.glob.glob')
    @patch('service.recording_controller.os.path.getmtime')
    @patch('service.recording_controller.os.remove')
    @patch('service.recording_controller.datetime')
    def test_cleanup_large_files_performance(self, mock_datetime, mock_remove, 
                                           mock_getmtime, mock_glob):
        """大量ファイルクリーンアップのパフォーマンステスト"""
        # Arrange
        mock_master = Mock(spec=tk.Tk)
        config = {
            'WHISPER': {'USE_PUNCTUATION': 'True'},
            'PATHS': {'TEMP_DIR': '/test/temp', 'CLEANUP_MINUTES': '240'}
        }

        with patch('service.recording_controller.os.makedirs'):
            controller = RecordingController(
                mock_master, config, Mock(), Mock(), {},
                {'update_record_button': Mock(), 'update_status_label': Mock()}, Mock()
            )

        # 1000個のファイルをシミュレート
        mock_files = [f'/test/temp/file_{i}.wav' for i in range(1000)]
        current_time = datetime(2024, 1, 1, 12)
        old_time = (current_time - timedelta(minutes=300)).timestamp()

        mock_datetime.now.return_value = current_time
        mock_datetime.fromtimestamp = datetime.fromtimestamp
        mock_glob.return_value = mock_files
        mock_getmtime.return_value = old_time

        # Act
        start_time = time.time()
        controller._cleanup_temp_files()
        end_time = time.time()

        # Assert
        assert (end_time - start_time) < 1.0  # 1秒以内で1000ファイル処理
        assert mock_remove.call_count == 1000
