# 💬 Dialogue Logging Design — Real-Time YouTube Live Translation App

對應文件：

* `/modules_specification.md`
* `/translation_system.md`
* `/system_logging.md`

---

## 🧭 1. 系統定位

**Dialogue Log 系統** 是應用的「語料紀錄層」。
其職責是保存翻譯階段的所有語言資料，包括：

* 原始語句（從 STT 取得）
* 翻譯結果（由 LLM1 產生）
* 情境摘要（由 LLM2 更新）
* 時間戳、Session、延遲與 Token 統計

這些資料可用於：

* 後續語境重播（Context Replay）
* 模型改進與訓練語料
* 用戶分析或翻譯修正
* 檢測翻譯準確率與延遲趨勢

---

## 🔄 2. 與系統架構關係

```text
[Fully Transcribed Sentence]
   │
   ├──► 存儲到 Dialogue Log（供後續使用：解釋、假名標註等）
   │
   ▼
[TranslationManager]
   │
   ├──► LLM1 翻譯結果 (Translated Sentence)
   ├──► LLM2 語境摘要 (New Scenario Context)
   ▼
[DialogueRecorder] ───► dialogue.log.jsonl / .csv
```

* **完整轉錄的句子**完成時 → 存儲到 Dialogue Log 供後續使用（解釋、假名標註等）
* 翻譯完成時 (`llm1.translate_finished`) → 寫入句子與翻譯。
* 語境更新完成 (`llm2.context_update_finished`) → 更新同筆記錄之 context 欄位。
* 每筆紀錄均對應一個 **sentence_id**，確保查詢與追蹤一致。

---

## 🧩 3. 與 System Log 的關係

| 分類      | System Log          | Dialogue Log |
| ------- | ------------------- | ------------ |
| 用途      | 紀錄系統事件與錯誤           | 紀錄語料、翻譯與上下文  |
| 儲存單位    | 系統事件（INFO/WARN/ERR） | 語句           |
| 更新頻率    | 每秒數十次               | 每完成一句        |
| 顯示於 GUI | ✅（System Log 分頁）    | ❌（僅檔案）       |
| 用途      | 除錯 / 效能分析           | 語言分析 / 訓練資料  |

---

## 💾 4. 檔案格式與儲存策略

支援三種儲存格式（由 `config.json` 控制）：

| 格式    | 副檔名      | 用途      | 優點                   |
| ----- | -------- | ------- | -------------------- |
| JSONL | `.jsonl` | 預設      | 結構清晰、支援快速附加          |
| CSV   | `.csv`   | 匯出分析用   | 可直接用 Excel/Sheets 檢視 |
| TXT   | `.txt`   | 純文字快速瀏覽 | 適合人工審閱               |

預設儲存路徑：

```
logs/dialogue/
 ├── dialogue_YYYYMMDD_HHMM.jsonl
 ├── dialogue_YYYYMMDD_HHMM.csv
 └── dialogue_YYYYMMDD_HHMM.txt
```

---

## 🧱 5. 資料結構（JSONL）

每一行代表一筆語句：

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

---

## 🧮 6. 欄位定義

| 欄位                    | 型別       | 說明                   |
| --------------------- | -------- | -------------------- |
| `timestamp`           | ISO-8601 | 翻譯完成時間               |
| `session_id`          | str      | 當前 Session 識別碼       |
| `sentence_id`         | int      | STT 產生之唯一句 ID        |
| `source_language`     | str      | `en` / `ja` / `auto` |
| `source_sentence`     | str      | 原始辨識文字               |
| `translated_sentence` | str      | 翻譯後文字                |
| `scenario_context`    | str      | 縮短後的語境記憶摘要           |
| `tokens_in`           | int      | 輸入 token 數           |
| `tokens_out`          | int      | 翻譯輸出 token 數         |
| `latency_ms`          | int      | 翻譯延遲（含 API 時間）       |
| `error_reason`        | str?     | 若翻譯失敗則記錄錯誤訊息         |

---

## ⚙️ 7. Dialogue Recorder 模組設計

```python
# dialogue/recorder.py
import json, csv, os, datetime

class DialogueRecorder:
    def __init__(self, bus, config):
        self.bus = bus
        self.file_path = self._init_path(config)
        self.buffer = []
        self.format = config["output_format"]  # "jsonl" / "csv" / "txt"
        bus.subscribe(EventName.LLM1_TRANSLATE_FINISHED, self.on_translate_finished)
        bus.subscribe(EventName.LLM2_CONTEXT_UPDATE_FINISHED, self.on_context_update_finished)

    def _init_path(self, config):
        folder = os.path.join("logs", "dialogue")
        os.makedirs(folder, exist_ok=True)
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M")
        ext = config.get("output_format", "jsonl")
        return os.path.join(folder, f"dialogue_{timestamp}.{ext}")

    def on_translate_finished(self, ev: Event[Llm1TranslateFinishedPayload]):
        rec = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "session_id": ev.session_id,
            "sentence_id": ev.payload["sentence_id"],
            "source_sentence": ev.payload.get("source_sentence"),
            "translated_sentence": ev.payload["translated_text"],
            "tokens_in": ev.payload["tokens_in"],
            "tokens_out": ev.payload["tokens_out"],
            "latency_ms": ev.payload.get("latency_ms", 0)
        }
        self.buffer.append(rec)
        self._flush_line(rec)

    def on_context_update_finished(self, ev: Event[Llm2ContextUpdateFinishedPayload]):
        # 更新最後一筆語境欄位
        if self.buffer:
            self.buffer[-1]["scenario_context"] = ev.payload["context_snippet"]
            self._flush_line(self.buffer[-1])

    def _flush_line(self, rec):
        if self.format == "jsonl":
            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        elif self.format == "csv":
            is_new = not os.path.exists(self.file_path)
            with open(self.file_path, "a", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=rec.keys())
                if is_new:
                    writer.writeheader()
                writer.writerow(rec)
        else:
            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(f"{rec['source_sentence']} → {rec['translated_sentence']}\n")

        self.bus.emit(
            EventName.DIALOGUE_RECORD_APPENDED,
            {"file_path": self.file_path, "sentence_id": rec["sentence_id"]},
        )
```

---

## 🧩 8. 事件互動與對應

| 來源事件                           | 動作                          | 輸出事件                       |
| ------------------------------ | --------------------------- | -------------------------- |
| `llm1.translate_finished`      | 新增一筆紀錄                      | `dialogue.record_appended` |
| `llm2.context_update_finished` | 更新上一筆紀錄的 `scenario_context` | `dialogue.record_appended` |
| `syslog.info`                  | 顯示「Dialogue Log updated」訊息  | GUI 訊息條                    |

---

## 🔍 9. 搜尋與索引（供回放與分析）

### 檔案內索引（JSONL）

可依據：

* `sentence_id`
* `timestamp`
* `source_language`
* `error_reason is not null`

快速檢索：

```python
def find_by_sentence(file, sid):
    for line in open(file, "r", encoding="utf-8"):
        rec = json.loads(line)
        if rec["sentence_id"] == sid:
            return rec
```

### 回放機制

* 可在之後開發 `DialogueReplayer` 模組，用於：

  * 重現語境串接過程
  * 重新計算 Context 連貫性
  * 訓練資料生成（fine-tuning）

---

## 📈 10. 效能與緩衝策略

| 機制      | 設計             | 說明                 |
| ------- | -------------- | ------------------ |
| 緩衝區     | `self.buffer`  | 暫存最新紀錄以便修改 context |
| 寫入策略    | 即時寫入 + 追加更新    | 確保即時與資料一致性         |
| 檔案輪替    | 每 1 小時或 10MB   | 自動建立新檔             |
| 異常處理    | 失敗重試一次         | 保證寫入穩定性            |
| Lock 機制 | File lock（選擇性） | 防止多執行緒同時寫檔         |

---

## ⚙️ 11. config.json 對應設定

```json
{
  "dialogue_log": {
    "enabled": true,
    "output_format": "jsonl",
    "max_file_size_mb": 10,
    "rotate_hourly": true,
    "folder": "logs/dialogue"
  }
}
```

---

## 🧮 12. 延遲與指標紀錄

* 每筆紀錄均包含：

  * LLM 翻譯延遲 (`latency_ms`)
  * token 消耗 (`tokens_in/out`)
* 可供後端分析效率或 API 費用估算。
* 若 `error_reason` 存在，標記為異常紀錄。

---

## 🧩 13. 與 Scenario Context 的同步機制

1. 當 LLM2 完成更新後，會發出 `llm2.context_update_finished`。
2. DialogueRecorder 根據最後一筆紀錄的 `sentence_id`，
   將該筆的 `scenario_context` 欄位覆蓋成新的內容。
3. 此內容同時儲存在 ContextManager（記憶體）中，用於後續翻譯 prompt。
4. 在分析階段可利用 Dialogue Log 逆推出語境演變。

---

## 🧰 14. 匯出與資料應用

| 應用         | 格式       | 說明                 |
| ---------- | -------- | ------------------ |
| 翻譯品質檢查     | `.csv`   | 對照原文與譯文            |
| Context 分析 | `.jsonl` | 重建語境鏈              |
| 模型微調資料集    | `.jsonl` | 可直接轉為 fine-tune 格式 |
| 翻譯延遲統計     | `.csv`   | 比較 STT/LLM 延遲分佈    |

---

## ✅ 15. 測試清單

* [ ] 翻譯完成後自動寫入紀錄
* [ ] 語境更新後正確覆蓋 `scenario_context` 欄位
* [ ] 檔案自動建立、輪替正常
* [ ] JSONL / CSV / TXT 格式皆可開啟與解析
* [ ] 記錄格式一致、無遺漏欄位
* [ ] 錯誤事件 (`error_reason`) 正確標記

---

## 🧱 16. 設計理念摘要

* **與 System Log 隔離**：保持語料乾淨，避免混入技術事件。
* **以句為單位**：每一句話都是獨立紀錄，可重播、分析或訓練。
* **即時但安全**：翻譯一完成即寫入，防止中途中斷遺失。
* **結構化輸出**：支援 JSONL 與 CSV 雙軌儲存，兼顧分析與人工閱讀。
* **上下文可重建**：記錄 Scenario Context，讓後續系統能理解當前語境。
