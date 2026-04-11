# my-automation-project

這是一個將 Git commit 紀錄同步到 Notion 資料庫的自動化專案。

## 功能

- 讀取本地 Git 倉庫的最新 commit 訊息（包含 hash、作者、時間、訊息）
- 透過 Notion API 將 commit 資料同步寫入指定的 Notion 資料庫

## 環境需求

- Python 3.8+
- Notion Integration Token
- Notion Database ID

## 快速開始

1. 複製 `.env` 並填入你的 Notion 憑證：

```
NOTION_TOKEN=your_notion_integration_token
NOTION_DATABASE_ID=your_notion_database_id
```

2. 安裝依賴：

```bash
pip install requests python-dotenv gitpython
```

3. 執行同步腳本：

```bash
python sync.py
```

## Notion 資料庫欄位設定

請確保你的 Notion 資料庫包含以下欄位：

| 欄位名稱 | 類型 |
|---------|------|
| Title   | Title |
| Hash    | Rich Text |
| Author  | Rich Text |
| Date    | Date |
| Message | Rich Text |
