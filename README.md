# Real-Time YouTube Live Translation App

即時 YouTube 直播翻譯應用程式

## 快速開始

### 1. 環境設置

```powershell
# 創建虛擬環境
py -3.10 -m venv .venv
. .\.venv\Scripts\Activate.ps1

# 安裝依賴
pip install -U pip wheel
pip install -r requirements.txt
```

### 2. 配置 API Keys

**方法 A：使用 API_KEY.txt（推薦）**

```powershell
# 複製範本文件
Copy-Item API_KEY.txt.example API_KEY.txt

# 編輯 API_KEY.txt，填入您的 API keys
# 然後載入環境變數
python tools/load_api_keys.py
```

**方法 B：直接設定環境變數**

```powershell
$env:OPENAI_API_KEY = "your-api-key-here"
```

### 3. 運行應用

```powershell
python app/main.py
```

## 重要文件

- **開發環境設置**：`doc/dev_environment_setup.md`
- **專案總覽**：`doc/project_overview.md`
- **架構說明**：`doc/architecture_overview.md`
- **模組規格**：`doc/modules_specification.md`

## 安全注意事項

⚠️ **請勿提交 API keys 到 git repository**

- `API_KEY.txt` 已加入 `.gitignore`
- 使用 `API_KEY.txt.example` 作為範本
- 確保 `.gitignore` 正確配置

## 開發規範

詳見 `doc/AGENT.md` 了解文檔結構與開發指南。
