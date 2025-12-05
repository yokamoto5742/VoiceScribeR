"""カスタム例外クラス"""


class VoiceScribeException(Exception):
    """VoiceScribe基底例外"""

    pass


class ConfigurationError(VoiceScribeException):
    """設定エラー"""

    pass


class AudioRecordingError(VoiceScribeException):
    """音声録音エラー"""

    pass


class AudioDeviceNotFoundError(AudioRecordingError):
    """音声デバイスが見つからない"""

    pass


class AudioStreamError(AudioRecordingError):
    """音声ストリームエラー"""

    pass


class RealtimeApiError(VoiceScribeException):
    """Realtime API エラー"""

    pass


class WebSocketConnectionError(RealtimeApiError):
    """WebSocket接続エラー"""

    pass


class WebSocketAuthenticationError(RealtimeApiError):
    """WebSocket認証エラー"""

    pass


class TranscriptionError(RealtimeApiError):
    """文字起こしエラー"""

    pass


class TextProcessingError(VoiceScribeException):
    """テキスト処理エラー"""

    pass


class ClipboardError(VoiceScribeException):
    """クリップボードエラー"""

    pass


class HotkeyRegistrationError(VoiceScribeException):
    """ホットキー登録エラー"""

    pass


class StateTransitionError(VoiceScribeException):
    """状態遷移エラー"""

    def __init__(self, current_state: str, event: str, message: str = ""):
        self.current_state = current_state
        self.event = event
        super().__init__(
            f"Invalid state transition: {current_state} -> {event}. {message}"
        )
