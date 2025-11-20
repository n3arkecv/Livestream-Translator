下面是可直接放進專案的
**`/document/config_json_spec.md`**（完整規格 + JSON Schema + 範例檔）。
它與先前文件完全對齊（音訊擷取、STT/LLM、Overlay、System Log、Dialogue Log、Runtime Check、Context Memory、重試與延遲預算）。

---

# 🧩 `config.json` 規格說明（Config Spec）

版本：v0.1
相依文件：`project_overview.md`、`architecture_overview.md`、`modules_specification.md`、`audio_input_capture.md`、`transcription_system.md`、`translation_system.md`、`system_logging.md`、`dialogue_logging.md`、`context_memory.md`

---

## 1) 概觀

* 檔案位置：`./config.json`（可由 `--config path` 覆蓋）
* 支援 **環境變數覆蓋**（見 §7）與 **執行參數覆蓋**（最高優先級）
* **設定檔版本化**：`config_version`（見 §9 版本遷移）

---

## 2) 主要節點（Top-level Keys）

| Key                    | 類型     | 必填 | 說明                                                           |
| ---------------------- | ------ | -- | ------------------------------------------------------------ |
| `config_version`       | string | ✅  | 設定檔版本（例如 `"1.0.0"`）                                          |
| `profile`              | string | ❌  | 啟動檔名/環境名（例如 `"default"`, `"low_latency"`）                    |
| `audio`                | object | ✅  | WASAPI 音訊捕獲設定（見 §3.1）                                        |
| `chunk`                | object | ✅  | 音訊切片參數（大小/重疊）                                                |
| `stt`                  | object | ✅  | STT 模式與模型設定                                                  |
| `llm`                  | object | ✅  | LLM 翻譯與 API 設定                                               |
| `overlay`              | object | ✅  | Overlay 樣式與互動                                                |
| `gui`                  | object | ❌  | GUI 行為與診斷面板                                                  |
| `context_memory`       | object | ✅  | 語境記憶長度與模型                                                    |
| `runtime_check`        | object | ✅  | 啟動檢查項目                                                       |
| `retry`                | object | ✅  | 失敗重試策略                                                       |
| `latency_budget_ms`    | object | ✅  | 延遲預算（總/子階段）                                                  |
| `dialogue_log`         | object | ✅  | 對話紀錄輸出                                                       |
| `logging`              | object | ✅  | System Log 輸出與等級                                             |
| `paths`                | object | ❌  | 自訂資料夾路徑                                                      |
| `feature_flags`        | object | ❌  | 功能開關（實驗性）                                                    |

---

## 3) 詳細鍵值說明

### 3.1 `audio`（WASAPI 音訊捕獲設定）

| Key                    | 類型      | 必填 | 預設        | 說明                              |
| ---------------------- | ------- | -- | --------- | ------------------------------- |
| `output_device`        | string  | ✅  | `"default"` | 輸出設備名稱（`"default"` 使用系統預設設備） |
| `use_loopback`         | boolean | ✅  | `true`     | 啟用 WASAPI Loopback 模式（必須為 `true`） |
| `silence_threshold_db` | number  | ❌  | `-35.0`    | 靜音檢測閾值（dB）                       |

> 實作：見 `audio_input_capture.md` 和 `audio_capture_wasapi.md`，使用 `pyaudiowpatch` 進行 WASAPI Loopback 捕獲。

### 3.2 `chunk`

| Key          | 類型      | 預設  | 範圍       | 說明           |
| ------------ | ------- | --- | -------- | ------------ |
| `size_ms`    | integer | 640 | 160–1280 | 每個 Chunk 長度  |
| `overlap_ms` | integer | 160 | 0–640    | 相鄰 Chunk 重疊區 |

> 實作：見 `audio_input_capture.md`，發送 `audio.chunk_ready`。

---

### 3.3 `stt`

| Key                        | 類型              | 必填      | 預設           | 說明                         |             |                  |
| -------------------------- | --------------- | ------- | ------------ | -------------------------- | ----------- | ---------------- |
| `mode`                     | enum(`"local"   | "api"`) | ✅            | `"local"`                  | STT 路由選擇    |                  |
| `model`                    | string          | ✅       | `"small.en"` | FasterWhisper 型號或 API 型號別名 |             |                  |
| `language_hint`            | enum(`"auto"    | "en"    | "ja"`)       | ❌                          | `"auto"`    | 語言提示             |
| `device`                   | enum(`"cuda"    | "cpu"`) | ❌            | `"cuda"`                   | 本地推論裝置      |                  |
| `compute_type`             | enum(`"float16" | "int8"  | "float32"`)  | ❌                          | `"float16"` | FasterWhisper 精度 |
| `api`                      | object          | ❌       |              | 僅 `mode="api"` 使用          |             |                  |
| `partial_emit_interval_ms` | integer         | ❌       | 80           | partial 廣播節流               |             |                  |
| `queue_max_parallel`       | integer         | ❌       | 4            | 併發推論數上限                    |             |                  |

`stt.api`（僅 `mode="api"` 時）

| Key           | 類型             | 必填         | 範例/預設                                             | 說明         |         |
| ------------- | -------------- | ---------- | ------------------------------------------------- | ---------- | ------- |
| `provider`    | enum(`"openai" | "google"`) | ✅                                                 | `"openai"` | API 供應商 |
| `model`       | string         | ✅          | `"gpt-4o-mini-transcribe"` / `"gemini-2.5-flash"` | API 模型     |         |
| `endpoint`    | string         | ❌          |                                                   | 私有端點（選填）   |         |
| `api_key_env` | string         | ✅          | `"OPENAI_API_KEY"`                                | 從環境變數讀取    |         |

---

### 3.4 `llm`

| Key                 | 類型               | 必填 | 預設                          | 說明             |
| ------------------- | ---------------- | -- | --------------------------- | -------------- |
| `provider`          | enum(`"openai"`) | ✅  | `"openai"`                  | （現階段鎖定 OpenAI） |
| `model_translation` | string           | ✅  | `"gpt-4.1-mini-2025-04-14"` | LLM1（翻譯）       |
| `model_context`     | string           | ✅  | `"gpt-4.1-mini-2025-04-14"` | LLM2（情境摘要）     |
| `api_key_env`       | string           | ✅  | `"OPENAI_API_KEY"`          | 環境變數名          |
| `timeout_ms`        | integer          | ❌  | 8000                        | API 超時         |
| `temperature`       | number           | ❌  | 0.2                         | 0–2            |
| `max_output_tokens` | integer          | ❌  | 256                         | 單句輸出上限         |

---

### 3.5 `overlay`

| Key                 | 類型      | 預設    | 說明           |
| ------------------- | ------- | ----- | ------------ |
| `opacity`           | number  | 0.82  | 0.3–1.0      |
| `font_size`         | integer | 20    | 基準字級         |
| `background`        | boolean | true  | 背景卡          |
| `width_ratio`       | number  | 0.6   | 0.3–1.0      |
| `click_through`     | boolean | false | 點擊穿透         |
| `max_context_lines` | integer | 3     | Context 行數上限 |
| `antialias_text`    | boolean | true  | 抗鋸齒          |

---

### 3.6 `gui`

| Key                   | 類型      | 預設        | 說明              |
| --------------------- | ------- | --------- | --------------- |
| `language`            | string  | `"zh-TW"` | 介面語言            |
| `hotkeys`             | object  | `{}`      | F9/F10 等        |
| `diagnostics_enabled` | boolean | true      | 顯示診斷頁籤          |
| `auto_scroll_log`     | boolean | true      | System Log 追隨滾動 |

---

### 3.7 `context_memory`

| Key          | 類型      | 預設                          | 說明              |
| ------------ | ------- | --------------------------- | --------------- |
| `enabled`    | boolean | true                        | 開關              |
| `max_tokens` | integer | 500                         | 200–500 建議      |
| `llm2_model` | string  | `"gpt-4.1-mini-2025-04-14"` | 摘要模型（可與 LLM1 同） |

---

### 3.8 `runtime_check`

| Key                  | 類型      | 預設   | 說明               |
| -------------------- | ------- | ---- | ---------------- |
| `enabled`            | boolean | true | 啟動檢查             |
| `check_cuda`         | boolean | true | CUDA 可用性         |
| `check_ffmpeg`       | boolean | true | FFmpeg           |
| `check_models`       | boolean | true | FasterWhisper 模型 |
| `check_api_keys`     | boolean | true | API 金鑰           |
| `check_audio_device` | boolean | true | 音源裝置存在           |

---

### 3.9 `retry`

| Key            | 類型      | 預設  | 說明           |
| -------------- | ------- | --- | ------------ |
| `max_attempts` | integer | 2   | 0–5          |
| `backoff_ms`   | integer | 400 | 指數退避基底（倍數：2） |
| `jitter_ms`    | integer | 120 | 隨機擾動上限       |

---

### 3.10 `latency_budget_ms`

| Key       | 類型      | 預設   | 說明        |
| --------- | ------- | ---- | --------- |
| `total`   | integer | 1500 | 總預算（ms）   |
| `stt`     | integer | 500  | STT 預算    |
| `llm`     | integer | 700  | 翻譯 + 摘要預算 |
| `overlay` | integer | 100  | 繪製預算（顯示）  |

---

### 3.11 `dialogue_log`

| Key                | 類型            | 預設                | 說明      |           |      |
| ------------------ | ------------- | ----------------- | ------- | --------- | ---- |
| `enabled`          | boolean       | true              | 是否寫入    |           |      |
| `output_format`    | enum(`"jsonl" | "csv"             | "txt"`) | `"jsonl"` | 檔案格式 |
| `folder`           | string        | `"logs/dialogue"` | 儲存資料夾   |           |      |
| `rotate_hourly`    | boolean       | true              | 逐時輪替    |           |      |
| `max_file_size_mb` | integer       | 10                | 超額新檔    |           |      |

---

### 3.12 `logging`（System Log）

| Key                | 類型           | 預設                  | 說明           |          |        |
| ------------------ | ------------ | ------------------- | ------------ | -------- | ------ |
| `level`            | enum(`"INFO" | "WARNING"           | "ERROR"`)    | `"INFO"` | 最低輸出級別 |
| `file_path`        | string       | `"logs/system.log"` | JSONL        |          |        |
| `rotate_daily`     | boolean      | true                | 每日換檔         |          |        |
| `max_file_size_mb` | integer      | 10                  | 超額新檔         |          |        |
| `console_output`   | boolean      | true                | 是否輸出到 STDOUT |          |        |

---

### 3.13 `paths`（選用）

| Key           | 類型     | 說明                  |
| ------------- | ------ | ------------------- |
| `models_dir`  | string | FasterWhisper 模型資料夾 |
| `temp_dir`    | string | 暫存路徑                |
| `exports_dir` | string | 匯出路徑                |

---

### 3.14 `feature_flags`（選用）

| Key                            | 類型      | 預設    | 說明                |
| ------------------------------ | ------- | ----- | ----------------- |
| `use_async_eventbus`           | boolean | false | 切換為 asyncio 事件匯流排 |
| `enable_click_through_overlay` | boolean | false | Windows 點擊穿透      |
| `silence_skip`                 | boolean | true  | 跳過靜音 Chunk        |

---

## 4) **最小可用設定**（Minimal Example）

```json
{
  "config_version": "1.0.0",
  "audio": {
    "output_device": "default",
    "use_loopback": true,
    "silence_threshold_db": -35.0
  },
  "chunk": { "size_ms": 640, "overlap_ms": 160 },
  "stt": { "mode": "local", "model": "small.en" },
  "llm": {
    "provider": "openai",
    "model_translation": "gpt-4.1-mini-2025-04-14",
    "model_context": "gpt-4.1-mini-2025-04-14",
    "api_key_env": "OPENAI_API_KEY"
  },
  "overlay": { "opacity": 0.82, "font_size": 20, "background": true, "width_ratio": 0.6, "click_through": false },
  "context_memory": { "enabled": true, "max_tokens": 500, "llm2_model": "gpt-4.1-mini-2025-04-14" },
  "runtime_check": { "enabled": true, "check_cuda": true, "check_ffmpeg": true, "check_models": true, "check_api_keys": true, "check_audio_device": true },
  "retry": { "max_attempts": 2, "backoff_ms": 400, "jitter_ms": 120 },
  "latency_budget_ms": { "total": 1500, "stt": 500, "llm": 700, "overlay": 100 },
  "dialogue_log": { "enabled": true, "output_format": "jsonl", "folder": "logs/dialogue", "rotate_hourly": true, "max_file_size_mb": 10 },
  "logging": { "level": "INFO", "file_path": "logs/system.log", "rotate_daily": true, "max_file_size_mb": 10, "console_output": true }
}
```

---

## 5) **完整進階設定**（Full Example）

```json
{
  "config_version": "1.0.0",
  "profile": "low_latency",

  "audio": {
    "output_device": "default",
    "use_loopback": true,
    "silence_threshold_db": -35.0
  },
  "chunk": { "size_ms": 640, "overlap_ms": 160 },

  "stt": {
    "mode": "api",
    "model": "gpt-4o-mini-transcribe",
    "language_hint": "auto",
    "device": "cuda",
    "compute_type": "float16",
    "api": {
      "provider": "openai",
      "model": "gpt-4o-mini-transcribe",
      "endpoint": "",
      "api_key_env": "OPENAI_API_KEY"
    },
    "partial_emit_interval_ms": 80,
    "queue_max_parallel": 4
  },

  "llm": {
    "provider": "openai",
    "model_translation": "gpt-4.1-mini-2025-04-14",
    "model_context": "gpt-4.1-mini-2025-04-14",
    "api_key_env": "OPENAI_API_KEY",
    "timeout_ms": 8000,
    "temperature": 0.2,
    "max_output_tokens": 256
  },

  "overlay": {
    "opacity": 0.85,
    "font_size": 22,
    "background": true,
    "width_ratio": 0.55,
    "click_through": false,
    "max_context_lines": 3,
    "antialias_text": true
  },

  "gui": {
    "language": "zh-TW",
    "diagnostics_enabled": true,
    "auto_scroll_log": true,
    "hotkeys": { "start": "F9", "stop": "F10", "toggle_overlay_bg": "Ctrl+Shift+O" }
  },

  "context_memory": {
    "enabled": true,
    "max_tokens": 500,
    "llm2_model": "gpt-4.1-mini-2025-04-14"
  },

  "runtime_check": {
    "enabled": true,
    "check_cuda": true,
    "check_ffmpeg": true,
    "check_models": true,
    "check_api_keys": true,
    "check_audio_device": true
  },

  "retry": { "max_attempts": 2, "backoff_ms": 400, "jitter_ms": 120 },

  "latency_budget_ms": { "total": 1500, "stt": 500, "llm": 700, "overlay": 100 },

  "dialogue_log": {
    "enabled": true,
    "output_format": "jsonl",
    "folder": "logs/dialogue",
    "rotate_hourly": true,
    "max_file_size_mb": 10
  },

  "logging": {
    "level": "INFO",
    "file_path": "logs/system.log",
    "rotate_daily": true,
    "max_file_size_mb": 10,
    "console_output": true
  },

  "paths": {
    "models_dir": "models",
    "temp_dir": "temp",
    "exports_dir": "exports"
  },

  "feature_flags": {
    "use_async_eventbus": false,
    "enable_click_through_overlay": false,
    "silence_skip": true
  }
}
```

---

## 6) **JSON Schema**（Draft 2020-12）

> 可用於啟動時驗證設定（若失敗，GUI 顯示缺失與建議）

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "YouTube Live Translation App Config",
  "type": "object",
  "required": ["config_version","audio","chunk","stt","llm","overlay","context_memory","runtime_check","retry","latency_budget_ms","dialogue_log","logging"],
  "properties": {
    "config_version": { "type": "string" },
    "profile": { "type": "string" },

    "audio": {
      "type": "object",
      "required": ["output_device","use_loopback"],
      "properties": {
        "output_device": { "type": "string", "minLength": 1 },
        "use_loopback": { "type": "boolean" },
        "silence_threshold_db": { "type": "number", "minimum": -60, "maximum": 0 }
      }
    },

    "chunk": {
      "type": "object",
      "required": ["size_ms","overlap_ms"],
      "properties": {
        "size_ms": { "type": "integer", "minimum": 160, "maximum": 1280 },
        "overlap_ms": { "type": "integer", "minimum": 0, "maximum": 640 }
      }
    },

    "silence_threshold_db": { "type": "number" },

    "stt": {
      "type": "object",
      "required": ["mode","model"],
      "properties": {
        "mode": { "enum": ["local","api"] },
        "model": { "type": "string" },
        "language_hint": { "enum": ["auto","en","ja"] },
        "device": { "enum": ["cuda","cpu"] },
        "compute_type": { "enum": ["float16","int8","float32"] },
        "partial_emit_interval_ms": { "type": "integer", "minimum": 20, "maximum": 500 },
        "queue_max_parallel": { "type": "integer", "minimum": 1, "maximum": 16 },
        "api": {
          "type": "object",
          "properties": {
            "provider": { "enum": ["openai","google"] },
            "model": { "type": "string" },
            "endpoint": { "type": "string" },
            "api_key_env": { "type": "string" }
          }
        }
      }
    },

    "llm": {
      "type": "object",
      "required": ["provider","model_translation","model_context","api_key_env"],
      "properties": {
        "provider": { "enum": ["openai"] },
        "model_translation": { "type": "string" },
        "model_context": { "type": "string" },
        "api_key_env": { "type": "string" },
        "timeout_ms": { "type": "integer", "minimum": 1000, "maximum": 60000 },
        "temperature": { "type": "number", "minimum": 0, "maximum": 2 },
        "max_output_tokens": { "type": "integer", "minimum": 16, "maximum": 4096 }
      }
    },

    "overlay": {
      "type": "object",
      "required": ["opacity","font_size","background","width_ratio","click_through"],
      "properties": {
        "opacity": { "type": "number", "minimum": 0.3, "maximum": 1.0 },
        "font_size": { "type": "integer", "minimum": 10, "maximum": 72 },
        "background": { "type": "boolean" },
        "width_ratio": { "type": "number", "minimum": 0.3, "maximum": 1.0 },
        "click_through": { "type": "boolean" },
        "max_context_lines": { "type": "integer", "minimum": 1, "maximum": 10 },
        "antialias_text": { "type": "boolean" }
      }
    },

    "gui": {
      "type": "object",
      "properties": {
        "language": { "type": "string" },
        "diagnostics_enabled": { "type": "boolean" },
        "auto_scroll_log": { "type": "boolean" },
        "hotkeys": { "type": "object" }
      }
    },

    "context_memory": {
      "type": "object",
      "required": ["enabled","max_tokens","llm2_model"],
      "properties": {
        "enabled": { "type": "boolean" },
        "max_tokens": { "type": "integer", "minimum": 200, "maximum": 2000 },
        "llm2_model": { "type": "string" }
      }
    },

    "runtime_check": {
      "type": "object",
      "required": ["enabled","check_cuda","check_ffmpeg","check_models","check_api_keys","check_audio_device"],
      "properties": {
        "enabled": { "type": "boolean" },
        "check_cuda": { "type": "boolean" },
        "check_ffmpeg": { "type": "boolean" },
        "check_models": { "type": "boolean" },
        "check_api_keys": { "type": "boolean" },
        "check_audio_device": { "type": "boolean" }
      }
    },

    "retry": {
      "type": "object",
      "required": ["max_attempts","backoff_ms","jitter_ms"],
      "properties": {
        "max_attempts": { "type": "integer", "minimum": 0, "maximum": 5 },
        "backoff_ms": { "type": "integer", "minimum": 0, "maximum": 60000 },
        "jitter_ms": { "type": "integer", "minimum": 0, "maximum": 2000 }
      }
    },

    "latency_budget_ms": {
      "type": "object",
      "required": ["total","stt","llm","overlay"],
      "properties": {
        "total": { "type": "integer", "minimum": 200, "maximum": 5000 },
        "stt": { "type": "integer", "minimum": 50, "maximum": 3000 },
        "llm": { "type": "integer", "minimum": 50, "maximum": 3000 },
        "overlay": { "type": "integer", "minimum": 10, "maximum": 1000 }
      }
    },

    "dialogue_log": {
      "type": "object",
      "required": ["enabled","output_format","folder","rotate_hourly","max_file_size_mb"],
      "properties": {
        "enabled": { "type": "boolean" },
        "output_format": { "enum": ["jsonl","csv","txt"] },
        "folder": { "type": "string" },
        "rotate_hourly": { "type": "boolean" },
        "max_file_size_mb": { "type": "integer", "minimum": 1, "maximum": 1024 }
      }
    },

    "logging": {
      "type": "object",
      "required": ["level","file_path","rotate_daily","max_file_size_mb","console_output"],
      "properties": {
        "level": { "enum": ["INFO","WARNING","ERROR"] },
        "file_path": { "type": "string" },
        "rotate_daily": { "type": "boolean" },
        "max_file_size_mb": { "type": "integer", "minimum": 1, "maximum": 1024 },
        "console_output": { "type": "boolean" }
      }
    },

    "paths": {
      "type": "object",
      "properties": {
        "models_dir": { "type": "string" },
        "temp_dir": { "type": "string" },
        "exports_dir": { "type": "string" }
      }
    },

    "feature_flags": {
      "type": "object",
      "properties": {
        "use_async_eventbus": { "type": "boolean" },
        "enable_click_through_overlay": { "type": "boolean" },
        "silence_skip": { "type": "boolean" }
      }
    }
  }
}
```

---

## 7) **環境變數覆蓋（ENV Overrides）**

* 目的：避免把金鑰寫進檔案；部署時可快速切換
* 規則：若存在對應環境變數，優先於 `config.json`
* 主要鍵位：

  * `OPENAI_API_KEY`（對應 `llm.api_key_env` 與 `stt.api.api_key_env`）
  * `YTTRANS_AUDIO_DEVICE`（覆蓋 `audio.output_device`）
  * `YTTRANS_PROFILE`（覆蓋 `profile`）

---

## 8) **驗證流程（Validation）**

* 啟動時執行：

  1. 載入 `config.json` → 以 **JSON Schema** 驗證（若失敗 GUI 彈窗 + `runtime.check_result`）
  2. 套用 ENV 覆蓋
  3. 套用 CLI 覆蓋（最高優先）
  4. 發送 `app.started`（帶 `config_snapshot`）

---

## 9) **版本遷移（Migration）**

* `config_version` 由 `major.minor.patch` 三段
* 若主版本不符（`major` 變化），由 `ConfigMigrator` 做鍵名搬遷與預設填補
* 典型遷移：

  * `stt.api_key` → `stt.api.api_key_env`
  * `llm.model` → `llm.model_translation` + `llm.model_context`
  * **WASAPI 遷移**：`audio_device` → `audio.output_device` + `audio.use_loopback`

### 9.1 WASAPI 配置遷移範例

從舊版配置（使用 `audio_device`）遷移至新版（使用 `audio` 物件）：

```python
# 舊配置
old_config = {
    "audio_device": "Stereo Mix",
    "silence_threshold_db": -35.0,
    ...
}

# 遷移腳本（ConfigMigrator 自動處理）
new_config = {
    "audio": {
        "output_device": old_config.get("audio_device", "default"),
        "use_loopback": True,  # WASAPI 必須啟用
        "silence_threshold_db": old_config.get("silence_threshold_db", -35.0)
    },
    ...
}
```

**注意**：
- 舊版 `audio_device` 值（如 "Stereo Mix"）需對應到 WASAPI 輸出設備名稱
- 若設備名稱不存在，自動使用 `"default"`（系統預設輸出設備）
- `use_loopback` 必須為 `true`（WASAPI Loopback 模式）

---

## 10) **安全與隱私**

* **不要**把 API 金鑰寫入 `config.json`；改用環境變數
* `dialogue_log` 可能含敏感語句；請控管 `folder` 權限
* 若要匿名化，擴充 `feature_flags.anonymize_dialogue`（後續版本）

---

## 11) **常見組合（Profiles）**

* `default`：本地 STT、一般延遲
* `low_latency`：API STT、較高頻 partial、LLM 超時更低
* `offline`：完全本地（STT 本地，LLM 連線；後續可加入本地 LLM）
