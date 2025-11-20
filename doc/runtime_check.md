# 🧩 Runtime Check Design — Real-Time YouTube Live Translation App
對應文件：

* `/project_overview.md`
* `/architecture_overview.md`
* `/modules_specification.md`
* `/gui_overlay.md`
* `/system_logging.md`

---

## 🧭 1. 系統定位

Runtime Check 模組是系統啟動階段的「診斷與依賴檢查層」。
負責在應用開啟 GUI 與 Overlay 後，
確認所有必要組件、模型、API 金鑰與執行環境皆可正常運作。

### 執行時機

```text
App 啟動 → GUI / Overlay Ready → RuntimeCheck.start() → STT / LLM 預熱
```

### 核心任務

| 分類     | 目標                         | 動作                      |
| ------ | -------------------------- | ----------------------- |
| 系統環境   | 檢查 OS / Python / CUDA      | 確保運行支援 GPU 加速           |
| 外部依賴   | 檢查 FFmpeg / pyaudiowpatch      | 音訊與影片處理                 |
| 模型檔案   | FasterWhisper 模型是否存在       | 提示下載缺失模型                |
| API 憑證 | 檢查 OpenAI / Google API Key | 避免 API 模式報錯             |
| 權限     | 確認音訊裝置可用                   | 驗證輸入來源                  |
| 錯誤處理   | 若缺項則提示安裝                   | GUI 彈出指引並記錄於 System Log |

---

## 🧱 2. 系統架構

```text
[Main App]
   │
   ├──► GUI & Overlay 啟動
   │
   └──► RuntimeCheck Module
          │
          ├──► 環境檢查 (EnvChecker)
          ├──► 模型檢查 (ModelChecker)
          ├──► API Key 檢查 (APIChecker)
          ├──► 音訊裝置檢查 (AudioDeviceChecker)
          └──► 結果廣播 (runtime.check_result)
```

---

## ⚙️ 3. 模組清單與職責

| 模組名稱                    | 職責                        | 輸出事件                                             |
| ----------------------- | ------------------------- | ------------------------------------------------ |
| **RuntimeCheckManager** | 啟動並整合所有檢查項目               | `runtime.check_started` / `runtime.check_result` |
| **EnvChecker**          | 檢查 OS、Python、CUDA、FFmpeg  | -                                                |
| **ModelChecker**        | 檢查 FasterWhisper 模型檔案     | -                                                |
| **APIChecker**          | 檢查 OpenAI / Google API 金鑰 | -                                                |
| **AudioDeviceChecker**  | 確認輸入裝置可用                  | -                                                |
| **SystemLogger**        | 紀錄檢查結果、錯誤                 | `syslog.info / syslog.warning / syslog.error`    |
| **GUI Handler**         | 顯示提示或安裝建議                 | 使用 QMessageBox 或 QDialog                         |

---

## 🔍 4. 檢查項目詳細規格

### 🧠 EnvChecker

| 項目        | 檢查方法                                     | 通過條件          | 錯誤提示                |
| --------- | ---------------------------------------- | ------------- | ------------------- |
| Python 版本 | `sys.version_info`                       | ≥ 3.10        | 請升級至 Python 3.10 以上 |
| CUDA 支援   | `torch.cuda.is_available()`              | True          | GPU 未啟用，可能造成延遲      |
| FFmpeg    | `subprocess.run(["ffmpeg", "-version"])` | exit=0        | 未安裝 FFmpeg          |
| OS        | `platform.system()`                      | Windows 10/11 | 其他系統可能不支援音源擷取       |

### 🧩 ModelChecker

| 檢查項目             | 路徑                                  | 備註                           |
| ---------------- | ----------------------------------- | ---------------------------- |
| FasterWhisper 模型 | `models/faster-whisper-{model}.bin` | 由 `config.json.stt_model` 指定 |
| 模型檔大小            | > 50MB                              | 判定模型是否完整下載                   |

若模型不存在 → GUI 彈窗提示：

> 「找不到 FasterWhisper 模型檔，是否立即下載？」

---

### 🔑 APIChecker

| 項目             | 環境變數             | 通過條件           | 錯誤提示          |
| -------------- | ---------------- | -------------- | ------------- |
| OpenAI API Key | `OPENAI_API_KEY` | 長度 > 40        | 未設定或無效        |
| Google API Key | `GOOGLE_API_KEY` | 可選（若啟用 Gemini） | 建議設定以使用雲端 STT |

---

### 🎧 AudioDeviceChecker

| 項目     | 方法                               | 條件             |
| ------ | -------------------------------- | -------------- |
| WASAPI 可用性 | `pyaudiowpatch.PyAudio().get_host_api_info_by_type(pyaudio.paWASAPI)` | WASAPI 主機 API 存在 |
| 輸出裝置列表 | `pyaudiowpatch` 遍歷 WASAPI 輸出設備    | 至少有一項輸出裝置      |
| 使用者選擇  | `config.json.audio.output_device`       | 必須存在於可用輸出裝置中（或為 `"default"`）     |
| Loopback 支援   | 驗證 `config.json.audio.use_loopback == true` | 必須啟用 Loopback 模式 |

**實作範例：**

```python
# runtime/audio_device_checker.py
import pyaudiowpatch as pyaudio
from typing import Tuple, List

class AudioDeviceChecker:
    def __init__(self, config):
        self.config = config
    
    async def run(self) -> Tuple[bool, List[str]]:
        """檢查 WASAPI 音訊設備"""
        missing = []
        
        # 1. 檢查 WASAPI 可用性
        try:
            p = pyaudio.PyAudio()
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
            p.terminate()
        except Exception as e:
            missing.append(f"WASAPI 不可用: {str(e)}")
            return False, missing
        
        # 2. 檢查輸出設備列表
        p = pyaudio.PyAudio()
        wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        output_devices = []
        
        for i in range(p.get_device_count()):
            dev = p.get_device_info_by_index(i)
            if dev['hostApi'] == wasapi_info['index']:
                if dev['maxOutputChannels'] > 0:
                    output_devices.append({
                        'index': i,
                        'name': dev['name']
                    })
        
        p.terminate()
        
        if len(output_devices) == 0:
            missing.append("找不到 WASAPI 輸出設備")
            return False, missing
        
        # 3. 檢查使用者選擇的設備
        audio_config = self.config.get("audio", {})
        output_device = audio_config.get("output_device", "default")
        use_loopback = audio_config.get("use_loopback", True)
        
        if not use_loopback:
            missing.append("use_loopback 必須為 true（WASAPI Loopback 模式）")
            return False, missing
        
        if output_device != "default":
            device_names = [d['name'] for d in output_devices]
            if output_device not in device_names:
                missing.append(f"指定的輸出設備 '{output_device}' 不存在")
                return False, missing
        
        return True, []
```

---

## 🧾 5. 檢查事件與回報格式

### 事件：`runtime.check_result`

對應 `/core/events.py` 中的 `RuntimeCheckResultPayload`

```json
{
  "ok": false,
  "missing_items": [
    "CUDA Toolkit",
    "FFmpeg",
    "faster-whisper-base.en model"
  ],
  "timestamp": "2025-11-11T09:00:12Z",
  "session_id": "yt_demo_001"
}
```

若通過全部檢查：

```json
{
  "ok": true,
  "missing_items": []
}
```

---

## 🧩 6. 類別設計（供程式生成）

```python
# runtime/check_manager.py
class RuntimeCheckManager:
    def __init__(self, bus, config, gui):
        self.bus = bus
        self.config = config
        self.gui = gui
        self.checkers = [
            EnvChecker(),
            ModelChecker(config),
            APIChecker(config),
            AudioDeviceChecker(config),
        ]

    async def run_all(self):
        self.bus.emit(EventName.RUNTIME_CHECK_STARTED)
        missing = []
        for checker in self.checkers:
            try:
                ok, items = await checker.run()
                if not ok:
                    missing.extend(items)
            except Exception as e:
                missing.append(str(e))
        ok = len(missing) == 0
        self.bus.emit(EventName.RUNTIME_CHECK_RESULT, {"ok": ok, "missing_items": missing})
        if ok:
            SystemLogger.info("Runtime check passed", component="runtime")
        else:
            SystemLogger.warning(f"Missing dependencies: {', '.join(missing)}", component="runtime")
            self.gui.prompt_missing_items(missing)
```

---

## 🧰 7. GUI 通知邏輯

### 行為流程

```text
runtime.check_result (ok=false)
   ↓
GUI 顯示彈窗提示
   ↓
使用者可點選「安裝指南」→ 開啟外部連結
```

### 介面範例

```python
# gui/runtime_prompt.py
class RuntimePrompt(QDialog):
    def __init__(self, missing_items):
        super().__init__()
        self.setWindowTitle("環境檢查結果")
        msg = "\n".join([f"• {m}" for m in missing_items])
        QLabel(f"以下項目缺失：\n{msg}\n\n請依指示安裝後重新啟動。", self)
```

---

## 🧩 8. System Log 整合

| 狀態   | Log 等級  | 範例訊息                                      |
| ---- | ------- | ----------------------------------------- |
| 檢查開始 | INFO    | `[Runtime] Checking environment...`       |
| 檢查通過 | INFO    | `[Runtime] All dependencies OK`           |
| 缺項   | WARNING | `[Runtime] Missing FFmpeg`                |
| 無法執行 | ERROR   | `[Runtime] Checker failed with Exception` |

---

## 🧩 9. Config.json 對應設定

```json
{
  "runtime_check": {
    "enabled": true,
    "check_cuda": true,
    "check_ffmpeg": true,
    "check_models": true,
    "check_api_keys": true,
    "check_audio_device": true
  }
}
```

---

## 🔍 10. 檢查優先順序與執行時間

| 順序 | 模組                 | 估計耗時      | 並行 |
| -- | ------------------ | --------- | -- |
| 1  | EnvChecker         | 100–300ms | ✅  |
| 2  | ModelChecker       | 50–100ms  | ✅  |
| 3  | APIChecker         | <50ms     | ✅  |
| 4  | AudioDeviceChecker | 50–200ms  | ✅  |

總耗時：約 0.5 秒（非同步並行）

---

## ⚡ 11. 事件互動圖

```text
app.started
   │
   ▼
runtime.check_started
   │
   ▼
RuntimeCheckManager.run_all()
   │
   ├─► EnvChecker
   ├─► ModelChecker
   ├─► APIChecker
   └─► AudioDeviceChecker
   │
   ▼
runtime.check_result
   ├─► SystemLog (info/warn)
   ├─► GUI RuntimePrompt
   └─► pipeline.prewarm()
```

---

## 📈 12. 效能與健全性

| 指標                  | 來源                   | 說明      |
| ------------------- | -------------------- | ------- |
| `check_duration_ms` | RuntimeCheckManager  | 單次檢查耗時  |
| `missing_count`     | runtime.check_result | 缺少項目數量  |
| `pass_rate`         | 週期性統計                | 環境健康度指標 |

---

## ✅ 13. 測試項目

* [ ] GUI 啟動後自動執行檢查
* [ ] 所有環境檢查項皆正確偵測
* [ ] 缺少模型時正確提示
* [ ] API Key 錯誤時出現警示窗
* [ ] 缺少音源裝置時顯示明確說明
* [ ] 正常環境下不影響 STT 預熱速度
* [ ] `runtime.check_result` 廣播事件格式正確

---

## 🧱 14. 設計理念摘要

* **用戶導向**：在 GUI 層清楚告知缺項與解法。
* **非阻塞設計**：檢查完成後才啟動 STT/LLM 預熱，避免 UI 卡頓。
* **高透明度**：所有檢查結果同步記錄到 System Log。
* **模組化**：可單獨關閉某類檢查（config 設定）。
* **可擴充性**：未來可加入 GPU 記憶體檢查、網路延遲檢查。
