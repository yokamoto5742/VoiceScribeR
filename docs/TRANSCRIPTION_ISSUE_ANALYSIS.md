# VoiceScribeR 文字起こし問題 調査報告書

## 1. 問題概要

| 項目 | 内容 |
|------|------|
| 症状 | ElevenLabs APIに接続は成功するが、文字起こしがうまくいかない |
| 対象バージョン | v2.0 (PyQt6 + qasync) |
| 調査日 | 2025-12-06 |

---

## 2. アーキテクチャ概要

### 2.1 コンポーネント構成

```
main.py (エントリポイント)
    ↓
TranscriptionOrchestrator (application/orchestrator.py)
    ├── RealtimeTranscriptionClient (infrastructure/realtime_client.py)
    │       └── WebSocket経由でElevenLabs APIに接続
    ├── AudioRecorderWorker (infrastructure/audio_recorder.py)
    │       └── QThreadで音声録音
    ├── TextPostProcessor (application/text_processor.py)
    └── ClipboardManager (application/clipboard_manager.py)
```

### 2.2 文字起こしフロー

```
1. start_recording()
   ↓
2. WebSocket接続 (RealtimeTranscriptionClient.connect())
   ↓
3. 音声録音開始 (AudioRecorderWorker.start_recording())
   ↓
4. 音声チャンク送信ループ
   ├── AudioRecorderWorker → audio_chunk_ready(bytes) Signal
   ├── Orchestrator._on_audio_chunk() → send_audio()
   └── WebSocket経由でElevenLabsに送信
   ↓
5. テキスト受信ループ
   ├── RealtimeTranscriptionClient.receive_loop()
   ├── partial_transcript_received Signal (部分結果)
   └── committed_transcript_received Signal (確定結果)
   ↓
6. テキスト処理 → クリップボード → 貼り付け
```

---

## 3. 発見された問題点

### 3.1 致命的問題（P0）- 文字起こし失敗の直接原因

#### 問題1: WebSocket接続状態判定の不安定性

**場所:** `infrastructure/realtime_client.py:43-59`

**現状のコード:**
```python
def _check_connected(self) -> bool:
    if self._ws is None:
        return False
    try:
        state = self._ws.state
        if hasattr(state, 'value'):
            return state.value == 1
        return state == "OPEN" or state == 1
    except AttributeError:
        ...
```

**問題点:**
- `websockets 15.x` の `state` プロパティの値が環境やバージョンによって異なる
- `state.value == 1` と `state == "OPEN"` の両方をチェックしているが、信頼性が低い
- 接続状態を誤認識すると、音声データが送信されない

**修正案:**
```python
def _check_connected(self) -> bool:
    return self._ws is not None and self._ws.open
```

---

#### 問題2: APIエラーメッセージの無視

**場所:** `external_service/elevenlabs_api.py:316-319`

**現状のコード:**
```python
if msg_type == "error":
    error_msg = data.get("message", "Unknown error")
    logger.error(f"Error from server: {error_msg}")
    # ← ユーザーへの通知なし、処理続行
```

**問題点:**
- サーバーからのエラーメッセージがログに記録されるだけ
- ユーザーには何も通知されず、「接続はしているが動かない」状態になる
- APIキー無効、レート制限、モデルアクセス権限不足などが検出できない

**修正案:**
```python
if msg_type == "error":
    error_msg = data.get("message", "Unknown error")
    logger.error(f"Error from server: {error_msg}")
    self.error_occurred.emit(TranscriptionError(error_msg))
    await self.disconnect()
```

---

#### 問題3: 再接続機能の欠如

**場所:** 全体（`infrastructure/realtime_client.py`）

**問題点:**
- ネットワーク切断やサーバー側の切断時に再接続ロジックがない
- 一度接続が切れると、ユーザーが手動で再起動するまで復旧しない
- 接続切断時のSignal発火はあるが、自動再接続は未実装

**修正案:**
```python
class ReconnectionManager:
    MAX_RETRIES = 3
    INITIAL_DELAY = 1.0
    BACKOFF_FACTOR = 2.0

    async def connect_with_retry(self, connect_func):
        delay = self.INITIAL_DELAY
        for attempt in range(self.MAX_RETRIES):
            try:
                return await connect_func()
            except (ConnectionError, websockets.exceptions.WebSocketException):
                if attempt == self.MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(delay)
                delay *= self.BACKOFF_FACTOR
```

---

#### 問題4: APIキー検証の欠如

**場所:** `infrastructure/realtime_client.py:87-91`

**問題点:**
- 接続前にAPIキーの有効性をチェックしていない
- 無効なAPIキーでWebSocket接続を試みると、接続自体は成功するがデータ送受信で失敗
- ユーザーには原因不明のエラーとして見える

**修正案:**
```python
async def connect(self):
    if not await self._validate_api_key():
        raise AuthenticationError("APIキーが無効または期限切れです")

    try:
        self._ws = await asyncio.wait_for(
            websockets.connect(self._ws_url, ...),
            timeout=10.0
        )
    except asyncio.TimeoutError:
        raise ConnectionError("WebSocket接続がタイムアウトしました")
```

---

### 3.2 重要問題（P1）

#### 問題5: タイムアウト設定なし

**場所:** `infrastructure/realtime_client.py:91`

**問題点:**
- WebSocket接続時のタイムアウトがデフォルト値に依存
- ネットワーク遅延時に無限待機の可能性

---

#### 問題6: 空文字列/無音の処理不足

**場所:** `external_service/elevenlabs_api.py:90-96`

**問題点:**
- APIが空文字列を返した場合、警告ログのみで処理続行
- ユーザーには「何も起きない」状態として見える

---

#### 問題7: ClipboardManager実装の不完全

**場所:** `application/clipboard_manager.py:76-80`

**問題点:**
- 貼り付け処理のコードが途中で切れている可能性
- テキストが正常に取得されても貼り付けで失敗する

---

### 3.3 軽微問題（P2）

| 問題 | 場所 | 影響 |
|------|------|------|
| 設定パラメータの分散 | `config/settings.py`, `utils/config.ini` | 設定変更時の不整合 |
| 正規表現エラーの無視 | `application/text_processor.py:65-74` | 置換ルールがスキップされる |
| v1.0コードの残存 | `scripts/voice_scribe_v1/` | 混乱の原因 |

---

## 4. 推奨修正優先順位

### Phase 1: 致命的問題の修正（即座に対応）

```
1. WebSocket接続状態判定の修正
   → infrastructure/realtime_client.py:_check_connected()

2. APIエラーメッセージの通知実装
   → external_service/elevenlabs_api.py:_handle_message()

3. 再接続ロジックの実装
   → infrastructure/realtime_client.py に ReconnectionManager 追加

4. APIキー検証の追加
   → infrastructure/realtime_client.py:connect()
```

### Phase 2: 重要問題の修正

```
5. タイムアウト設定の追加
   → config/settings.py に TimeoutSettings 追加

6. 空文字列/無音の処理改善
   → external_service/elevenlabs_api.py

7. ClipboardManager の完成
   → application/clipboard_manager.py
```

### Phase 3: 既存計画との統合

- `docs/refactoring_plan.md` に記載のフェーズと統合
- 既存のPhase 2（インフラ層）に上記修正を組み込む

---

## 5. 検証手順

### 5.1 問題1の検証（WebSocket接続状態）

```python
# テストコード
async def test_connection_state():
    client = RealtimeTranscriptionClient(settings)
    await client.connect()
    assert client.is_connected == True
    # 接続状態の確認
    print(f"WebSocket state: {client._ws.state}")
    print(f"WebSocket open: {client._ws.open}")
```

### 5.2 問題2の検証（エラーメッセージ）

```python
# 無効なAPIキーで接続を試みる
async def test_invalid_api_key():
    settings.api_key = "invalid_key"
    client = RealtimeTranscriptionClient(settings)
    try:
        await client.connect()
    except AuthenticationError as e:
        print(f"Expected error: {e}")
```

### 5.3 問題3の検証（再接続）

```python
# ネットワーク切断をシミュレート
async def test_reconnection():
    client = RealtimeTranscriptionClient(settings)
    await client.connect()
    # 強制切断
    await client._ws.close()
    # 再接続が発生するか確認
    await asyncio.sleep(5)
    assert client.is_connected == True
```

---

## 6. 修正後の期待動作

| シナリオ | 修正前 | 修正後 |
|---------|--------|--------|
| APIキー無効 | 接続成功→無言で失敗 | エラー通知表示、録音開始せず |
| ネットワーク切断 | 接続切れて終了 | 自動再接続（3回まで） |
| 無音録音 | 無言で完了 | 「音声が検出されませんでした」通知 |
| サーバーエラー | ログのみ | ユーザーに原因表示 |
| 正常な文字起こし | （変更なし） | テキストが正常に貼り付けられる |

---

## 7. 次のステップ

1. **Phase 1の修正を実施**
   - `infrastructure/realtime_client.py` の改修
   - `external_service/elevenlabs_api.py` のエラーハンドリング強化

2. **ユニットテストの追加**
   - `tests/unit/test_realtime_client.py` の作成
   - 各修正箇所のテストケース作成

3. **統合テストの実施**
   - 実際のElevenLabs APIとの接続テスト
   - 各エラーシナリオの確認

---

## 8. 参考情報

### 8.1 関連ファイル一覧

| ファイル | 役割 | 問題関連度 |
|---------|------|-----------|
| `infrastructure/realtime_client.py` | WebSocketクライアント | 高 |
| `external_service/elevenlabs_api.py` | APIクライアント（旧版） | 高 |
| `application/orchestrator.py` | 全体制御 | 中 |
| `application/clipboard_manager.py` | クリップボード操作 | 中 |
| `config/settings.py` | 設定管理 | 低 |

### 8.2 ElevenLabs Realtime API 仕様

- WebSocket URL: `wss://api.elevenlabs.io/v1/speech-to-text/realtime`
- 音声フォーマット: PCM 16kHz 16bit mono
- メッセージタイプ: `partial`, `final`, `error`
