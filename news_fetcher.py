"""
news_fetcher.py — 通过 RSS 抓取当日 AI 资讯（10条）+ 全球资讯（10条）
无需任何 API Key，依赖 feedparser 库。
"""
import time
from datetime import datetime, timezone, timedelta
from typing import TypedDict

import feedparser


class NewsItem(TypedDict):
    title: str
    link: str
    summary: str
    source: str
    published: str


# AI 资讯 RSS 源（英文为主）
AI_RSS_FEEDS = [
    ("TechCrunch AI",       "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("VentureBeat AI",      "https://venturebeat.com/category/ai/feed/"),
    ("MIT Tech Review",     "https://www.technologyreview.com/feed/"),
    ("The Verge AI",        "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
    ("Wired AI",            "https://www.wired.com/feed/tag/ai/latest/rss"),
]

# 全球资讯 RSS 源（中英混合）
GLOBAL_RSS_FEEDS = [
    ("Reuters World",       "https://feeds.reuters.com/reuters/worldNews"),
    ("BBC 中文",             "https://feeds.bbci.co.uk/zhongwen/simp/rss.xml"),
    ("36Kr",                "https://36kr.com/feed"),
    ("Hacker News Top",     "https://hnrss.org/frontpage"),
    ("The Guardian World",  "https://www.theguardian.com/world/rss"),
]


def _is_today(entry) -> bool:
    """判断 RSS 条目是否为当天发布（UTC+8 北京时间）"""
    tz_cst = timezone(timedelta(hours=8))
    today_cst = datetime.now(tz_cst).date()

    # feedparser 解析的 time_struct（UTC）
    t = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if t is None:
        return True  # 无时间信息则不过滤
    try:
        dt_utc = datetime(*t[:6], tzinfo=timezone.utc)
        dt_cst = dt_utc.astimezone(tz_cst)
        return dt_cst.date() == today_cst
    except Exception:
        return True


def _parse_entry(entry, source_name: str) -> NewsItem:
    title = entry.get("title", "").strip()
    link = entry.get("link", "").strip()

    # 优先取 summary，其次取 content
    summary = ""
    if hasattr(entry, "summary"):
        summary = entry.summary.strip()
    elif hasattr(entry, "content") and entry.content:
        summary = entry.content[0].get("value", "").strip()

    # 去掉 HTML 标签（简单处理）
    import re
    summary = re.sub(r"<[^>]+>", "", summary).strip()
    # 截取摘要，最多 200 字符
    if len(summary) > 200:
        summary = summary[:200] + "..."

    # 发布时间
    t = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    published = ""
    if t:
        try:
            published = datetime(*t[:6], tzinfo=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        except Exception:
            pass

    return NewsItem(title=title, link=link, summary=summary, source=source_name, published=published)


def _fetch_from_feeds(feeds: list[tuple[str, str]], limit: int) -> list[NewsItem]:
    """从 RSS 源列表中抓取，按当天内容优先，总数不超过 limit。"""
    today_items: list[NewsItem] = []
    fallback_items: list[NewsItem] = []

    for source_name, url in feeds:
        if len(today_items) >= limit:
            break
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"[news_fetcher] 抓取失败 {source_name}: {e}")
            continue

        entries = feed.get("entries", [])
        for entry in entries:
            if len(today_items) >= limit:
                break
            item = _parse_entry(entry, source_name)
            if not item["title"] or not item["link"]:
                continue
            if _is_today(entry):
                today_items.append(item)
            else:
                # 保留作为兜底（当今天文章不足时补充）
                if len(fallback_items) < limit:
                    fallback_items.append(item)

    # 若当天内容不足，用最近文章补充
    if len(today_items) < limit:
        needed = limit - len(today_items)
        today_items.extend(fallback_items[:needed])

    return today_items[:limit]


def fetch_ai_news(limit: int = 10) -> list[NewsItem]:
    """抓取 AI 相关资讯，默认10条。"""
    print("[news_fetcher] 正在抓取 AI 资讯...")
    items = _fetch_from_feeds(AI_RSS_FEEDS, limit)
    print(f"[news_fetcher] AI 资讯获取 {len(items)} 条")
    return items


def fetch_global_news(limit: int = 10) -> list[NewsItem]:
    """抓取全球资讯，默认10条。"""
    print("[news_fetcher] 正在抓取全球资讯...")
    items = _fetch_from_feeds(GLOBAL_RSS_FEEDS, limit)
    print(f"[news_fetcher] 全球资讯获取 {len(items)} 条")
    return items
