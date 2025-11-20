# 音頻捕獲系統 - WASAPI 實現

## 概述

新的音頻捕獲模組使用 **Windows WASAPI (Windows Audio Session API)** 直接捕獲系統音頻輸出，取代了之前基於 PortAudio/sounddevice 的實現。

## 主要特點

### 1. 直接 WASAPI 支持
- 使用 `pyaudiowpatch` 庫直接訪問 WASAPI
- 支持 **Loopback 模式**：直接捕獲音頻輸出設備的音頻流
- 避免了 PortAudio 的通道數不匹配問題

### 2. 自動音頻格式轉換
無論設備的原生格式如何，音頻捕獲器都會自動轉換為 STT 所需的格式：
- **通道數**：任意多聲道 → 單聲道（Mono）
- **採樣率**：任意採樣率 → 44100Hz
- **位深度**：int16/int32/float32 → int16

轉換流程：
```
原始音頻 (多聲道, 任意採樣率, 任意格式)
    ↓ 解析字節數據
    ↓ 轉換為單聲道（取平均值）
    ↓ 轉換為 float32 [-1.0, 1.0]
    ↓ 重採樣到 44100Hz
       ├─ 預設：線性插值（numpy，快速但質量一般）
       └─ 可選：高質量重採樣（resampy，較慢但質量更好）
    ↓ 轉換為 int16（僅在需要時）
目標音頻 (單聲道, 44100Hz, float32 或 int16)
```

**重採樣策略**：
- **預設模式**：使用 `numpy.interp` 進行線性插值（快速，適合實時處理）
- **高質量模式**：如果安裝了 `resampy`，優先使用 `resampy.resample`（質量更好，但稍慢）
- **自動降級**：如果 `resampy` 不可用，自動降級到線性插值

### 3. Chunk 處理
- 將連續音頻流切割為固定大小的 Chunks
- 支持 Chunk 之間的重疊（提高識別準確度）
- 自動靜音檢測（跳過靜音片段）
- 轉換為 float32 格式後發送給 STT

## 系統要求

### 操作系統
- **僅支持 Windows**（WASAPI 是 Windows 專有 API）
- Windows 7 或更高版本
- 推薦 Windows 10/11

### Python 依賴
```
pyaudiowpatch>=0.2.12.4  # WASAPI 支持的 PyAudio 分支
numpy>=1.26              # 音頻數據處理（必需）
resampy>=0.4.2           # 高質量音頻重採樣（可選，推薦）
librosa>=0.10.0          # 音頻分析與處理（可選，提供更多功能）
```

**依賴說明**：
- **必需**：`pyaudiowpatch` 和 `numpy` 是核心依賴，用於音頻捕獲和基本處理
- **可選但推薦**：`resampy` 提供高質量的重採樣算法（優於線性插值）
- **可選**：`librosa` 提供更多音頻處理功能，但體積較大

## 安裝

### 1. 安裝依賴
```bash
pip install -r requirements.txt
```

或手動安裝：
```bash
# 基本安裝（必需）
pip install pyaudiowpatch numpy

# 推薦：添加高質量重採樣支持
pip install resampy

# 可選：添加更多音頻處理功能
pip install librosa
```

### 2. 列出可用設備
運行設備列表工具：
```bash
python tools/device_list.py
```

這會顯示所有可用的音頻輸出設備。

### 3. 配置設備
在 `config.json` 中設置：
```json
{
  "audio": {
    "output_device": "default",  // 或具體設備名稱
    "use_loopback": true,
    "silence_threshold_db": -35.0
  },
  "chunk": {
    "size_ms": 640,      // Chunk 大小（毫秒）
    "overlap_ms": 160    // 重疊大小（毫秒）
  }
}
```

## 配置參數

### audio.output_device
指定要捕獲的音頻輸出設備。

選項：
- `"default"` - 使用系統預設輸出設備
- 具體設備名稱 - 例如 `"SteelSeries Sonar - Aux"`

### audio.silence_threshold_db
靜音檢測閾值（單位：dB）

- 預設值：`-35.0`
- 較低的值（如 `-40.0`）：檢測更細微的聲音
- 較高的值（如 `-30.0`）：只捕獲較大的聲音

### chunk.size_ms
每個音頻 Chunk 的大小（毫秒）

- 預設值：`640` (0.64秒)
- 範圍：建議 200-2000ms
- 較小的值：更低的延遲，但可能影響識別準確度
- 較大的值：更高的準確度，但延遲增加

### chunk.overlap_ms
相鄰 Chunks 之間的重疊時間（毫秒）

- 預設值：`160` (0.16秒)
- 範圍：建議 50-500ms
- 重疊可以減少因分割導致的單詞被截斷

## 使用示例

### 基本使用
```python
from app.audio.capture import AudioCapture
from app.core.event import _SINGLETON_BUS
from app.logging.system_logger import SystemLogger

# 配置
config = {
    "audio": {
        "output_device": "default",
        "use_loopback": True
    },
    "chunk": {
        "size_ms": 640,
        "overlap_ms": 160
    }
}

# 初始化
logger = SystemLogger(bus=_SINGLETON_BUS)
audio_capture = AudioCapture(
    bus=_SINGLETON_BUS,
    config=config,
    logger=logger
)

# 訂閱音頻 Chunk 事件
def on_audio_chunk(event):
    audio_data = event.blob  # numpy array (float32)
    chunk_id = event.payload["chunk_id"]
    print(f"收到音頻 Chunk #{chunk_id}, 長度: {len(audio_data)}")

_SINGLETON_BUS.subscribe(EventName.AUDIO_CHUNK_READY, on_audio_chunk)

# 啟動捕獲
audio_capture.start()

# ... 運行應用程式 ...

# 停止捕獲
audio_capture.stop()
```

### 列出可用設備
```python
audio_capture = AudioCapture(bus=_SINGLETON_BUS, config={})
devices = audio_capture.get_available_output_devices()
for device in devices:
    print(device)
```

### 動態更改設備
```python
# 必須在停止狀態下更改
audio_capture.stop()
audio_capture.set_device("SteelSeries Sonar - Aux")
audio_capture.start()
```

## 工作原理

### 1. 設備選擇
- 查找 WASAPI 主機 API
- 根據配置選擇輸出設備
- 如果指定 `"default"`，使用系統預設輸出設備
- 支持完全匹配和部分匹配（不區分大小寫）

### 2. 音頻捕獲
- 在獨立線程中運行捕獲循環
- 使用阻塞模式從 WASAPI 讀取音頻數據
- 每次讀取 4096 個樣本（約 93ms @ 44100Hz）

### 3. 格式轉換
- **AudioFormatConverter** 負責所有格式轉換
- 自動檢測設備的原生格式（通道數、採樣率、位深度）
- 轉換步驟：
  1. 字節 → numpy array
  2. 多聲道 → 單聲道（取平均值）
  3. 任意格式 → float32 [-1.0, 1.0]
  4. 重採樣到 44100Hz（自動選擇最佳方法）
     - 優先使用 `resampy`（如果已安裝）
     - 降級到 `numpy.interp` 線性插值（如果 `resampy` 不可用）
  5. 保持 float32 格式發送給 STT（STT 通常接受 float32）

### 4. Chunk 處理
- **ChunkProcessor** 負責切割和發送 Chunks
- 使用 deque 作為循環緩衝區
- 當緩衝區達到 Chunk 大小時，提取並發送
- 保留重疊部分供下一個 Chunk 使用
- 靜音檢測：計算 RMS 並與閾值比較

### 5. 事件發送
發送的音頻 Chunks 格式：
- **Event**: `AUDIO_CHUNK_READY`
- **Payload**:
  - `chunk_id`: Chunk 編號（遞增）
  - `overlap_ms`: 重疊時間
  - `duration_ms`: Chunk 時長
- **Blob**: numpy array (float32, 範圍 [-1.0, 1.0])

## 故障排除

### 問題 1: "pyaudiowpatch 未安裝"
**解決方案**:
```bash
pip install pyaudiowpatch
```

### 問題 2: "找不到輸出音訊設備"
**原因**: 設備名稱配置不正確

**解決方案**:
1. 運行 `python tools/device_list.py` 列出所有設備
2. 複製正確的設備名稱到 `config.json`
3. 或使用 `"default"` 作為設備名稱

### 問題 3: 沒有捕獲到音頻
**可能原因**:
1. 沒有音頻正在播放
2. 音量太小或靜音
3. 選擇了錯誤的設備

**解決方案**:
1. 確保有音頻正在播放（音樂、視頻等）
2. 檢查系統音量
3. 運行測試腳本: `python tools/test_audio_capture.py`
4. 調整 `silence_threshold_db` 到更低的值（如 `-40.0`）

### 問題 4: 音頻延遲過高
**解決方案**:
- 減小 `chunk.size_ms`（如 320ms）
- 減小 `chunk.overlap_ms`（如 80ms）
- 注意：過小的值可能影響識別準確度

### 問題 5: 音頻質量差
**可能原因**: 重採樣質量問題

**解決方案**:
1. **安裝高質量重採樣庫**：
   ```bash
   pip install resampy
   ```
   系統會自動使用 `resampy` 進行更高質量的重採樣

2. **檢查源設備的採樣率**：
   - 如果源採樣率過低（如 8000Hz），重採樣到 44100Hz 可能導致質量下降
   - 建議使用至少 16000Hz 以上的源採樣率

3. **使用 librosa（進階）**：
   ```bash
   pip install librosa
   ```
   可以通過配置使用 `librosa.resample`，但性能開銷較大

## 測試

### 運行測試腳本
```bash
python tools/test_audio_capture.py
```

這會：
1. 初始化音頻捕獲器
2. 列出可用設備
3. 捕獲 10 秒音頻
4. 顯示捕獲的 Chunk 數量

### 運行設備列表工具
```bash
python tools/device_list.py
```

顯示：
- 所有輸出設備
- 設備參數（通道數、採樣率）
- WASAPI 主機 API 信息
- Loopback 設備標記

## 與舊版本的差異

### 舊版本（sounddevice）
- 使用 PortAudio 作為後端
- 通道數不匹配問題
- 需要 resampy 進行重採樣
- 跨平台支持

### 新版本（WASAPI）
- 直接使用 Windows WASAPI
- 內建格式轉換器
- 智能重採樣：自動選擇最佳方法（resampy > numpy 線性插值）
- 支持可選的高質量重採樣庫（resampy/librosa）
- 僅支持 Windows

## 性能考慮

### 資源使用
- **CPU**: 輕量級（主要是音頻格式轉換）
- **記憶體**: 約 10-20MB（緩衝區和處理）
- **線程**: 1 個獨立捕獲線程

### 延遲
總延遲 ≈ 設備緩衝 + Chunk 大小 + 處理時間
- 設備緩衝: ~93ms (4096 samples @ 44100Hz)
- Chunk 大小: 可配置 (預設 640ms)
- 處理時間: <5ms
- **總計**: ~740ms (可通過減小 Chunk 大小降低)

## 實現指南（給 Agent）

### AudioFormatConverter 實現要點

**重採樣方法選擇邏輯**：
```python
def _resample(self, audio: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    """智能重採樣：優先使用高質量方法，自動降級"""
    if source_rate == target_rate:
        return audio
    
    # 優先使用 resampy（如果可用）
    try:
        import resampy
        return resampy.resample(audio, source_rate, target_rate)
    except ImportError:
        pass
    
    # 降級到 numpy 線性插值
    ratio = target_rate / source_rate
    indices = np.arange(len(audio) * ratio) / ratio
    return np.interp(indices, np.arange(len(audio)), audio)
```

**關鍵實現要求**：
1. **自動檢測依賴**：使用 `try/except ImportError` 檢測 `resampy` 是否可用
2. **無縫降級**：如果高質量庫不可用，自動使用 numpy 線性插值
3. **性能考慮**：`resampy` 質量更好但稍慢，適合對質量要求高的場景
4. **配置選項**：可以在 `config.json` 中添加 `audio.use_high_quality_resampling` 選項

### 配置選項建議

在 `config.json` 中可以添加：
```json
{
  "audio": {
    "output_device": "default",
    "use_loopback": true,
    "silence_threshold_db": -35.0,
    "resampling": {
      "method": "auto",  // "auto" | "resampy" | "numpy" | "librosa"
      "quality": "high"   // "high" | "fast" (僅 resampy 有效)
    }
  }
}
```

## 未來改進

1. ✅ **高質量重採樣**: 已整合 `resampy` 支持（自動檢測和降級）
2. **跨平台支持**: 為 Linux (PulseAudio/ALSA) 和 macOS (CoreAudio) 添加支持
3. **自適應緩衝**: 根據系統負載動態調整緩衝區大小
4. **音頻增強**: 添加降噪、自動增益控制等功能（可使用 librosa）
5. **回調模式**: 支持非阻塞的回調模式以減少延遲
6. **配置化重採樣**: 允許用戶在配置文件中選擇重採樣方法

## 相關文件

- `app/audio/capture.py` - 主實現
- `tools/device_list.py` - 設備列表工具
- `tools/test_audio_capture.py` - 測試腳本
- `requirements.txt` - 依賴列表
- `Documents/audio_input_capture.md` - 原始音頻捕獲文檔

