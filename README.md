# Kitchen Automation System

這是一套為專業廚房設計的輕量化管理系統，旨在透過行動端介面簡化每日的「叫貨統計」與「備料損耗紀錄」，並透過自動化流程將數據同步至 Google 試算表與 Notion 作品集。

---

## 🚀 系統功能分頁說明

### 1. 叫貨單 (Order)
用於每日向供應商叫貨前的數量統計。
* **填寫方式**：在品項右側直接輸入數量。
* **自動縮寫**：系統會根據預設單位自動生成對應縮寫。
* **確認送出**：點擊後自動跳轉至「匯出」頁面產出 LINE 格式純文字。
* **快速清空**：點擊「✕ 清空」可一鍵重置所有暫存數據。

### 2. 損耗回報 (Loss Report)
用於精確紀錄食材處理過程中的重量損失（出成率計算）。
* **核心欄位**：
    * **日期/負責人**：系統自動記憶姓名，日期請維持 8 位數格式（如 `20260330`）。
    * **三欄式數據**：
        1. **進貨(g)**：原始採購重量。
        2. **退冰(g)**：退冰後重量（蔬果不需退冰可留空）。
        3. **成品(g)**：最終可使用重量（系統依此計算出成率）。

### 3. 匯出 (Export)
將數據轉換為標準化文字，以便快速貼上至 LINE 工作群組。
* **自動分批處理**：為避免數據過長導致系統處理過載，若單次紀錄**超過 10 筆**，系統會自動拆分為「第 1 批」、「第 2 批」按鈕分次匯出。
* **標準格式**：
    * 叫貨：`節瓜-5根`
    * 損耗：使用 `/` 分隔格式，便於後端解析。

### 4. 設定 (Settings)
自定義專屬於該廚房的食材名單。
* **品項管理**：可隨時新增類別、修改縮寫或刪除不常用的品項。
* **資料維護**：支援「清除所有損耗紀錄」，方便每月初重新開始統計。

## ⚠️ 使用注意事項
* **純數字輸入**：請勿輸入單位（如填寫 `3000` 而非 `3000g`），確保系統計算邏輯正確。
* **本地儲存機制**：資料存放於手機瀏覽器的 LocalStorage。
    * *注意：* 若清除瀏覽器快取或使用「無痕模式」，自訂品項與紀錄將會遺失。

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

## 🛠 技術架構
* **Frontend**: HTML5, CSS3 (Flexbox/Grid), JavaScript (ES6)
* **Backend**: n8n Automation Engine
* **Storage**: Google Sheets, Notion API
* **Deployment**: GitHub Pages

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
