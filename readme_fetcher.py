import base64
import requests
from config import GITHUB_TOKEN, GITHUB_API_BASE


def fetch_readme(full_name: str) -> str:
    """抓取仓库完整 README 内容，失败返回空字符串"""
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    try:
        resp = requests.get(
            f"{GITHUB_API_BASE}/repos/{full_name}/readme",
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data.get("content", "")
        encoding = data.get("encoding", "base64")
        _MAX_CHARS = 600
        if encoding == "base64":
            text = base64.b64decode(content.replace("\n", "")).decode("utf-8", errors="ignore")
        else:
            text = content
        return text[:_MAX_CHARS]
    except Exception as e:
        print(f"[readme_fetcher] 抓取 {full_name} 失败: {e}")
        return ""
