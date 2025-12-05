"""型安全な設定管理 - Pydantic Settings"""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AudioSettings(BaseSettings):
    """音声録音設定"""

    sample_rate: int = Field(default=16000, description="サンプリングレート (Hz)")
    channels: int = Field(default=1, description="チャンネル数 (モノラル)")
    chunk_size: int = Field(default=512, description="チャンクサイズ (samples)")
    format_bits: int = Field(default=16, description="ビット深度")

    model_config = SettingsConfigDict(env_prefix="AUDIO_")


class RealtimeApiSettings(BaseSettings):
    """ElevenLabs Realtime API設定"""

    model: str = Field(default="scribe_v2_realtime", description="モデル名")
    language: str = Field(default="jpn", description="言語コード")
    audio_format: str = Field(default="pcm_16000", description="音声フォーマット")
    vad_silence_threshold: float = Field(
        default=0.5, description="VAD無音判定閾値"
    )
    max_reconnect_attempts: int = Field(default=5, description="最大再接続試行回数")
    initial_reconnect_delay: float = Field(
        default=1.0, description="初回再接続遅延 (秒)"
    )

    model_config = SettingsConfigDict(env_prefix="REALTIME_API_")


class HotkeySettings(BaseSettings):
    """キーボードショートカット設定"""

    toggle_recording: str = Field(default="pause", description="録音開始/停止")
    exit_app: str = Field(default="esc", description="アプリ終了")
    toggle_punctuation: str = Field(default="f9", description="句読点トグル")
    reload_replacements: str = Field(default="f8", description="置換ルール再読込")

    model_config = SettingsConfigDict(env_prefix="HOTKEY_")


class PathSettings(BaseSettings):
    """パス設定"""

    temp_dir: Path = Field(
        default_factory=lambda: Path("temp"), description="一時ファイルディレクトリ"
    )
    replacements_file: Path = Field(
        default_factory=lambda: Path("service/replacements.txt"),
        description="置換ルールファイル",
    )
    log_dir: Path = Field(
        default_factory=lambda: Path("logs"), description="ログディレクトリ"
    )

    model_config = SettingsConfigDict(env_prefix="PATH_")


class LoggingSettings(BaseSettings):
    """ログ設定"""

    log_level: str = Field(default="INFO", description="ログレベル")
    debug_mode: bool = Field(default=False, description="デバッグモード")
    log_retention_days: int = Field(default=7, description="ログ保持日数")
    max_log_size_mb: int = Field(default=10, description="最大ログサイズ (MB)")

    model_config = SettingsConfigDict(env_prefix="LOG_")


class RecordingSettings(BaseSettings):
    """録音制御設定"""

    auto_stop_timer: int = Field(default=60, description="自動停止タイマー (秒)")
    use_punctuation: bool = Field(default=True, description="句読点を使用")
    paste_delay_ms: int = Field(default=100, description="貼り付け遅延 (ミリ秒)")

    model_config = SettingsConfigDict(env_prefix="RECORDING_")


class UiSettings(BaseSettings):
    """UI設定"""

    start_minimized: bool = Field(default=True, description="最小化で起動")
    window_width: int = Field(default=600, description="ウィンドウ幅")
    window_height: int = Field(default=400, description="ウィンドウ高さ")
    max_transcript_lines: int = Field(
        default=1000, description="文字起こし表示最大行数"
    )

    model_config = SettingsConfigDict(env_prefix="UI_")


class AppSettings(BaseSettings):
    """アプリケーション全体の設定"""

    elevenlabs_api_key: str = Field(..., description="ElevenLabs APIキー")

    audio: AudioSettings = Field(default_factory=AudioSettings)
    realtime_api: RealtimeApiSettings = Field(default_factory=RealtimeApiSettings)
    hotkeys: HotkeySettings = Field(default_factory=HotkeySettings)
    paths: PathSettings = Field(default_factory=PathSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    recording: RecordingSettings = Field(default_factory=RecordingSettings)
    ui: UiSettings = Field(default_factory=UiSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    @classmethod
    def load(cls, env_file: Optional[Path] = None) -> "AppSettings":
        """設定をロード"""
        if env_file and env_file.exists():
            return cls(_env_file=str(env_file))
        return cls()
