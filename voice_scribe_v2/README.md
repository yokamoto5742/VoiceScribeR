# VoiceScribe v2.0

ElevenLabs Realtime API を使用したリアルタイム音声文字起こしアプリケーション

## 概要

VoiceScribe v2.0 は、ElevenLabs Scribe V2 Realtime API を活用し、音声をリアルタイムで文字起こしして他のアプリケーションに自動貼り付けする Windows デスクトップアプリケーションです。

### 主な特徴

- ✨ **リアルタイム文字起こし**: ElevenLabs Realtime API による低遅延処理
- 🎤 **ワンタッチ録音**: グローバルホットキーで簡単操作
- 📝 **自動貼り付け**: 文字起こし結果を即座にクリップボードへコピー&貼り付け
- 🔄 **テキスト後処理**: 句読点制御・置換ルールによるカスタマイズ
- 🎨 **モダンUI**: PyQt6 による洗練されたインターフェース
- 🔁 **自動再接続**: 接続が切れても自動復旧

## システム要件

- **OS**: Windows 10/11
- **Python**: 3.10 以降
- **メモリ**: 4GB 以上推奨
- **ネットワーク**: インターネット接続必須
- **音声入力**: マイク

## インストール

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd voice_scribe_v2
```

### 2. 仮想環境の作成（推奨）

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 4. 環境変数の設定

プロジェクトルートに `.env` ファイルを作成し、ElevenLabs API キーを設定:

```
ELEVENLABS_API_KEY=your_api_key_here
```

## 使い方

### 起動

```bash
python main.py
```

### 基本操作

1. **録音開始/停止**: `Pause` キー（または UI の録音ボタン）
2. **句読点トグル**: `F9` キー
3. **置換ルール再読込**: `F8` キー
4. **アプリ終了**: `Esc` キー

### ホットキーカスタマイズ

設定ダイアログ（設定ボタン）から変更可能

### テキスト置換ルール

`service/replacements.txt` に以下の形式で記述:

```
置換前<TAB>置換後
例: きょう<TAB>今日
```

正規表現を使用する場合:

```
パターン<TAB>置換後<TAB>regex
```

## アーキテクチャ

VoiceScribe v2.0 は レイヤードアーキテクチャを採用:

```
presentation/    # PyQt6 UI層
  ├── main_window.py
  ├── widgets/
  └── dialogs/

application/     # ビジネスロジック層
  ├── orchestrator.py
  ├── text_processor.py
  └── clipboard_manager.py

infrastructure/  # 外部サービス連携層
  ├── realtime_client.py
  ├── audio_recorder.py
  └── keyboard_listener.py

domain/          # ドメインモデル層
  ├── models.py
  └── exceptions.py

config/          # 設定管理
  └── settings.py
```

### 主要コンポーネント

- **TranscriptionOrchestrator**: 全体の制御と状態管理
- **RealtimeTranscriptionClient**: WebSocket通信 (ElevenLabs API)
- **AudioRecorderWorker**: PyAudio による音声録音
- **TextPostProcessor**: テキスト後処理パイプライン
- **GlobalHotkeyManager**: グローバルホットキー管理

## 設定

### 環境変数

- `ELEVENLABS_API_KEY`: ElevenLabs API キー（必須）

### 設定ファイル（.env で上書き可能）

```ini
# 音声設定
AUDIO__SAMPLE_RATE=16000
AUDIO__CHUNK_SIZE=512

# リアルタイムAPI設定
REALTIME_API__MODEL=scribe_v2_realtime
REALTIME_API__LANGUAGE=jpn

# ホットキー設定
HOTKEY__TOGGLE_RECORDING=pause
HOTKEY__EXIT_APP=esc
HOTKEY__TOGGLE_PUNCTUATION=f9

# UI設定
UI__START_MINIMIZED=True
UI__WINDOW_WIDTH=600
UI__WINDOW_HEIGHT=400
```

## トラブルシューティング

### 音声デバイスが見つからない

- マイクが正しく接続されているか確認
- Windows のプライバシー設定でマイクアクセスが許可されているか確認

### WebSocket接続エラー

- インターネット接続を確認
- ElevenLabs API キーが正しいか確認
- ElevenLabs のサービス状態を確認

### ホットキーが動作しない

- 他のアプリケーションとキーが競合していないか確認
- 管理者権限で実行してみる

## 開発

### テスト実行

```bash
# Phase 1-3 の検証
python tests/verify_phase1.py
python tests/verify_phase2.py
python tests/verify_phase3.py

# 単体テスト
python -m pytest tests/unit/ -v
```

### コード品質チェック

```bash
# 型チェック
pyright

# フォーマット
black .
```

## ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。

## 謝辞

- **ElevenLabs**: Scribe V2 Realtime API の提供
- **PyQt6**: 優れた GUI フレームワーク
- **PyAudio**: 音声録音機能

---

**VoiceScribe v2.0** - Powered by ElevenLabs Realtime API
