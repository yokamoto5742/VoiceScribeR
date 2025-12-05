"""ドメインモデルの単体テスト"""

from datetime import datetime

import pytest

from domain.models import (
    AudioChunk,
    ConnectionState,
    RecordingSession,
    RecordingState,
    ReplacementRule,
    Transcript,
    TranscriptType,
)


class TestTranscriptType:
    """TranscriptType のテスト"""

    def test_enum_values(self):
        """列挙型の値が定義されている"""
        assert TranscriptType.PARTIAL
        assert TranscriptType.COMMITTED


class TestRecordingState:
    """RecordingState のテスト"""

    def test_all_states_defined(self):
        """全ての状態が定義されている"""
        assert RecordingState.IDLE
        assert RecordingState.CONNECTING
        assert RecordingState.READY
        assert RecordingState.RECORDING
        assert RecordingState.PROCESSING
        assert RecordingState.ERROR


class TestConnectionState:
    """ConnectionState のテスト"""

    def test_all_states_defined(self):
        """全ての状態が定義されている"""
        assert ConnectionState.DISCONNECTED
        assert ConnectionState.CONNECTING
        assert ConnectionState.CONNECTED
        assert ConnectionState.RECONNECTING
        assert ConnectionState.FAILED


class TestTranscript:
    """Transcript のテスト"""

    def test_create_with_timestamp(self):
        """タイムスタンプ付きで作成"""
        now = datetime.now()
        transcript = Transcript(
            text="こんにちは", type=TranscriptType.PARTIAL, timestamp=now
        )
        assert transcript.text == "こんにちは"
        assert transcript.type == TranscriptType.PARTIAL
        assert transcript.timestamp == now
        assert transcript.is_processed is False

    def test_auto_timestamp(self):
        """タイムスタンプが自動設定される"""
        transcript = Transcript(
            text="テスト", type=TranscriptType.COMMITTED, timestamp=None
        )
        assert transcript.timestamp is not None
        assert isinstance(transcript.timestamp, datetime)


class TestReplacementRule:
    """ReplacementRule のテスト"""

    def test_exact_match_rule(self):
        """完全一致の置換ルール"""
        rule = ReplacementRule(pattern="きょう", replacement="今日", is_regex=False)
        assert rule.pattern == "きょう"
        assert rule.replacement == "今日"
        assert rule.is_regex is False

    def test_regex_rule(self):
        """正規表現の置換ルール"""
        rule = ReplacementRule(pattern=r"\d+", replacement="数値", is_regex=True)
        assert rule.is_regex is True

    def test_str_representation(self):
        """文字列表現"""
        rule = ReplacementRule(pattern="test", replacement="テスト")
        assert "exact" in str(rule)
        assert "test" in str(rule)


class TestAudioChunk:
    """AudioChunk のテスト"""

    def test_create_audio_chunk(self):
        """音声チャンクを作成"""
        data = b"\x00\x01" * 100
        chunk = AudioChunk(
            data=data, timestamp=datetime.now(), sample_rate=16000, channels=1
        )
        assert chunk.data == data
        assert chunk.sample_rate == 16000
        assert chunk.channels == 1

    def test_size_bytes(self):
        """バイトサイズの計算"""
        data = b"\x00\x01" * 100
        chunk = AudioChunk(
            data=data, timestamp=datetime.now(), sample_rate=16000, channels=1
        )
        assert chunk.size_bytes == 200

    def test_duration_ms(self):
        """音声の長さの計算 (ミリ秒)"""
        # 512 samples, 16kHz, mono, 16-bit
        data = b"\x00\x01" * 512
        chunk = AudioChunk(
            data=data, timestamp=datetime.now(), sample_rate=16000, channels=1
        )
        assert chunk.duration_ms == pytest.approx(32.0, rel=0.01)


class TestRecordingSession:
    """RecordingSession のテスト"""

    def test_create_session(self):
        """セッションを作成"""
        session = RecordingSession(
            session_id="test_session_001", start_time=datetime.now()
        )
        assert session.session_id == "test_session_001"
        assert session.is_active is True
        assert session.end_time is None

    def test_duration_calculation(self):
        """セッション時間の計算"""
        start = datetime.now()
        session = RecordingSession(session_id="test", start_time=start)
        duration = session.duration_seconds
        assert duration >= 0

    def test_inactive_session(self):
        """終了したセッション"""
        start = datetime.now()
        end = datetime.now()
        session = RecordingSession(
            session_id="test", start_time=start, end_time=end
        )
        assert session.is_active is False
