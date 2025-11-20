# 🌐 Translation System Design — Real-Time YouTube Live Translation App
---

## 🧩 1. 系統定位

**Translation System** 是核心主流程的第二階段，
負責將 STT 模組產出的完整句（`final_sentence`）即時翻譯成繁體中文，
並根據語境維持短篇記憶（Scenario Context），確保連貫語意。

架構主要分為三層：

| 層級          | 組件                           | 說明                      |
| ----------- | ---------------------------- | ----------------------- |
| 上層 (Input)  | **STT Output Handler**       | 接收完整句（Final Sentence）事件 |
| 中層 (Core)   | **LLM1 翻譯核心**、**LLM2 語境更新器** | 負責翻譯與語境記憶維護             |
| 下層 (Output) | **Overlay**、**Dialogue Log** | 顯示翻譯結果與儲存語料             |

---

## 🧠 2. 翻譯流程概述

```text
[Fully Transcribed Sentence] + [Scenario Context]
    ↓
[LLM1: 翻譯處理]
    ↓
[Translated Sentence] → Display Translated Sentence
    ↓
[原始 Scenario Context] + [Translated Sentence]
    ↓
[LLM2: 情境更新處理]
    ↓
[New Scenario Context]
    ↓
[儲存至 Dialogue Log]
```

* **LLM1** 輸入：**Scenario Context** + **Fully Transcribed Sentence**，輸出：**Translated Sentence**
* **LLM2** 輸入：**原始 Scenario Context** + **Translated Sentence**，輸出：**New Scenario Context**
* Scenario Context 僅保留最近 200–500 tokens，維持記憶與效能平衡。

---

## ⚙️ 3. 模組分層設計

| 模組名稱                   | 角色  | 功能摘要                                   |
| ---------------------- | --- | -------------------------------------- |
| **TranslationManager** | 控制層 | 串接 STT、LLM1、LLM2，管理翻譯任務                |
| **LLMClient**          | 通訊層 | 呼叫 OpenAI API（gpt-4.1-mini-2025-04-14） |
| **ContextManager**     | 記憶層 | 維護與裁剪 Scenario Context                 |
| **PromptBuilder**      | 組合層 | 動態構建 prompt（語境 + 句子 + 翻譯指示）            |
| **DialogueRecorder**   | 輸出層 | 寫入 Dialogue Log 檔案                     |
| **LatencyTracker**     | 監測層 | 計算 LLM 延遲並上報 System Log                |

---

## 🧩 4. 模組互動流程

| 步驟 | 事件                             | 處理模組               | 結果             |
| -- | ------------------------------ | ------------------ | -------------- |
| 1  | `stt.final_sentence`           | TranslationManager | 收到完整句          |
| 2  | `llm1.translate_started`       | LLMClient          | 向 API 發出翻譯請求   |
| 3  | `llm1.translate_finished`      | LLMClient          | 回傳譯文與 Token 統計 |
| 4  | `llm2.context_update_started`  | ContextManager     | 取得舊語境，準備更新     |
| 5  | `llm2.context_update_finished` | ContextManager     | 新語境產生、裁剪       |
| 6  | `overlay.translation_rendered` | Overlay            | 顯示翻譯           |
| 7  | `dialogue.record_appended`     | DialogueRecorder   | 寫入對話資料         |
| 8  | `syslog.info`                  | SystemLog          | 記錄延遲與 token 用量 |

---

## 💬 5. Prompt 設計（LLM1 翻譯）

### 輸入組合：
- **Scenario Context** + **Fully Transcribed Sentence**

### 目標語言：

* **英文 → 繁體中文**
* **日文 → 繁體中文**

### PromptBuilder 輸出樣式：

```text
You are a real-time translation assistant.
Translate the following sentence into Traditional Chinese accurately
while preserving tone, subject, and context.

Scenario Context:
{scenario_context}

Sentence to Translate:
"{fully_transcribed_sentence}"

Output only the translation, without explanation.
```

### 範例：

```text
Scenario Context:
講者正在介紹新產品的功能，前一句提到價格實惠。

Sentence to Translate:
"This feature allows users to control everything from one dashboard."

→ Output:
「這項功能讓使用者能從單一儀表板控制所有設定。」
```

---

## 🧩 6. Prompt 設計（LLM2 語境更新）

### 輸入組合：
- **原始 Scenario Context** + **Translated Sentence**

### 功能：

將「原始情境上下文 + 翻譯後的句子」壓縮成 200–500 tokens 的新語境摘要，
用以保留話題脈絡、口氣、人稱與主題延續性。

### Prompt 模板：

```text
You are a summarization assistant.
Update the scenario context to reflect the latest translated sentence.

Previous Context:
{original_scenario_context}

New Translated Sentence:
{translated_sentence}

Return a concise updated context summary (max 500 tokens).
```

---

## 🧮 7. 情境管理策略（Scenario Context）

| 項目   | 策略                       | 實作方式                |
| ---- | ------------------------ | ------------------- |
| 保留長度 | 200–500 tokens           | 限制字數後裁剪舊內容（FIFO）    |
| 更新時機 | 每句翻譯後                    | 在 LLM2 完成後覆蓋        |
| 暫存方式 | 記憶體 + 快取檔                | JSON 格式（含時間戳）       |
| 錯誤保護 | 若更新失敗則維持舊 Context        | 發出 `syslog.warning` |
| 對話重播 | Dialogue Log 可還原 Context | 模組間共享讀取介面           |

---

## ⚡ 8. 延遲預算與併發策略

| 階段            | 目標延遲          | 說明                |
| ------------- | ------------- | ----------------- |
| STT → LLM1 啟動 | ≤ 150 ms      | 事件傳遞與 prompt 構建   |
| LLM1 翻譯 API   | ≤ 700 ms      | gpt-4.1-mini 回傳時間 |
| LLM2 更新       | ≤ 200 ms      | 摘要生成              |
| Overlay 顯示    | ≤ 100 ms      | UI 渲染與排程          |
| **總延遲目標**     | **0.5–1.5 s** | 含網路浮動與 I/O        |

### 技術策略

* TranslationManager 維護 **async 任務池**，同時處理多句。
* 若 backlog 過多 → 發出 `rate_limit.backpressure`，暫緩新句進入。
* API 失敗 → 重試（見 Config.retry 設定）。

---

## 🧾 9. Dialogue Log 寫入格式

每句翻譯後寫入一筆（由 DialogueRecorder 處理）：

```json
{
  "timestamp": "2025-11-05T15:42:11Z",
  "session_id": "yt_2025_1105",
  "sentence_id": 27,
  "source_language": "en",
  "source_sentence": "This feature allows users to control everything from one dashboard.",
  "translated_sentence": "這項功能讓使用者能從單一儀表板控制所有設定。",
  "scenario_context": "講者介紹新功能，延續產品說明語氣。",
  "tokens_in": 38,
  "tokens_out": 45,
  "latency_ms": 812
}
```

> 檔案可為 `.jsonl`（每行一筆 JSON）或 `.csv`；由 Dialogue Log 模組自動選擇。

---

## 🪶 10. 事件對應與觸發邏輯

| 事件名稱                           | 觸發來源             | 內容           | 下游行為                        |
| ------------------------------ | ---------------- | ------------ | --------------------------- |
| `stt.final_sentence`           | STT 模組           | 完整句          | TranslationManager 接收       |
| `llm1.translate_started`       | LLMClient        | sentence_id  | System Log 標記               |
| `llm1.translate_finished`      | LLMClient        | 翻譯結果         | Overlay 更新 + DialogueLog 寫入 |
| `llm2.context_update_started`  | ContextManager   | 舊語境          | 準備摘要                        |
| `llm2.context_update_finished` | ContextManager   | 新語境          | Overlay Context 更新          |
| `dialogue.record_appended`     | DialogueRecorder | 檔案路徑         | System Log 記錄               |
| `syslog.*`                     | 所有模組             | 狀態 / 錯誤 / 延遲 | GUI 顯示                      |

---

## 🧩 11. 類別介面（供程式生成）

```python
# translation/manager.py
class TranslationManager:
    def __init__(self, bus, llm_client, context_mgr, recorder, config):
        ...
    async def handle_final_sentence(self, ev: Event[SttFinalSentencePayload]): ...
    async def run_translation(self, sentence: str, lang: str): ...
    async def update_context(self, translated: str): ...

# translation/llm_client.py
class LLMClient:
    async def translate(self, sentence: str, context: str) -> dict: ...
    async def summarize_context(self, old_context: str, translated: str) -> str: ...

# translation/context_manager.py
class ContextManager:
    def __init__(self, max_tokens=500): ...
    def get_context(self) -> str: ...
    def update(self, new_sentence: str, translated: str): ...
    def save_cache(self, path: str): ...

# translation/prompt_builder.py
class PromptBuilder:
    def build_translation_prompt(self, sentence: str, context: str, lang: str) -> str: ...
    def build_summary_prompt(self, context: str, translated: str) -> str: ...

# translation/recorder.py
class DialogueRecorder:
    def append_record(self, record: dict): ...
    def flush(self): ...

# translation/latency_tracker.py
class LatencyTracker:
    def start(self, sentence_id: int): ...
    def stop(self, sentence_id: int) -> int: ...
```

---

## 🧠 12. 錯誤與重試邏輯

| 錯誤類型               | 行為            | 事件                |
| ------------------ | ------------- | ----------------- |
| API 超時             | 自動重試（最多 2 次）  | `retry.scheduled` |
| Token Overflow     | 裁剪 Context、重送 | `syslog.warning`  |
| 翻譯失敗（HTTP 4xx/5xx） | 記錄空翻譯並保留原文    | `syslog.error`    |
| Context 更新失敗       | 保留舊 Context   | `syslog.warning`  |

---

## 📈 13. 效能監測與度量

* **LatencyTracker**：追蹤 LLM1、LLM2 時間差
* **Metrics 推送**（可選）：傳送到 Diagnostics 面板

  * `tokens_in/out`
  * `avg_latency_ms`
  * `context_len`
  * `throughput (sentences/min)`

---

## 🧩 14. 模組輸入/輸出摘要

| 模組                 | Input              | Output                         |
| ------------------ | ------------------ | ------------------------------ |
| TranslationManager | STT.final_sentence | Translated Sentence + Context  |
| LLMClient          | sentence/context   | translated_text / summary_text |
| ContextManager     | translated_text    | updated_context                |
| DialogueRecorder   | translated_record  | `.jsonl` / `.csv`              |
| LatencyTracker     | start/stop events  | latency_ms                     |
| PromptBuilder      | context + sentence | ready-to-send prompt           |

---

## 🧩 15. 模組之間的非同步事件圖

```text
STT.final_sentence
   │
   ▼
TranslationManager ──────────────┐
   │                             │
   ▼                             │
 LLMClient (LLM1)                │
   │                             │
   ▼                             │
 ContextManager (LLM2) ──────────┘
   │
   ├──► Overlay.update_translation()
   ├──► Overlay.update_context()
   └──► DialogueRecorder.append_record()
```


## 🧰 16. 依賴設定（config.json）

```json
{
  "llm_api": "gpt-4.1-mini-2025-04-14",
  "context_tokens": 500,
  "latency_budget_ms": { "total": 1500, "llm": 700 },
  "retry": { "max_attempts": 2, "backoff_ms": 400 },
  "output_format": "jsonl"
}
```

---

## ✅ 17. 測試清單

* [ ] 翻譯延遲 < 1.5 秒
* [ ] Context 長度穩定 < 500 tokens
* [ ] Context 串接準確（主題連貫）
* [ ] 重試策略在失敗時正確觸發
* [ ] Dialogue Log 格式正確且可被重播
* [ ] 翻譯與語境更新事件正確順序（LLM1→LLM2）

---

## 🧱 18. 設計理念摘要

* **語境導向翻譯**：每句翻譯都帶入短篇語境，避免片段式直譯。
* **事件驅動非同步設計**：LLM1 / LLM2 並行處理、減少延遲。
* **可觀測性**：延遲、token 使用、Context 變化全記錄於 System Log。
* **可擴充性**：可替換其他 API（Gemini / Claude）而不改主流程。
* **安全降級**：任一層失敗不阻塞 Overlay 顯示。