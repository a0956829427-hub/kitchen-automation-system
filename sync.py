"""
sync.py — 讀取最新 Git commit 並同步到 Notion 資料庫
"""

import os
import subprocess
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
NOTION_API_URL = "https://api.notion.com/v1/pages"
NOTION_VERSION = "2022-06-28"


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
        commits.append(
            {
                "hash": hash_,
                "author": author,
                "date": date_str,
                "message": message,
            }
        )
    return commits


def commit_exists_in_notion(hash_: str) -> bool:
    """檢查該 commit hash 是否已存在於 Notion 資料庫，避免重複寫入。"""
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    headers = _headers()
    payload = {
        "filter": {
            "property": "Hash",
            "rich_text": {"equals": hash_},
        }
    }
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    response.raise_for_status()
    return len(response.json().get("results", [])) > 0


def sync_commit_to_notion(commit: dict) -> dict:
    """將單筆 commit 寫入 Notion 資料庫。"""
    headers = _headers()
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Title": {
                "title": [{"text": {"content": commit["message"][:100]}}]
            },
            "Hash": {
                "rich_text": [{"text": {"content": commit["hash"]}}]
            },
            "Author": {
                "rich_text": [{"text": {"content": commit["author"]}}]
            },
            "Date": {
                "date": {"start": commit["date"]}
            },
            "Message": {
                "rich_text": [{"text": {"content": commit["message"]}}]
            },
        },
    }
    response = requests.post(NOTION_API_URL, headers=headers, json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def main():
    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        raise ValueError("請在 .env 中設定 NOTION_TOKEN 與 NOTION_DATABASE_ID")

    print("讀取最新 Git commits...")
    commits = get_latest_commits(n=10)
    print(f"找到 {len(commits)} 筆 commit")

    synced = 0
    skipped = 0
    for commit in commits:
        if commit_exists_in_notion(commit["hash"]):
            print(f"  [略過] {commit['hash'][:7]} — 已存在於 Notion")
            skipped += 1
            continue

        sync_commit_to_notion(commit)
        print(f"  [同步] {commit['hash'][:7]} — {commit['message'][:60]}")
        synced += 1

    print(f"\n完成。同步 {synced} 筆，略過 {skipped} 筆。")


if __name__ == "__main__":
    main()
