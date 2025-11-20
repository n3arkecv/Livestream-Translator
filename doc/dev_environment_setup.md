# 🧰 Dev Environment Setup — Real-Time YouTube Live Translation App

版本：v0.1
對應文件：`config_json_spec.md`, `runtime_check_design.md`, `audio_input_capture.md`, `transcription_system_design.md`, `translation_system_design.md`, `system_logging_design.md`

---

## 0) TL;DR（三步跑起來）

```powershell
# 1) 用 venv 建環境（Windows PowerShell）
py -3.10 -m venv .venv
. .\.venv\Scripts\Activate.ps1

# 2) 安裝依賴（CPU 也可先跑；GPU 版看 §3）
pip install -U pip wheel
pip install -r requirements.txt

# 3) 設定 API Keys（二選一）
# 方法 A：使用 API_KEY.txt（推薦）
#   複製 API_KEY.txt.example 為 API_KEY.txt，填入您的 keys
#   然後執行：python tools/load_api_keys.py
# 方法 B：直接設定環境變數
$env:OPENAI_API_KEY = "<your_key>"

# 4) 執行假資料煙囪測試
python tools/smoke_test.py
```

> 看到 Overlay 視窗、GUI System Log 滾動且無紅字，即基本就緒。

---

## 1) 作業系統與硬體需求

* **OS**：Windows 11（優先）或 Windows 10 22H2+
* **CPU**：Intel i7-14700HX（或同級）
* **GPU**：RTX 4070 8GB（建議；本地 STT 使用 CUDA）
* **RAM**：≥ 16 GB（建議 32 GB 以利同時開發/錄影）
* **磁碟**：剩餘 ≥ 10 GB（模型、快取與 logs）
* **音訊**：使用 **WASAPI Loopback** 模式（Windows 原生，無需額外設定）

> macOS / Linux 可開發非音訊截取部分，但「系統回錄 + Overlay 置頂 + 點擊穿透」與 WASAPI 體驗以 Windows 最佳。WSL **不支援**系統音源回錄。

---

## 2) 開發工具

* **Python**：3.10.x 或 3.11.x（專案以 3.10 驗證）
* **Git**：2.40+
* **Cursor（Composer 1）**：安裝 Cursor IDE，登入並啟用 Composer 1 Model
* **Visual C++ Build Tools**（若需編譯本地套件）
* **FFmpeg**：音訊/媒體工具（PATH 需可呼叫）

---

## 3) GPU/CUDA 堆疊（本地 STT 推論）

### 3.1 安裝順序（Windows）

1. **NVIDIA 顯示卡驅動**（Studio 或 Game Ready；2024+ 版）
2. **CUDA Toolkit（可選）**：若只用 PyTorch CUDA **不必**裝整套 Toolkit；
   我們優先使用 **PyTorch 官方 CUDA Runtime wheel**（內含 cuDNN）。
3. **PyTorch（CUDA）**

   * RTX 4070 → 建議 **CUDA 12.1 或 12.4** build
   * 指令（以 CUDA 12.1 為例）：

     ```powershell
     # 啟用 venv 後
     pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
     ```
4. **Faster-Whisper**（綁定本地推論）

   ```powershell
   pip install faster-whisper
   ```

> 若只做 API STT（GPT-4o Transcribe / Gemini），可跳過 CUDA/PyTorch 部分。

---

## 4) FFmpeg 與音訊系統

### 4.1 FFmpeg

* 下載 Windows 版（gpl/shared），解壓至 `C:\ffmpeg\bin`
* 將 `C:\ffmpeg\bin` 加入 **PATH**
* 驗證：

  ```powershell
  ffmpeg -version
  ```

### 4.2 WASAPI 音訊捕獲

* **無需額外設定**：WASAPI Loopback 模式直接捕獲系統音頻輸出
* **無需 Stereo Mix 或虛擬音源**：直接使用 Windows 原生音訊 API
* 驗證可用輸出裝置（Python）：

```powershell
python - <<'PY'
import pyaudiowpatch as pyaudio
p = pyaudio.PyAudio()
wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
print(f"WASAPI Default Output Device: {wasapi_info['defaultOutputDevice']}")
for i in range(p.get_device_count()):
    dev = p.get_device_info_by_index(i)
    if dev['hostApi'] == wasapi_info['index']:
        print(f"  [{i}] {dev['name']} - {dev['maxInputChannels']} channels")
p.terminate()
PY
```

---

## 5) 專案結構（重點資料夾）

```
project_root/
 ├─ app/
 │   ├─ core/               # events.py, bus 實作
 │   ├─ gui/                # MainWindow / Panels
 │   ├─ overlay/            # OverlayWindow
 │   ├─ audio/              # AudioCapture, ChunkProcessor
 │   ├─ transcription/      # STT manager & engines
 │   ├─ translation/        # LLM client, manager
 │   ├─ runtime/            # RuntimeCheck
 │   ├─ logging/            # System/Dialogue logger
 │   └─ metrics/            # MetricsCollector（可選）
 ├─ models/                 # 本地 STT 模型（可空）
 ├─ logs/
 │   ├─ system.log
 │   └─ dialogue/           # *.jsonl / *.csv
 ├─ tools/                  # smoke_test.py, device_list.py ...
 ├─ document/               # 本資料夾（*.md）
 ├─ config.json
 ├─ requirements.txt
 └─ run_app.pyw / run_app.bat
```

---

## 6) Python 環境與依賴

### 6.1 建立 venv（Windows）

```powershell
py -3.10 -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -V
pip install -U pip wheel setuptools
```

### 6.2 `requirements.txt`（建議版本範例）

```txt
# Core
pydantic>=2.7
numpy>=1.26
pyaudiowpatch>=0.2.12.4  # WASAPI 支持的 PyAudio 分支（Windows 專用）
tqdm>=4.66

# GUI
PySide6>=6.7  ; 或 PyQt6，請二選一並在程式碼保持介面一致
# PyQt6>=6.7

# STT (local)
faster-whisper>=1.0
# 若用 PyTorch CUDA 版，請先依 §3 安裝對應 wheel

# LLM / HTTP
openai>=1.50.0
httpx>=0.27

# Logging / Metrics
colorama>=0.4
pandas>=2.2

# JSON Schema 驗證（config）
jsonschema>=4.23

# Optional Dev
pytest>=8.3
rich>=13.7
```

> 若選 **PyQt6**，請把 `PySide6` 換成 `PyQt6`，程式碼需對應。

---

## 7) 環境變數與金鑰

### 7.1 使用 API_KEY.txt（推薦方法）

**步驟：**

1. **複製範本文件**：
   ```powershell
   Copy-Item API_KEY.txt.example API_KEY.txt
   ```

2. **編輯 API_KEY.txt**，填入您的 API keys：
   ```text
   OPENAI_API_KEY=sk-your-actual-openai-key-here
   GOOGLE_API_KEY=your-google-api-key-here
   ```

3. **載入環境變數**：
   ```powershell
   # 方法 A：使用工具腳本（推薦）
   python tools/load_api_keys.py
   
   # 方法 B：在 Python 程式中載入
   from tools.load_api_keys import load_api_keys
   load_api_keys()
   ```

**安全性：**
- `API_KEY.txt` 已加入 `.gitignore`，**不會被提交到 git**
- 請勿將 `API_KEY.txt` 分享或上傳到任何公開位置
- `API_KEY.txt.example` 是範本文件，可以安全提交到 git

### 7.2 直接設定環境變數（替代方法）

**PowerShell（僅當前視窗有效）：**
```powershell
$env:OPENAI_API_KEY = "<your_openai_key>"
$env:GOOGLE_API_KEY = "<your_google_key>"   # 若用 Gemini STT
```

**永久設定（User 環境變數）：**
- 「編輯系統環境變數」→「環境變數」→ 新增/修改 `OPENAI_API_KEY`

**config.json 對應**：參考 `/document/config_json_spec.md`

---

## 8) Cursor（Composer 1）開發流程

1. 在專案根目錄開啟 **Cursor**
2. 確保 `.cursor/rules` 中已加入本專案 `/document/*.md` 做為 **Source of Truth**
3. 在 Command 面板輸入：

   * 「Generate module skeleton from `/document/02_modules_specification.md`」
   * 「Implement event bus per `app/core/events.py`」
4. 使用 `Composer 1` 模型生成後，逐檔執行 `pytest` 或 `tools/smoke_test.py` 做煙囪測試
5. 對齊 `/document/performance_targets.md` 的 KPI 逐步優化

---

## 9) 首次執行與驗證

### 9.1 檢查裝置與環境

```powershell
python tools/device_list.py      # 列出可用音訊輸入
python tools/check_runtime.py    # 驗證 CUDA/FFmpeg/Model/API（對應 runtime_check）
```

### 9.2 啟動 App

* **GUI/Overlay 方式**

  ```powershell
  python run_app.pyw
  ```
* **批次檔**

  ```bat
  @echo off
  call .\.venv\Scripts\activate
  python run_app.pyw
  ```

看到：

* GUI 主視窗 + Overlay 出現
* System Log 顯示 `app.started` → `runtime.check_result ok=true` → `app.pipeline_ready`
* 按 **Start** 後，講話 → 0.5–1.5s 內出現翻譯

---

## 10) 常見問題（FAQ / Troubleshooting）

| 問題                          | 原因                    | 解法                                                                     |
| --------------------------- | --------------------- | ---------------------------------------------------------------------- |
| WASAPI 不可用                  | Windows 版本過舊或 API 缺失      | 確保 Windows 7+；檢查 `pyaudiowpatch` 安裝正確                                |
| `OSError: device not found` | 輸出裝置名稱不一致               | 用 `tools/device_list.py` 找正確名稱，更新 `config.json.audio.output_device`                        |
| Loopback 模式失敗              | `use_loopback` 設定錯誤        | 確保 `config.json.audio.use_loopback = true`                                |
| `CUDA not available`        | PyTorch 未裝 CUDA build | 依 §3 重新安裝 `cu121/cu124` 版 wheel                                        |
| `ffmpeg not found`          | PATH 未設定              | 將 `C:\ffmpeg\bin` 加入 PATH，重開終端機                                        |
| Overlay 無法置頂/穿透             | 權限或旗標不正確              | 以系統管理員啟動；確認 `Qt.FramelessWindowHint`/`Tool`/`WA_TranslucentBackground` |
| 翻譯超時                        | 網路或 API 限流            | 調高 `llm.timeout_ms`；檢查 Proxy；觀察 `syslog.warning`/`retry.scheduled`     |
| 本地 STT 太慢                   | 模型太大/無 GPU            | 改 `small.en`、`compute_type=int8`；或切到 API STT                           |

---

## 11) 重現性與鎖版本

* 固定 Python 版本（3.10.x）
* 鎖 `requirements-lock.txt`（可用 `pip-tools` 生成）

  ```powershell
  pip install pip-tools
  pip-compile -o requirements-lock.txt requirements.txt
  pip-sync requirements-lock.txt
  ```

---

## 12) 開發腳本（tools/）

* `device_list.py`：列出音訊輸入裝置
* `check_runtime.py`：模擬 `runtime_check` 全面檢查
* `smoke_test.py`：啟動 EventBus，送假事件到 Overlay/GUI，檢查路徑與 Log
* `gen_test_audio.py`：輸出正弦波或讀取 wav 餵入 ChunkProcessor

---

## 13) macOS / Linux 差異（參考）

* **macOS**：無原生「系統回錄」；需 `BlackHole`/`Loopback`。Overlay 視窗 API 與點擊穿透行為與 Windows 略異。
* **Linux**：可用 PulseAudio/ALSA；OBS-Virtual-Audio 或 `pavucontrol` 路由；Overlay 取決於 WM/Compositor。
* **WSL**：不支援 WASAPI/DirectSound；**不建議**做音源截取。

---

## 14) 安全與隱私

* 不將 API key 寫入版本庫；使用 **環境變數**
* `logs/dialogue/*` 可能包含敏感語料，注意權限與清理政策
* 觀察 `/document/system_logging_design.md` 中 **System Log** 與 **Dialogue Log** 分離原則

---

## 15) 驗收檢查表（準備就緒）

* [ ] `ffmpeg -version` 可用
* [ ] `sounddevice.query_devices()` 能看到選定裝置
* [ ] `python -c "import torch; print(torch.cuda.is_available())"` → True（若用本地 STT）
* [ ] `OPENAI_API_KEY` 設定正確
* [ ] `runtime.check_result ok=true`
* [ ] 假資料煙囪測試通過，Overlay 正常顯示

---

*附註：若要一鍵化，可在 `tools/bootstrap.ps1` 寫入上述步驟與檢查項。*