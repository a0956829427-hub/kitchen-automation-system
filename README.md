# Kitchen Automation System

一套以 **n8n 自動化中台** 為核心、整合 **LINE 機器人**與 **HTML 前端**的廚房食材備料管理系統。透過雙重校驗機制確保入庫資料的正確性，並自動同步至 Google Sheets 進行持久化儲存與追蹤。

---

## 系統架構

```
[LINE 群組訊息]
      │
      ▼
[n8n Webhook 接收]
      │
      ▼
[雙重校驗機制]
  ├─ 1st Check：群組權限驗證（僅限指定廚房管理群組）
  └─ 2nd Check：品項白名單比對（對照 Google Sheets 名單）
      │
   ┌──┴──┐
  fail  success
   │      │
   ▼      ▼
[LINE  [Switch 路由]
 錯誤   ├─ add    → Append row
 回覆]  └─ update → Update row
             │
             ▼
       [Google Sheets]
             │
             ▼
       [LINE 成功回覆]
```

---

## 核心功能

### 雙重校驗機制
系統在寫入資料前執行兩道防線：

| 驗證層 | 說明 |
|--------|------|
| **群組權限驗證** | 僅接受來自指定 LINE 群組的訊息，拒絕所有非授權來源 |
| **品項白名單比對** | 即時讀取 Google Sheets 名單，確認品項存在才允許入庫 |

任一驗證失敗即立刻透過 LINE 回覆具體錯誤訊息，整批資料取消寫入。

### HTML 前端
提供網頁版資料輸入介面，支援：
- 視覺化表單輸入（新增 / 修改模式）
- 輸入格式即時提示與範例
- 行動裝置友善的響應式版面

### n8n 自動化中台
以 n8n workflow 作為系統中樞：
- Webhook 接收 LINE 推播事件
- Code 節點執行業務邏輯（JavaScript）
- Switch 節點依操作類型路由（新增 / 修改）
- 整合 Google Sheets API 完成讀寫
- 自動組裝 LINE Reply API 回應訊息

### LINE 機器人整合
透過 LINE Messaging API 實現：
- 群組訊息接收與解析
- 支援批次輸入（單次最多 10 筆）
- 操作結果即時推播回群組

---

## 訊息格式

### 新增備料紀錄（5 或 6 段）

```
日期/品項/進貨重量/成品重量/負責人
日期/品項/進貨重量/退冰重量/成品重量/負責人
```

範例：
```
20250411/雞胸肉/5000/4200/小明
20250411/豬里肌/3000/500/2100/小華
```

### 修改已有紀錄（7 或 8 段）

```
修改/行號/日期/品項/進貨重量/成品重量/負責人
修改/行號/日期/品項/進貨重量/退冰重量/成品重量/負責人
```

---

## 技術棧

| 層級 | 技術 |
|------|------|
| 前端 | HTML / CSS / JavaScript |
| 自動化中台 | n8n (self-hosted) |
| 訊息平台 | LINE Messaging API |
| 資料儲存 | Google Sheets |
| 程式語言 | JavaScript (n8n Code Node) |

---

## 快速部署

### 1. 匯入 n8n Workflow

1. 開啟你的 n8n 實例
2. 前往 **Workflows → Import**
3. 上傳 `clean-workflow.json`
4. 填入以下憑證：

| 變數 | 說明 |
|------|------|
| `YOUR_LINE_CHANNEL_ACCESS_TOKEN` | LINE Bot Channel Access Token |
| `YOUR_LINE_GROUP_ID` | 授權廚房管理群組的 Group ID |
| `YOUR_GOOGLE_SHEETS_DOCUMENT_ID` | Google Sheets 文件 ID |
| `YOUR_GOOGLE_SHEETS_CREDENTIAL_ID` | n8n Google Sheets OAuth 憑證 ID |

### 2. 設定 Google Sheets

確保試算表包含以下分頁與欄位：

**總數據**（`gid=0`）：`日期` / `品項` / `進貨重量(g)` / `退冰實際重量` / `成品重量(g)` / `負責人`

**各類名單**（`gid=882636940`）：`品項名單`（白名單來源）

### 3. 設定 LINE Bot

1. 至 [LINE Developers Console](https://developers.line.biz/) 建立 Messaging API Channel
2. 將 n8n Webhook URL 貼入 **Webhook URL** 欄位
3. 將機器人加入廚房管理群組

---

## 安全注意事項

- **請勿**將含有真實憑證的 workflow 檔案（`kitchen-prep-workflow.json`）上傳至版本控制
- 本倉庫僅包含已去敏化的 `clean-workflow.json`
- 所有私密 ID、Token 請透過 n8n 的 Credentials 管理介面填入

---

## 授權

MIT License
