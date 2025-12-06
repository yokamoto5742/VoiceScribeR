import logging
import os
import threading
import time
from unittest.mock import Mock, patch

import pyaudio
import pytest

from service.audio_recorder import AudioRecorder, save_audio


class TestAudioRecorderInit:
    """AudioRecorder初期化のテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.mock_config = {
            'AUDIO': {
                'SAMPLE_RATE': '16000',
                'CHANNELS': '1',
                'CHUNK': '1024'
            },
            'PATHS': {
                'TEMP_DIR': '/test/temp'
            }
        }

    @patch('service.audio_recorder.os.makedirs')
    def test_audio_recorder_init_success(self, mock_makedirs):
        """正常系: AudioRecorder正常初期化"""
        # Act
        recorder = AudioRecorder(self.mock_config)

        # Assert
        assert recorder.sample_rate == 16000
        assert recorder.channels == 1
        assert recorder.chunk == 1024
        assert recorder.temp_dir == '/test/temp'
        assert recorder.frames == []
        assert recorder.is_recording is False
        assert recorder.p is None
        assert recorder.stream is None
        mock_makedirs.assert_called_once_with('/test/temp', exist_ok=True)

    @patch('service.audio_recorder.os.makedirs')
    def test_audio_recorder_init_with_different_config(self, mock_makedirs):
        """正常系: 異なる設定値での初期化"""
        # Arrange
        custom_config = {
            'AUDIO': {
                'SAMPLE_RATE': '44100',
                'CHANNELS': '2',
                'CHUNK': '2048'
            },
            'PATHS': {
                'TEMP_DIR': '/custom/temp'
            }
        }

        # Act
        recorder = AudioRecorder(custom_config)

        # Assert
        assert recorder.sample_rate == 44100
        assert recorder.channels == 2
        assert recorder.chunk == 2048
        assert recorder.temp_dir == '/custom/temp'

    @patch('service.audio_recorder.os.makedirs')
    def test_audio_recorder_init_existing_directory(self, mock_makedirs):
        """正常系: 既存ディレクトリがある場合"""
        # Arrange
        mock_makedirs.side_effect = None  # 既存ディレクトリでもエラーなし

        # Act
        recorder = AudioRecorder(self.mock_config)

        # Assert
        assert recorder.temp_dir == '/test/temp'
        mock_makedirs.assert_called_once_with('/test/temp', exist_ok=True)

    @patch('service.audio_recorder.os.makedirs')
    def test_audio_recorder_init_directory_creation_error(self, mock_makedirs):
        """異常系: ディレクトリ作成エラー（権限不足等）"""
        # Arrange
        mock_makedirs.side_effect = PermissionError("Permission denied")

        # Act & Assert
        with pytest.raises(PermissionError):
            AudioRecorder(self.mock_config)


class TestAudioRecorderStartRecording:
    """録音開始のテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.mock_config = {
            'AUDIO': {
                'SAMPLE_RATE': '16000',
                'CHANNELS': '1',
                'CHUNK': '1024'
            },
            'PATHS': {
                'TEMP_DIR': '/test/temp'
            }
        }

    @patch('service.audio_recorder.os.makedirs')
    @patch('service.audio_recorder.pyaudio.PyAudio')
    def test_start_recording_success(self, mock_pyaudio_class, mock_makedirs):
        """正常系: 録音開始成功"""
        # Arrange
        mock_pyaudio_instance = Mock()
        mock_stream = Mock()
        mock_pyaudio_class.return_value = mock_pyaudio_instance
        mock_pyaudio_instance.open.return_value = mock_stream

        recorder = AudioRecorder(self.mock_config)

        # Act
        recorder.start_recording()

        # Assert
        assert recorder.is_recording is True
        assert recorder.frames == []
        assert recorder.p == mock_pyaudio_instance
        assert recorder.stream == mock_stream

        # PyAudio初期化の確認
        mock_pyaudio_class.assert_called_once()
        
        # ストリーム開始の確認
        mock_pyaudio_instance.open.assert_called_once_with(
            format=pyaudio.paInt16,  # ← 直接定数を使用
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1024,
        )

    @patch('service.audio_recorder.os.makedirs')
    @patch('service.audio_recorder.pyaudio.PyAudio')
    def test_start_recording_pyaudio_initialization_error(self, mock_pyaudio_class, mock_makedirs):
        """異常系: PyAudio初期化エラー"""
        # Arrange
        mock_pyaudio_class.side_effect = Exception("PyAudio initialization failed")
        recorder = AudioRecorder(self.mock_config)

        # Act
        recorder.start_recording()

        # Assert
        assert recorder.is_recording is True  # エラーでも状態は変更される
        assert recorder.p is None
        assert recorder.stream is None

    @patch('service.audio_recorder.os.makedirs')
    @patch('service.audio_recorder.pyaudio.PyAudio')
    def test_start_recording_stream_open_error(self, mock_pyaudio_class, mock_makedirs):
        """異常系: ストリーム開始エラー"""
        # Arrange
        mock_pyaudio_instance = Mock()
        mock_pyaudio_class.return_value = mock_pyaudio_instance
        mock_pyaudio_instance.open.side_effect = Exception("Stream open failed")

        recorder = AudioRecorder(self.mock_config)

        # Act
        recorder.start_recording()

        # Assert
        assert recorder.is_recording is True
        assert recorder.p == mock_pyaudio_instance
        assert recorder.stream is None

    @patch('service.audio_recorder.os.makedirs')
    @patch('service.audio_recorder.pyaudio.PyAudio')
    def test_start_recording_multiple_calls(self, mock_pyaudio_class, mock_makedirs):
        """境界値: 複数回start_recordingを呼んだ場合"""
        # Arrange
        mock_pyaudio_instance = Mock()
        mock_stream = Mock()
        mock_pyaudio_class.return_value = mock_pyaudio_instance
        mock_pyaudio_instance.open.return_value = mock_stream

        recorder = AudioRecorder(self.mock_config)

        # Act
        recorder.start_recording()
        recorder.start_recording()  # 2回目の呼び出し

        # Assert
        # PyAudioとストリームが2回初期化されることを確認
        assert mock_pyaudio_class.call_count == 2
        assert mock_pyaudio_instance.open.call_count == 2


class TestAudioRecorderStopRecording:
    """録音停止のテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.mock_config = {
            'AUDIO': {
                'SAMPLE_RATE': '16000',
                'CHANNELS': '1',
                'CHUNK': '1024'
            },
            'PATHS': {
                'TEMP_DIR': '/test/temp'
            }
        }

    @patch('service.audio_recorder.os.makedirs')
    def test_stop_recording_success(self, mock_makedirs):
        """正常系: 録音停止成功"""
        # Arrange
        recorder = AudioRecorder(self.mock_config)
        
        # モックストリームとPyAudioインスタンスを設定
        mock_stream = Mock()
        mock_pyaudio = Mock()
        recorder.stream = mock_stream
        recorder.p = mock_pyaudio
        recorder.is_recording = True
        recorder.frames = [b'test_frame_1', b'test_frame_2']

        # Act
        frames, sample_rate = recorder.stop_recording()

        # Assert
        assert recorder.is_recording is False
        assert frames == [b'test_frame_1', b'test_frame_2']
        assert sample_rate == 16000

        # ストリームとPyAudioの適切な終了を確認
        mock_stream.stop_stream.assert_called_once()
        mock_stream.close.assert_called_once()
        mock_pyaudio.terminate.assert_called_once()

    @patch('service.audio_recorder.os.makedirs')
    def test_stop_recording_no_stream(self, mock_makedirs):
        """境界値: ストリームが存在しない場合"""
        # Arrange
        recorder = AudioRecorder(self.mock_config)
        recorder.is_recording = True
        recorder.frames = [b'test_data']

        # Act
        frames, sample_rate = recorder.stop_recording()

        # Assert
        assert recorder.is_recording is False
        assert frames == [b'test_data']
        assert sample_rate == 16000

    @patch('service.audio_recorder.os.makedirs')
    def test_stop_recording_stream_error(self, mock_makedirs):
        """異常系: ストリーム停止時のエラー"""
        # Arrange
        recorder = AudioRecorder(self.mock_config)
        
        mock_stream = Mock()
        mock_stream.stop_stream.side_effect = Exception("Stream stop error")
        mock_pyaudio = Mock()
        
        recorder.stream = mock_stream
        recorder.p = mock_pyaudio
        recorder.is_recording = True
        recorder.frames = [b'test_data']

        # Act
        frames, sample_rate = recorder.stop_recording()

        # Assert
        assert recorder.is_recording is False
        assert frames == [b'test_data']
        # エラーが発生してもterminateは呼ばれる
        mock_pyaudio.terminate.assert_called_once()

    @patch('service.audio_recorder.os.makedirs')
    def test_stop_recording_pyaudio_terminate_error(self, mock_makedirs):
        """異常系: PyAudio終了時のエラー"""
        # Arrange
        recorder = AudioRecorder(self.mock_config)
        
        mock_stream = Mock()
        mock_pyaudio = Mock()
        mock_pyaudio.terminate.side_effect = Exception("PyAudio terminate error")
        
        recorder.stream = mock_stream
        recorder.p = mock_pyaudio
        recorder.is_recording = True
        recorder.frames = [b'audio_data']

        # Act
        frames, sample_rate = recorder.stop_recording()

        # Assert
        assert recorder.is_recording is False
        assert frames == [b'audio_data']
        assert sample_rate == 16000

    @patch('service.audio_recorder.os.makedirs')
    def test_stop_recording_empty_frames(self, mock_makedirs):
        """境界値: 録音データが空の場合"""
        # Arrange
        recorder = AudioRecorder(self.mock_config)
        recorder.is_recording = True
        recorder.frames = []

        # Act
        frames, sample_rate = recorder.stop_recording()

        # Assert
        assert frames == []
        assert sample_rate == 16000
        assert recorder.is_recording is False


class TestAudioRecorderRecord:
    """録音処理のテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.mock_config = {
            'AUDIO': {
                'SAMPLE_RATE': '16000',
                'CHANNELS': '1',
                'CHUNK': '1024'
            },
            'PATHS': {
                'TEMP_DIR': '/test/temp'
            }
        }

    @patch('service.audio_recorder.os.makedirs')
    def test_record_success(self, mock_makedirs):
        """正常系: 録音処理成功"""
        # Arrange
        recorder = AudioRecorder(self.mock_config)
        
        mock_stream = Mock()
        test_data = [b'chunk1', b'chunk2', b'chunk3']
        mock_stream.read.side_effect = test_data + [Exception("Stop recording")]
        
        recorder.stream = mock_stream
        recorder.is_recording = True
        
        # 3回読み取った後に録音停止
        def stop_after_reads():
            time.sleep(0.01)  # 短い待機
            recorder.is_recording = False
        
        threading.Thread(target=stop_after_reads, daemon=True).start()

        # Act
        recorder.record()

        # Assert
        assert len(recorder.frames) >= 3  # 最低3つのチャンクを読み取り
        assert recorder.frames[:3] == test_data

    @patch('service.audio_recorder.os.makedirs')
    def test_record_stream_read_error(self, mock_makedirs):
        """異常系: ストリーム読み取りエラー"""
        # Arrange
        recorder = AudioRecorder(self.mock_config)
        
        mock_stream = Mock()
        mock_stream.read.side_effect = Exception("Stream read error")
        
        recorder.stream = mock_stream
        recorder.is_recording = True

        # Act
        recorder.record()

        # Assert
        assert recorder.is_recording is False  # エラーで録音停止
        assert recorder.frames == []

    @patch('service.audio_recorder.os.makedirs')
    def test_record_immediate_stop(self, mock_makedirs):
        """境界値: 即座に停止される場合"""
        # Arrange
        recorder = AudioRecorder(self.mock_config)
        recorder.is_recording = False  # 開始前に停止状態

        # Act
        recorder.record()

        # Assert
        assert recorder.frames == []

    @patch('service.audio_recorder.os.makedirs')
    def test_record_no_stream(self, mock_makedirs):
        """異常系: ストリームが存在しない場合"""
        # Arrange
        recorder = AudioRecorder(self.mock_config)
        recorder.stream = None
        recorder.is_recording = True

        # Act & Assert
        with pytest.raises(AttributeError):
            recorder.record()


class TestSaveAudio:
    """音声ファイル保存のテストクラス"""

    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.mock_config = {
            'PATHS': {
                'TEMP_DIR': '/test/temp'
            },
            'AUDIO': {
                'CHANNELS': '1'
            }
        }
        self.test_frames = [b'frame1', b'frame2', b'frame3']
        self.sample_rate = 16000

    @patch('service.audio_recorder.os.makedirs')
    @patch('service.audio_recorder.os.path.exists')
    @patch('service.audio_recorder.wave.open')
    @patch('service.audio_recorder.pyaudio.PyAudio')
    @patch('service.audio_recorder.datetime')
    def test_save_audio_success(self, mock_datetime, mock_pyaudio_class, mock_wave_open, 
                               mock_exists, mock_makedirs):
        """正常系: 音声ファイル保存成功"""
        # Arrange
        mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
        mock_exists.return_value = True
        
        mock_wave_file = Mock()
        mock_wave_open.return_value.__enter__.return_value = mock_wave_file
        
        mock_pyaudio_instance = Mock()
        mock_pyaudio_class.return_value = mock_pyaudio_instance
        mock_pyaudio_instance.get_sample_size.return_value = 2

        # Act
        result = save_audio(self.test_frames, self.sample_rate, self.mock_config)

        # Assert
        expected_path = os.path.join('/test/temp', 'audio_20240101_120000.wav')
        assert result == expected_path
        
        # WAVファイル設定の確認
        mock_wave_file.setnchannels.assert_called_once_with(1)
        mock_wave_file.setsampwidth.assert_called_once_with(2)
        mock_wave_file.setframerate.assert_called_once_with(16000)
        mock_wave_file.writeframes.assert_called_once_with(b'frame1frame2frame3')

    @patch('service.audio_recorder.os.makedirs')
    @patch('service.audio_recorder.os.path.exists')
    @patch('service.audio_recorder.wave.open')
    @patch('service.audio_recorder.pyaudio.PyAudio')
    @patch('service.audio_recorder.datetime')
    def test_save_audio_directory_creation(self, mock_datetime, mock_pyaudio_class, 
                                          mock_wave_open, mock_exists, mock_makedirs):
        """正常系: ディレクトリが存在しない場合の作成"""
        # Arrange
        mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
        mock_exists.return_value = False  # ディレクトリが存在しない
        
        mock_wave_file = Mock()
        mock_wave_open.return_value.__enter__.return_value = mock_wave_file
        
        mock_pyaudio_instance = Mock()
        mock_pyaudio_class.return_value = mock_pyaudio_instance
        mock_pyaudio_instance.get_sample_size.return_value = 2

        # Act
        result = save_audio(self.test_frames, self.sample_rate, self.mock_config)

        # Assert
        mock_makedirs.assert_called_once_with('/test/temp')
        assert result is not None

    @patch('service.audio_recorder.os.makedirs')
    @patch('service.audio_recorder.os.path.exists')
    @patch('service.audio_recorder.datetime')
    def test_save_audio_directory_creation_error(self, mock_datetime, mock_exists, mock_makedirs):
        """異常系: ディレクトリ作成エラー"""
        # Arrange
        mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
        mock_exists.return_value = False
        mock_makedirs.side_effect = PermissionError("Permission denied")

        # Act
        result = save_audio(self.test_frames, self.sample_rate, self.mock_config)

        # Assert
        assert result is None

    @patch('service.audio_recorder.os.makedirs')
    @patch('service.audio_recorder.os.path.exists')
    @patch('service.audio_recorder.wave.open')
    @patch('service.audio_recorder.datetime')
    def test_save_audio_wave_file_error(self, mock_datetime, mock_exists, mock_makedirs, mock_wave_open):
        """異常系: WAVファイル作成エラー"""
        # Arrange
        mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
        mock_exists.return_value = True
        mock_wave_open.side_effect = Exception("Wave file creation error")

        # Act
        result = save_audio(self.test_frames, self.sample_rate, self.mock_config)

        # Assert
        assert result is None

    @patch('service.audio_recorder.os.makedirs')
    @patch('service.audio_recorder.os.path.exists')
    @patch('service.audio_recorder.wave.open')
    @patch('service.audio_recorder.pyaudio.PyAudio')
    @patch('service.audio_recorder.datetime')
    def test_save_audio_empty_frames(self, mock_datetime, mock_pyaudio_class, mock_wave_open, 
                                    mock_exists, mock_makedirs):
        """境界値: 空のフレームデータ"""
        # Arrange
        mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
        mock_exists.return_value = True
        
        mock_wave_file = Mock()
        mock_wave_open.return_value.__enter__.return_value = mock_wave_file
        
        mock_pyaudio_instance = Mock()
        mock_pyaudio_class.return_value = mock_pyaudio_instance
        mock_pyaudio_instance.get_sample_size.return_value = 2

        # Act
        result = save_audio([], self.sample_rate, self.mock_config)

        # Assert
        assert result is not None
        mock_wave_file.writeframes.assert_called_once_with(b'')  # 空データ

    @patch('service.audio_recorder.os.makedirs')
    @patch('service.audio_recorder.os.path.exists')
    @patch('service.audio_recorder.wave.open')
    @patch('service.audio_recorder.pyaudio.PyAudio')
    @patch('service.audio_recorder.datetime')
    def test_save_audio_large_frames(self, mock_datetime, mock_pyaudio_class, mock_wave_open, 
                                    mock_exists, mock_makedirs):
        """境界値: 大量のフレームデータ"""
        # Arrange
        large_frames = [b'x' * 1024 for _ in range(1000)]  # 1MB程度のデータ
        mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
        mock_exists.return_value = True
        
        mock_wave_file = Mock()
        mock_wave_open.return_value.__enter__.return_value = mock_wave_file
        
        mock_pyaudio_instance = Mock()
        mock_pyaudio_class.return_value = mock_pyaudio_instance
        mock_pyaudio_instance.get_sample_size.return_value = 2

        # Act
        result = save_audio(large_frames, self.sample_rate, self.mock_config)

        # Assert
        assert result is not None
        expected_data = b''.join(large_frames)
        mock_wave_file.writeframes.assert_called_once_with(expected_data)

    @patch('service.audio_recorder.os.makedirs')
    @patch('service.audio_recorder.os.path.exists')
    @patch('service.audio_recorder.wave.open')
    @patch('service.audio_recorder.pyaudio.PyAudio')
    @patch('service.audio_recorder.datetime')
    def test_save_audio_stereo_channels(self, mock_datetime, mock_pyaudio_class, mock_wave_open, 
                                       mock_exists, mock_makedirs):
        """正常系: ステレオ音声の保存"""
        # Arrange
        stereo_config = {
            'PATHS': {'TEMP_DIR': '/test/temp'},
            'AUDIO': {'CHANNELS': '2'}
        }
        mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
        mock_exists.return_value = True
        
        mock_wave_file = Mock()
        mock_wave_open.return_value.__enter__.return_value = mock_wave_file
        
        mock_pyaudio_instance = Mock()
        mock_pyaudio_class.return_value = mock_pyaudio_instance
        mock_pyaudio_instance.get_sample_size.return_value = 2

        # Act
        result = save_audio(self.test_frames, self.sample_rate, stereo_config)

        # Assert
        assert result is not None
        mock_wave_file.setnchannels.assert_called_once_with(2)

    @patch('service.audio_recorder.os.makedirs')
    @patch('service.audio_recorder.os.path.exists')
    @patch('service.audio_recorder.wave.open')
    @patch('service.audio_recorder.pyaudio.PyAudio')
    @patch('service.audio_recorder.datetime')
    def test_save_audio_different_sample_rates(self, mock_datetime, mock_pyaudio_class, 
                                              mock_wave_open, mock_exists, mock_makedirs):
        """正常系: 異なるサンプルレート"""
        # Arrange
        mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
        mock_exists.return_value = True
        
        mock_wave_file = Mock()
        mock_wave_open.return_value.__enter__.return_value = mock_wave_file
        
        mock_pyaudio_instance = Mock()
        mock_pyaudio_class.return_value = mock_pyaudio_instance
        mock_pyaudio_instance.get_sample_size.return_value = 2

        # Act
        result = save_audio(self.test_frames, 44100, self.mock_config)

        # Assert
        assert result is not None
        mock_wave_file.setframerate.assert_called_once_with(44100)

    def test_save_audio_logging_verification(self, caplog):
        """ログ出力の確認"""
        # Arrange
        caplog.set_level(logging.INFO)
        
        with patch('service.audio_recorder.os.makedirs'), \
             patch('service.audio_recorder.os.path.exists', return_value=True), \
             patch('service.audio_recorder.wave.open') as mock_wave_open, \
             patch('service.audio_recorder.pyaudio.PyAudio') as mock_pyaudio_class, \
             patch('service.audio_recorder.datetime') as mock_datetime:
            
            mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
            mock_wave_file = Mock()
            mock_wave_open.return_value.__enter__.return_value = mock_wave_file
            mock_pyaudio_instance = Mock()
            mock_pyaudio_class.return_value = mock_pyaudio_instance
            mock_pyaudio_instance.get_sample_size.return_value = 2

            # Act
            result = save_audio(self.test_frames, self.sample_rate, self.mock_config)

            # Assert
            assert result is not None
            assert "音声ファイル保存完了" in caplog.text


class TestIntegrationScenarios:
    """統合シナリオテスト"""

    def setup_method(self):
        """各テストメソッドの前に実行される設定"""
        self.mock_config = {
            'AUDIO': {
                'SAMPLE_RATE': '16000',
                'CHANNELS': '1',
                'CHUNK': '1024'
            },
            'PATHS': {
                'TEMP_DIR': '/test/temp'
            }
        }

    @patch('service.audio_recorder.os.makedirs')
    @patch('service.audio_recorder.pyaudio.PyAudio')
    @patch('service.audio_recorder.os.path.exists')
    @patch('service.audio_recorder.wave.open')
    @patch('service.audio_recorder.datetime')
    def test_full_recording_workflow(self, mock_datetime, mock_wave_open, mock_exists, 
                                    mock_pyaudio_class, mock_makedirs):
        """統合テスト: 録音開始→録音→停止→保存の完全なワークフロー"""
        # Arrange
        mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
        mock_exists.return_value = True
        
        # PyAudioとストリームのモック
        mock_pyaudio_instance = Mock()
        mock_stream = Mock()
        mock_pyaudio_class.return_value = mock_pyaudio_instance
        mock_pyaudio_instance.open.return_value = mock_stream
        mock_pyaudio_instance.get_sample_size.return_value = 2
        
        # ストリーム読み取りデータ
        test_audio_data = [b'chunk1', b'chunk2', b'chunk3']
        mock_stream.read.side_effect = test_audio_data + [Exception("Stop")]
        
        # WAVファイルモック
        mock_wave_file = Mock()
        mock_wave_open.return_value.__enter__.return_value = mock_wave_file

        # Act
        recorder = AudioRecorder(self.mock_config)
        
        # 録音開始
        recorder.start_recording()
        assert recorder.is_recording is True
        
        # 短時間録音をシミュレート
        recorder.frames = test_audio_data  # 直接設定してシミュレート
        
        # 録音停止
        frames, sample_rate = recorder.stop_recording()
        
        # ファイル保存
        saved_path = save_audio(frames, sample_rate, self.mock_config)

        # Assert
        assert frames == test_audio_data
        assert sample_rate == 16000
        assert saved_path == os.path.join('/test/temp', 'audio_20240101_120000.wav')
        
        # PyAudio呼び出しの確認
        mock_pyaudio_class.assert_called()
        mock_pyaudio_instance.open.assert_called_once()
        mock_stream.stop_stream.assert_called_once()
        mock_stream.close.assert_called_once()
        mock_pyaudio_instance.terminate.assert_called_once()
        
        # WAVファイル作成の確認
        mock_wave_file.writeframes.assert_called_once_with(b'chunk1chunk2chunk3')

    @patch('service.audio_recorder.os.makedirs')
    @patch('service.audio_recorder.pyaudio.PyAudio')
    def test_recording_error_recovery(self, mock_pyaudio_class, mock_makedirs):
        """異常系: 録音エラーからの回復"""
        # Arrange
        mock_pyaudio_class.side_effect = Exception("PyAudio not available")
        
        # Act
        recorder = AudioRecorder(self.mock_config)
        recorder.start_recording()  # エラーが発生するが処理は継続
        frames, sample_rate = recorder.stop_recording()

        # Assert
        assert frames == []
        assert sample_rate == 16000
        assert recorder.is_recording is False

    @patch('service.audio_recorder.os.makedirs')
    def test_multiple_recording_sessions(self, mock_makedirs):
        """正常系: 複数回の録音セッション"""
        # Act
        recorder = AudioRecorder(self.mock_config)
        
        # 1回目の録音セッション
        with patch('service.audio_recorder.pyaudio.PyAudio') as mock_pyaudio1:
            mock_stream1 = Mock()
            mock_pyaudio1.return_value.open.return_value = mock_stream1
            
            recorder.start_recording()
            recorder.frames = [b'session1_data']
            frames1, rate1 = recorder.stop_recording()
        
        # 2回目の録音セッション
        with patch('service.audio_recorder.pyaudio.PyAudio') as mock_pyaudio2:
            mock_stream2 = Mock()
            mock_pyaudio2.return_value.open.return_value = mock_stream2
            
            recorder.start_recording()
            recorder.frames = [b'session2_data']
            frames2, rate2 = recorder.stop_recording()

        # Assert
        assert frames1 == [b'session1_data']
        assert frames2 == [b'session2_data']
        assert rate1 == rate2 == 16000


# パフォーマンステスト
class TestPerformance:
    """パフォーマンステスト"""

    @patch('service.audio_recorder.os.makedirs')
    @patch('service.audio_recorder.os.path.exists')
    @patch('service.audio_recorder.wave.open')
    @patch('service.audio_recorder.pyaudio.PyAudio')
    @patch('service.audio_recorder.datetime')
    def test_large_audio_data_performance(self, mock_datetime, mock_pyaudio_class, 
                                         mock_wave_open, mock_exists, mock_makedirs):
        """大量音声データの処理性能テスト"""
        # Arrange
        mock_datetime.now.return_value.strftime.return_value = "20240101_120000"
        mock_exists.return_value = True
        
        # 10秒分の音声データをシミュレート（16kHz, 1024バイト/チャンク）
        large_frames = [b'x' * 1024 for _ in range(160)]  # 約10秒分
        
        mock_wave_file = Mock()
        mock_wave_open.return_value.__enter__.return_value = mock_wave_file
        
        mock_pyaudio_instance = Mock()
        mock_pyaudio_class.return_value = mock_pyaudio_instance
        mock_pyaudio_instance.get_sample_size.return_value = 2

        config = {
            'PATHS': {'TEMP_DIR': '/test/temp'},
            'AUDIO': {'CHANNELS': '1'}
        }

        # Act
        start_time = time.time()
        result = save_audio(large_frames, 16000, config)
        end_time = time.time()

        # Assert
        assert result is not None
        assert (end_time - start_time) < 1.0  # 1秒以内で完了


# エラーハンドリングの詳細テスト
class TestErrorHandling:
    """エラーハンドリングの詳細テスト"""

    @patch('service.audio_recorder.os.makedirs')
    def test_comprehensive_error_logging(self, mock_makedirs, caplog):
        """包括的なエラーログ出力確認"""
        # Arrange
        caplog.set_level(logging.ERROR)
        config = {
            'AUDIO': {'SAMPLE_RATE': '16000', 'CHANNELS': '1', 'CHUNK': '1024'},
            'PATHS': {'TEMP_DIR': '/test/temp'}
        }

        # 各種エラーシナリオをテスト
        with patch('service.audio_recorder.pyaudio.PyAudio') as mock_pyaudio:
            mock_pyaudio.side_effect = Exception("Critical PyAudio error")
            
            recorder = AudioRecorder(config)
            recorder.start_recording()

            # Assert
            assert "音声入力の開始中に予期せぬエラーが発生しました" in caplog.text

    @patch('service.audio_recorder.os.makedirs')
    @patch('service.audio_recorder.pyaudio.PyAudio')
    def test_stream_read_exception_handling(self, mock_pyaudio_class, mock_makedirs, caplog):
        """ストリーム読み取り例外の詳細処理"""
        # Arrange
        caplog.set_level(logging.ERROR)
        config = {
            'AUDIO': {'SAMPLE_RATE': '16000', 'CHANNELS': '1', 'CHUNK': '1024'},
            'PATHS': {'TEMP_DIR': '/test/temp'}
        }

        mock_stream = Mock()
        mock_stream.read.side_effect = OSError("Audio device disconnected")
        mock_pyaudio_class.return_value.open.return_value = mock_stream

        recorder = AudioRecorder(config)
        recorder.stream = mock_stream
        recorder.is_recording = True

        # Act
        recorder.record()

        # Assert
        assert recorder.is_recording is False
        assert "音声入力中に予期せぬエラーが発生しました" in caplog.text
