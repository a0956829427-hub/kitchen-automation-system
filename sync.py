import os
import re
import subprocess
from pathlib import Path
import requests
from dotenv import load_dotenv

# 加載環境變數
load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")  # Commit 資料庫 ID
NOTION_PAGE_ID = os.getenv("NOTION_PAGE_ID")          # 作品集頁面 ID
GITHUB_REPO_URL = "https://github.com/a0956829427-hub/kitchen-automation-system"
README_PATH = Path(__file__).parent / "README.md"

_NOTION_CODE_LANGUAGES = {
    "bash", "c", "cpp", "csharp", "css", "go", "html", "java", "javascript", 
    "json", "python", "sql", "typescript", "yaml", "plain text"
}

def _headers() -> dict:
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }

# ─────────────────────────── 1. Git Commit 同步邏輯 ───────────────────────

def get_latest_commits(n: int = 10) -> list[dict]:
    """取得最近 n 筆 git commit 資訊"""
    fmt = "%H\x1f%an\x1f%aI\x1f%s"
    result = subprocess.run(
        ["git", "log", f"-{n}", f"--pretty=format:{fmt}"],
        capture_output=True, text=True, check=True,
    )
    commits = []
    for line in result.stdout.strip().splitlines():
        if not line: continue
        parts = line.split("\x1f", 3)
        if len(parts) == 4:
            commits.append({"hash": parts[0], "author": parts[1], "date": parts[2], "message": parts[3]})
    return commits

def commit_exists_in_notion(hash_: str) -> bool:
    """檢查 commit 是否已存在，避免重複寫入"""
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    payload = {
        "filter": {
            "property": "GitHub連結",
            "url": {"equals": f"{GITHUB_REPO_URL}/commit/{hash_}"},
        }
    }
    resp = requests.post(url, headers=_headers(), json=payload)
    return len(resp.json().get("results", [])) > 0

def sync_commit_to_notion(commit: dict):
    """寫入單筆 Commit 到資料庫"""
    url = "https://api.notion.com/v1/pages"
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "專案名稱": {"title": [{"text": {"content": commit["message"][:100]}}]},
            "專案描述": {"rich_text": [{"text": {"content": f"作者：{commit['author']}\n{commit['message']}"}}]},
            "GitHub連結": {"url": f"{GITHUB_REPO_URL}/commit/{commit['hash']}"},
            "開始日期": {"date": {"start": commit["date"]}},
        },
    }
    requests.post(url, headers=_headers(), json=payload)

# ─────────────────────────── 2. README 解析與同步 ───────────────────────

def _parse_inline(text: str) -> list[dict]:
    """處理粗體、程式碼、斜體"""
    if not text.strip(): return [{"type": "text", "text": {"content": text}}]
    parts = []
    pattern = re.compile(r'\*\*(.+?)\*\*|`(.+?)`|\*(.+?)\*')
    last = 0
    for m in pattern.finditer(text):
        if m.start() > last:
            parts.append({"type": "text", "text": {"content": text[last:m.start()]}})
        if m.group(1): parts.append({"type": "text", "text": {"content": m.group(1)}, "annotations": {"bold": True}})
        elif m.group(2): parts.append({"type": "text", "text": {"content": m.group(2)}, "annotations": {"code": True}})
        elif m.group(3): parts.append({"type": "text", "text": {"content": m.group(3)}, "annotations": {"italic": True}})
        last = m.end()
    if last < len(text): parts.append({"type": "text", "text": {"content": text[last:]}})
    return parts

def _parse_readme_to_blocks(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8").splitlines()
    blocks = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # 1. 圖片解析
        image_match = re.match(r'^!\[.*\]\((https?://.*)\)', line.strip())
        if image_match:
            blocks.append({
                "type": "image", 
                "image": {"type": "external", "external": {"url": image_match.group(1)}}
            })
            i += 1
            continue
        # 2. 程式碼區塊 (含 2000 字元切割)
        if line.startswith("```"):
            lang = line[3:].strip().lower() or "plain text"
            if lang not in _NOTION_CODE_LANGUAGES: lang = "plain text"
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i]); i += 1
            content = "\n".join(code_lines)
            for chunk_start in range(0, max(len(content), 1), 2000):
                blocks.append({
                    "type": "code", 
                    "code": {
                        "rich_text": [{"type": "text", "text": {"content": content[chunk_start:chunk_start+2000]}}], 
                        "language": lang
                    }
                })
            i += 1; continue
        # 3. 表格解析
        if line.startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].startswith("|"):
                table_lines.append(lines[i]); i += 1
            data_lines = [l for l in table_lines if not re.match(r'^\|\s*[:|-]+\s*\|', l)]
            if data_lines:
                rows_cells = [[c.strip() for c in tl.strip("|").split("|")] for tl in data_lines]
                max_cols = max(len(r) for r in rows_cells)
                table_rows = []
                for row in rows_cells:
                    padded = row + [""] * (max_cols - len(row))
                    table_rows.append({"type": "table_row", "table_row": {"cells": [_parse_inline(c) for c in padded]}})
                blocks.append({
                    "type": "table", 
                    "table": {"table_width": max_cols, "has_column_header": True, "children": table_rows}
                })
            continue
        # 4. 標題、分隔線、清單與段落
        heading_match = re.match(r'^(#{1,3}) (.+)', line)
        if heading_match:
            level = len(heading_match.group(1))
            blocks.append({"type": f"heading_{level}", f"heading_{level}": {"rich_text": _parse_inline(heading_match.group(2))}})
        elif line.strip() == "---":
            blocks.append({"type": "divider", "divider": {}})
        elif re.match(r'^\s*[*\-] ', line):
            text = re.sub(r'^\s*[*\-] ', '', line)
            blocks.append({"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": _parse_inline(text)}})
        elif line.strip():
            blocks.append({"type": "paragraph", "paragraph": {"rich_text": _parse_inline(line)}})
        i += 1
    return blocks

def _get_all_block_ids(page_id: str) -> list[str]:
    """獲取頁面上所有區塊 ID (處理超過 100 個區塊的分頁問題)"""
    ids = []
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    params = {"page_size": 100}
    while True:
        resp = requests.get(url, headers=_headers(), params=params).json()
        results = resp.get("results", [])
        for block in results:
            ids.append(block["id"])
        if not resp.get("has_more"):
            break
        params["start_cursor"] = resp.get("next_cursor")
    return ids

def sync_readme():
    print("🚀 同步 README 至 Notion 頁面...")
    blocks = _parse_readme_to_blocks(README_PATH)
    
    # 深度清除：抓取所有 ID 並刪除
    all_ids = _get_all_block_ids(NOTION_PAGE_ID)
    if all_ids:
        print(f"  → 偵測到 {len(all_ids)} 個舊區塊，正在清空頁面...")
        for bid in all_ids:
            requests.delete(f"https://api.notion.com/v1/blocks/{bid}", headers=_headers())
    
    # 批次寫入新內容
    url = f"https://api.notion.com/v1/blocks/{NOTION_PAGE_ID}/children"
    for s in range(0, len(blocks), 100):
        requests.patch(url, headers=_headers(), json={"children": blocks[s:s+100]})
    print(f"✅ README 更新完成 (目前頁面共 {len(blocks)} 個區塊)")

# ─────────────────────────── 執行主程式 ───────────────────────────

if __name__ == "__main__":
    # 1. 同步 Commit
    if NOTION_DATABASE_ID:
        print("=== 同步 Git Commits → Notion 資料庫 ===")
        try:
            commits = get_latest_commits(10)
            synced_count = 0
            for c in commits:
                if not commit_exists_in_notion(c["hash"]):
                    sync_commit_to_notion(c)
                    synced_count += 1
            print(f"✅ Commit 同步完成。新增 {synced_count} 筆紀錄。\n")
        except Exception as e:
            print(f"❌ Commit 同步失敗: {e}\n")

    # 2. 同步 README
    if NOTION_PAGE_ID:
        try:
            sync_readme()
        except Exception as e:
            print(f"❌ README 同步失敗: {e}")