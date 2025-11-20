# Livestream Translator (直播即時字幕翻譯助手)

這是一個基於 Python 的即時語音轉寫與翻譯工具，專為直播場景設計。它能捕捉系統音訊（如 YouTube 直播聲音），使用本地 AI 模型（Faster Whisper）進行即時轉寫，並透過透明的 Overlay 視窗將字幕顯示在螢幕上。

## ✨ 主要功能 (Key Features)

### 1. 語音轉寫 (Speech-to-Text)
*   **本地運算**: 使用 `faster-whisper` 模型，無需上傳音訊，保護隱私且無 API 費用。
*   **即時串流 (Streaming Style)**: 採用 "Voice Assistant" 風格，文字會隨著語音即時逐字浮現，並在句子結束後自動穩定。
*   **多模型支援**:
    *   **Turbo v3**: 高準確度 (預設)。
    *   **Small**: 平衡速度與準確度。
    *   **Tiny / Tiny.en**: 極速模式，適合資源受限的電腦。
*   **多語言支援**: 支援自動偵測語言，或手動鎖定目標語言 (EN, JA, ZH, KO, ES, FR, DE)。

### 2. 智慧 Overlay 介面
*   **透明浮窗**: 無邊框設計，背景半透明，可常駐於直播視窗上方。
*   **動態視覺效果**:
    *   **Shimmer Effect**: 正在轉寫的內容會有類似 "Slide to unlock" 的微光流動特效。
    *   **顏色區分**: 進行中 (Cyan) vs 已確認 (Gold)。
*   **完全可自定義**:
    *   **可調整大小**: 拖曳視窗邊緣即可調整寬高。
    *   **字體大小**: 從 Small (18) 到 Extra Large (48)。
    *   **歷史紀錄**: 可設定保留 0~5 行歷史字幕，舊字幕會自動滾動變灰。

### 3. 高效能優化
*   **VAD (語音活動偵測)**: 自動偵測靜音斷句 (預設 300-400ms 靜音判定)。
*   **動態調節**: 自動偵測語言模式下會自動調節更新頻率，避免卡頓。
*   **GPU 加速**: 支援 CUDA (NVIDIA 顯示卡) 加速運算。

---

## 🛠️ 安裝與執行 (Installation)

### 1. 環境需求
*   Windows 10/11
*   Python 3.10+
*   NVIDIA 顯示卡 (建議，需安裝 CUDA Toolkit 以獲得最佳效能)

### 2. 安裝依賴
```powershell
# 建立虛擬環境 (可選)
python -m venv .venv
.venv\Scripts\activate

# 安裝套件
pip install -r requirements.txt
```

### 3. 執行程式
```powershell
python main_gui.py
```

---

## 🎮 使用指南 (User Guide)

啟動程式後，會出現 **控制面板 (Control Panel)** 與 **字幕視窗 (Overlay)**。

### 控制面板功能
1.  **Model**: 選擇 AI 模型。
    *   *注意：轉寫進行中無法切換模型，請先按 Stop。*
2.  **Target Language**:
    *   **Auto Detect**: 自動辨識 (反應稍慢)。
    *   **指定語言 (如 Japanese)**: 反應最快，適合已知語言的直播。
3.  **Start / Stop**: 開始或是停止監聽系統音訊。
4.  **Show/Hide Overlay**: 隱藏或顯示字幕視窗。

### Overlay 設定
1.  **Font Size**: 調整字幕文字大小。
2.  **History Lines**: 設定要保留幾行舊字幕 (0 為不保留)。

### 操作技巧
*   **移動視窗**: 按住 Overlay 視窗中央區域即可拖曳。
*   **調整大小**: 滑鼠移至 Overlay 邊緣或角落，游標變為箭頭時即可拖拉調整大小。

---

## ⚙️ 技術架構 (Technical Details)

*   **Audio Capture**: 使用 `PyAudioWPatch` 捕捉 Windows WASAPI Loopback (系統聲音)。
*   **Core Logic**: `STTManager` 負責維護 Audio Buffer，實現 Accumulating Buffer 機制，解決傳統區塊轉寫的不連貫問題。
*   **GUI**: 基於 `PySide6` (Qt for Python)。
*   **Event System**: 自製 `EventBus` 實現各模組解耦 (Audio -> STT -> GUI)。

## ⚠️ 注意事項
*   首次切換到新模型時，系統會自動下載模型檔案，可能會卡住幾分鐘，請耐心等待。
*   若遇到 `Audio queue full` 警告，通常是因為 GPU 運算來不及處理音訊，建議切換至較小的模型 (如 `small` 或 `tiny`)。

---
