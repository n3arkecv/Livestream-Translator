/document
│
├─ 00_project_overview.md              ← 專案總覽與願景
├─ 01_architecture_overview.md         ← 整體架構圖與流程說明（對應你上傳的流程圖）
├─ 02_modules_specification.md         ← 各模塊功能、依賴、接口定義
├─ 03_gui_overlay.md                   ← PyQt/PySide GUI 與 Overlay 設計文件
├─ 04_transcription_system.md          ← STT 模組（FasterWhisper / API）設計
├─ 05_translation_system.md            ← LLM 翻譯模組與情境上下文管理
├─ 06_context_memory.md                ← 維持語境與翻譯品質
├─ 07_audio_input_capture.md           ← 系統音源截取與輸入流處理設計
├─ 08_runtime_check.md                 ← RUNTIME/模型檢查與提示機制
├─ 09_system_logging.md                ← LOG 系統與顏色分類規範
├─ 10_dialogue_logging.md              ← 語料紀錄層使用規範
├─ 11_config_json_spec.md              ← config.json 結構與設定說明
├─ 12_performance_targets.md           ← 性能與延遲優化目標 (0.5~1.5s pipeline)
├─ 13_dev_environment_setup.md         ← 環境設置、依賴、建構步驟
└─ 14_future_expansion.md              ← 後續擴充構想與 API 替換策略

## System Workflow

```mermaid
flowchart TD
    %% Nodes
    Start((User Start))
    Init[Initialize & Runtime Check]
    Warmup[Model Warmup]
    Ready{System Ready}
    
    AudioInput[Audio Capture<br/>WASAPI Loopback]
    Chunking[Audio Chunking<br/>Overlap Processing]
    
    STT[STT Decoding<br/>FasterWhisper / API]
    Decision{Sentence End?}
    
    PartialDisplay[Update Overlay<br/>Partial Transcript]
    FinalSentence[Final Sentence Generated]
    
    LLM1[LLM 1: Translation<br/>Context + Sentence]
    TransDisplay[Update Overlay<br/>Translation]
    
    LLM2[LLM 2: Context Update<br/>Context + Trans]
    ContextDisplay[Update Overlay<br/>Context]
    
    LogSystem[System Log<br/>Info/Warn/Error]
    LogDialogue[Dialogue Log<br/>CSV/JSON]
    
    %% Flow
    Start --> Init --> Warmup --> Ready
    Ready -->|Start Pressed| AudioInput
    AudioInput --> Chunking --> STT
    
    STT -->|Partial| PartialDisplay
    STT --> Decision
    
    Decision -- No --> PartialDisplay
    Decision -- Yes --> FinalSentence
    
    FinalSentence --> LLM1
    FinalSentence -.-> LogDialogue
    
    LLM1 --> TransDisplay
    LLM1 --> LLM2
    LLM1 -.-> LogDialogue
    
    LLM2 --> ContextDisplay
    LLM2 -.-> LogDialogue
    
    %% Feedback Loops
    LLM2 -->|New Context| LLM1
    
    %% Logging side connections
    Init -.-> LogSystem
    STT -.-> LogSystem
    LLM1 -.-> LogSystem
    
    %% Subgraphs for visual grouping
    subgraph Transcription [Transcription Workflow]
        AudioInput
        Chunking
        STT
        Decision
        PartialDisplay
        FinalSentence
    end
    
    subgraph Translation [Translation Workflow]
        LLM1
        TransDisplay
        LLM2
        ContextDisplay
    end
    
    subgraph Storage [Logging & Memory]
        LogSystem
        LogDialogue
    end

    style Start fill:#f9f,stroke:#333,stroke-width:2px
    style FinalSentence fill:#ff9,stroke:#333,stroke-width:2px
```
