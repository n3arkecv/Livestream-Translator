# ⚙️ Module Specification — Real-Time YouTube Live Translation App

---

## 🧱 模組總覽

| 模組名稱 | 類型 | 關鍵職責 | 主要依賴 |
|-----------|------|-----------|-----------|
| GUI 模組 | 前端 | 使用者介面、控制流程、設定輸入 | PyQt / PySide |
| Overlay 模組 | 前端 | 顯示字幕、翻譯結果與情境 | PyQt / PySide |
| Audio Capture 模組 | 主流程 | 使用 WASAPI (pyaudiowpatch) Loopback 模式捕獲系統音頻輸出並產生重疊 Chunk | pyaudiowpatch / numpy |
| STT 模組 | 主流程 | 將音訊 Chunk 轉錄為文字（partial/final） | FasterWhisper / GPT-4o / Gemini |
| LLM 翻譯模組 | 主流程 | 翻譯句子（LLM1）並維護情境（LLM2） | OpenAI API / Async HTTP |
| Scenario Context 管理模組 | 主流程 | 管理語境記憶（200–500 tokens） | JSON / internal buffer |
| System Log 模組 | 後台 | 紀錄事件與錯誤、彩色輸出 | logging / colorama |
| Dialogue Log 模組 | 後台 | 紀錄原文/翻譯/情境/時間戳 | pandas / json / csv |
| Runtime Check 模組 | 系統 | 啟動時檢查環境與模型 | subprocess / os |
| Config 模組 | 系統 | 管理使用者設定與模型選項 | JSON |

---

## 🧭 事件命名規則（簡述）

- 形式：`<領域>.<動作>`，例如：`app.started`、`audio.chunk_ready`  
- 錯誤事件：`*.error`；警告：`*.warning`；資訊：`*.info`  
- 事件皆攜帶 `timestamp`、`session_id`；必要時附 `latency_ms`、`seq`（流水號）

通用事件 Payload（基底）：
```json
{
  "event": "string",
  "timestamp": "ISO-8601",
  "session_id": "string",
  "seq": 123,
  "latency_ms": 0
}
````

---

## 🔌 全域事件總覽（對齊圖中每一步）

| 序  | 事件名稱                         | 來源模組          | 關鍵欄位(補充於基底)                                         | 說明                       |
| -- | ---------------------------- | ------------- | --------------------------------------------------- | ------------------------ |
| 1  | app.started                  | GUI           | config_snapshot                                     | 使用者啟動應用，GUI/Overlay 先上線  |
| 2  | runtime.check_started        | Runtime Check |                                                     | 開始檢查環境/模型                |
| 3  | runtime.check_result         | Runtime Check | ok, missing_items[]                                 | 檢查結果；若缺少則 GUI 提示         |
| 4  | model.warmup_started         | STT / LLM     | model, mode                                         | 預熱本地模型或 API 連線           |
| 5  | model.warmup_finished        | STT / LLM     | success                                             | 完成預熱                     |
| 6  | app.pipeline_ready           | Core          |                                                     | 主流程可接受「開始」               |
| 7  | app.start_pressed            | GUI           |                                                     | 使用者按「開始」                 |
| 8  | audio.stream_opened          | Audio         | device_name, sample_rate, channels                  | 開啟 WASAPI Loopback 設備              |
| 9  | audio.chunk_ready            | Audio         | chunk_id, overlap_ms, duration_ms                   | 產出帶重疊的 Chunk（float32, 44100Hz）             |
| 10 | stt.decode_started           | STT           | chunk_id, backend                                   | 開始解碼                     |
| 11 | stt.partial                  | STT           | text_partial                                        | 局部轉錄（Overlay 逐字）         |
| 12 | stt.boundary_detected        | STT           | reason (silence/punc/timeout)                       | 偵測句界                     |
| 13 | stt.final_sentence           | STT           | sentence_id, text, lang                             | 輸出完整句（Fully Transcribed Sentence，進 LLM）             |
| 14 | stt.revise_previous          | STT           | prev_sentence_id, new_text                          | 前一句校正覆寫（對齊圖：Review & Correction previous sentence）          |
| 15 | llm1.translate_started       | LLM           | sentence_id                                         | LLM1 翻譯起始（輸入：Scenario Context + Fully Transcribed Sentence）                |
| 16 | llm1.translate_finished      | LLM           | sentence_id, translated_text, tokens_in, tokens_out | 翻譯完成（輸出：Translated Sentence，供顯示與記錄）             |
| 17 | llm2.context_update_started  | LLM           | context_len_before                                  | LLM2/第二輪：更新情境（輸入：原始 Scenario Context + Translated Sentence）            |
| 18 | llm2.context_update_finished | LLM           | context_len_after, context_snippet                  | 產出新 Scenario Context（輸出：New Scenario Context）     |
| 19 | overlay.partial_updated      | Overlay       | text_partial                                        | Ongoing Sentence 更新      |
| 20 | overlay.translation_rendered | Overlay       | sentence_id                                         | Translated Sentence 顯示完成 |
| 21 | overlay.context_rendered     | Overlay       | context_snippet                                     | Scenario Context 顯示完成    |
| 22 | dialogue.record_appended     | Dialogue Log  | file_path, sentence_id                              | 紀錄一行語料（原文/譯文/情境）         |
| 23 | syslog.info                  | System Log    | message                                             | 一般運作狀態（藍色）               |
| 24 | syslog.warning               | System Log    | message                                             | 警告（黃色）                   |
| 25 | syslog.error                 | System Log    | message, exc                                        | 錯誤（紅色）                   |
| 26 | rate_limit.backpressure      | Core          | queue_len                                           | 產能不足時啟動背壓控管              |
| 27 | retry.scheduled              | Core          | target_event, retry_in_ms                           | API/網路失敗的重試排程            |
| 28 | app.stop_pressed             | GUI           |                                                     | 使用者按「停止」                 |
| 29 | audio.stream_closed          | Audio         |                                                     | 關閉音源                     |
| 30 | app.session_closed           | Core          |                                                     | 清理資源、封存 Log              |

> 提示：`stt.revise_previous` 對應圖中「Review & Correction previous sentence」。

---

## 🧩 GUI 模組（事件擴充）

**新增/擴充 Hooks**

* `on_app_started(config_snapshot)` → 觸發 `app.started`
* `on_start_pressed()` → `app.start_pressed`
* `on_stop_pressed()` → `app.stop_pressed`
* `emit_warning(message)` → `syslog.warning`
* `emit_error(message, exc)` → `syslog.error`

---

## 🧩 Overlay 模組（事件擴充）

**Hooks**

* `update_partial(text)` → 觸發 `overlay.partial_updated`
* `update_translation(sentence_id, text)` → `overlay.translation_rendered`
* `update_context(context_snippet)` → `overlay.context_rendered`

**UI 行為**

* partial 每 ~50–120ms 刷新一次
* translation/context 採原子更新以避免閃爍

---

## 🧩 Audio Capture 模組（事件擴充）

**Hooks**

* `open_stream(device, sample_rate)` → `audio.stream_opened`
* `emit_chunk(chunk_id, overlap_ms, duration_ms, np_array)` → `audio.chunk_ready`
* `close_stream()` → `audio.stream_closed`

**錯誤**

* 裝置被占用 / 取樣率不支援 → `syslog.error`

---

## 🧩 STT 模組（事件擴充）

**Hooks**

* `decode_started(chunk_id, backend)` → `stt.decode_started`
* `emit_partial(text_partial)` → `stt.partial`
* `emit_boundary(reason)` → `stt.boundary_detected`
* `emit_final(sentence_id, text, lang)` → `stt.final_sentence`
* `revise_previous(prev_sentence_id, new_text)` → `stt.revise_previous`

**延遲指標**

* `decode_latency_ms`、`queue_wait_ms` → 寫入 System Log

---

## 🧩 LLM 翻譯模組（事件擴充）

**LLM1：翻譯**

* `translate_started(sentence_id)` → `llm1.translate_started`
* `translate_finished(sentence_id, translated_text, tokens_in, tokens_out, latency_ms)` → `llm1.translate_finished`

**LLM2：情境更新**

* `context_update_started(context_len_before)` → `llm2.context_update_started`
* `context_update_finished(context_len_after, context_snippet)` → `llm2.context_update_finished`

**錯誤/重試**

* API 超時 → `syslog.warning` + `retry.scheduled`
* 重試成功/失敗 → `syslog.info`/`syslog.error`

---

## 🧩 Scenario Context 管理模組（事件擴充）

**Hooks**

* `get_context()`：回傳最近 200–500 tokens 摘要
* `update_context(source_sentence, translated_sentence)`：更新快取
* 重要變更時發出 `llm2.context_update_finished`（由 LLM 模組代理）

---

## 🧩 System Log 模組（事件擴充）

**分級 API**

* `info(message, **kv)` → 觸發 `syslog.info`（🔵）
* `warning(message, **kv)` → `syslog.warning`（🟡）
* `error(message, exc=None, **kv)` → `syslog.error`（🔴）

**建議欄位**

* `component`、`latency_ms`、`chunk_id`、`sentence_id`、`api_model`、`queue_len`

---

## 🧩 Dialogue Log 模組（事件擴充）

**寫入時機**

* 在 `llm1.translate_finished` 與 `llm2.context_update_finished` 之後，寫一筆完整資料；完成後發 `dialogue.record_appended`。

**Row Schema（CSV/TXT 對齊；JSON 同鍵名）**

```
timestamp | session_id | sentence_id | source_language | source_sentence | translated_sentence | context_snippet | tokens_in | tokens_out | latency_ms
```

---

## 🧩 Runtime Check 模組（事件擴充）

**Hooks**

* `check_started()` → `runtime.check_started`
* `check_result(ok, missing_items[])` → `runtime.check_result`
* 缺項列舉：CUDA、ffmpeg、模型檔、API Key 等

---

## 🧩 Config 模組（不變，但補充欄位）

```json
{
  "stt_mode": "local | api",
  "stt_model": "faster-whisper-base.en",
  "llm_api": "gpt-4.1-mini-2025-04-14",
  "audio_device": "Stereo Mix",
  "chunk": { "size_ms": 640, "overlap_ms": 160 },
  "overlay": { "opacity": 0.82, "font_size": 18, "background": true },
  "latency_budget_ms": { "total": 1200, "stt": 500, "llm": 500 },
  "retry": { "max_attempts": 2, "backoff_ms": 400 }
}
```

---

## 🚦 背壓與重試策略（事件互動）

* 當 `queue_len` 超出門檻 → 發 `rate_limit.backpressure`，暫緩音訊入列/降低更新頻率。
* LLM/STT 失敗 → 發 `retry.scheduled`，使用指數退避；超過次數 → `syslog.error` 並標記該句失敗（仍寫入 Dialogue Log，`translated_sentence` 可為空並附 `error_reason`）。

---

## 🧪 端到端單句範例（事件時間線）

**轉錄流程：**
1. `audio.chunk_ready` → 2) `stt.decode_started` → 3) `stt.partial`(多次) →
2. 判斷是否有句子進行中：
   - Yes: `Transcript Words so far` → `Display Transcription so far` → `Review & Correction previous sentence`（循環）
   - No: `Display Last Fully Transcribed sentence`
3. `stt.boundary_detected` → 4) `stt.final_sentence`（Fully Transcribed Sentence）→
4. 存儲到 Dialogue Log（供後續使用：解釋、假名標註等）

**翻譯流程：**
5. `llm1.translate_started`（輸入：Scenario Context + Fully Transcribed Sentence）→
6. `llm1.translate_finished`（輸出：Translated Sentence）→
7. `overlay.translation_rendered`（Display Translated Sentence）→
8. `llm2.context_update_started`（輸入：原始 Scenario Context + Translated Sentence）→
9. `llm2.context_update_finished`（輸出：New Scenario Context）→
10. `overlay.context_rendered` →
11. `dialogue.record_appended`

整段同時伴隨：`syslog.info / warning / error` 視狀況插入。
