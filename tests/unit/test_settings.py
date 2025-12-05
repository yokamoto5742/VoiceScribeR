"""設定クラスの単体テスト"""

import os
from pathlib import Path

import pytest

from config.settings import (
    AppSettings,
    AudioSettings,
    HotkeySettings,
    LoggingSettings,
    PathSettings,
    RealtimeApiSettings,
    RecordingSettings,
    UiSettings,
)


class TestAudioSettings:
    """AudioSettings のテスト"""

    def test_default_values(self):
        """デフォルト値が正しく設定される"""
        settings = AudioSettings()
        assert settings.sample_rate == 16000
        assert settings.channels == 1
        assert settings.chunk_size == 512
        assert settings.format_bits == 16


class TestRealtimeApiSettings:
    """RealtimeApiSettings のテスト"""

    def test_default_values(self):
        """デフォルト値が正しく設定される"""
        settings = RealtimeApiSettings()
        assert settings.model == "scribe_v2_realtime"
        assert settings.language == "jpn"
        assert settings.vad_silence_threshold == 0.5
        assert settings.max_reconnect_attempts == 5


class TestHotkeySettings:
    """HotkeySettings のテスト"""

    def test_default_values(self):
        """デフォルト値が正しく設定される"""
        settings = HotkeySettings()
        assert settings.toggle_recording == "pause"
        assert settings.exit_app == "esc"
        assert settings.toggle_punctuation == "f9"


class TestAppSettings:
    """AppSettings のテスト"""

    def test_load_from_env(self, monkeypatch, tmp_path):
        """環境変数から設定をロード"""
        # 環境変数を設定
        monkeypatch.setenv("ELEVENLABS_API_KEY", "test_api_key_12345")

        settings = AppSettings()
        assert settings.elevenlabs_api_key == "test_api_key_12345"

    def test_nested_settings(self, monkeypatch):
        """ネストされた設定が正しくロードされる"""
        monkeypatch.setenv("ELEVENLABS_API_KEY", "test_key")

        settings = AppSettings()
        assert isinstance(settings.audio, AudioSettings)
        assert isinstance(settings.realtime_api, RealtimeApiSettings)
        assert isinstance(settings.hotkeys, HotkeySettings)
        assert isinstance(settings.paths, PathSettings)
        assert isinstance(settings.logging, LoggingSettings)
        assert isinstance(settings.recording, RecordingSettings)
        assert isinstance(settings.ui, UiSettings)

    def test_missing_api_key_raises_error(self, monkeypatch):
        """APIキーが未設定の場合にエラーが発生"""
        # ELEVENLABS_API_KEY を削除
        monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)

        with pytest.raises(Exception):  # ValidationError
            AppSettings()
