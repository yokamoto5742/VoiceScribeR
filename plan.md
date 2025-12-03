VoiceScribeRをElevenLabs Scribe V2のリアルタイムAPI（WebSocket）対応に変更するための計画を提案します。

現在の実装は「録音完了 → ファイル保存 → API送信 → テキスト取得」という**バッチ処理**になっています。これを「録音しながら音声データを送信 → リアルタイムでテキスト受信」という**ストリーミング処理**に変更するには、アーキテクチャの大幅な変更が必要です。

以下に段階的な実装計画を提示します。

関連サイト

https://elevenlabs.io/docs/cookbooks/speech-to-text/streaming

# VoiceScribeR リアルタイムAPI化計画

## フェーズ 1: API仕様の確認とクライアントの実装
ElevenLabsのScribe V2リアルタイムAPIはWebSocketを使用します。現在のREST（HTTP）クライアントとは異なる通信層が必要です。

1.  **調査と検証**:
    * ElevenLabsのScribe V2 WebSocketエンドポイント仕様の確認（認証方法、音声フォーマット指定、イベントハンドリング）。
    * `websockets` ライブラリを使用した非同期通信の基本実装。

2.  **`external_service/elevenlabs_api.py` の拡張**:
    * 既存の `transcribe_audio`（ファイルベース）に加え、`RealtimeClient` クラスを追加します。
    * `asyncio` と `websockets` を使用し、以下の機能を実装します：
        * `connect()`: WebSocket接続とハンドシェイク。
        * `send_audio_chunk(data)`: 音声データをバイナリで送信。
        * `receive_text()`: サーバーからの部分的な文字起こし結果（Partial）と確定結果（Final）の受信ジェネレータ。

## フェーズ 2: 音声レコーダーのストリーミング対応
現在の `AudioRecorder` はメモリに全データを貯めてから返していますが、これを逐次処理に変更する必要があります。

1.  **`service/audio_recorder.py` の修正**:
    * 録音データをリスト `self.frames` に貯め込むだけでなく、取得したチャンクを即座に外部（コントローラー）へ渡すコールバック機能、または `queue.Queue` へのプッシュ機能を追加します。
    * PyAudioのストリーム読み取り処理が、WebSocket送信をブロックしないように設計します。

## フェーズ 3: コントローラーの非同期・並行処理化
ここが最も大きな変更点です。Tkinter（GUI）とWebSocket（非同期IO）を共存させる必要があります。

1.  **`service/recording_controller.py` の再設計**:
    * **スレッド構成の変更**:
        * Main Thread: Tkinter UI描画。
        * Recording Thread: PyAudioからの音声取得。
        * Network Thread (Asyncio Loop): WebSocket通信（音声送信とテキスト受信）。
    * **データフローの変更**:
        * `start_recording` でWebSocket接続を開始。
        * 録音中、音声をNetwork Threadへキューイング。
        * 受信したテキストをリアルタイムで `text_processing` に渡し、UI更新キューに入れる。

## フェーズ 4: テキスト処理とUIのリアルタイム更新
部分的な結果（入力中のテキスト）と確定した結果をどう扱うかを定義します。

1.  **`service/text_processing.py` の修正**:
    * ストリーミングで送られてくる断片的なテキストを結合・整形するロジックを追加。
    * 「確定前（グレーアウト等）」と「確定後」のテキストを区別して扱う必要があるか検討（今回は簡易的に、確定した部分から順次貼り付ける方針とします）。

2.  **`service/safe_paste_sendinput.py` の調整**:
    * 頻繁な貼り付け（Paste）が発生するとユーザーの操作を阻害するため、バッファリング（一定文字数または句読点で区切って貼り付け）のロジックを検討します。

## フェーズ 5: 設定とクリーンアップ

1.  **`utils/config.ini` の更新**:
    * リアルタイムAPI用のモデルIDやバッファサイズの設定を追加。

2.  **`requirements.txt` の確認**:
    * `websockets` は既に含まれていますが、`asyncio` 関連で必要なものがないか確認します。

---

### 次のステップ

まずは **フェーズ 1: API仕様の確認** を行うため、Google検索を使用してElevenLabs Scribe V2 Real-time APIの正確なWebSocketエンドポイントとプロトコル仕様を特定します。その後、コードの修正に入ります。

よろしいでしょうか？承認いただければ調査を開始します。
Google検索の結果、ElevenLabs Scribe V2のリアルタイムAPIはWebSocketを使用し、低遅延（<150ms）でのストリーミング文字起こしが可能であることが確認できました。

以下に、既存のVoiceScribeRをリアルタイムAPI（WebSocket）対応に変更するための具体的な実装計画を提示します。

# VoiceScribeR Scribe V2 リアルタイムAPI化計画

## 1. アーキテクチャの変更概要

現在の「録音完了後に一括送信（Batch）」から「録音しながら順次送信（Streaming）」へ変更します。

| コンポーネント | 現行 (Batch) | 変更後 (Real-time Streaming) |
| :--- | :--- | :--- |
| **通信プロトコル** | HTTP (REST API) | WebSocket (wss://) |
| **音声処理** | 全データをメモリ/ファイルに保存 | マイク入力を小分け(Chunk)にして即時Queueへ |
| **テキスト化** | 録音停止後に実行 | 録音中に逐次実行（部分結果と確定結果） |
| **並行処理** | `threading` のみ | `threading` + `asyncio` (WebSocket用) |

## 2. 実装ステップ

### Step 1: バックエンド通信層の実装 (`external_service/elevenlabs_api.py`)
`websockets` ライブラリ（`requirements.txt`に既にある）を使用して、非同期WebSocketクライアントを実装します。

* **クラス追加**: `ElevenLabsRealtimeClient`
* **機能**:
    * WebSocket接続の確立（APIキー認証）。
    * 初期設定（モデル: `scribe_v2`、言語: `jpn`）の送信。
    * 音声データ（chunks）の送信ループ。
    * サーバーからのJSONメッセージ（`partial` / `final`）受信とパース。

### Step 2: 音声入力層のストリーム化 (`service/audio_recorder.py`)
マイク入力を溜め込むのではなく、逐次取り出せるように変更します。

* **変更点**:
    * スレッドセーフな `queue.Queue` を受け取れるように変更。
    * `record()` メソッド内で、読み取った音声データを即座にQueueに `put` する処理を追加。

### Step 3: コントローラーの非同期統合 (`service/recording_controller.py`)
Tkinter（GUI）とWebSocket（Asyncio）を共存させるため、専用のスレッドでイベントループを回します。

* **スレッド構成**:
    1.  **Main Thread (UI)**: Tkinterの描画、ボタン操作。
    2.  **Audio Thread**: PyAudioからのマイク入力 → Queueへ。
    3.  **WebSocket Thread**: Asyncioイベントループ。Queueから音声を取り出して送信し、受信したテキストを処理。
* **ロジック変更**:
    * `start_recording` でWebSocket接続と録音を同時に開始。
    * 受信したテキスト（確定結果）をリアルタイムで `text_processing` に渡し、クリップボード/UIへ反映。

### Step 4: テキスト処理の適応 (`service/text_processing.py`)
ストリーミング特有の「断片的なテキスト」の扱いや、重複貼り付けの防止を考慮します。

* **変更点**:
    * 今回はシンプルに「確定（is_final=True）」したテキストのみを順次処理するロジックを採用し、置換処理やクリップボードコピーへ回します。

### Step 5: 設定とクリーンアップ
* `config.ini`: バッファサイズやWebSocket関連の設定があれば追加（基本は既存設定を流用）。
* 不要になった一時ファイル保存ロジック（WAV保存）の削除または無効化。

## 3. 注意点と対策

* **API仕様**: 正確なWebSocketエンドポイントは `wss://api.elevenlabs.io/v1/speech-to-text/scribe-v2/real-time` (仮定) を使用し、接続時にハンドシェイクを行います。
* **UIのレスポンス**: WebSocket通信がUIをブロックしないよう、スレッド間のデータ受け渡しは `queue` と `master.after` を徹底して使用します。

---

この計画に基づき、コードの修正作業を開始しますか？