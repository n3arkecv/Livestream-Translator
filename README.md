# Livestream Translator (直播即時字幕翻譯助手)

這是一個基於 Python 的即時語音轉寫與翻譯工具，專為直播場景設計。它能捕捉系統音訊（如 YouTube 直播聲音），使用本地 AI 模型（Faster Whisper）進行即時轉寫，並透過 LLM (如 GPT-4o) 進行高品質翻譯與情境理解，最後將字幕顯示在透明的 Overlay 視窗上。

## ✨ 主要功能 (Key Features)

### 1. 語音轉寫 (Speech-to-Text)
*   **本地運算**: 使用 `faster-whisper` 模型，無需上傳音訊，保護隱私且無 API 費用。
*   **即時串流 (Streaming Style)**: 採用 "Voice Assistant" 風格，文字會隨著語音即時逐字浮現，並在句子結束後自動穩定。
*   **多模型支援**:
    *   **Turbo v3**: 高準確度 (預設)。
    *   **Small**: 平衡速度與準確度。
    *   **Tiny / Tiny.en**: 極速模式，適合資源受限的電腦。
*   **多語言支援**: 支援自動偵測語言，或手動鎖定目標語言 (EN, JA, ZH, KO, ES, FR, DE)。

### 2. AI 翻譯與情境理解 (Translation & Context)
*   **高品質翻譯**: 整合 OpenAI / Google Gemini API，提供比傳統機器翻譯更流暢的結果。
*   **情境感知 (Scenario Context)**: 系統會自動摘要對話歷史，讓翻譯模型了解 "前情提要"，避免因缺乏上下文而翻譯錯誤。
*   **雙語對照**: Overlay 同時顯示原文 (轉寫) 與譯文。

### 3. 智慧 Overlay 介面
*   **透明浮窗**: 無邊框設計，背景半透明，可常駐於直播視窗上方。
*   **資訊豐富**:
    *   **Listening**: 即時顯示正在說話的內容 (Shimmer 特效)。
    *   **Transcription**: 已確認的原文句子 (黃色)。
    *   **Translation**: AI 翻譯結果 (青色)。
    *   **History**: 歷史對話紀錄 (灰色)。
    *   **Context**: 當前對話情境摘要 (底部綠色小字)。
*   **完全可自定義**:
    *   **可調整大小**: 拖曳視窗邊緣即可調整寬高。
    *   **字體大小**: 從 Small (18) 到 Extra Large (48)。
    *   **歷史紀錄**: 可設定保留 0~5 行歷史字幕。

### 4. 高效能優化
*   **VAD (語音活動偵測)**: 自動偵測靜音斷句。
*   **GPU 加速**: 支援 CUDA (NVIDIA 顯示卡) 加速運算。

---

## 🛠️ 安裝與設定 (Installation & Setup)

### 1. 環境需求
*   Windows 10/11
*   Python 3.10+
*   NVIDIA 顯示卡 (建議，需安裝 CUDA Toolkit 以獲得最佳效能)
*   **OpenAI API Key** 或 **Google API Key** (用於翻譯功能)

### 2. 安裝依賴
```powershell
# 建立虛擬環境 (可選)
python -m venv .venv
.venv\Scripts\activate

# 安裝套件
pip install -r requirements.txt
```

### 3. 設定 API Key
本程式提供圖形化設定介面：
1.  執行程式 `python main_gui.py`。
2.  點擊控制面板上的 **Settings** 按鈕。
3.  填入您的 **OpenAI API Key** 或 **Google API Key**。
4.  (可選) 修改使用的 LLM 模型 (預設 `gpt-4o-mini`)。
5.  點擊 **Save** 保存設定。

> 設定檔會儲存於 `User_config.txt`，您也可以手動編輯此檔案。

### 4. 執行程式
```powershell
python main_gui.py
```

---

## 🎮 使用指南 (User Guide)

啟動程式後，會出現 **控制面板 (Control Panel)** 與 **字幕視窗 (Overlay)**。

### 控制面板功能
1.  **Model**: 選擇語音轉寫 (STT) 模型。
    *   *注意：轉寫進行中無法切換模型，請先按 Stop。*
2.  **Target Language**:
    *   **Auto Detect**: 自動辨識 (反應稍慢)。
    *   **指定語言 (如 Japanese)**: 反應最快，適合已知語言的直播。
3.  **Start / Stop**: 開始或是停止監聽與翻譯。
4.  **Settings**: 開啟設定視窗 (API Key、模型設定)。
5.  **Overlay Controls**:
    *   **Show/Hide Overlay**: 開關字幕視窗。
    *   **Font Size**: 調整字幕大小。
    *   **History Lines**: 設定保留幾行歷史字幕。

### Overlay 狀態說明
*   **Standby...**: 等待程式啟動或等待語音輸入。
*   **Listening... (流動特效)**: 正在接收語音並進行初步轉寫。
*   **黃色文字**: 轉寫完成的句子。
*   **青色文字**: AI 翻譯完成的句子。
*   **底部綠色小字**: AI 分析出的當前對話情境 (Context)。

### 操作技巧
*   **移動視窗**: 按住 Overlay 視窗中央區域即可拖曳。
*   **調整大小**: 滑鼠移至 Overlay 邊緣或角落，游標變為箭頭時即可拖拉調整大小。

---

## ⚙️ 技術架構 (Technical Details)

*   **Audio Capture**: `PyAudioWPatch` (WASAPI Loopback)。
*   **STT**: `Faster-Whisper` (Local Inference)。
*   **Translation**: `OpenAI API` / `Google Gemini API`。
*   **Context Management**: 實作了 Sliding Window 與 Summary 機制，將對話歷史壓縮為 Context 傳送給 LLM，提升翻譯準確度。
*   **GUI**: `PySide6` (Qt for Python)。
*   **Architecture**: Event-Driven Architecture (EventBus) 解耦各個模組。

## ⚠️ 注意事項
*   首次使用新模型會自動下載，請耐心等待。
*   翻譯功能需要消耗 API Token (OpenAI)，請留意您的額度。
*   若遇到 `Audio queue full` 警告，建議切換至較小的 STT 模型 (如 `small`)。
