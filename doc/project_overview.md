# 🎯 Project Overview — Real-Time YouTube Live Translation App

## 🧭 專案願景
本專案旨在開發一款 **可於單台 RTX 4070 8GB + i7-14700HX 電腦上流暢執行的 YouTube 直播即時翻譯應用程式**。  
應用程式將即時擷取直播音訊、轉錄成文字、進行情境式翻譯，並以 Overlay 形式顯示。  
整體延遲控制在 **0.5–1.5 秒** 之間，達到「近乎同聲傳譯」的流暢體驗。

---

## 🧩 系統總覽
整個系統分為兩大核心流程：
1. **Transcription Workflow（語音轉錄流程）**
2. **Translation Workflow（翻譯流程）**

此外，系統包含兩套獨立的後台與資料紀錄系統：
- **System Log 系統**：負責監控與除錯，記錄應用內部運作狀態。
- **Dialogue Log 系統**：負責語料與翻譯資料儲存，供後續模組載入或分析。

---

## 🌀 TRANSCRIPTION WORKFLOW — 語音轉錄流程

### 🔊 1. 輸入句子
- 系統持續接收語音輸入，產生多個句子狀態：
  - **Sentence 1 (Done)**：已完成轉錄的句子
  - **Sentence 2 (Still speaking)**：正在進行中的句子

---

### 🔊 2. Audio Chunking（音訊分塊）
- 系統使用 **WASAPI (pyaudiowpatch) Loopback 模式**直接捕獲系統音頻輸出（無需 Stereo Mix 或虛擬音源）。  
- 音訊被切割為 **部分重疊的音訊片段（Chunks）**：
  - `Audio Chunk 1`: 句子 1 的部分內容（Partial sentence 1）
  - `Audio Chunk 2`: 句子 1 結尾 + 句子 2 開頭（重疊區，Overlap）
  - `Audio Chunk 3`: 句子 2 的部分內容（Partial sentence 2）
- 自動格式轉換：任意設備格式 → 單聲道/44100Hz/float32

這樣設計能確保語音邊界更準確，減少斷句錯誤。

---

### ⚙️ 3. STT 模型選擇與轉錄
- 程式會依據 **`config.json`** 設定決定使用：
  - **本地模型（Local STT Model）**：FasterWhisper
  - 或 **雲端 API（API STT Model）**：GPT-4o Transcribe / Gemini 2.5 Flash
- STT 模組接收 Chunk 後進行轉錄處理

---

### 🧩 4. 轉錄處理與顯示邏輯
- **判斷是否有句子進行中**：
  - **如果有句子進行中（Yes）**：
    1. **Transcript Words so far**：累積目前辨識到的字詞
    2. **Display Transcription so far**：在 Overlay 顯示即時轉錄文字
    3. **Review & Correction previous sentence**：審查並修正前一句
    4. 循環回到「Display Transcription so far」，持續更新顯示
  - **如果沒有句子進行中（No）**：
    1. **Display Last Fully Transcribed sentence**：顯示最後一個完整轉錄的句子

---

### ✅ 5. 輸出完整轉錄句子
- 當句子完成轉錄時，輸出 **Fully Transcribed Sentence（完整轉錄的句子）**
- 該完整句子將：
  - 送入 Translation Workflow 進行翻譯
  - 存儲到 Dialogue Log 供後續使用（解釋、假名標註等）

---

## 🌐 TRANSLATION WORKFLOW — 翻譯流程

### 🧠 1. 接收輸入
- 當 Transcription Workflow 傳出 **Fully Transcribed Sentence（完整轉錄的句子）** 時，
  該文字與目前的 **Scenario Context（情境上下文）** 一同送入翻譯流程。

---

### 💬 2. LLM1 翻譯處理
- **輸入組合**：**Scenario Context** + **Fully Transcribed Sentence**
- 將組合後的內容送入 **LLM 1 (API)** 進行翻譯
- **LLM 1** 的任務是根據當前情境進行即時翻譯：
  - 翻譯目標：**英文 → 中文** 或 **日文 → 中文**
  - 模型：**gpt-4.1-mini-2025-04-14**
- **輸出**：**Translated Sentence（翻譯後的句子）**

---

### 🪶 3. 顯示翻譯結果
- **Display Translated Sentence**：在 Overlay 顯示翻譯後的句子

---

### 🧠 4. LLM2 情境更新處理
- **輸入組合**：**原始 Scenario Context** + **Translated Sentence**
- 將組合後的內容送入 **LLM 2 (API)** 進行情境更新
- **LLM 2** 的任務是：
  - 整合新翻譯句子至 Scenario Context
  - 更新語境摘要（例如主題延續、人稱、語氣等）
- **輸出**：**New Scenario Context（新情境上下文）**
- **新 Scenario Context** 會儲存在記憶中（約 200–500 tokens）供下次翻譯使用

---

### 📝 5. 記錄與日誌
- **Dialogue Log**：完整轉錄的句子存儲到日誌供後續使用（解釋、假名標註等）
- **System Log**：系統負責後台事件追蹤與監控

---

## 🧱 模組化設計原則

| 模組 | 職責 | 備註 |
|------|------|------|
| **GUI 模組** | 使用者操作介面：開始/停止、音源選擇、透明度調整、Log 顯示 | PyQt / PySide |
| **Overlay 模組** | 顯示字幕（Partial / Final / Context），支援透明度與拖曳 | 可重繪與自訂樣式 |
| **STT 模組** | 負責語音辨識（Local 或 API） | FasterWhisper / GPT-4o / Gemini |
| **LLM 翻譯模組** | 翻譯 + 情境上下文維護 | GPT-4.1-mini |
| **Audio Capture 模組** | 使用 WASAPI Loopback 模式直接捕獲系統音頻輸出並切割成 Chunk | pyaudiowpatch (Windows 專用) |
| **Runtime Check 模組** | 啟動時檢查 Runtime、模型與依賴 | 缺少時提供安裝指引 |
| **System Log 模組** | 後台監控系統運作與事件記錄，使用顏色標示不同事件類別（藍＝資訊、紅＝錯誤、黃＝警告），主要用於分析與除錯。 | 獨立於主流程運作 |
| **Dialogue Log 模組** | 儲存每句原文與翻譯、Scenario Context 與時間戳記，輸出為 `.csv`、`.json` 或 `.txt` 格式供後續模組載入。 | 可供分析、回放或語料學應用 |
| **Config 模組** | 控制使用者設定與運行參數 | JSON 檔 |

---

## ⚙️ 啟動與執行流程（對應圖例）

1. 使用者雙擊入口檔（`.pyw` 或 `.bat`）。  
2. 系統啟動：
   - GUI 模組 → Overlay 模組
3. 檢查環境與模型（Runtime Check 模組）
4. 使用者按下「開始」：
   - Audio Capture 啟動 → STT 開始辨識
   - 即時輸出 Partial Sentence 至 Overlay
5. 當句子完成：
   - Final Sentence 傳入 Translation Workflow
   - LLM 1 翻譯 → LLM 2 更新 Scenario Context
6. 翻譯結果與情境更新後：
   - Overlay 顯示新句與 Context
   - System Log 寫入系統事件
   - Dialogue Log 儲存語料資料
7. 使用者可隨時停止流程；STT 將輸出最後一句，然後結束。

---

## 🎨 Overlay 顯示邏輯

| 區塊 | 功能 |
|------|------|
| **Ongoing Sentence** | 逐字顯示正在發話的內容（Partial Transcript） |
| **Translated Sentence** | 一句完整後顯示翻譯結果 |
| **Scenario Context** | 顯示短篇情境上下文，幫助使用者理解語意流向 |

---

## 🧠 設計理念
- **模組分離**：所有邏輯獨立實作，互不干擾。  
- **低延遲**：從發話到顯示翻譯延遲 < 1.5 秒。  
- **情境連貫**：翻譯保留 200–500 tokens 的語境記憶。  
- **資料分層**：System Log 與 Dialogue Log 完全獨立，分別支援除錯與語料分析。  
- **擴充性高**：可替換模型或新增語言而不破壞主流程。  
- **資料持續性**：Dialogue Log 提供可讀且可再利用的紀錄檔。  
- **開發者友善**：所有設計以 markdown 文件描述，方便 Cursor Agent 擴散式開發。

---

## 🚀 專案指標

| 項目 | 目標 |
|------|------|
| **延遲** | 0.5–1.5 秒 |
| **輸入語言** | 英文 / 日文 |
| **輸出語言** | 繁體中文 |
| **STT 模型** | FasterWhisper / GPT-4o Transcribe / Gemini 2.5 Flash |
| **翻譯模型** | gpt-4.1-mini-2025-04-14 |
| **主要框架** | PyQt / PySide |
| **GPU 要求** | RTX 4070 8GB |
| **執行環境** | Windows（支援系統回錄） |

---

_版本：v0.5 — System Log 與 Dialogue Log 系統分離版（由 GPT-5 更新）_
