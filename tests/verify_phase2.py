"""Phase 2 検証スクリプト"""

import sys
from pathlib import Path

# UTF-8出力設定
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_infrastructure_imports():
    """インフラ層のインポートテスト"""
    print("✓ インフラ層インポートテスト開始...")

    try:
        from infrastructure.realtime_client import RealtimeTranscriptionClient

        print("  ✓ RealtimeTranscriptionClient")
    except ImportError as e:
        print(f"  ✗ RealtimeTranscriptionClient インポート失敗: {e}")
        return False

    try:
        from infrastructure.audio_recorder import AudioRecorderWorker

        print("  ✓ AudioRecorderWorker")
    except ImportError as e:
        print(f"  ✗ AudioRecorderWorker インポート失敗: {e}")
        return False

    try:
        from infrastructure.keyboard_listener import GlobalHotkeyManager

        print("  ✓ GlobalHotkeyManager")
    except ImportError as e:
        print(f"  ✗ GlobalHotkeyManager インポート失敗: {e}")
        return False

    print("✓ インフラ層インポート成功\n")
    return True


def test_realtime_client_creation():
    """RealtimeTranscriptionClient の作成テスト"""
    print("✓ RealtimeTranscriptionClient 作成テスト開始...")

    try:
        from config.settings import RealtimeApiSettings
        from infrastructure.realtime_client import RealtimeTranscriptionClient

        settings = RealtimeApiSettings()
        client = RealtimeTranscriptionClient(api_key="test_key", settings=settings)

        print(f"  ✓ クライアント作成成功: 接続状態={client.connection_state}")
        print(f"  ✓ is_connected={client.is_connected}")

        print("✓ RealtimeTranscriptionClient 作成テスト成功\n")
        return True

    except Exception as e:
        print(f"  ✗ RealtimeTranscriptionClient 作成テスト失敗: {e}\n")
        import traceback

        traceback.print_exc()
        return False


def test_audio_recorder_creation():
    """AudioRecorderWorker の作成テスト"""
    print("✓ AudioRecorderWorker 作成テスト開始...")

    try:
        from config.settings import AudioSettings
        from infrastructure.audio_recorder import AudioRecorderWorker

        settings = AudioSettings()
        recorder = AudioRecorderWorker(settings=settings)

        print(f"  ✓ レコーダー作成成功: 録音中={recorder.is_recording}")

        print("✓ AudioRecorderWorker 作成テスト成功\n")
        return True

    except Exception as e:
        print(f"  ✗ AudioRecorderWorker 作成テスト失敗: {e}\n")
        import traceback

        traceback.print_exc()
        return False


def test_hotkey_manager_creation():
    """GlobalHotkeyManager の作成テスト"""
    print("✓ GlobalHotkeyManager 作成テスト開始...")

    try:
        from config.settings import HotkeySettings
        from infrastructure.keyboard_listener import GlobalHotkeyManager

        settings = HotkeySettings()
        manager = GlobalHotkeyManager(settings=settings)

        print(f"  ✓ マネージャー作成成功: 有効={manager.is_active}")

        # Signal が定義されているか確認
        assert hasattr(manager, "toggle_recording_pressed")
        assert hasattr(manager, "toggle_punctuation_pressed")
        assert hasattr(manager, "exit_app_pressed")
        print("  ✓ Signal定義確認")

        print("✓ GlobalHotkeyManager 作成テスト成功\n")
        return True

    except Exception as e:
        print(f"  ✗ GlobalHotkeyManager 作成テスト失敗: {e}\n")
        import traceback

        traceback.print_exc()
        return False


def test_signal_connections():
    """PyQt6 Signal接続テスト"""
    print("✓ PyQt6 Signal接続テスト開始...")

    try:
        from PyQt6.QtWidgets import QApplication

        from config.settings import AudioSettings, HotkeySettings, RealtimeApiSettings
        from infrastructure.audio_recorder import AudioRecorderWorker
        from infrastructure.keyboard_listener import GlobalHotkeyManager
        from infrastructure.realtime_client import RealtimeTranscriptionClient

        # QApplication 作成
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        # 各コンポーネント作成
        audio_settings = AudioSettings()
        recorder = AudioRecorderWorker(settings=audio_settings)

        api_settings = RealtimeApiSettings()
        client = RealtimeTranscriptionClient(api_key="test_key", settings=api_settings)

        hotkey_settings = HotkeySettings()
        hotkey_manager = GlobalHotkeyManager(settings=hotkey_settings)

        # Signal が発火可能か確認
        signal_received = []

        def on_signal():
            signal_received.append(True)

        recorder.recording_started.connect(on_signal)
        client.connection_state_changed.connect(lambda state: signal_received.append(True))
        hotkey_manager.toggle_recording_pressed.connect(on_signal)

        print("  ✓ Signal接続成功")
        print("✓ PyQt6 Signal接続テスト成功\n")
        return True

    except Exception as e:
        print(f"  ✗ PyQt6 Signal接続テスト失敗: {e}\n")
        import traceback

        traceback.print_exc()
        return False


def main():
    """メイン検証プロセス"""
    print("=" * 60)
    print("Phase 2: インフラストラクチャ層 検証スクリプト")
    print("=" * 60)
    print()

    results = []

    results.append(("インフラ層インポートテスト", test_infrastructure_imports()))
    results.append(
        ("RealtimeTranscriptionClient 作成", test_realtime_client_creation())
    )
    results.append(("AudioRecorderWorker 作成", test_audio_recorder_creation()))
    results.append(("GlobalHotkeyManager 作成", test_hotkey_manager_creation()))
    results.append(("PyQt6 Signal接続", test_signal_connections()))

    print("=" * 60)
    print("検証結果サマリー")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✓ 成功" if passed else "✗ 失敗"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n✓✓✓ Phase 2 検証: 全テスト成功 ✓✓✓\n")
        return 0
    else:
        print("\n✗✗✗ Phase 2 検証: 一部テスト失敗 ✗✗✗\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
