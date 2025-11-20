# 🎙️ Transcription System Design — Real-Time YouTube Live Translation App
---

## 🧭 1. 系統定位

Transcription System 為整體流程的第一階段，
負責從系統音源擷取直播音訊 → 切割成可即時辨識的片段 (Chunk) → 語音辨識 → 生成轉錄文字 → 提供翻譯模組使用。

架構支援兩種 STT 模式：

| 模式            | 模型                                   | 運行位置        | 用途      |
| ------------- | ------------------------------------ | ----------- | ------- |
| **Local STT** | FasterWhisper                        | GPU 加速，本地推論 | 低延遲、高隱私 |
| **API STT**   | GPT-4o Transcribe / Gemini 2.5 Flash | 雲端 API      | 高精度、跨平台 |

---

## 🎛️ 2. 系統組成模組

| 模組名稱                  | 職責        | 說明                                              |
| --------------------- | --------- | ----------------------------------------------- |
| **AudioCapture**      | 音源擷取      | 使用 **WASAPI (pyaudiowpatch)** Loopback 模式直接捕獲系統音頻輸出，產生 Chunk |
| **AudioFormatConverter** | 格式轉換    | 自動轉換多聲道/任意採樣率/任意格式 → 單聲道/44100Hz/float32        |
| **ChunkProcessor**    | 音訊切片管理    | 處理重疊切割、緩衝、排程                                    |
| **STTManager**        | 模式選擇與任務管理 | 根據 `config.json` 選擇 local 或 API                 |
| **LocalSTTEngine**    | 本地推論      | FasterWhisper (FP16/INT8)                       |
| **APISTTEngine**      | 雲端推論      | GPT-4o Transcribe / Gemini 2.5 Flash            |
| **SentenceAssembler** | 句子組裝      | 合併 partial、判斷句界、輸出 final sentence               |
| **CorrectionModule**  | 校正覆寫      | 修正上一句的誤辨字串                                      |
| **LatencyMonitor**    | 延遲追蹤      | STT pipeline latency 與 buffer 滿載狀態              |
| **SystemLog**         | 後台監控      | 事件顏色分級（INFO / WARNING / ERROR）                  |
| **EventBus**          | 事件分派      | 各模組間通訊（stt.partial / stt.final_sentence 等）      |

---

## 🔊 3. 音訊擷取與切片流程

### 3.1 流程概述

```text
WASAPI Loopback → AudioCapture → AudioFormatConverter → ChunkProcessor → STTManager → LocalSTT / APISTT → SentenceAssembler
```

### 3.2 WASAPI 音訊捕獲

**技術實作：**
- 使用 **`pyaudiowpatch`** 庫（PyAudio 的 WASAPI 分支）
- **Loopback 模式**：直接捕獲音頻輸出設備的音頻流
- 自動格式轉換：任意格式 → 單聲道/44100Hz/float32

### 3.3 Chunk 設計

| 項目       | 值         | 說明                 |
| -------- | --------- | ------------------ |
| 原始取樣率    | 任意（設備原生） | WASAPI 自動檢測          |
| 目標取樣率    | 44100 Hz  | 轉換後統一格式            |
| Chunk 時長 | 640 ms    | 每片固定長度             |
| 重疊區間     | 160 ms    | 25% overlap，減少切斷現象 |
| 緩衝數量     | 3–5       | 確保 pipeline 穩定     |
| 輸出格式     | float32   | 範圍 [-1.0, 1.0]，供 STT 使用 |

### 3.3 音訊流事件

| 事件                    | 說明       | 傳遞對象       |
| --------------------- | -------- | ---------- |
| `audio.stream_opened` | 成功開啟輸入裝置 | SystemLog  |
| `audio.chunk_ready`   | 產生新片段    | STTManager |
| `audio.stream_closed` | 停止錄音     | SystemLog  |

---

## 🧠 4. STT Manager 流程

### 4.1 模式選擇

* `config.json.stt_mode = "local"` → 使用 `LocalSTTEngine`
* `config.json.stt_mode = "api"` → 使用 `APISTTEngine`

### 4.2 事件驅動工作流程

```text
[audio.chunk_ready]
   ↓
[STTManager.dispatch()]
   ↓
[LocalSTT | APISTT]
   ↓
 partial_text → (stt.partial)
 final_sentence → (stt.final_sentence)
```

### 4.3 平行處理

* 每個 Chunk 使用非同步任務池。
* 若任務超過 4 個尚未完成 → 觸發 `rate_limit.backpressure`。

---

## 🗣️ 5. Sentence 組裝與邊界判斷

### SentenceAssembler 邏輯

1. 接收 STT partial 文字，累積於緩衝。
2. **判斷是否有句子進行中**：
   - **如果有句子進行中（Yes）**：
     - **Transcript Words so far**：累積目前辨識到的字詞
     - **Display Transcription so far**：在 Overlay 顯示即時轉錄文字
     - **Review & Correction previous sentence**：審查並修正前一句
     - 循環回到「Display Transcription so far」，持續更新顯示
   - **如果沒有句子進行中（No）**：
     - **Display Last Fully Transcribed sentence**：顯示最後一個完整轉錄的句子
3. 若偵測下列任一條件，產出 `final_sentence` 事件：

   * 停頓時間 > 0.8s
   * 出現句號、問號、感嘆號
   * STT 模型輸出結尾 flag（end_of_segment）

### 事件順序

| 事件名稱                    | 說明            |
| ----------------------- | ------------- |
| `stt.partial`           | 每次 partial 更新 |
| `stt.boundary_detected` | 辨識句界          |
| `stt.final_sentence`    | 句子完成並傳給翻譯系統（Fully Transcribed Sentence）   |

---

## ✍️ 6. 校正覆寫機制（CorrectionModule）

對應圖中「Review & Correction previous sentence」

* 若新輸入句與前一輸出句存在重疊字詞（由 overlap chunk 判定），
  系統會重新檢查最後 1–2 句。
* 差異量計算：

  ```python
  from difflib import SequenceMatcher
  ratio = SequenceMatcher(None, prev_sentence, new_text).ratio()
  ```
* 若 `ratio < 0.85` → 觸發 `stt.revise_previous`，覆蓋上句文字並重發至 Overlay。

---

## ⚙️ 7. 模組事件流程總覽

| 步驟 | 來源                            | 事件                          | 處理模組               | 結果     |
| -- | ----------------------------- | --------------------------- | ------------------ | ------ |
| 1  | AudioCapture                  | `audio.chunk_ready`         | STTManager         | 傳送音訊片段 |
| 2  | STTManager                    | `stt.decode_started`        | STT Engine         | 啟動辨識   |
| 3  | LocalSTTEngine / APISTTEngine | `stt.partial`               | Overlay            | 顯示即時文字 |
| 4  | SentenceAssembler             | `stt.boundary_detected`     | SystemLog          | 確認句界   |
| 5  | SentenceAssembler             | `stt.final_sentence`        | TranslationManager | 傳送完整句  |
| 6  | CorrectionModule              | `stt.revise_previous`       | Overlay            | 覆寫上一句  |
| 7  | STTManager                    | `syslog.info/warning/error` | GUI Log            | 顯示狀態   |

---

## 🧮 8. 延遲預算（STT Pipeline）

| 區段                 | 目標延遲        | 說明                |
| ------------------ | ----------- | ----------------- |
| WASAPI 捕獲 → 格式轉換    | ≤ 50 ms     | Loopback 讀取 + 格式轉換    |
| 格式轉換 → Chunk 輸出    | ≤ 50 ms     | ChunkProcessor 切片        |
| Chunk 傳遞 → 模型輸入    | ≤ 50 ms     | 資料轉換與排程（如需要可重採樣至 16kHz）           |
| 模型推論（Local）        | ≤ 300 ms    | FasterWhisper（支援 16kHz/32kHz/44100Hz）     |
| 模型推論（API）          | ≤ 500 ms    | GPT-4o Transcribe（自動處理採樣率） |
| Sentence Assembler | ≤ 100 ms    | 判斷句界、合併           |
| **總計**             | **≤ 1.0 s** | STT 全流程目標延遲       |

**注意：** WASAPI 輸出為 44100Hz，但 FasterWhisper 通常使用 16kHz。若使用 Local STT，需要在 STTManager 中進行重採樣（44100Hz → 16kHz）。API STT 通常自動處理採樣率轉換。

---

## 🧾 9. 模型配置與 API

### Local STT 模式

* 模型：`faster-whisper-base.en` / `small.en` / `medium.en`
* 執行環境：CUDA / Torch FP16
* **採樣率處理**：
  - WASAPI 輸出：44100Hz（float32）
  - FasterWhisper 支援：16kHz / 32kHz / 44100Hz（可自動處理）
  - **建議**：直接使用 44100Hz（FasterWhisper 原生支援），無需重採樣
* 推論：

  ```python
  from faster_whisper import WhisperModel
  
  # 直接使用 44100Hz（推薦，無需重採樣）
  model = WhisperModel("small.en", device="cuda", compute_type="float16")
  segments, info = model.transcribe(audio_chunk, sample_rate=44100)
  
  # 若需重採樣至 16kHz（可選）
  # audio_16k = resample_audio(audio_chunk, 44100, 16000)
  # segments, info = model.transcribe(audio_16k, sample_rate=16000)
  ```

### API STT 模式

* GPT-4o Transcribe:

  ```python
  client.audio.transcriptions.create(
      model="gpt-4o-mini-transcribe",
      file=chunk.wav()
  )
  ```
* Gemini Flash:

  ```python
  model = genai.GenerativeModel("gemini-2.5-flash")
  response = model.transcribe(audio=chunk.wav())
  ```

---

## 🧰 10. 類別介面（供實作）

```python
# audio/capture.py (WASAPI 實作)
import pyaudiowpatch as pyaudio
import numpy as np

class AudioCapture:
    def __init__(self, bus, config, logger):
        self.bus = bus
        self.config = config
        self.logger = logger
        self.output_device = config.get("audio", {}).get("output_device", "default")
        self.use_loopback = config.get("audio", {}).get("use_loopback", True)
        self.chunk_ms = config["chunk"]["size_ms"]
        self.overlap_ms = config["chunk"]["overlap_ms"]
        self.format_converter = AudioFormatConverter()
        self.chunk_processor = ChunkProcessor(bus, 44100, self.chunk_ms, self.overlap_ms)
        
    def start(self):
        """啟動 WASAPI Loopback 捕獲"""
        try:
            p = pyaudio.PyAudio()
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
            device_index = self._find_output_device(p, wasapi_info)
            
            self.stream = p.open(
                format=pyaudio.paInt16,
                channels=2,  # 設備原生通道數
                rate=44100,  # 目標採樣率
                frames_per_buffer=4096,
                input=True,
                input_device_index=device_index,
                as_loopback=self.use_loopback
            )
            self.bus.emit(EventName.AUDIO_STREAM_OPENED, {
                "device_name": self.output_device,
                "sample_rate": 44100
            })
            # 啟動捕獲線程
            self._start_capture_thread()
        except Exception as e:
            self.logger.error("Failed to open WASAPI device", exc=e)
    
    def _start_capture_thread(self):
        """在獨立線程中運行捕獲循環"""
        import threading
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
    
    def _capture_loop(self):
        """捕獲循環：讀取音頻 → 格式轉換 → Chunk 處理"""
        while not self.stop_event.is_set():
            try:
                data = self.stream.read(4096, exception_on_overflow=False)
                # 轉換格式
                audio_array = self.format_converter.convert(data)
                # 送入 Chunk 處理器
                self.chunk_processor.push(audio_array)
            except Exception as e:
                self.logger.error("Capture loop error", exc=e)
    
    def stop(self):
        """停止捕獲"""
        self.stop_event.set()
        if hasattr(self, "stream"):
            self.stream.stop_stream()
            self.stream.close()
        self.bus.emit(EventName.AUDIO_STREAM_CLOSED)

class AudioFormatConverter:
    """自動音頻格式轉換器"""
    def convert(self, raw_bytes: bytes) -> np.ndarray:
        """轉換任意格式 → float32 [-1.0, 1.0]"""
        # 1. 字節 → numpy array
        # 2. 多聲道 → 單聲道（取平均值）
        # 3. 重採樣到 44100Hz（線性插值）
        # 4. 轉換為 float32
        # 返回: numpy array (float32, 範圍 [-1.0, 1.0])
        pass

# transcription/chunk_processor.py
class ChunkProcessor:
    def __init__(self, bus, chunk_ms=640, overlap_ms=160): ...
    def add_audio(self, stream_data: np.ndarray): ...
    def get_next_chunk(self): ...

# transcription/stt_manager.py
class STTManager:
    def __init__(self, bus, config): ...
    async def handle_chunk(self, ev: Event[AudioChunkReadyPayload]): ...
    def _dispatch_to_engine(self, audio_chunk): ...

# transcription/local_stt_engine.py
class LocalSTTEngine:
    def __init__(self, model_name="small.en", device="cuda"): ...
    async def transcribe(self, audio_chunk: np.ndarray) -> str: ...

# transcription/api_stt_engine.py
class APISTTEngine:
    async def transcribe(self, audio_chunk: bytes) -> str: ...

# transcription/sentence_assembler.py
class SentenceAssembler:
    def __init__(self): ...
    def add_partial(self, text): ...
    def detect_boundary(self, text): ...
    def get_final_sentence(self) -> str: ...

# transcription/correction_module.py
class CorrectionModule:
    def compare_and_fix(self, prev: str, new: str) -> Optional[str]: ...

# transcription/latency_monitor.py
class LatencyMonitor:
    def start(self, chunk_id): ...
    def stop(self, chunk_id) -> int: ...
```

---

## 🔍 11. System Log 與 GUI 顯示

| 類型      | 顏色 | 範例                                  |
| ------- | -- | ----------------------------------- |
| INFO    | 🔵 | `[Audio] stream opened @48000Hz`    |
| WARNING | 🟡 | `[STT] High latency: 620ms`         |
| ERROR   | 🔴 | `[API] Transcribe failed: HTTP 503` |

GUI Log 僅顯示 System Log，不包含翻譯內容。

---

## 📈 12. 效能監測指標

| 指標                   | 來源                | 用途              |
| -------------------- | ----------------- | --------------- |
| `avg_stt_latency_ms` | LatencyMonitor    | 分析即時延遲          |
| `queue_len`          | STTManager        | 背壓控制            |
| `partial_rate`       | OverlayController | 檢測 partial 更新頻率 |
| `revision_rate`      | CorrectionModule  | 校正率統計           |

---

## ✅ 13. 測試項目

* [ ] 本地/雲端模式切換正常
* [ ] 音訊 Chunk 重疊準確
* [ ] partial → final 事件順序正確
* [ ] 修正覆寫機制運作正常
* [ ] 延遲控制在 1s 以內
* [ ] 錯誤事件正確觸發 SystemLog

---

## 🧩 14. 事件關聯圖（對應圖例）

```text
AudioCapture ──► ChunkProcessor ──► STTManager ─┬──► LocalSTT
                                                 │
                                                 └──► APISTT
         │
         ▼
 SentenceAssembler ─► CorrectionModule ─► Overlay
         │
         └──► TranslationManager
```

---

## 🧠 15. 設計理念

* **低延遲管線**：以非同步任務池實作，最長延遲 < 1 秒。
* **語音邊界穩定性**：透過重疊區與校正機制確保句子完整。
* **模組獨立**：Audio / STT / Assembler / Correction 各自可替換。
* **可觀測性**：所有延遲與事件均上報 System Log。
* **自我修正**：上一句誤辨可即時覆蓋，不干擾翻譯流程。
