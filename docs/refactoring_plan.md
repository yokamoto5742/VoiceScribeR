# VoiceScribe リファクタリング実行計画

## 概要

| 項目 | 内容 |
|------|------|
| プロジェクト名 | VoiceScribe v2.0 |
| 目的 | ElevenLabs Realtime API の特性を最大限に活かす構成への移行 |
| フレームワーク | Tkinter → PyQt6 |
| 処理方式 | バッチ処理廃止、リアルタイム処理に統一 |
| 推定期間 | 5フェーズ（各フェーズ独立してテスト可能） |

---

## フェーズ一覧

```
Phase 1: 基盤構築        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Phase 2: インフラ層      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Phase 3: アプリケーション層 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Phase 4: プレゼンテーション層 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Phase 5: 統合・最適化    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Phase 1: 基盤構築

### 目標
- 新しいプロジェクト構造の作成
- 依存関係の整理
- 設定管理の刷新
- ドメインモデルの定義

### Step 1.1: プロジェクト構造作成

**タスク:**
```
□ 新規ディレクトリ構造を作成
□ __init__.py ファイルを各パッケージに配置
```

**成果物:**
```
voice_scribe_v2/
├── main.py
├── pyproject.toml
├── requirements.txt
├── presentation/
│   ├── __init__.py
│   └── widgets/
│       └── __init__.py
├── application/
│   └── __init__.py
├── infrastructure/
│   └── __init__.py
├── domain/
│   └── __init__.py
└── config/
    └── __init__.py
```

### Step 1.3: 設定管理の刷新

**タスク:**
```
□ Pydantic Settings を使用した型安全な設定クラス作成
□ 環境変数との統合
□ 設定のバリデーション機能追加
```

**ファイル:** `config/settings.py`

**設定クラス設計:**
```python
# 構造イメージ
class AudioSettings:
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 512  # 最適化: 1024 → 512

class RealtimeApiSettings:
    model: str = "scribe_v2_realtime"
    language: str = "jpn"
    vad_silence_threshold: float = 0.5
    
class HotkeySettings:
    toggle_recording: str = "pause"
    exit_app: str = "esc"
    toggle_punctuation: str = "f9"

class AppSettings:
    audio: AudioSettings
    realtime_api: RealtimeApiSettings
    hotkeys: HotkeySettings
    # ... 他の設定
```

### Step 1.4: ドメインモデル定義

**タスク:**
```
□ Transcript モデル（部分結果/確定結果）
□ ReplacementRule モデル
□ RecordingState 列挙型
□ カスタム例外クラス
```

**ファイル:** `domain/models.py`, `domain/exceptions.py`

**モデル設計:**
```python
# domain/models.py 構造イメージ
from enum import Enum, auto
from dataclasses import dataclass
from datetime import datetime

class TranscriptType(Enum):
    PARTIAL = auto()   # 部分結果
    COMMITTED = auto()  # 確定結果

@dataclass
class Transcript:
    text: str
    type: TranscriptType
    timestamp: datetime
    is_processed: bool = False

class RecordingState(Enum):
    IDLE = auto()
    CONNECTING = auto()
    READY = auto()
    RECORDING = auto()
    PROCESSING = auto()
    ERROR = auto()
```

### Step 1.5: Phase 1 検証

**検証項目:**
```
□ すべてのパッケージがインポート可能
□ 設定ファイルの読み込みテスト
□ ドメインモデルの単体テスト
□ PyQt6 の基本動作確認
```

---

## Phase 2: インフラストラクチャ層

### 目標
- WebSocketクライアントの再設計
- 音声録音モジュールの最適化
- キーボードリスナーのPyQt6対応

### Step 2.1: WebSocketクライアント再設計

**タスク:**
```
□ 非同期専用クライアントクラス作成
□ 自動再接続機能の実装
□ バックプレッシャー制御の実装
□ 接続状態の監視機能
```

**ファイル:** `infrastructure/realtime_client.py`

**クラス設計:**
```python
# 構造イメージ
class RealtimeTranscriptionClient:
    """ElevenLabs Realtime API WebSocketクライアント"""
    
    # Signal定義（PyQt6）
    partial_transcript_received = pyqtSignal(Transcript)
    committed_transcript_received = pyqtSignal(Transcript)
    connection_state_changed = pyqtSignal(ConnectionState)
    error_occurred = pyqtSignal(Exception)
    
    async def connect(self) -> bool
    async def disconnect(self)
    async def send_audio(self, data: bytes)
    async def receive_loop(self)
    
    # 内部メソッド
    async def _handle_reconnect(self)
    async def _apply_backpressure(self)
```

**再接続ロジック:**
```
接続失敗/切断
    │
    ▼
再接続カウンター確認 (max: 5回)
    │
    ├─ 上限未達 ─→ 指数バックオフ待機 (1s, 2s, 4s, 8s, 16s)
    │                  │
    │                  ▼
    │              再接続試行
    │                  │
    │                  ├─ 成功 ─→ カウンターリセット
    │                  │
    │                  └─ 失敗 ─→ ループ先頭へ
    │
    └─ 上限到達 ─→ エラーSignal発火 → ユーザー通知
```

### Step 2.2: 音声録音モジュール最適化

**タスク:**
```
□ PyAudio録音をQThread内で実行
□ チャンクサイズの最適化（512 samples）
□ 音声データキューの実装
□ 録音状態の監視Signal
```

**ファイル:** `infrastructure/audio_recorder.py`

**クラス設計:**
```python
# 構造イメージ
class AudioRecorderWorker(QThread):
    """音声録音ワーカースレッド"""
    
    audio_chunk_ready = pyqtSignal(bytes)
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()
    error_occurred = pyqtSignal(Exception)
    
    def __init__(self, settings: AudioSettings)
    def run(self)  # QThread のメインループ
    def start_recording(self)
    def stop_recording(self)
```

**音声パイプライン:**
```
PyAudio入力 (16kHz, 16bit, mono)
    │
    ▼
512 samples/チャンク (32ms)
    │
    ▼
audio_chunk_ready Signal
    │
    ▼
WebSocketクライアント
```

### Step 2.3: キーボードリスナーのPyQt6対応

**タスク:**
```
□ グローバルホットキー登録
□ PyQt6 Signal との連携
□ キー設定の動的変更対応
```

**ファイル:** `infrastructure/keyboard_listener.py`

**クラス設計:**
```python
# 構造イメージ
class GlobalHotkeyManager(QObject):
    """グローバルホットキー管理"""
    
    toggle_recording_pressed = pyqtSignal()
    toggle_punctuation_pressed = pyqtSignal()
    exit_app_pressed = pyqtSignal()
    
    def register_hotkeys(self, settings: HotkeySettings)
    def unregister_all(self)
    def update_hotkey(self, action: str, new_key: str)
```

### Step 2.4: Phase 2 検証

**検証項目:**
```
□ WebSocket接続・切断テスト
□ 再接続機能の動作確認
□ 音声録音の品質確認（無音・有音）
□ ホットキーの応答性テスト
□ 各コンポーネントの単体テスト
```

**テストスクリプト例:**
```python
# tests/test_realtime_client.py
async def test_connection():
    client = RealtimeTranscriptionClient(settings)
    assert await client.connect() == True
    assert client.is_connected == True
    await client.disconnect()
    assert client.is_connected == False
```

---

## Phase 3: アプリケーション層

### 目標
- オーケストレーターの実装
- テキスト後処理パイプライン
- イベントシステムの構築

### Step 3.1: 状態管理とオーケストレーター

**タスク:**
```
□ 状態マシンの実装
□ 各コンポーネントの協調制御
□ エラーハンドリングの一元化
□ ログ出力の統合
```

**ファイル:** `application/orchestrator.py`

**クラス設計:**
```python
# 構造イメージ
class TranscriptionOrchestrator(QObject):
    """文字起こし全体の制御"""
    
    # 状態変更Signal
    state_changed = pyqtSignal(RecordingState)
    
    # テキスト関連Signal
    partial_text_ready = pyqtSignal(str)      # UI表示用（グレー）
    committed_text_ready = pyqtSignal(str)    # UI表示用（黒）
    processed_text_ready = pyqtSignal(str)    # 後処理済み（貼り付け用）
    
    # エラーSignal
    error_occurred = pyqtSignal(str, str)  # (title, message)
    
    def __init__(
        self,
        recorder: AudioRecorderWorker,
        client: RealtimeTranscriptionClient,
        text_processor: TextPostProcessor,
        settings: AppSettings
    )
    
    # 公開メソッド
    def start_recording(self)
    def stop_recording(self)
    def toggle_recording(self)
    def toggle_punctuation(self)
    
    # 内部メソッド
    def _on_audio_chunk(self, data: bytes)
    def _on_partial_transcript(self, transcript: Transcript)
    def _on_committed_transcript(self, transcript: Transcript)
    def _handle_state_transition(self, new_state: RecordingState)
```

**状態遷移表:**
```
| 現在の状態   | イベント           | 次の状態     | アクション                    |
|-------------|-------------------|-------------|------------------------------|
| IDLE        | start_recording   | CONNECTING  | WebSocket接続開始            |
| CONNECTING  | connected         | READY       | 録音準備完了通知              |
| CONNECTING  | error             | ERROR       | エラー表示、再試行オプション   |
| READY       | start_capture     | RECORDING   | 音声キャプチャ開始            |
| RECORDING   | partial_received  | RECORDING   | 部分テキストをUI表示          |
| RECORDING   | committed_received| RECORDING   | 確定テキストを処理・貼り付け   |
| RECORDING   | stop_recording    | PROCESSING  | 最終処理実行                  |
| PROCESSING  | complete          | READY       | 次の録音待機                  |
| PROCESSING  | disconnect        | IDLE        | 接続終了                      |
| ERROR       | retry             | CONNECTING  | 再接続試行                    |
| ERROR       | cancel            | IDLE        | 初期状態に戻る                |
| *           | force_stop        | IDLE        | 強制終了                      |
```

### Step 3.2: テキスト後処理パイプライン

**タスク:**
```
□ 句読点処理
□ 置換ルール適用
□ 処理パイプラインの構築
□ 置換ルールの動的リロード
```

**ファイル:** `application/text_processor.py`

**クラス設計:**
```python
# 構造イメージ
class TextPostProcessor:
    """テキスト後処理パイプライン"""
    
    def __init__(self, settings: AppSettings)
    
    def process(self, text: str) -> str:
        """メイン処理パイプライン"""
        text = self._apply_punctuation_rules(text)
        text = self._apply_replacements(text)
        return text
    
    def _apply_punctuation_rules(self, text: str) -> str
    def _apply_replacements(self, text: str) -> str
    
    def reload_replacements(self)
    def set_punctuation_enabled(self, enabled: bool)
```

**処理パイプライン:**
```
入力テキスト
    │
    ▼
┌─────────────────┐
│ 句読点処理       │ ← use_punctuation 設定に依存
│ 。、の削除/保持  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 置換ルール適用   │ ← replacements.txt
│ 医療用語変換等   │
└────────┬────────┘
         │
         ▼
出力テキスト
```

### Step 3.3: クリップボード管理

**タスク:**
```
□ スレッドセーフなクリップボード操作
□ 貼り付け遅延の最適化
□ エラーリカバリー
```

**ファイル:** `application/clipboard_manager.py`

**クラス設計:**
```python
# 構造イメージ
class ClipboardManager(QObject):
    """クリップボード操作管理"""
    
    paste_completed = pyqtSignal()
    paste_failed = pyqtSignal(str)
    
    def __init__(self, settings: AppSettings)
    
    def copy_and_paste(self, text: str)
    def copy_only(self, text: str) -> bool
    
    # 内部メソッド
    def _safe_copy(self, text: str) -> bool
    def _safe_paste(self) -> bool
    def _verify_clipboard(self, expected: str) -> bool
```

### Step 3.4: Phase 3 検証

**検証項目:**
```
□ 状態遷移の正確性テスト
□ テキスト処理パイプラインテスト
□ クリップボード操作の信頼性テスト
□ 各Signal/Slotの接続テスト
□ エラーハンドリングのシナリオテスト
```

---

## Phase 4: プレゼンテーション層

### 目標
- PyQt6によるUI実装
- リアルタイム文字表示
- モダンなデザイン

### Step 4.1: メインウィンドウ

**タスク:**
```
□ メインウィンドウレイアウト
□ システムトレイ統合
□ ウィンドウ状態の保存/復元
```

**ファイル:** `presentation/main_window.py`

**レイアウト設計:**
```
┌─────────────────────────────────────────────┐
│ VoiceScribe v2.0                    [_][□][×]│
├─────────────────────────────────────────────┤
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │         TranscriptView              │   │
│  │  (リアルタイム文字表示エリア)         │   │
│  │                                     │   │
│  │  部分結果: グレー文字               │   │
│  │  確定結果: 黒文字                   │   │
│  │                                     │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │         ControlPanel                │   │
│  │  [🎤 録音開始/停止]  [句読点: ON]    │   │
│  │  [置換設定]  [設定]                 │   │
│  └─────────────────────────────────────┘   │
│                                             │
├─────────────────────────────────────────────┤
│ ● 待機中 | Pause: 録音 | Esc: 終了          │
└─────────────────────────────────────────────┘
```

### Step 4.2: TranscriptView（リアルタイム表示）

**タスク:**
```
□ 部分結果と確定結果の視覚的区別
□ スクロール自動追従
□ テキスト選択・コピー機能
```

**ファイル:** `presentation/widgets/transcript_view.py`

**クラス設計:**
```python
# 構造イメージ
class TranscriptView(QTextEdit):
    """リアルタイム文字起こし表示ウィジェット"""
    
    def __init__(self, parent=None)
    
    # スロット
    @pyqtSlot(str)
    def show_partial(self, text: str):
        """部分結果を表示（グレー、イタリック）"""
    
    @pyqtSlot(str)
    def show_committed(self, text: str):
        """確定結果を表示（黒、通常）"""
    
    def clear_partial(self):
        """部分結果をクリア"""
    
    def clear_all(self):
        """全てクリア"""
```

**表示スタイル:**
```
部分結果（partial）:
  - 色: #888888（グレー）
  - スタイル: イタリック
  - 末尾に "..." を追加

確定結果（committed）:
  - 色: #000000（黒）
  - スタイル: 通常
  - 部分結果を置換して表示
```

### Step 4.3: ControlPanel（操作パネル）

**タスク:**
```
□ 録音ボタン（状態に応じてアイコン/テキスト変更）
□ 句読点トグルボタン
□ 設定ボタン
□ キーボードショートカット表示
```

**ファイル:** `presentation/widgets/control_panel.py`

### Step 4.4: StatusBar（ステータスバー）

**タスク:**
```
□ 接続状態インジケーター
□ 録音時間表示
□ ホットキーヒント表示
```

**ファイル:** `presentation/widgets/status_bar.py`

### Step 4.5: 設定ダイアログ

**タスク:**
```
□ 一般設定タブ
□ 音声設定タブ
□ ホットキー設定タブ
□ 置換ルールエディタ
```

**ファイル:** `presentation/dialogs/settings_dialog.py`

### Step 4.6: スタイルシート

**タスク:**
```
□ 全体的なテーマ定義
□ ダークモード対応（オプション）
□ ボタン・ラベルのスタイル統一
```

**ファイル:** `presentation/styles/theme.qss`

### Step 4.7: Phase 4 検証

**検証項目:**
```
□ UI起動・終了テスト
□ 各ウィジェットの表示テスト
□ ボタン操作の応答性テスト
□ リアルタイム表示のパフォーマンステスト
□ ウィンドウリサイズ時のレイアウト確認
```

---

## Phase 5: 統合・最適化

### 目標
- 全コンポーネントの統合
- パフォーマンス最適化
- ドキュメント整備
- 配布準備

### Step 5.1: 全体統合

**タスク:**
```
□ main.py でのDI（依存性注入）設定
□ 全Signal/Slotの接続
□ アプリケーションライフサイクル管理
□ 例外ハンドリングの最終確認
```

**ファイル:** `main.py`

**起動シーケンス:**
```
main.py
    │
    ▼
1. 設定読み込み (AppSettings)
    │
    ▼
2. インフラ層初期化
   - AudioRecorderWorker
   - RealtimeTranscriptionClient
   - GlobalHotkeyManager
    │
    ▼
3. アプリケーション層初期化
   - TextPostProcessor
   - ClipboardManager
   - TranscriptionOrchestrator
    │
    ▼
4. プレゼンテーション層初期化
   - MainWindow
   - 各ウィジェット
    │
    ▼
5. Signal/Slot接続
    │
    ▼
6. イベントループ開始
    │
    ▼
7. (終了時) クリーンアップ
```

### Step 5.2: パフォーマンス最適化

**タスク:**
```
□ 音声送信レイテンシの計測・最適化
□ UI更新頻度の調整
□ メモリ使用量の監視・最適化
□ CPU使用率の最適化
```

**最適化ポイント:**
```
1. 音声チャンクサイズ: 512 samples (32ms)
   - 低レイテンシと安定性のバランス

2. WebSocket送信バッファ:
   - 最大10チャンクをバッファリング
   - バックプレッシャー発生時は古いデータを破棄

3. UI更新間隔:
   - 部分結果: 最大10回/秒に制限
   - 確定結果: 即座に反映

4. メモリ管理:
   - TranscriptViewの最大行数制限（1000行）
   - 古いログの自動削除
```

### Step 5.3: エラーハンドリング強化

**タスク:**
```
□ グローバル例外ハンドラー設定
□ エラーログの詳細化
□ ユーザー向けエラーメッセージの改善
□ クラッシュレポート機能（オプション）
```

### Step 5.4: テスト整備

**タスク:**
```
□ 単体テストの完成
□ 統合テストの作成
□ E2Eテストの作成
□ パフォーマンステストの作成
```

**テスト構成:**
```
tests/
├── unit/
│   ├── test_settings.py
│   ├── test_models.py
│   ├── test_text_processor.py
│   └── test_clipboard.py
├── integration/
│   ├── test_realtime_client.py
│   ├── test_orchestrator.py
│   └── test_audio_pipeline.py
└── e2e/
    ├── test_full_workflow.py
    └── test_ui_interactions.py
```

### Step 5.5: ドキュメント整備

**タスク:**
```
□ README.md の更新
□ インストール手順
□ 設定ファイルの説明
□ トラブルシューティングガイド
□ API/クラスリファレンス（オプション）
```

### Step 5.6: 配布準備

**タスク:**
```
□ PyInstaller設定の更新
□ 実行ファイルのビルドテスト
□ インストーラー作成（オプション）
□ バージョン番号の更新
```

### Step 5.7: Phase 5 検証

**検証項目:**
```
□ フル機能統合テスト
□ 長時間稼働テスト（1時間以上）
□ メモリリークチェック
□ 配布パッケージの動作確認
□ 旧バージョンからの移行テスト
```

---

## リスクと対策

| リスク | 影響度 | 発生確率 | 対策 |
|-------|--------|---------|------|
| PyQt6のライセンス問題 | 中 | 低 | GPL/商用ライセンスの確認、PySide6への切り替え検討 |
| WebSocket接続の不安定性 | 高 | 中 | 自動再接続、エクスポネンシャルバックオフの実装 |
| 音声遅延の増加 | 高 | 中 | チャンクサイズ調整、バッファ管理の最適化 |
| Windows以外での動作 | 低 | 低 | keyboardライブラリのOS別対応確認 |
| ElevenLabs API仕様変更 | 中 | 低 | バージョン固定、変更監視 |

---

## 成果物チェックリスト

### Phase 1 完了条件
- [ ] ディレクトリ構造作成完了
- [ ] requirements.txt 更新完了
- [ ] 設定クラス実装完了
- [ ] ドメインモデル実装完了
- [ ] 基本的なテスト通過

### Phase 2 完了条件
- [ ] WebSocketクライアント実装完了
- [ ] 音声録音モジュール実装完了
- [ ] キーボードリスナー実装完了
- [ ] 各コンポーネントの単体テスト通過

### Phase 3 完了条件
- [ ] オーケストレーター実装完了
- [ ] テキスト処理パイプライン実装完了
- [ ] クリップボード管理実装完了
- [ ] 状態遷移テスト通過

### Phase 4 完了条件
- [ ] メインウィンドウ実装完了
- [ ] 全ウィジェット実装完了
- [ ] スタイルシート適用完了
- [ ] UIテスト通過

### Phase 5 完了条件
- [ ] 全体統合完了
- [ ] パフォーマンス目標達成
- [ ] 全テスト通過
- [ ] ドキュメント整備完了
- [ ] 配布パッケージ作成完了

---

## 付録

### A. 必要なPyQt6の知識

```python
# Signal/Slot の基本
class MyClass(QObject):
    my_signal = pyqtSignal(str)
    
    def emit_signal(self):
        self.my_signal.emit("data")

# QThread の使い方
class Worker(QThread):
    result_ready = pyqtSignal(object)
    
    def run(self):
        # バックグラウンド処理
        result = heavy_computation()
        self.result_ready.emit(result)

# asyncio との統合
class AsyncWorker(QThread):
    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.async_main())
```

### B. 参考リンク

- [PyQt6 Documentation](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [ElevenLabs Scribe V2 Realtime API](https://elevenlabs.io/docs/api-reference/speech-to-text-realtime)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)

---

## 更新履歴

| 日付 | バージョン | 内容 |
|------|-----------|------|
| 2025-12-04 | 1.0 | 初版作成 |
