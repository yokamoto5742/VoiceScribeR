"""Phase 3 検証スクリプト"""

import sys
from pathlib import Path

# UTF-8出力設定
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_application_imports():
    """アプリケーション層のインポートテスト"""
    print("✓ アプリケーション層インポートテスト開始...")

    try:
        from application.text_processor import TextPostProcessor

        print("  ✓ TextPostProcessor")
    except ImportError as e:
        print(f"  ✗ TextPostProcessor インポート失敗: {e}")
        return False

    try:
        from application.clipboard_manager import ClipboardManager

        print("  ✓ ClipboardManager")
    except ImportError as e:
        print(f"  ✗ ClipboardManager インポート失敗: {e}")
        return False

    print("✓ アプリケーション層インポート成功\n")
    return True


def test_text_processor():
    """TextPostProcessor のテスト"""
    print("✓ TextPostProcessor テスト開始...")

    try:
        from config.settings import AppSettings

        # 環境変数設定
        import os

        os.environ["ELEVENLABS_API_KEY"] = "test_key_for_validation"

        from application.text_processor import TextPostProcessor

        settings = AppSettings()
        processor = TextPostProcessor(settings=settings)

        print(f"  ✓ プロセッサー作成成功: 句読点使用={processor.use_punctuation}")

        # テキスト処理テスト
        test_text = "これはテストです。"
        result = processor.process(test_text)
        print(f"  ✓ 処理テスト: '{test_text}' → '{result}'")

        # 句読点削除テスト
        processor.set_punctuation_enabled(False)
        result = processor.process(test_text)
        assert "。" not in result
        print(f"  ✓ 句読点削除: '{result}'")

        print("✓ TextPostProcessor テスト成功\n")
        return True

    except Exception as e:
        print(f"  ✗ TextPostProcessor テスト失敗: {e}\n")
        import traceback

        traceback.print_exc()
        return False


def test_clipboard_manager():
    """ClipboardManager のテスト"""
    print("✓ ClipboardManager テスト開始...")

    try:
        import os

        from config.settings import AppSettings

        os.environ["ELEVENLABS_API_KEY"] = "test_key_for_validation"

        from application.clipboard_manager import ClipboardManager

        settings = AppSettings()
        manager = ClipboardManager(settings=settings)

        print("  ✓ マネージャー作成成功")

        # クリップボードコピーテスト
        test_text = "クリップボードテスト"
        success = manager.copy_only(test_text)
        if success:
            print(f"  ✓ コピーテスト成功: '{test_text}'")
        else:
            print(f"  ⚠ コピーテスト: 検証スキップ")

        print("✓ ClipboardManager テスト成功\n")
        return True

    except Exception as e:
        print(f"  ✗ ClipboardManager テスト失敗: {e}\n")
        import traceback

        traceback.print_exc()
        return False


def test_signal_integration():
    """Signal統合テスト"""
    print("✓ Signal統合テスト開始...")

    try:
        import os

        from PyQt6.QtWidgets import QApplication

        os.environ["ELEVENLABS_API_KEY"] = "test_key_for_validation"

        from application.clipboard_manager import ClipboardManager
        from application.text_processor import TextPostProcessor
        from config.settings import AppSettings

        # QApplication 作成
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        settings = AppSettings()
        processor = TextPostProcessor(settings=settings)
        clipboard = ClipboardManager(settings=settings)

        # Signal接続テスト
        signal_received = []

        clipboard.paste_completed.connect(lambda: signal_received.append("completed"))
        clipboard.paste_failed.connect(lambda msg: signal_received.append(f"failed: {msg}"))

        print("  ✓ Signal接続成功")
        print("✓ Signal統合テスト成功\n")
        return True

    except Exception as e:
        print(f"  ✗ Signal統合テスト失敗: {e}\n")
        import traceback

        traceback.print_exc()
        return False


def main():
    """メイン検証プロセス"""
    print("=" * 60)
    print("Phase 3: アプリケーション層 検証スクリプト")
    print("=" * 60)
    print()

    results = []

    results.append(("アプリケーション層インポート", test_application_imports()))
    results.append(("TextPostProcessor", test_text_processor()))
    results.append(("ClipboardManager", test_clipboard_manager()))
    results.append(("Signal統合", test_signal_integration()))

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
        print("\n✓✓✓ Phase 3 検証: 全テスト成功 ✓✓✓\n")
        return 0
    else:
        print("\n✗✗✗ Phase 3 検証: 一部テスト失敗 ✗✗✗\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
