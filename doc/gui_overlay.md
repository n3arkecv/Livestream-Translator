# 🪟 GUI & Overlay Design — Real-Time YouTube Live Translation App

對齊 `project_overview.md` / `architecture_overview.md` / `modules_specification.md`
框架：**PyQt6 / PySide6**（以 Qt 6 API 為主，若選 PyQt5 請在實作時替換匯入）

---

## 1. 目標

* 啟動順序：**GUI → Overlay → RuntimeCheck → STT/LLM 預熱**
* 使用者可視化控制：音源選擇、透明度、背景、大小、拖曳、Start/Stop、Log 區
* 顯示三區塊（同時）：**Ongoing Sentence / Translated Sentence / Scenario Context**
* System Log 與 Dialogue Log 分離：

  * GUI Log 面板只顯示 **System Log**（資訊/警告/錯誤彩色）
  * Dialogue Log **不在 GUI 面板中呈現**，僅寫檔
* 延遲預算：整體 0.5–1.5s；UI 重繪頻率 60Hz（partial 文字節流至 50–120ms）

---

## 2. UI 版面（Wireframe）

### 2.1 主視窗（MainWindow）

| 區塊      | 元件                          | 說明                                                                             |
| ------- | --------------------------- | ------------------------------------------------------------------------------ |
| Toolbar | `QToolBar` + `QAction`      | Start / Stop、開啟設定、匯出 System Log                                                |
| 左側面板    | `QGroupBox` + `QFormLayout` | **音源**（輸出裝置下拉，WASAPI Loopback）、**STT 模式**（Local/API）、**Overlay 外觀**（透明度、背景開關、字體大小、寬度）          |
| 中央面板    | `QTabWidget`                | Tab1: **System Log**（`QPlainTextEdit`，只讀、彩色高亮）／Tab2: **診斷**（即時延遲、Queue 長度、FPS） |
| 狀態列     | `QStatusBar`                | 目前狀態（Idle / Running / Error）、當前 session_id、GPU/CPU 利用率摘要                       |

> 工程細節：左側面板變更設定後 **不立即套用 Overlay**，需點擊「套用」或 Start 才會生效（避免高頻訊號造成卡頓）。

### 2.2 Overlay 視窗（浮動字幕）

* `QWidget`（無邊框、**AlwaysOnTop**、**FramelessWindowHint**、**Tool**）
* 透明背景（`setAttribute(Qt.WA_TranslucentBackground)`），可選「有背景卡」模式（半透明圓角）
* 可拖曳、可調整大小（自製邊框抓手）
* 三段文字區（直向堆疊）：

  1. **Ongoing**：`QLabel`（大字、動態更新，單行省略）
  2. **Translated**：`QLabel`（中大字、整句出現）
  3. **Scenario Context**：`QLabel`（小字、可換行，最多 N 行，超出以淡出尾端）
* 可選 **點擊穿透模式**（讓滑鼠事件穿過 Overlay，不擋到前景 App；透過 Windows API/Qt Flag 實作，預設關閉）

---

## 3. 外觀樣式（預設 Theme）

* 字型：`Noto Sans TC` / `Noto Sans JP` / 系統字型 fallback
* 顏色（可在 `config.json.overlay` 覆寫）：

  * Ongoing：#FFFFFF / 投影描邊
  * Translated：#E6F4FF / 粗體
  * Context：#BBD2F3 / 小字
* 背景卡：圓角 12px、半透明黑 `rgba(0,0,0,0.25)`（可關閉）
* System Log 彩色規則（顯示在 GUI Log 面板）：

  * INFO 🔵：`#5DA9FF`
  * WARNING 🟡：`#FFC857`
  * ERROR 🔴：`#FF4D4F`（行前加❗）

---

## 4. GUI 控制項與設定對應

| 設定鍵                       | 元件                 | 型別    | 範圍/選項                     | 影響             |
| ------------------------- | ------------------ | ----- | ------------------------- | -------------- |
| `audio.output_device`     | QComboBox          | str   | WASAPI 輸出設備列表（Loopback 模式） | Audio Capture  |
| `stt_mode`                | QComboBox          | enum  | `local`/`api`             | STT Routing    |
| `stt_model`               | QComboBox/LineEdit | str   | faster-whisper 款式或 API 選項 | STT            |
| `overlay.opacity`         | QSlider + Spin     | float | 0.3–1.0                   | 視窗透明度          |
| `overlay.font_size`       | Spin               | int   | 12–48                     | 三區塊基準字級        |
| `overlay.background`      | QCheckBox          | bool  | ON/OFF                    | 背景卡            |
| `overlay.width_ratio`     | Slider             | float | 0.3–1.0                   | Overlay 寬度佔螢幕比 |
| `overlay.click_through`   | QCheckBox          | bool  | ON/OFF                    | 點擊穿透           |
| `latency_budget_ms.total` | Spin               | int   | 500–2000                  | 診斷與警示線         |
| `retry.max_attempts`      | Spin               | int   | 0–5                       | LLM/STT 重試上限   |

> 設定持久化：由 **Config 模組** 讀寫 `config.json`，GUI 僅作編輯/呈現。

---

## 5. Overlay 渲染設計

* **資料來源**：事件匯流排（EventBus）

  * `stt.partial` → `update_partial(text)`（節流 50–120ms）
  * `llm1.translate_finished` → `update_translation(text)`
  * `llm2.context_update_finished` → `update_context(snippet)`
* **更新策略**：

  * Ongoing 採「覆寫」；若句界確定 (`stt.boundary_detected`) 則暫停 80–150ms 等待 `final`
  * Translated/Context 為「原子替換」，避免中途閃爍
* **DPI/縮放**：讀取 `QScreen.logicalDotsPerInch()` 調整字體大小與邊距
* **抗鋸齒**：啟用 `Qt.TextAntialiasing` 與 `Qt.HighDpiScaling`

---

## 6. 設備選擇器實作（WASAPI 輸出設備）

### 6.1 輸出設備列表獲取

GUI 模組需要列出 WASAPI 輸出設備供使用者選擇：

```python
# gui/device_selector.py
import pyaudiowpatch as pyaudio
from PyQt6.QtWidgets import QComboBox

def get_output_devices():
    """獲取 WASAPI 輸出設備列表"""
    p = pyaudio.PyAudio()
    wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
    devices = []
    
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        if dev['hostApi'] == wasapi_info['index']:
            # 只列出輸出設備（maxOutputChannels > 0）
            if dev['maxOutputChannels'] > 0:
                devices.append({
                    'index': i,
                    'name': dev['name'],
                    'is_default': i == wasapi_info['defaultOutputDevice']
                })
    
    p.terminate()
    return devices

class AudioDeviceComboBox(QComboBox):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.refresh_devices()
        self.currentTextChanged.connect(self.on_device_changed)
    
    def refresh_devices(self):
        """刷新設備列表"""
        self.clear()
        devices = get_output_devices()
        for dev in devices:
            name = dev['name']
            if dev['is_default']:
                name += " (預設)"
            self.addItem(name, dev['index'])
        
        # 設定當前選擇
        current_device = self.config.get("audio", {}).get("output_device", "default")
        if current_device == "default":
            # 選擇預設設備
            for i in range(self.count()):
                if "(預設)" in self.itemText(i):
                    self.setCurrentIndex(i)
                    break
        else:
            # 選擇指定設備
            for i in range(self.count()):
                if self.itemText(i).replace(" (預設)", "") == current_device:
                    self.setCurrentIndex(i)
                    break
    
    def on_device_changed(self, text):
        """設備變更時更新配置"""
        index = self.currentData()
        if index is not None:
            device_name = self.itemText(self.currentIndex()).replace(" (預設)", "")
            self.config["audio"]["output_device"] = device_name
```

> **注意**：設備選擇器需在 GUI 啟動時初始化，並在 Runtime Check 通過後刷新列表。

---

## 7. 狀態機（State Machine）

```text
IDLE -> (Start) -> RUNNING -> (Error | Stop) -> STOPPING -> IDLE
```

* **IDLE**：GUI 可編輯設定；Overlay 可見但顯示空白提示
* **RUNNING**：管線啟動；部件只讀；顯示 partial/translated/context
* **STOPPING**：收尾（關 stream、flush Dialogue Log）；完成後回 IDLE

> 狀態切換由 GUI 發 `app.start_pressed` / `app.stop_pressed`；其他模組在 System Log 回報完成。

---

## 7. 訊號／事件對應（Qt Signals ↔ EventBus）

| 來源       | UI/事件                          | 發送/接收                                 | 說明                 |
| -------- | ------------------------------ | ------------------------------------- | ------------------ |
| GUI      | Start 按鈕                       | 發送 `app.start_pressed`                | 觸發主流程              |
| GUI      | Stop 按鈕                        | 發送 `app.stop_pressed`                 | 終止流程               |
| GUI      | 設定變更                           | 寫入 Config → `app.started` 內含 snapshot | 不即時套用，待 Start      |
| EventBus | `stt.partial`                  | Overlay 處理                            | 更新 Ongoing         |
| EventBus | `llm1.translate_finished`      | Overlay 處理 & DialogueLog 寫入           | 顯示譯文               |
| EventBus | `llm2.context_update_finished` | Overlay 處理 & DialogueLog 寫入           | 顯示語境               |
| EventBus | `syslog.*`                     | GUI Log 面板處理                          | 彩色輸出（僅 System Log） |

---

## 8. 執行緒與非同步

* 主執行緒：**GUI/Overlay**（Qt 事件迴圈）
* 後台工作：Audio、STT、LLM → 使用 `QThread` 或 `asyncio` + `QEventLoop`（二擇一，專案統一）
* EventBus：目前同步；若採 `asyncio`，提供 async bus（之後可替換）
* UI 更新：使用 `QMetaObject.invokeMethod` 或 `pyqtSignal` 切回主執行緒

---

## 9. System Log 與 Dialogue Log

* **System Log（GUI 顯示）**：訂閱 `syslog.info/warning/error`；彩色追加到 `QPlainTextEdit`
* **Dialogue Log（不顯示）**：由 Dialogue Log 模組寫 `.csv/.json/.txt`，GUI 只在「診斷」Tab 顯示**累計筆數**與檔案路徑

---

## 10. 鍵盤快捷鍵（預設）

* `F9`：Start
* `F10`：Stop
* `Ctrl + + / -`：Overlay 字體放大/縮小
* `Ctrl + Shift + O`：切換 Overlay 背景卡
* `Ctrl + Shift + T`：切換點擊穿透

---

## 11. 錯誤處理與提示

* 重大錯誤（`syslog.error`）→ `QSystemTrayIcon` 氣泡 + 狀態列紅點
* 缺少 Runtime 項：彈出 `QMessageBox`，同時在左側面板提供「一鍵安裝指引」連結
* Overlay 文字過長：省略（`elide`）+ 滾動字幕（可選，預設關閉）

---

## 12. 測試清單（UI/UX）

* [ ] 4K/HiDPI 顯示正常、字體比例正確
* [ ] Drag/Resize 邊界不誤觸 Click-Through
* [ ] Partial 刷新不卡頓、無跳動
* [ ] 翻譯/語境原子更新、無閃爍
* [ ] Start/Stop 後資源完整釋放（音源裝置可再次開啟）
* [ ] System Log 彩色分類正確
* [ ] 低光/高光模式對比足夠（可之後加入 Theme 切換）

---

## 13. 主要類別與介面（供生成程式碼）

```python
# gui/main_window.py
class MainWindow(QMainWindow):
    def __init__(self, bus, config): ...
    def bind_actions(self): ...
    def apply_config_to_overlay(self): ...
    def append_syslog(self, level: str, message: str, **kv): ...
    def set_state(self, state: Literal["IDLE","RUNNING","STOPPING"]): ...

# gui/panels.py
class ControlPanel(QWidget):  # 左側面板
    sigStart = pyqtSignal()
    sigStop = pyqtSignal()
    sigApply = pyqtSignal(dict)  # 局部設定變更

class DiagnosticsPanel(QWidget):  # 診斷資訊
    def update_metrics(self, *, latency_ms:int, queue_len:int, fps:int): ...

# overlay/overlay_window.py
class OverlayWindow(QWidget):
    def __init__(self, bus, config): ...
    def set_opacity(self, v: float): ...
    def set_background(self, enabled: bool): ...
    def set_click_through(self, enabled: bool): ...
    def update_partial(self, text: str): ...
    def update_translation(self, text: str): ...
    def update_context(self, text: str): ...
    # 拖曳/縮放事件處理：mousePressEvent / mouseMoveEvent / paintEvent

# glue/overlay_controller.py
class OverlayController(QObject):
    """訂閱 EventBus，節流、格式化後轉呼叫 OverlayWindow。"""
    def __init__(self, bus, overlay: OverlayWindow, config): ...
    def on_stt_partial(ev): ...
    def on_llm1_finished(ev): ...
    def on_llm2_context(ev): ...
```

---

## 14. 效能指標與節流

* Partial 更新節流：**≥50ms**；若累積字元未變則忽略
* Repaint 頻率：最大 60Hz（`QTimer` or `requestUpdate`）
* 字體排版快取：對相同樣式的 `QStaticText` 做快取，減少 layout 成本
* 診斷指標：`fps`、`avg_latency_ms(stt/llm/total)`、`queue_len`

---

## 15. 無障礙與在地化（基線）

* 按鈕與控制項提供 `accessibleName`
* 文字大小可調；支援深色模式
* 未來可加入多語系 UI（Qt 翻譯檔），目前以繁中為主

---

## 16. 與 `config.json` 的對應

```json
{
  "audio": {
    "output_device": "default",
    "use_loopback": true,
    "silence_threshold_db": -35.0
  },
  "stt_mode": "local",
  "stt_model": "faster-whisper-base.en",
  "overlay": {
    "opacity": 0.82,
    "font_size": 20,
    "background": true,
    "width_ratio": 0.6,
    "click_through": false
  }
}
```

---

## 17. 啟動流程（UI 觀點）

1. 啟動 `MainWindow` 與 `OverlayWindow`
2. `RuntimeCheck` 執行，結果顯示於 System Log
3. 使用者按 **Start** → 發 `app.start_pressed`
4. 收到 `app.pipeline_ready` 後，切狀態為 **RUNNING**
5. 收事件更新 Overlay；Stop 時回 **IDLE**