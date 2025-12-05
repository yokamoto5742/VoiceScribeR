# Changelog

VoiceScribe v2.0 の変更履歴

フォーマットは [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) に基づきます。

## [2.0.0] - 2025-12-05

### Added (追加)

#### 基盤構築 (Phase 1)
- レイヤードアーキテクチャの導入 (Domain, Infrastructure, Application, Presentation)
- Pydantic Settings による型安全な設定管理
- ドメインモデルの定義 (Transcript, ReplacementRule, AudioChunk, RecordingSession)
- カスタム例外クラスの実装
- 包括的な単体テスト (20件)

#### インフラストラクチャ層 (Phase 2)
- ElevenLabs Realtime API WebSocketクライアント
  - 自動再接続機能（エクスポネンシャルバックオフ）
  - バックプレッシャー制御
  - PyQt6 Signal統合
- PyAudio + QThread による非同期音声録音
  - チャンクサイズ最適化 (512 samples = 32ms)
- グローバルホットキー管理
  - 動的なホットキー変更対応

#### アプリケーション層 (Phase 3)
- TranscriptionOrchestrator による全体制御
  - 状態管理 (RecordingState)
  - Signal/Slotによるイベント駆動アーキテクチャ
- テキスト後処理パイプライン
  - 句読点処理 (削除/保持)
  - カスタム置換ルール適用
  - 正規表現サポート
- ClipboardManager
  - Windows SendInput API による確実な貼り付け
  - クリップボード検証

#### プレゼンテーション層 (Phase 4)
- PyQt6 メインウィンドウ
  - システムトレイ統合
  - ウィンドウ状態保存/復元
- TranscriptView - リアルタイム文字起こし表示
  - 部分結果（グレー・イタリック）
  - 確定結果（黒・通常）
  - 自動スクロール
  - 最大行数制限 (1000行)
- ControlPanel - 操作パネル
  - 録音トグルボタン
  - 句読点トグルボタン
  - クリアボタン
  - 設定ボタン
- VoiceScribeStatusBar - ステータスバー
  - 接続状態インジケーター
  - 録音時間表示
  - ホットキーヒント
- SettingsDialog - 設定ダイアログ
  - 一般設定、音声設定、録音設定、ホットキー設定
- モダンなスタイルシート (theme.qss)

#### 統合・最適化 (Phase 5)
- main.py による全コンポーネント統合
  - 依存性注入
  - Signal/Slot 完全接続
  - ライフサイクル管理
- グローバル例外ハンドラ
- エラーログ詳細化
- 包括的なドキュメント
  - README.md
  - IMPLEMENTATION_SUMMARY.md
  - COMPLETION_REPORT.md
  - CHANGELOG.md

### Changed (変更)

- **処理方式**: バッチ処理 → リアルタイム処理に完全移行
- **GUI フレームワーク**: Tkinter → PyQt6
- **設定管理**: INI ファイル → Pydantic Settings (環境変数統合)
- **音声録音**: 同期処理 → QThread による非同期処理
- **API**: ElevenLabs Speech-to-Text (バッチ) → Scribe V2 Realtime API

### Removed (削除)

- Tkinter UI コンポーネント
- バッチ処理関連コード
- WAV ファイル保存機能（リアルタイム処理のため不要）
- 旧設定管理システム (config_manager.py)
- 旧 audio_recorder.py (新規実装に置き換え)

### Fixed (修正)

- WebSocket接続の安定性向上（自動再接続）
- クリップボード操作の信頼性向上（SendInput API）
- エラーハンドリングの改善（グローバル例外ハンドラ）

### Performance (パフォーマンス)

- 音声チャンクサイズを 1024 → 512 samples に最適化（遅延32ms）
- バックプレッシャー制御による音声送信の最適化
- UI更新頻度の制限（部分結果: 最大10回/秒）
- TranscriptView の行数制限によるメモリ管理

### Security (セキュリティ)

- API キーを環境変数で管理（.env ファイル）
- Pydantic による設定バリデーション

---

## [1.0.0] - 過去

### Added
- 初期リリース
- ElevenLabs Speech-to-Text API によるバッチ処理
- Tkinter による GUI
- グローバルホットキー対応
- テキスト置換機能

---

## リンク

- [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/)
- [ElevenLabs Scribe V2 Realtime API](https://elevenlabs.io/docs/api-reference/speech-to-text-realtime)
