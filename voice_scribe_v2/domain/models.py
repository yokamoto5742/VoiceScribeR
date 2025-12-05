"""ドメインモデル定義"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto


class TranscriptType(Enum):
    """文字起こし結果のタイプ"""

    PARTIAL = auto()  # 部分結果 (リアルタイム更新)
    COMMITTED = auto()  # 確定結果 (最終確定)


class RecordingState(Enum):
    """録音状態"""

    IDLE = auto()  # アイドル状態
    CONNECTING = auto()  # WebSocket接続中
    READY = auto()  # 録音準備完了
    RECORDING = auto()  # 録音中
    PROCESSING = auto()  # 処理中
    ERROR = auto()  # エラー状態


class ConnectionState(Enum):
    """WebSocket接続状態"""

    DISCONNECTED = auto()  # 切断状態
    CONNECTING = auto()  # 接続中
    CONNECTED = auto()  # 接続完了
    RECONNECTING = auto()  # 再接続中
    FAILED = auto()  # 接続失敗


@dataclass
class Transcript:
    """文字起こし結果"""

    text: str
    type: TranscriptType
    timestamp: datetime
    is_processed: bool = False

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class ReplacementRule:
    """テキスト置換ルール"""

    pattern: str  # 置換対象パターン
    replacement: str  # 置換後の文字列
    is_regex: bool = False  # 正規表現として扱うか

    def __str__(self) -> str:
        mode = "regex" if self.is_regex else "exact"
        return f"ReplacementRule({mode}: '{self.pattern}' → '{self.replacement}')"


@dataclass
class AudioChunk:
    """音声データチャンク"""

    data: bytes
    timestamp: datetime
    sample_rate: int
    channels: int

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    @property
    def size_bytes(self) -> int:
        """データサイズ (バイト)"""
        return len(self.data)

    @property
    def duration_ms(self) -> float:
        """音声の長さ (ミリ秒)"""
        bytes_per_sample = 2  # 16-bit
        samples = self.size_bytes / (bytes_per_sample * self.channels)
        return (samples / self.sample_rate) * 1000


@dataclass
class RecordingSession:
    """録音セッション情報"""

    session_id: str
    start_time: datetime
    end_time: datetime | None = None
    total_chunks: int = 0
    total_bytes: int = 0

    @property
    def duration_seconds(self) -> float:
        """セッション時間 (秒)"""
        if self.end_time is None:
            end = datetime.now()
        else:
            end = self.end_time
        return (end - self.start_time).total_seconds()

    @property
    def is_active(self) -> bool:
        """セッションがアクティブか"""
        return self.end_time is None
