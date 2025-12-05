"""Phase 1 検証スクリプト"""

import sys
from pathlib import Path

# UTF-8出力設定
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_imports():
    """全パッケージのインポートテスト"""
    print("✓ インポートテスト開始...")

    try:
        import config
        print("  ✓ config パッケージ")
    except ImportError as e:
        print(f"  ✗ config パッケージのインポート失敗: {e}")
        return False

    try:
        import domain
        print("  ✓ domain パッケージ")
    except ImportError as e:
        print(f"  ✗ domain パッケージのインポート失敗: {e}")
        return False

    try:
        import application
        print("  ✓ application パッケージ")
    except ImportError as e:
        print(f"  ✗ application パッケージのインポート失敗: {e}")
        return False

    try:
        import infrastructure
        print("  ✓ infrastructure パッケージ")
    except ImportError as e:
        print(f"  ✗ infrastructure パッケージのインポート失敗: {e}")
        return False

    try:
        import presentation
        print("  ✓ presentation パッケージ")
    except ImportError as e:
        print(f"  ✗ presentation パッケージのインポート失敗: {e}")
        return False

    print("✓ 全パッケージのインポート成功\n")
    return True


def test_settings():
    """設定クラスのテスト"""
    print("✓ 設定クラステスト開始...")

    try:
        from config.settings import (
            AudioSettings,
            HotkeySettings,
            RealtimeApiSettings,
        )

        audio = AudioSettings()
        print(f"  ✓ AudioSettings: sample_rate={audio.sample_rate}")

        realtime = RealtimeApiSettings()
        print(f"  ✓ RealtimeApiSettings: model={realtime.model}")

        hotkeys = HotkeySettings()
        print(f"  ✓ HotkeySettings: toggle_recording={hotkeys.toggle_recording}")

        print("✓ 設定クラステスト成功\n")
        return True
    except Exception as e:
        print(f"  ✗ 設定クラステスト失敗: {e}\n")
        return False


def test_models():
    """ドメインモデルのテスト"""
    print("✓ ドメインモデルテスト開始...")

    try:
        from datetime import datetime

        from domain.models import (
            RecordingState,
            ReplacementRule,
            Transcript,
            TranscriptType,
        )

        # Transcript 作成
        transcript = Transcript(
            text="テスト", type=TranscriptType.PARTIAL, timestamp=datetime.now()
        )
        print(f"  ✓ Transcript作成: text='{transcript.text}'")

        # ReplacementRule 作成
        rule = ReplacementRule(pattern="きょう", replacement="今日")
        print(f"  ✓ ReplacementRule作成: {rule}")

        # RecordingState 確認
        state = RecordingState.IDLE
        print(f"  ✓ RecordingState: {state}")

        print("✓ ドメインモデルテスト成功\n")
        return True
    except Exception as e:
        print(f"  ✗ ドメインモデルテスト失敗: {e}\n")
        import traceback

        traceback.print_exc()
        return False


def test_pyqt6():
    """PyQt6基本動作確認"""
    print("✓ PyQt6基本動作確認開始...")

    try:
        from PyQt6.QtCore import QObject, pyqtSignal
        from PyQt6.QtWidgets import QApplication

        # QApplication 作成（GUI不要）
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        print("  ✓ QApplication作成成功")

        # Signal/Slot テスト
        class TestObject(QObject):
            test_signal = pyqtSignal(str)

        obj = TestObject()
        print("  ✓ Signal定義成功")

        print("✓ PyQt6基本動作確認成功\n")
        return True
    except Exception as e:
        print(f"  ✗ PyQt6基本動作確認失敗: {e}\n")
        import traceback

        traceback.print_exc()
        return False


def main():
    """メイン検証プロセス"""
    print("=" * 60)
    print("Phase 1: 基盤構築 検証スクリプト")
    print("=" * 60)
    print()

    results = []

    results.append(("インポートテスト", test_imports()))
    results.append(("設定クラステスト", test_settings()))
    results.append(("ドメインモデルテスト", test_models()))
    results.append(("PyQt6動作確認", test_pyqt6()))

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
        print("\n✓✓✓ Phase 1 検証: 全テスト成功 ✓✓✓\n")
        return 0
    else:
        print("\n✗✗✗ Phase 1 検証: 一部テスト失敗 ✗✗✗\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
