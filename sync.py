"""
sync.py —
  1. 讀取最新 Git commit 並同步到 Notion 資料庫
  2. 讀取 README.md 並同步到 Notion 作品集頁面
"""

import os
import re
import subprocess
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
NOTION_PAGE_ID = os.getenv("NOTION_PAGE_ID")  # 作品集首頁 ID
NOTION_API_URL = "https://api.notion.com/v1/pages"
NOTION_VERSION = "2022-06-28"
GITHUB_REPO_URL = "https://github.com/a0956829427-hub/kitchen-automation-system"
README_PATH = Path(__file__).parent / "README.md"

_NOTION_CODE_LANGUAGES = {
    "abap", "arduino", "bash", "basic", "c", "clojure", "coffeescript",
    "cpp", "csharp", "css", "dart", "diff", "docker", "elixir", "elm",
    "erlang", "flow", "fortran", "fsharp", "gherkin", "glsl", "go",
    "graphql", "groovy", "haskell", "html", "java", "javascript", "json",
    "julia", "kotlin", "latex", "less", "lisp", "livescript", "lua",
    "makefile", "markdown", "markup", "matlab", "mermaid", "nix",
    "objective-c", "ocaml", "pascal", "perl", "php", "plain text",
    "powershell", "prolog", "protobuf", "python", "r", "reason", "ruby",
    "rust", "scala", "scss", "shell", "sql", "swift", "typescript",
    "vb.net", "verilog", "vhdl", "visual basic", "webassembly", "xml", "yaml",
}


# ─────────────────────────── 共用 helpers ───────────────────────

def _headers() -> dict:
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


# ─────────────────────────── commit 同步 ────────────────────────

def get_latest_commits(n: int = 10) -> list[dict]:
    """取得最近 n 筆 git commit 資訊。"""
    fmt = "%H\x1f%an\x1f%aI\x1f%s"
    result = subprocess.run(
        ["git", "log", f"-{n}", f"--pretty=format:{fmt}"],
        capture_output=True,
        text=True,
        check=True,
    )
    commits = []
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        parts = line.split("\x1f", 3)
        if len(parts) != 4:
            continue
        hash_, author, date_str, message = parts
        commits.append({"hash": hash_, "author": author, "date": date_str, "message": message})
    return commits


def commit_exists_in_notion(hash_: str) -> bool:
    """檢查該 commit hash 是否已存在於 Notion 資料庫，避免重複寫入。"""
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    payload = {
        "filter": {
            "property": "GitHub連結",
            "url": {"equals": f"{GITHUB_REPO_URL}/commit/{hash_}"},
        }
    }
    response = requests.post(url, headers=_headers(), json=payload, timeout=10)
    response.raise_for_status()
    return len(response.json().get("results", [])) > 0


def sync_commit_to_notion(commit: dict) -> dict:
    """將單筆 commit 寫入 Notion 資料庫。"""
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "專案名稱": {"title": [{"text": {"content": commit["message"][:100]}}]},
            "專案描述": {
                "rich_text": [{"text": {"content": f"作者：{commit['author']}\n{commit['message']}"}}]
            },
            "GitHub連結": {"url": f"{GITHUB_REPO_URL}/commit/{commit['hash']}"},
            "開始日期": {"date": {"start": commit["date"]}},
        },
    }
    response = requests.post(NOTION_API_URL, headers=_headers(), json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


# ─────────────────────────── README 同步 ────────────────────────

def _parse_inline(text: str) -> list[dict]:
    """將 inline markdown 轉換為 Notion rich_text 陣列。
    支援：**粗體**、`行內程式碼`、*斜體*
    """
    if not text.strip():
        return [{"type": "text", "text": {"content": text}}]

    parts: list[dict] = []
    pattern = re.compile(r'\*\*(.+?)\*\*|`(.+?)`|\*(.+?)\*')
    last = 0
    for m in pattern.finditer(text):
        if m.start() > last:
            parts.append({"type": "text", "text": {"content": text[last:m.start()]}})
        if m.group(1) is not None:        # **bold**
            parts.append({
                "type": "text",
                "text": {"content": m.group(1)},
                "annotations": {"bold": True},
            })
        elif m.group(2) is not None:      # `code`
            parts.append({
                "type": "text",
                "text": {"content": m.group(2)},
                "annotations": {"code": True},
            })
        elif m.group(3) is not None:      # *italic*
            parts.append({
                "type": "text",
                "text": {"content": m.group(3)},
                "annotations": {"italic": True},
            })
        last = m.end()
    if last < len(text):
        parts.append({"type": "text", "text": {"content": text[last:]}})
    return parts or [{"type": "text", "text": {"content": text}}]


def _is_table_separator(line: str) -> bool:
    return bool(re.match(r'^\|\s*[:|-]+\s*\|', line))


def _parse_readme_to_blocks(path: Path) -> list[dict]:
    """將 README.md 解析成 Notion block 陣列。"""
    lines = path.read_text(encoding="utf-8").splitlines()
    blocks: list[dict] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # ── 程式碼區塊 ──────────────────────────────────────────
        if line.startswith("```"):
            lang = line[3:].strip().lower() or "plain text"
            if lang not in _NOTION_CODE_LANGUAGES:
                lang = "plain text"
            code_lines: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            content = "\n".join(code_lines)[:2000]  # Notion 上限 2000 字元
            blocks.append({
                "type": "code",
                "code": {
                    "rich_text": [{"type": "text", "text": {"content": content}}],
                    "language": lang,
                },
            })
            i += 1  # 跳過結尾 ```
            continue

        # ── 表格 ────────────────────────────────────────────────
        if line.startswith("|"):
            table_lines: list[str] = []
            while i < len(lines) and lines[i].startswith("|"):
                table_lines.append(lines[i])
                i += 1
            data_lines = [l for l in table_lines if not _is_table_separator(l)]
            if data_lines:
                rows_cells = [
                    [c.strip() for c in tl.strip("|").split("|")]
                    for tl in data_lines
                ]
                max_cols = max(len(r) for r in rows_cells)
                table_rows = []
                for row in rows_cells:
                    padded = row + [""] * (max_cols - len(row))
                    table_rows.append({
                        "type": "table_row",
                        "table_row": {"cells": [_parse_inline(c) for c in padded]},
                    })
                blocks.append({
                    "type": "table",
                    "table": {
                        "table_width": max_cols,
                        "has_column_header": True,
                        "has_row_header": False,
                        "children": table_rows,
                    },
                })
            continue  # i 已在 while 內推進

        # ── 標題（h1 / h2 / h3）────────────────────────────────
        heading_match = re.match(r'^(#{1,3}) (.+)', line)
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2)
            htype = f"heading_{level}"
            blocks.append({
                "type": htype,
                htype: {"rich_text": _parse_inline(text)},
            })
            i += 1
            continue

        # ── 分隔線 ──────────────────────────────────────────────
        if line.strip() == "---":
            blocks.append({"type": "divider", "divider": {}})
            i += 1
            continue

        # ── 有序清單 ─────────────────────────────────────────────
        if re.match(r'^\s*\d+\. ', line):
            text = re.sub(r'^\s*\d+\. ', '', line)
            blocks.append({
                "type": "numbered_list_item",
                "numbered_list_item": {"rich_text": _parse_inline(text)},
            })
            i += 1
            continue

        # ── 無序清單（含縮排子項目）──────────────────────────────
        if re.match(r'^\s*[*\-] ', line):
            text = re.sub(r'^\s*[*\-] ', '', line)
            blocks.append({
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": _parse_inline(text)},
            })
            i += 1
            continue

        # ── 空行 ─────────────────────────────────────────────────
        if not line.strip():
            i += 1
            continue

        # ── 一般段落 ─────────────────────────────────────────────
        blocks.append({
            "type": "paragraph",
            "paragraph": {"rich_text": _parse_inline(line)},
        })
        i += 1

    return blocks


def _get_all_block_ids(page_id: str) -> list[str]:
    """取得頁面下所有頂層 block ID（支援分頁）。"""
    ids: list[str] = []
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    params: dict = {"page_size": 100}
    while True:
        resp = requests.get(url, headers=_headers(), params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        for block in data.get("results", []):
            ids.append(block["id"])
        if not data.get("has_more"):
            break
        params["start_cursor"] = data["next_cursor"]
    return ids


def _delete_block(block_id: str) -> None:
    resp = requests.delete(
        f"https://api.notion.com/v1/blocks/{block_id}",
        headers=_headers(),
        timeout=10,
    )
    resp.raise_for_status()


def _append_blocks(page_id: str, blocks: list[dict]) -> None:
    """批次寫入 blocks（每批最多 100 個，符合 Notion API 上限）。"""
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    for start in range(0, len(blocks), 100):
        batch = blocks[start : start + 100]
        resp = requests.patch(url, headers=_headers(), json={"children": batch}, timeout=30)
        resp.raise_for_status()


def sync_readme_to_page(page_id: str, readme_path: Path = README_PATH) -> None:
    """清除頁面現有內容，再將 README.md 完整寫入 Notion 頁面。"""
    print("解析 README.md...")
    blocks = _parse_readme_to_blocks(readme_path)
    print(f"  → 共 {len(blocks)} 個 block")

    print("清除 Notion 頁面現有內容...")
    existing_ids = _get_all_block_ids(page_id)
    for bid in existing_ids:
        _delete_block(bid)
    print(f"  → 已刪除 {len(existing_ids)} 個舊 block")

    print("寫入新內容至 Notion 頁面...")
    _append_blocks(page_id, blocks)
    print(f"  → 成功寫入 {len(blocks)} 個 block")


# ─────────────────────────── main ───────────────────────────────

def main():
    if not NOTION_TOKEN:
        raise ValueError("請在 .env 中設定 NOTION_TOKEN")

    # 1. 同步 Git commits → Notion 資料庫
    if NOTION_DATABASE_ID:
        print("=== 同步 Git Commits → Notion 資料庫 ===")
        commits = get_latest_commits(n=10)
        print(f"找到 {len(commits)} 筆 commit")
        synced = skipped = 0
        for commit in commits:
            if commit_exists_in_notion(commit["hash"]):
                print(f"  [略過] {commit['hash'][:7]} — 已存在於 Notion")
                skipped += 1
            else:
                sync_commit_to_notion(commit)
                print(f"  [同步] {commit['hash'][:7]} — {commit['message'][:60]}")
                synced += 1
        print(f"完成。同步 {synced} 筆，略過 {skipped} 筆。\n")
    else:
        print("[略過] NOTION_DATABASE_ID 未設定，跳過 commit 同步。\n")

    # 2. 同步 README.md → Notion 作品集頁面
    if NOTION_PAGE_ID:
        print("=== 同步 README.md → Notion 作品集頁面 ===")
        sync_readme_to_page(NOTION_PAGE_ID)
        print("README 同步完成！")
    else:
        print("[略過] NOTION_PAGE_ID 未設定，跳過 README 同步。")
        print("請在 .env 加入：NOTION_PAGE_ID=<你的作品集頁面 ID>")


if __name__ == "__main__":
    main()
