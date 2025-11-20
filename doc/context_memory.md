# 🧠 Context Memory Design — Real-Time YouTube Live Translation App

對應文件：

* `/translation_system.md`
* `/dialogue_logging.md`
* `/02_modules_specification.md`
* `/system_logging.md`

---

## 🧭 1. 系統定位

**Context Memory 模組**（又稱 *Scenario Context Manager*）
是翻譯系統中維持「短期語境連續性」的核心。

它在每一次翻譯完成後：

* 擷取新句內容與 LLM1 翻譯結果
* 透過 LLM2 (Context Summarizer) 更新情境摘要
* 保留最近 200–500 tokens 的語境記憶

其設計使 LLM 翻譯每一句時，都能結合過去幾句的語境而非單句翻譯。

---

## 🧱 2. 架構總覽

```text
[Fully Transcribed Sentence] + [Scenario Context]
   │
   ▼
[LLM1 Translator] ─► Translated Sentence
   │
   ▼
[Display Translated Sentence]
   │
   ▼
[原始 Scenario Context] + [Translated Sentence]
   │
   ▼
[LLM2 ContextUpdater]
   │
   ├──► 壓縮過去記憶
   ├──► 更新情境摘要
   └──► 廣播 (llm2.context_update_finished) → New Scenario Context
```

---

## 🧩 3. 模組組成

| 模組名稱                    | 職責                    | 關鍵事件                                                           |
| ----------------------- | --------------------- | -------------------------------------------------------------- |
| **ContextManager**      | 儲存與維護語境記憶（短篇）         | `llm2.context_update_started` / `llm2.context_update_finished` |
| **LLM2 ContextUpdater** | 將當前翻譯結果 + 過去摘要 → 壓縮更新 | -                                                              |
| **DialogueRecorder**    | 接收更新後的 context 並寫入紀錄  | `dialogue.record_appended`                                     |
| **SystemLogger**        | 記錄更新耗時與記憶長度           | `syslog.info / warning`                                        |

---

## 📜 4. 記憶模型概念

* 記憶儲存結構：

  ```python
  {
    "sentences": [ { "id": 24, "src": "...", "tr": "..." }, ... ],
    "summary": "..."  # Scenario Context
  }
  ```
* 每次翻譯完成後：

  * LLM1 使用 **Scenario Context** + **Fully Transcribed Sentence** 進行翻譯
  * 翻譯完成後，LLM2 使用 **原始 Scenario Context** + **Translated Sentence** 更新情境
  * 新增一句到 `sentences`
  * 若總 token 數超過上限 (max_tokens)，呼叫 LLM2 進行摘要壓縮
* `summary`（Scenario Context）永遠維持在 **200–500 tokens** 範圍內

---

## ⚙️ 5. 主要類別設計

```python
# context/context_manager.py
import tiktoken
import time

class ContextManager:
    def __init__(self, bus, config):
        self.bus = bus
        self.encoder = tiktoken.get_encoding("cl100k_base")
        self.sentences = []
        self.summary = ""
        self.max_tokens = config["context_memory"]["max_tokens"]
        self.model_summary = config["context_memory"]["llm2_model"]

    def append(self, src_text, translated_text, sentence_id):
        """新增一筆語句並檢查是否需要壓縮"""
        self.sentences.append({"id": sentence_id, "src": src_text, "tr": translated_text})
        if self._estimate_tokens() > self.max_tokens:
            self._update_context()

    def _estimate_tokens(self):
        joined = " ".join([s["src"] + " " + s["tr"] for s in self.sentences]) + self.summary
        return len(self.encoder.encode(joined))

    def _update_context(self, original_context: str, translated_sentence: str):
        """使用 LLM2 產生壓縮摘要
        
        輸入：原始 Scenario Context + Translated Sentence
        輸出：New Scenario Context
        """
        start = time.time()
        self.bus.emit(EventName.LLM2_CONTEXT_UPDATE_STARTED, {"context_len_before": self._estimate_tokens()})

        # Prompt 結構：使用原始 Scenario Context + Translated Sentence
        prompt = f"""
        請更新情境上下文，整合新的翻譯句子。

        原始情境上下文：
        {original_context}

        新增翻譯句子：
        {translated_sentence}

        請以繁體中文生成一段簡短摘要，描述目前對話的情境或主題（200–500 tokens 內）。
        """
        try:
            summary = self._call_llm(prompt)
            self.summary = summary
            self.sentences = self.sentences[-5:]  # 保留最近幾句原文
            latency = int((time.time() - start) * 1000)
            self.bus.emit(EventName.LLM2_CONTEXT_UPDATE_FINISHED, {
                "context_len_after": self._estimate_tokens(),
                "context_snippet": summary,
                "latency_ms": latency
            })
        except Exception as e:
            self.bus.emit(EventName.SYSLOG_ERROR, {
                "message": "LLM2 context update failed",
                "exc": str(e)
            })

    def _get_recent_sentences(self, n):
        return "\n".join([f"{s['src']} → {s['tr']}" for s in self.sentences[-n:]])

    def _call_llm(self, prompt):
        from openai import OpenAI
        client = OpenAI()
        response = client.chat.completions.create(
            model=self.model_summary,
            messages=[{"role": "system", "content": "你是情境摘要助理。"},
                      {"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content.strip()
```

---

## 🧠 6. Context Update Prompt 範例

> 系統提示：
> 「以下是近期的對話內容，請維持語氣與主題一致，產生簡短摘要」

```
目前主題：開發者介紹新功能，正在說明用戶如何設定參數。
新輸入：
"This setting helps you control the latency of the response."
→ 「此設定可讓您控制回應延遲。」
```

LLM2 回覆：

> 「講者持續在解說應用程式效能相關設定，著重於延遲與回應速度調整。」

---

## 🔁 7. 記憶更新策略

| 條件                | 行為            |
| ----------------- | ------------- |
| 總 token < 200     | 不更新           |
| 200 ≤ token ≤ 500 | 視為健康狀態        |
| token > 500       | 呼叫 LLM2 產生新摘要 |
| LLM2 失敗           | 保留原摘要並紀錄錯誤    |

---

## 🧮 8. Token 預算規劃

| 模型                 | Token 上限 | Context 保留範圍      |
| ------------------ | -------- | ----------------- |
| `gpt-4.1-mini`     | 8k       | 保留約 500 tokens    |
| `gpt-4.1`          | 128k     | 可擴至 1k–2k tokens  |
| `gemini-2.5-flash` | 32k      | 約 500 tokens 為理想值 |

---

## 🧩 9. 事件與回報格式

### 事件：`llm2.context_update_started`

```json
{
  "context_len_before": 612
}
```

### 事件：`llm2.context_update_finished`

```json
{
  "context_len_after": 285,
  "context_snippet": "講者持續說明延遲設定與系統優化。",
  "latency_ms": 420
}
```

---

## 🧾 10. 與 Dialogue Log 的整合

1. `llm2.context_update_finished` → 由 DialogueRecorder 接收
2. 更新最後一筆紀錄的 `"scenario_context"` 欄位
3. 同步寫入 `dialogue.jsonl`

此步驟確保語境記憶與語料紀錄一致。

---

## 📊 11. 效能與監測

| 指標                          | 說明          | 來源               |
| --------------------------- | ----------- | ---------------- |
| `context_len_before`        | 更新前 token 數 | ContextManager   |
| `context_len_after`         | 更新後 token 數 | LLM2 回傳          |
| `context_update_latency_ms` | LLM2 呼叫耗時   | SystemLog        |
| `update_count`              | 累積摘要次數      | MetricsCollector |

---

## 🧩 12. System Log 範例

| 等級      | 模組   | 訊息                                                        |
| ------- | ---- | --------------------------------------------------------- |
| INFO    | llm2 | `[Context] update started (tokens=612)`                   |
| INFO    | llm2 | `[Context] summary generated (tokens=285, latency=420ms)` |
| WARNING | llm2 | `[Context] skipped update (tokens<200)`                   |
| ERROR   | llm2 | `[Context] failed to update: APIError 503`                |

---

## 🧰 13. config.json 對應設定

```json
{
  "context_memory": {
    "enabled": true,
    "max_tokens": 500,
    "llm2_model": "gpt-4.1-mini-2025-04-14"
  }
}
```

---

## 🧮 14. 測試項目

* [ ] Context 更新事件正確觸發
* [ ] Token 計算與預期一致
* [ ] LLM2 回傳摘要可被儲存與覆寫
* [ ] 超出上限自動壓縮
* [ ] 更新延遲 < 1 秒
* [ ] 對話紀錄與 Context 同步
* [ ] 異常情況能自動恢復前一摘要

---

## 🧱 15. 設計理念摘要

* **短期記憶導向**：保留最近語境片段，而非整場對話。
* **語意摘要而非拼接**：LLM2 產生語境摘要，而非串接文字。
* **自動壓縮**：當記憶超標時自動更新，避免記憶爆炸。
* **上下文一致性**：翻譯模組每次呼叫 LLM1 前都附帶最新摘要。
* **模組獨立可替換**：Context 管理可更換 LLM2 模型或算法。

---

## 🧩 16. 總結流程圖

```text
┌──────────────────────────────┐
│       ContextManager         │
│ ┌─────────────────────────┐ │
│ │ Append(sentence, trans) │ │
│ └────────────┬────────────┘ │
│              ▼               │
│   [Token > 500?]───Yes──────► LLM2 Summarizer
│        │                     │
│       No                     │
│        ▼                     │
│   保留原摘要                 │
└──────────────────────────────┘
            │
            ▼
   EventBus.emit(llm2.context_update_finished)
            │
            ▼
     DialogueRecorder 更新記錄
```
