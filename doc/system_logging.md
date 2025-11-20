# 🧾 System Logging Design — Real-Time YouTube Live Translation App
範圍：僅描述 **System Log 系統**，不含 Dialogue Log
依據事件架構與 GUI 顯示行為設計

---

## 🧩 1. System Log 定位

System Log 是後台核心監控模組，
負責即時記錄 **模組事件、執行狀態、延遲數據、錯誤與警告**，
並以統一事件格式（`syslog.info / syslog.warning / syslog.error`）廣播至 EventBus。

System Log 提供：

* 即時 GUI 顯示（彩色分級）
* 檔案記錄（可選，循環儲存）
* 延遲與資源監測報告
* 自動與 EventBus 事件整合

> 💡 **System Log ≠ Dialogue Log**
> Dialogue Log 儲存「使用者語料（原文+翻譯）」，
> System Log 專注「應用層事件與性能狀態」。

---

## ⚙️ 2. 系統結構總覽

```text
[各模組] ──► SystemLogger.emit(level, message, **kwargs)
                │
                ▼
          EventBus ─► (syslog.info / warning / error)
                │
        ┌───────┴────────┐
        ▼                 ▼
[GUI Log Panel]     [File Writer / Rotator]
```

---

## 🧱 3. 模組構成

| 類別                   | 職責             | 關鍵行為                                      |
| -------------------- | -------------- | ----------------------------------------- |
| **SystemLogger**     | 封裝 logging API | 提供 `info()`, `warning()`, `error()` 三級別介面 |
| **SystemLogHandler** | 事件廣播器          | 將訊息轉換為 EventBus 事件                        |
| **FileLogWriter**    | 檔案寫入器          | 輪替輸出 `.log` / `.txt`（按天或大小）               |
| **LogFormatter**     | 格式化輸出          | 控制顏色、高亮、縮排、時間戳                            |
| **LatencyTracker**   | 延遲監測           | 追蹤每階段 pipeline latency                    |
| **GUISink**          | 視覺輸出           | 接收 `syslog.*` 並上色顯示在 PyQt GUI 面板          |

---

## 🔌 4. 與 EventBus 整合

System Log 透過 **EventBus** 廣播，與所有模組即時互通。
每次 Log 皆為一個標準事件：

### 基底格式（符合 `/app/core/events.py`）

```json
{
  "event": "syslog.info",
  "timestamp": "2025-11-05T15:43:21Z",
  "session_id": "yt_2025_1105",
  "seq": 128,
  "component": "stt",
  "payload": {
    "level": "INFO",
    "message": "[STT] Chunk #42 decoded successfully (latency=348ms)",
    "chunk_id": 42,
    "latency_ms": 348
  }
}
```

### 廣播流程

```text
各模組 → SystemLogger.info()
           ↓
       SystemLogHandler.emit()
           ↓
       EventBus.emit(syslog.info)
           ↓
   GUI.LogPanel / FileLogWriter / Diagnostics
```

---

## 🧠 5. 日誌級別與顏色規則

| Level   | 顏色           | 說明              | 範例                                       |
| ------- | ------------ | --------------- | ---------------------------------------- |
| INFO    | 🔵 `#5DA9FF` | 正常運行資訊、狀態變更     | `[LLM] Translation finished #27 (815ms)` |
| WARNING | 🟡 `#FFC857` | 延遲偏高、重試啟動       | `[STT] Backpressure triggered (queue=5)` |
| ERROR   | 🔴 `#FF4D4F` | 模組錯誤、API失敗、設備錯誤 | `[Audio] Failed to open Stereo Mix`      |

---

## 🧮 6. 延遲與效能監測

System Log 負責收集 pipeline 延遲指標，用於 GUI 診斷面板顯示。

### 延遲監測事件

| 來源          | 指標             | 事件欄位               |
| ----------- | -------------- | ------------------ |
| STT         | 每片段處理時間        | `latency_ms`       |
| LLM1 / LLM2 | API 延遲         | `latency_ms`       |
| Overlay     | UI 更新延遲        | `render_ms`        |
| 整體          | pipeline total | `total_latency_ms` |

### 行為

* `LatencyTracker.start(sentence_id)` → 標記時間戳
* `LatencyTracker.stop(sentence_id)` → 回傳差值（ms）
* 發出 `syslog.info`，附加延遲欄位

範例：

```python
logger.info("Translation latency", component="llm1", latency_ms=745, sentence_id=27)
```

---

## 🧰 7. API 介面定義

```python
# system_log/logger.py
class SystemLogger:
    def __init__(self, bus, file_writer=None):
        self.bus = bus
        self.file_writer = file_writer

    def info(self, message: str, **kv):
        self._emit("info", message, **kv)

    def warning(self, message: str, **kv):
        self._emit("warning", message, **kv)

    def error(self, message: str, exc: Exception | None = None, **kv):
        self._emit("error", message, exc=exc, **kv)

    def _emit(self, level: str, message: str, **kv):
        # 1. 組裝 payload
        payload = {"level": level.upper(), "message": message, **kv}
        # 2. 發送至 EventBus
        self.bus.emit(f"syslog.{level}", payload, component=kv.get("component"))
        # 3. 寫入檔案（非必要）
        if self.file_writer:
            self.file_writer.write(payload)
```

---

## 📂 8. 檔案寫入策略（FileLogWriter）

### 檔案格式

```
2025-11-05 15:42:11 [INFO] [STT] Chunk #42 decoded successfully (348ms)
2025-11-05 15:42:12 [WARNING] [LLM] High latency (923ms)
2025-11-05 15:42:13 [ERROR] [Audio] Failed to open device
```

### 管理策略

| 項目   | 設定                       | 說明      |
| ---- | ------------------------ | ------- |
| 檔案類型 | `.log`                   | 純文字     |
| 命名規則 | `systemlog_YYYYMMDD.log` | 按天自動分檔  |
| 輪替大小 | 10 MB                    | 超過即切換   |
| 保存天數 | 7                        | 自動刪除舊檔案 |
| 編碼   | UTF-8                    | 防止亂碼    |

---

## 🪟 9. GUI 整合行為

### 事件接收

GUI 模組訂閱：

```python
bus.subscribe(EventName.SYSLOG_INFO, self.on_log_event)
bus.subscribe(EventName.SYSLOG_WARNING, self.on_log_event)
bus.subscribe(EventName.SYSLOG_ERROR, self.on_log_event)
```

### 顯示規則

* 以時間戳排序顯示最新 500 筆（舊訊息自動捲動或移除）
* 顏色根據 `level` 套用
* `QPlainTextEdit` 為只讀狀態，禁止選取時閃爍
* 點擊可展開完整訊息（長字串換行）
* StatusBar 顯示最近一筆錯誤摘要（紅點提示）

---

## 🔍 10. Log 與模組銜接關係

| 來源模組               | 範例訊息                                  | Log Level | 用途     |
| ------------------ | ------------------------------------- | --------- | ------ |
| AudioCapture       | `[Audio] stream opened @48kHz`        | INFO      | 確認設備啟動 |
| STTManager         | `[STT] Backpressure triggered`        | WARNING   | 警示暫緩   |
| LocalSTTEngine     | `[STT] Decoded chunk #23 (348ms)`     | INFO      | 正常運行   |
| APISTTEngine       | `[API] 429 Too Many Requests`         | ERROR     | API 限流 |
| TranslationManager | `[LLM1] Translation finished (745ms)` | INFO      | 成功翻譯   |
| LLMClient          | `[LLM2] Context updated`              | INFO      | 語境更新   |
| OverlayController  | `[Overlay] Render updated`            | INFO      | 顯示完成   |
| ConfigManager      | `[Config] Missing runtime: ffmpeg`    | WARNING   | 安裝提醒   |

---

## 🧮 11. 延遲度量指標格式

System Log 事件攜帶延遲時，附加統一欄位：

```json
{
  "event": "syslog.info",
  "payload": {
    "level": "INFO",
    "message": "[LLM] Translation finished",
    "latency_ms": 745,
    "component": "llm1",
    "sentence_id": 27
  }
}
```

> GUI 診斷面板可從此提取平均延遲與峰值。

---

## 🧱 12. 整合其他系統

| 系統                    | 銜接方式                | 目的             |
| --------------------- | ------------------- | -------------- |
| **EventBus**          | 發送與接收 `syslog.*` 事件 | 模組通訊主幹         |
| **GUI Log 面板**        | 訂閱事件顯示              | 前端呈現           |
| **Diagnostics 面板**    | 解析 latency 欄位       | 性能分析           |
| **Runtime Check**     | 寫入缺項報告              | 啟動時狀態          |
| **OverlayController** | 不直接連接               | 不顯示 system log |
| **Dialogue Log**      | 無關                  | 獨立系統           |

---

## 🧩 13. 錯誤處理策略

| 狀況              | 行為                                             | 顏色 |
| --------------- | ---------------------------------------------- | -- |
| 模組失敗（Exception） | 發 `syslog.error` + traceback                   | 🔴 |
| 延遲超標            | 發 `syslog.warning`（含 latency_ms）               | 🟡 |
| 任務重試            | 發 `syslog.info` (`retry.scheduled`)            | 🔵 |
| 背壓觸發            | 發 `syslog.warning` (`rate_limit.backpressure`) | 🟡 |
| 日誌寫入失敗          | 僅 print，不遞迴 log                                | ⚫  |

---

## 🧩 14. 設定範例（config.json）

```json
{
  "logging": {
    "enable_file": true,
    "log_dir": "./logs",
    "rotate_size_mb": 10,
    "keep_days": 7,
    "console_level": "info"
  }
}
```

---

## 🧮 15. 效能與穩定性考量

* 每秒事件上限：500 條（含 partial）
* 檔案寫入非同步（thread pool）
* 若緩衝超過 200 條 → 丟棄最舊項並發 `syslog.warning("Log buffer overflow")`
* Log I/O 避免阻塞主線程
* GUI 更新節流：最短刷新 100ms 一次

---

## 🧩 16. 類別互動圖

```text
各模組 ─► SystemLogger ─► EventBus ─► GUI / FileLogWriter
                                  │
                                  └──► Diagnostics Panel (Latency)
```

---

## 🧪 17. 單元測試建議

* [ ] INFO/WARNING/ERROR 能正確廣播與接收
* [ ] GUI 顯示顏色與格式正確
* [ ] File Writer 正確分檔輪替
* [ ] 延遲欄位顯示正確
* [ ] 發生 Exception 時能記錄錯誤不崩潰
* [ ] 超過緩衝大小能自動警告

---

## 💡 18. 設計理念

* **事件即日誌（Event-as-Log）**：所有 Log 都以事件廣播，減少耦合。
* **人機可讀 + 機器可解析**：兼容 GUI 顯示與 CSV/JSON 匯出。
* **低延遲非同步**：Log 不應阻塞 STT/LLM pipeline。
* **安全降級**：即使 File Writer 失敗，也不影響 GUI 與 EventBus。
* **透明診斷**：延遲、錯誤、重試皆可追溯。
