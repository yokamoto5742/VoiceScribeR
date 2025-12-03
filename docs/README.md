# VoiceScribe

Windows デスクトップアプリケーション。ElevenLabs Speech-to-Text API を使用した音声テキスト変換を提供します。キーボードショートカットでリアルタイム音声録音、自動テキスト貼り付け機能を備えています。

- **現在のバージョン**: 0.0.1
- **最終更新日**: 2025年12月3日

## 主な機能

- リアルタイム音声録音と ElevenLabs API による自動テキスト変換
- グローバルキーボードショートカット (Pause キーで録音開始/停止)
- テキスト置換機能 (replacements.txt により任意の単語を自動変換)
- 句読点の自動挿入機能
- 他のアプリケーションへの自動テキスト貼り付け
- トースト通知による操作フィードバック
- 設定ファイルによるカスタマイズ
- ログファイルとエラーレポート機能

## 必要な環境

- Windows 10 以上
- Python 3.9 以上 (開発環境)
- オーディオ入力デバイス (マイク)

## インストール

### 1. リポジトリをクローン

```bash
git clone https://github.com/your-repo/VoiceScribe.git
cd VoiceScribe
```

### 2. 仮想環境を作成

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. 依存パッケージをインストール

```bash
pip install -r requirements.txt
```

### 4. 環境変数を設定

プロジェクトルートに `.env` ファイルを作成します

```
ELEVENLABS_API_KEY=your_api_key_here
```

ElevenLabs API キーは [ElevenLabs](https://elevenlabs.io) から取得できます

### 5. 設定を確認

`utils/config.ini` にアプリケーションの詳細設定があります。デフォルト設定は以下の通りです

```ini
[AUDIO]
sample_rate = 16000
channels = 1
chunk = 1024

[ELEVENLABS]
model = scribe_v2
language = jpn

[KEYS]
toggle_recording = pause
exit_app = esc
reload_audio = f8
toggle_punctuation = f9

[RECORDING]
auto_stop_timer = 60

[OPTIONS]
start_minimized = True
```

## 使用方法

### アプリケーションを実行

```bash
python main.py
```

アプリケーションはデフォルトで最小化状態で起動します

### キーボードショートカット

| キー | 機能 |
|------|------|
| Pause | 録音開始/停止 |
| Esc | アプリケーション終了 |
| F8 | 最新の音声ファイルを再ロード |
| F9 | 句読点機能の有効/無効を切り替え |

### 基本的な使用フロー

1. **Pause キーを押す** → 音声録音を開始
2. **マイクに向かって話す** → 最大 60 秒間自動で録音
3. **Pause キーを押す** → 録音を終了し、テキスト変換を開始
4. **テキストが自動的に他のアプリケーションに貼り付けられます**

### テキスト置換機能

`service/replacements.txt` にカスタム置換ルールを定義できます

ファイル形式 (1行に1つの置換ルール)

```
元のテキスト|置換後のテキスト
```

例

```
ありがとうございます。|ありがとうございます
こんにちは|こんにちは
```

アプリケーション内の置換エディター (UI) からも編集可能です

## アーキテクチャ

### レイヤー構成

```
UI層 (app/)
  ├─ main_window.py: メインウィンドウとコンポーネント調整
  └─ ui_components.py: Tkinter ウィジェット

ビジネスロジック層 (service/)
  ├─ recording_controller.py: 録音/テキスト変換フロー
  ├─ audio_recorder.py: PyAudio による音声キャプチャ
  ├─ keyboard_handler.py: グローバルキーボードショートカット
  ├─ text_processing.py: テキスト置換とクリップボード操作
  ├─ safe_paste_sendinput.py: Windows SendInput API での貼り付け
  ├─ notification.py: トースト通知
  └─ replacements_editor.py: UI置換エディター

外部サービス層 (external_service/)
  └─ elevenlabs_api.py: ElevenLabs Speech-to-Text API クライアント

ユーティリティ層 (utils/)
  ├─ config_manager.py: INI 設定ファイル管理
  ├─ env_loader.py: .env ファイルの読み込み
  └─ log_rotation.py: ログ設定と回転管理
```

### データフロー

```
音声録音 → WAV ファイル保存 → ElevenLabs API → テキスト変換
→ テキスト置換 → 句読点処理 → クリップボード格納 → SendInput で貼り付け
```

### スレッド管理

- `RecordingController` は音声処理をスレッド上で実行
- UI 更新はスレッドセーフなキューを経由して main スレッドで実行
- タイマー機能による自動停止機構 (デフォルト 60 秒)

## 開発環境のセットアップ

### パッケージのインストール

```bash
pip install -r requirements.txt
```

### テストの実行

```bash
# すべてのテストを実行
python -m pytest tests/ -v --tb=short

# カバレッジレポート付きで実行
python -m pytest tests/ -v --tb=short --cov=. --cov-report=html

# 特定のテストファイルを実行
python -m pytest tests/test_audio_recorder.py -v

# 特定のテストクラスまたは関数を実行
python -m pytest tests/test_audio_recorder.py::TestAudioRecorderInit -v
```

### 型チェック

```bash
# メインディレクトリを型チェック
pyright app service utils

# 特定のファイルをチェック
pyright service/recording_controller.py
```

### ビルド (実行可能ファイル化)

```bash
python build.py
```

実行可能ファイルは `dist/VoiceScribe.exe` に出力されます。ビルド時にバージョンが自動的にインクリメントされます

## プロジェクト構造

```
VoiceScribe/
├── main.py                          # エントリーポイント
├── requirements.txt                 # 依存パッケージ
├── build.py                         # ビルドスクリプト
├── pyrightconfig.json              # 型チェック設定
├── .env                            # API キー (Git 除外)
├── CLAUDE.md                        # プロジェクト規約
│
├── app/                            # UI レイヤー
│   ├── __init__.py                 # バージョン情報
│   ├── main_window.py              # メインウィンドウ
│   └── ui_components.py            # UI コンポーネント
│
├── service/                        # ビジネスロジック
│   ├── recording_controller.py     # 録音フロー制御
│   ├── audio_recorder.py           # 音声キャプチャ
│   ├── keyboard_handler.py         # キーボード入力処理
│   ├── text_processing.py          # テキスト処理
│   ├── safe_paste_sendinput.py     # 安全な貼り付け
│   ├── notification.py             # 通知機能
│   ├── replacements_editor.py      # 置換エディター UI
│   └── replacements.txt            # カスタム置換ルール
│
├── external_service/               # API クライアント
│   └── elevenlabs_api.py           # ElevenLabs API
│
├── utils/                          # ユーティリティ
│   ├── config.ini                  # 設定ファイル
│   ├── config_manager.py           # 設定管理
│   ├── env_loader.py               # 環境変数読み込み
│   └── log_rotation.py             # ログ設定
│
├── tests/                          # テストスイート
│   ├── test_audio_recorder.py
│   ├── test_text_processing.py
│   ├── test_config_manager.py
│   └── ...
│
├── scripts/                        # ビルドスクリプト
│   └── version_manager.py          # バージョン管理
│
├── assets/                         # リソースファイル
│   └── VoiceScribe.ico            # アイコン
│
├── logs/                           # ログファイル (Git 除外)
│   └── error_log.txt
│
├── temp/                           # 一時ファイル (Git 除外)
│   └── [audio_files].wav
│
└── docs/                           # ドキュメント
    └── README.md                   # このファイル
```

## 設定ファイルの説明

### utils/config.ini

#### [AUDIO] セクション
- `sample_rate`: サンプリングレート (Hz)。デフォルト 16000
- `channels`: オーディオチャンネル数。デフォルト 1 (モノラル)
- `chunk`: フレームバッファサイズ。デフォルト 1024

#### [ELEVENLABS] セクション
- `model`: 文字起こしモデル。デフォルト `scribe_v2`
- `language`: 言語コード。デフォルト `jpn` (日本語)

#### [KEYS] セクション
キーボードショートカットのキーバインディング
- `toggle_recording`: 録音開始/停止。デフォルト `pause`
- `exit_app`: アプリケーション終了。デフォルト `esc`
- `reload_audio`: 音声ファイル再ロード。デフォルト `f8`
- `toggle_punctuation`: 句読点機能切り替え。デフォルト `f9`

#### [PATHS] セクション
- `replacements_file`: テキスト置換ファイルのパス
- `temp_dir`: 一時ファイルの保存先
- `cleanup_minutes`: 一時ファイルのクリーンアップ周期 (分)。デフォルト 240

#### [RECORDING] セクション
- `auto_stop_timer`: 自動停止時間 (秒)。デフォルト 60

#### [OPTIONS] セクション
- `start_minimized`: アプリケーション起動時に最小化。デフォルト `True`

#### [FORMATTING] セクション
- `use_punctuation`: 句読点の自動挿入。デフォルト `True`
- `use_comma`: 句読点機能で読点を使用。デフォルト `True`

#### [CLIPBOARD] セクション
- `paste_delay`: テキスト貼り付けの遅延時間 (秒)。デフォルト 0.2
- `use_sendinput`: Windows SendInput API を使用。デフォルト `True`
- `sendinput_delay`: SendInput の遅延時間 (秒)。デフォルト 0.05

#### [LOGGING] セクション
- `log_level`: ログレベル (`DEBUG`、`INFO`、`WARNING`、`ERROR`、`CRITICAL`)
- `log_directory`: ログファイルの保存先。デフォルト `logs`
- `log_retention_days`: ログファイルの保持期間 (日)。デフォルト 7
- `debug_mode`: デバッグモードの有効化。デフォルト `True`

## 依存関係

### 主要パッケージ

| パッケージ | バージョン | 用途 |
|-----------|-----------|------|
| elevenlabs | 2.25.0 | Speech-to-Text API クライアント |
| PyAudio | 0.2.14 | 音声録音 |
| keyboard | 0.13.5 | グローバルキーボードショートカット |
| pyperclip | 1.9.0 | クリップボード操作 |
| python-dotenv | 1.1.1 | 環境変数管理 |
| pywin32-ctypes | 0.2.3 | Windows API インターフェース |
| pyinstaller | 6.14.2 | 実行可能ファイル生成 |
| pytest | 8.4.1 | テストフレームワーク |
| pytest-cov | 6.2.1 | テストカバレッジ測定 |
| pytest-mock | 3.14.1 | テスト用モック機能 |
| pyright | 1.1.407 | 静的型チェッカー |

すべての依存関係は `requirements.txt` で管理されています

## トラブルシューティング

### 「ELEVENLABS_API_KEY が未設定です」エラー

`.env` ファイルが存在することと、`ELEVENLABS_API_KEY` が正しく設定されていることを確認してください

```bash
# .env ファイルの確認
cat .env
```

### 「設定ファイルが見つかりません」エラー

`utils/config.ini` が存在することを確認してください。開発環境ではプロジェクトルートの `utils/` ディレクトリに配置します

```bash
ls utils/config.ini
```

### 音声が録音されない

1. Windows の設定でマイクが有効か確認
2. PyAudio が正しくインストールされているか確認
   ```bash
   python -c "import pyaudio; print('PyAudio OK')"
   ```
3. 別のアプリケーションがマイクを排他的に使用していないか確認

### テキスト貼り付けが機能しない

1. `utils/config.ini` の `[CLIPBOARD]` セクションで `use_sendinput = True` に設定
2. アプリケーションを管理者権限で実行してみる
3. 対象アプリケーションがテキスト入力に対応しているか確認

### テスト実行時に PyAudio エラーが発生

テスト環境では PyAudio がモック化されます。`pytest-mock` がインストールされていることを確認してください

```bash
pip install pytest-mock
```

## ライセンス

このプロジェクトのライセンス情報については、プロジェクトルートの LICENSE ファイルを参照してください

## サポート

問題が発生した場合は、`logs/` ディレクトリのログファイルと `error_log.txt` を確認してください。詳細なエラー情報が記録されています
