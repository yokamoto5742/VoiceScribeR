# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## House Rules:
- 文章ではなくパッチの差分を返す
- コードの変更範囲は最小限に抑える
- コードの修正は直接適用する
- Pythonのコーディング規約はPEP8に従います
- KISSの原則に従い、できるだけシンプルなコードにします
- 可読性を優先します。一度読んだだけで理解できるコードが最高のコードです
- Pythonのコードのimport文は以下の適切な順序に並べ替えてください:
  1. 標準ライブラリ
  2. サードパーティライブラリ
  3. カスタムモジュール
  それぞれアルファベット順に並べます。importが先でfromは後です

## CHANGELOG
このプロジェクトにおけるすべての重要な変更は日本語でdocs/CHANGELOG.mdに記録します。
フォーマットは[Keep a Changelog](https://keepachangelog.com/ja/1.1.0/)に基づきます。

## Automatic Notifications (Hooks)
自動通知は`.claude/settings.local.json` で設定済:
- **Stop Hook**: ユーザーがClaude Codeを停止した時に「作業が完了しました」と通知
- **SessionEnd Hook**: セッション終了時に「Claude Code セッションが終了しました」と通知

## クリーンコードガイドライン
- 関数のサイズ: 関数は50行以下に抑えることを目標にしてください。関数の処理が多すぎる場合は、より小さなヘルパー関数に分割してください
- 単一責任: 各関数とモジュールには明確な目的が1つあるようにします。無関係なロジックをまとめないでください
- 命名: 説明的な名前を使用してください。`tmp` 、`data`、`handleStuff`のような一般的な名前は避けてください。例えば、`doCalc`よりも`calculateInvoiceTotal` の方が適しています
- DRY原則: コードを重複させないでください。類似のロジックが2箇所に存在する場合は、共有関数にリファクタリングしてください。それぞれに独自の実装が必要な場合はその理由を明確にしてください
- コメント: 分かりにくいロジックについては説明を加えます。説明不要のコードには過剰なコメントはつけないでください
- コメントとdocstringは必要最小限に日本語で記述します。文末に"。"や"."をつけないでください

## Project Overview

VoiceScribe is a Windows desktop application for voice-to-text transcription using ElevenLabs Speech-to-Text API. It provides real-time audio recording with keyboard shortcuts and automatic text pasting into other applications.

## Core Architecture

### Application Flow
1. **main.py**: Entry point that initializes components and handles error recovery
2. **VoiceInputManager** (app/main_window.py): Coordinates UI, recording, and keyboard handling
3. **RecordingController** (service/recording_controller.py): Manages recording lifecycle, transcription, and text processing
4. **AudioRecorder** (service/audio_recorder.py): Handles PyAudio recording and WAV file generation
5. **elevenlabs_api.py** (external_service/): Communicates with ElevenLabs API for transcription

### Key Components

**UI Layer** (app/):
- `main_window.py`: Main application window and component coordination
- `ui_components.py`: Tkinter UI widgets and layout

**Service Layer** (service/):
- `recording_controller.py`: Core business logic for recording/transcription workflow
- `audio_recorder.py`: Audio capture using PyAudio
- `keyboard_handler.py`: Global keyboard shortcuts using keyboard library
- `text_processing.py`: Text replacement and clipboard operations
- `safe_paste_sendinput.py`: Windows SendInput API for reliable pasting
- `notification.py`: Windows toast notifications
- `replacements_editor.py`: UI for editing text replacements

**External Services** (external_service/):
- `elevenlabs_api.py`: ElevenLabs Speech-to-Text API client with error handling

**Utilities** (utils/):
- `config_manager.py`: INI configuration file management
- `env_loader.py`: .env file loading for API keys
- `log_rotation.py`: Logging setup with file rotation

## Common Development Commands

### Running Tests
```bash
# Run all tests with verbose output
python -m pytest tests/ -v --tb=short

# Run with coverage report
python -m pytest tests/ -v --tb=short --cov=. --cov-report=html

# Run specific test file
python -m pytest tests/test_audio_recorder.py -v

# Run specific test class or function
python -m pytest tests/test_audio_recorder.py::TestAudioRecorderInit -v

# Run without warnings
python -m pytest tests/ -v --tb=short --disable-warnings
```

### Type Checking
```bash
# Type check main source directories
pyright app service utils

# Type check specific file
pyright service/recording_controller.py
```

### Building Executable
```bash
# Build Windows executable with PyInstaller
python build.py
# Output: dist/VoiceScribe.exe
```

### Running the Application
```bash
# Run from source
python main.py

# Required: .env file with ELEVENLABS_API_KEY
```

## Configuration

### Environment Variables (.env)
- `ELEVENLABS_API_KEY`: Required for ElevenLabs API access

### Configuration File (utils/config.ini)
Key settings for development:
- `[ELEVENLABS]`: Model selection (scribe_v2 default), language (jpn)
- `[AUDIO]`: Audio settings (sample_rate=16000, channels=1, chunk=1024)
- `[KEYS]`: Keyboard shortcuts (pause=toggle_recording, esc=exit, f8=reload, f9=toggle_punctuation)
- `[PATHS]`: temp_dir for audio files, replacements_file location
- `[LOGGING]`: log_level, debug_mode, log_retention_days
- `[RECORDING]`: auto_stop_timer (60 seconds default)
- `[OPTIONS]`: start_minimized (True default)

## Development Patterns

### Error Handling
- All external API calls wrapped in try-except with specific error types
- UI errors shown via NotificationManager
- Comprehensive logging with traceback in debug mode
- Emergency cleanup handlers in main.py for graceful shutdown

### Threading
- RecordingController uses threading for non-blocking audio processing
- UI updates via queue.Queue for thread safety (_ui_queue, _schedule_ui_callback)
- Timer-based auto-stop for recordings (recording_timer)
- All UI operations must be scheduled through _schedule_ui_callback to avoid TclError

### Text Processing Pipeline
1. Audio recorded → saved as WAV
2. ElevenLabs API transcription
3. Text replacements applied (from replacements.txt)
4. Punctuation processing (optional)
5. Copy to clipboard
6. Paste via SendInput API

### Testing Strategy
- pytest with mock for external dependencies (PyAudio, ElevenLabs API)
- Coverage tracking enabled
- Test structure mirrors source structure (tests/test_<module>.py)
- Tests cover core functionality for audio recording, text processing, and UI components

## Key Technical Constraints

- **Windows-only**: Uses Windows-specific APIs (SendInput, pywin32-ctypes)
- **PyAudio dependency**: Requires audio hardware access
- **ElevenLabs API**: Online-only, requires API key and network connection
- **Config paths**: Hardcoded paths in config.ini need adjustment for development vs. production
- **Keyboard library**: Global keyboard hooks require proper cleanup to avoid conflicts

## Version Management
- Version defined in app/__init__.py (__version__, __date__)
- scripts/version_manager.py auto-increments on build
- PyInstaller bundles version into executable

## Important Files Not to Modify
- service/replacements.txt: User data for text replacements
- logs/: Runtime logs with rotation
- temp/: Temporary audio files (auto-cleanup after 240 minutes)

## Dependencies
Key packages from requirements.txt:
- elevenlabs==2.25.0: ElevenLabs API client
- PyAudio==0.2.14: Audio recording
- keyboard==0.13.5: Global keyboard shortcuts
- pyperclip==1.9.0: Clipboard operations
- pytest==8.4.1: Testing framework
- pyright==1.1.407: Type checking
- pyinstaller==6.14.2: Executable building
