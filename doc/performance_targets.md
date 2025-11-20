# ⚡ Performance Targets — Real-Time YouTube Live Translation App

對應文件：

* `/architecture_overview.md`
* `/transcription_system.md`
* `/translation_system.md`
* `/context_memory.md`
* `/system_logging.md`
* `/dialogue_logging.md`

---

## 🧭 1. 設計目標

本系統的最終效能目標是：

> **「從發話者說出一句話 → 翻譯文字出現在 Overlay 上」的整體延遲 ≤ 1.5 秒。**

並且保持高準確率、穩定輸出速率與可長時間運行不崩潰的特性。

---

## 🧩 2. 效能測量維度（Performance Dimensions）

| 類別            | 指標                           | 測量單位  | 說明                        |
| ------------- | ---------------------------- | ----- | ------------------------- |
| 🎧 音訊擷取       | **Input Latency**            | ms    | 音訊流輸入到第一個 chunk 的延遲       |
| 🧠 STT 推論     | **STT Latency**              | ms    | chunk 開始推論到 transcript 輸出 |
| ✍️ 翻譯處理       | **LLM Latency**              | ms    | 翻譯請求到回傳文字                 |
| 🧩 語境更新       | **Context Update Latency**   | ms    | LLM2 摘要更新耗時               |
| 🪄 Overlay 顯示 | **Render Delay**             | ms    | 翻譯結果顯示到螢幕的時間              |
| 🔁 系統整體       | **End-to-End Latency**       | ms    | 發話→字幕顯示總時間                |
| 💾 穩定性        | **Crash-Free Uptime**        | hours | 平均穩定運行時間                  |
| 🔉 語音辨識準確率    | **Word Accuracy Rate (WAR)** | %     | 正確字詞比例                    |
| 🌐 翻譯準確率      | **Semantic Accuracy (SA)**   | %     | 翻譯語意與原文一致度                |
| 🧮 資源使用       | **CPU / GPU Utilization**    | %     | 在指定硬體上之負載比率               |

---

## ⚙️ 3. 效能目標表（Performance KPI Table）

| 模組                       | 指標                  | 目標值         | 最佳值    | 可接受上限   | 測量方式                   |
| ------------------------ | ------------------- | ----------- | ------ | ------- | ---------------------- |
| **AudioCapture**         | Input Latency       | ≤ 50 ms     | 20 ms  | 100 ms  | stream callback 時間差    |
| **ChunkProcessor**       | Chunk Emit Interval | 480 ± 10 ms | 480 ms | 500 ms  | chunk_id 時差統計          |
| **STTManager**           | STT Latency         | ≤ 500 ms    | 300 ms | 800 ms  | decode start → final   |
| **LLM1 Translator**      | Translation Latency | ≤ 700 ms    | 400 ms | 1000 ms | API request → response |
| **LLM2 ContextUpdater**  | Context Update      | ≤ 300 ms    | 200 ms | 600 ms  | update start → finish  |
| **OverlayRenderer**      | Render Delay        | ≤ 100 ms    | 50 ms  | 150 ms  | text commit → paint    |
| **Total E2E Delay**      | Full Pipeline       | ≤ 1500 ms   | 900 ms | 1800 ms | speech start → overlay |
| **Crash-Free Time**      | Stability           | ≥ 24h       | 72h    | 12h     | 監控 uptime              |
| **STT Accuracy (EN)**    | Word Accuracy       | ≥ 93%       | 96%    | 85%     | 比對人工標記                 |
| **Translation Accuracy** | Semantic Accuracy   | ≥ 90%       | 95%    | 80%     | BLEU / COMET           |
| **CPU Usage**            | 平均 CPU 占用           | ≤ 25%       | 15%    | 40%     | 系統監測                   |
| **GPU Usage (4070)**     | GPU 利用率             | ≤ 40%       | 30%    | 60%     | NVML API               |
| **Memory Usage**         | 常駐記憶體               | ≤ 3 GB      | 2.0 GB | 4 GB    | psutil 監控              |

---

## 🔍 4. 測量點與事件對應

每個指標對應系統事件（由 `EventBus` 廣播），
可由 `MetricsCollector` 監聽並寫入 JSON/CSV 報表。

| 事件                                                             | 對應指標                | 記錄欄位                    |
| -------------------------------------------------------------- | ------------------- | ----------------------- |
| `audio.chunk_ready`                                            | Chunk Emit Interval | chunk_id, timestamp     |
| `stt.decode_started` / `stt.final_sentence`                    | STT Latency         | latency_ms              |
| `llm1.translate_started` / `llm1.translate_finished`           | Translation Latency | tokens, latency         |
| `llm2.context_update_started` / `llm2.context_update_finished` | Context Update      | tokens_before/after     |
| `overlay.translation_rendered`                                 | Render Delay        | latency_ms              |
| `dialogue.record_appended`                                     | E2E Pipeline 延遲     | sentence_id, total_time |

---

## 🧮 5. 延遲預算分配（Latency Budget Breakdown）

### 目標：0.5–1.5 秒間完成整體流程

```text
┌─────────────────────────────┐
│ Audio In → Chunk Ready     │  ≈ 100 ms
│ Chunk → STT Final Sentence │  ≈ 400 ms
│ STT → Translation Ready    │  ≈ 600 ms
│ Translation → Overlay Draw │  ≈ 200 ms
│ Context Update (async)     │  ≈ 200 ms
└─────────────────────────────┘
TOTAL ≈ 1.3 秒
```

### 表格版：

| 區段           | 預算 (ms)     | 描述                       |
| ------------ | ----------- | ------------------------ |
| 音訊輸入         | 100         | Stereo Mix → Chunk Ready |
| STT Pipeline | 400         | FasterWhisper / API 推論   |
| LLM 翻譯       | 600         | 翻譯階段                     |
| Overlay 顯示   | 200         | 文字繪製、GUI 更新              |
| Context 更新   | 200         | 非同步處理（不阻塞主流程）            |
| **總計**       | **1500 ms** | 最大容許延遲                   |

---

## 📊 6. 效能監測機制（Performance Monitoring）

### 模組：`MetricsCollector`

* 透過訂閱 EventBus 事件紀錄時序
* 自動統計延遲分佈與平均值
* 每分鐘產生一次快照報表 (`logs/metrics.jsonl`)

### 事件輸入

* `stt.*`
* `llm1.*`
* `llm2.*`
* `overlay.translation_rendered`
* `dialogue.record_appended`

### 輸出格式

```json
{
  "timestamp": "2025-11-11T10:23:14Z",
  "stt_latency_ms": 412,
  "translation_latency_ms": 615,
  "context_latency_ms": 190,
  "overlay_delay_ms": 72,
  "e2e_latency_ms": 1289
}
```

### 可視化

* GUI 的 Diagnostics 頁面以折線圖展示
* CLI 版支援 ASCII bar chart（平均延遲趨勢）

---

## 🧠 7. 穩定性與錯誤率指標

| 指標                               | 定義                   | 目標        |
| -------------------------------- | -------------------- | --------- |
| **Error Rate**                   | `syslog.error` 每分鐘次數 | < 0.2/min |
| **Recoverable Failure**          | 自動重試後成功率             | ≥ 95%     |
| **Backpressure Event Frequency** | 每小時觸發次數              | ≤ 3       |
| **Memory Leak Growth**           | 24h 內常駐記憶體變化         | < +200MB  |
| **File I/O Stability**           | Log I/O 成功率          | 100%      |

---

## 🔄 8. 效能測試方案（Performance Testing Plan）

| 測試項目             | 方法                | 期望結果         |
| ---------------- | ----------------- | ------------ |
| **長時間穩定性測試**     | 模擬 8 小時連續直播音訊輸入   | 無崩潰、無記憶體異常增長 |
| **高負載 STT 測試**   | 模擬多發話者音源（雙聲道混合）   | 延遲 < 1.5s    |
| **低頻網路測試**       | 模擬 API 50% RTT 延遲 | 翻譯延遲 < 2.0s  |
| **高並行 Chunk 測試** | 強制多任務併行 STT       | 無丟句、log 完整   |
| **渲染效能測試**       | 1000 次 Overlay 刷新 | 平均耗時 < 100ms |

---

## 📈 9. 實際效能目標（針對開發環境）

| 硬體   | CPU         | GPU          | 系統    | 預期表現        |
| ---- | ----------- | ------------ | ----- | ----------- |
| 開發機  | i7-14700HX  | RTX 4070 8GB | Win11 | 平均延遲 ≈ 1.1s |
| 輕量筆電 | i5-13500H   | RTX 3050 4GB | Win11 | 平均延遲 ≈ 1.4s |
| 雲端機  | Xeon + A100 | Linux        | 部署測試  | 平均延遲 ≈ 0.9s |

---

## 🧾 10. 效能報表輸出範例

每次 Session 結束時會自動輸出：

`logs/metrics_summary.json`

```json
{
  "session_id": "yt_demo_2025_1111",
  "avg_stt_latency_ms": 421,
  "avg_translation_latency_ms": 607,
  "avg_context_latency_ms": 212,
  "avg_overlay_delay_ms": 68,
  "avg_total_latency_ms": 1308,
  "stt_accuracy": 0.94,
  "translation_accuracy": 0.91,
  "error_rate_per_min": 0.08,
  "uptime_hours": 9.4
}
```

---

## 🧮 11. 效能警示規則（Alert Rules）

| 條件                            | 行動                           |
| ----------------------------- | ---------------------------- |
| `avg_total_latency_ms > 1500` | GUI 顯示紅色警示、SystemLog WARNING |
| `error_rate_per_min > 0.5`    | 將狀態列變橙色並提示「請檢查網路」            |
| `gpu_util > 60%`              | 降低 STT 任務併發（動態 backpressure） |
| `memory_usage > 4GB`          | 自動清理 Context 緩衝區             |

---

## 🧱 12. 設計理念摘要

* **用數據導向優化**：所有效能資料皆事件驅動、可量化。
* **可持續監測**：MetricsCollector 常駐運行，與 System Log 分離。
* **延遲透明化**：每筆翻譯都能追蹤 pipeline 時間。
* **以體驗為中心**：一切指標皆圍繞「即時感」與「語意正確」。
* **自我校正**：異常頻繁時可調整任務池與 Token 上限。

---

## 🧩 13. 效能改進路線圖（Performance Roadmap）

| 版本   | 改進重點                     | 預期效果                 |
| ---- | ------------------------ | -------------------- |
| v1.0 | 基準版 STT/LLM 管線穩定         | 1.3s 平均延遲            |
| v1.1 | 加入非同步 Context 更新         | 降低 150ms 延遲          |
| v1.2 | Partial rendering 優化     | Partial 文字更即時        |
| v1.3 | GPU batch inference      | STT 減少 100ms 延遲      |
| v1.4 | Token cache 翻譯重用         | LLM 延遲下降 20%         |
| v2.0 | Streaming Translation 模式 | End-to-End 延遲 ≈ 0.7s |

---

## ✅ 14. 測試驗收標準（Acceptance Criteria）

| 測試項目        | 驗收條件              |
| ----------- | ----------------- |
| **平均延遲**    | E2E < 1.5s        |
| **錯誤率**     | Error < 1/500 次事件 |
| **STT 精度**  | WAR ≥ 90%         |
| **翻譯準確率**   | SA ≥ 85%          |
| **GUI 流暢度** | Overlay FPS ≥ 30  |
| **記憶體穩定性**  | 無增長超過 200MB/24h   |
| **長時穩定性**   | 無崩潰 ≥ 8 小時連續運行    |
