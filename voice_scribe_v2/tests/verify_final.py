"""最終統合検証スクリプト"""

import sys
from pathlib import Path

# UTF-8出力設定
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_all_imports():
    """全モジュールのインポートテスト"""
    print("✓ 全モジュールインポートテスト開始...")

    modules = [
        ("config.settings", "AppSettings"),
        ("domain.models", "Transcript"),
        ("domain.exceptions", "VoiceScribeException"),
        ("infrastructure.realtime_client", "RealtimeTranscriptionClient"),
        ("infrastructure.audio_recorder", "AudioRecorderWorker"),
        ("infrastructure.keyboard_listener", "GlobalHotkeyManager"),
        ("application.orchestrator", "TranscriptionOrchestrator"),
        ("application.text_processor", "TextPostProcessor"),
        ("application.clipboard_manager", "ClipboardManager"),
        ("presentation.main_window", "MainWindow"),
        ("presentation.widgets.transcript_view", "TranscriptView"),
        ("presentation.widgets.control_panel", "ControlPanel"),
        ("presentation.widgets.status_bar", "VoiceScribeStatusBar"),
        ("presentation.dialogs.settings_dialog", "SettingsDialog"),
        ("utils.error_handler", "setup_exception_handler"),
    ]

    failed = []
    for module_name, class_name in modules:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            print(f"  ✓ {module_name}.{class_name}")
        except ImportError as e:
            print(f"  ✗ {module_name}.{class_name} インポート失敗: {e}")
            failed.append(module_name)

    if failed:
        print(f"\n✗ インポート失敗: {len(failed)}件\n")
        return False

    print("✓ 全モジュールインポート成功\n")
    return True


def test_main_entry_point():
    """main.py エントリポイントテスト"""
    print("✓ main.py エントリポイントテスト開始...")

    try:
        import main

        assert hasattr(main, "main")
        assert hasattr(main, "setup_logging")
        assert hasattr(main, "load_stylesheet")

        print("  ✓ main関数定義確認")
        print("  ✓ setup_logging関数定義確認")
        print("  ✓ load_stylesheet関数定義確認")

        print("✓ main.py エントリポイントテスト成功\n")
        return True

    except Exception as e:
        print(f"  ✗ main.py エントリポイントテスト失敗: {e}\n")
        import traceback

        traceback.print_exc()
        return False


def test_file_structure():
    """ファイル構造テスト"""
    print("✓ ファイル構造テスト開始...")

    required_files = [
        "main.py",
        "requirements.txt",
        "README.md",
        "config/__init__.py",
        "config/settings.py",
        "domain/__init__.py",
        "domain/models.py",
        "domain/exceptions.py",
        "infrastructure/__init__.py",
        "infrastructure/realtime_client.py",
        "infrastructure/audio_recorder.py",
        "infrastructure/keyboard_listener.py",
        "application/__init__.py",
        "application/orchestrator.py",
        "application/text_processor.py",
        "application/clipboard_manager.py",
        "presentation/__init__.py",
        "presentation/main_window.py",
        "presentation/widgets/transcript_view.py",
        "presentation/widgets/control_panel.py",
        "presentation/widgets/status_bar.py",
        "presentation/dialogs/settings_dialog.py",
        "presentation/styles/theme.qss",
        "utils/__init__.py",
        "utils/error_handler.py",
    ]

    missing = []
    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"  ✓ {file_path}")
        else:
            print(f"  ✗ {file_path} が見つかりません")
            missing.append(file_path)

    if missing:
        print(f"\n✗ ファイル不足: {len(missing)}件\n")
        return False

    print("✓ ファイル構造テスト成功\n")
    return True


def test_dependencies():
    """依存パッケージテスト"""
    print("✓ 依存パッケージテスト開始...")

    dependencies = [
        ("PyQt6", "PyQt6"),
        ("pydantic", "pydantic"),
        ("pydantic_settings", "pydantic-settings"),
        ("websockets", "websockets"),
        ("pyaudio", "PyAudio"),
        ("keyboard", "keyboard"),
        ("pyperclip", "pyperclip"),
        ("pytest", "pytest"),
    ]

    missing = []
    for import_name, package_name in dependencies:
        try:
            __import__(import_name)
            print(f"  ✓ {package_name}")
        except ImportError:
            print(f"  ✗ {package_name} が見つかりません")
            missing.append(package_name)

    if missing:
        print(f"\n⚠ パッケージ不足: {len(missing)}件")
        print(f"  インストール: pip install {' '.join(missing)}\n")
        return False

    print("✓ 依存パッケージテスト成功\n")
    return True


def main():
    """メイン検証プロセス"""
    print("=" * 60)
    print("VoiceScribe v2.0 最終統合検証")
    print("=" * 60)
    print()

    results = []

    results.append(("ファイル構造", test_file_structure()))
    results.append(("依存パッケージ", test_dependencies()))
    results.append(("全モジュールインポート", test_all_imports()))
    results.append(("main.py エントリポイント", test_main_entry_point()))

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
        print("\n✓✓✓ 最終検証: 全テスト成功 ✓✓✓")
        print("\nVoiceScribe v2.0 は実行可能な状態です！")
        print("\n起動方法:")
        print("  python main.py\n")
        return 0
    else:
        print("\n✗✗✗ 最終検証: 一部テスト失敗 ✗✗✗\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
