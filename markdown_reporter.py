from pathlib import Path
from datetime import datetime, timezone, timedelta

REPORTS_DIR = Path("reports")


def save_report(week: str, repos: list, llm_map: dict) -> str:
    """生成 Markdown 周报并保存到 reports/{week}.md，返回文件路径。"""
    REPORTS_DIR.mkdir(exist_ok=True)

    tz_cst = timezone(timedelta(hours=8))
    today = datetime.now(tz_cst).strftime("%Y-%m-%d")

    lines = []
    lines.append(f"# StarPulse 周报 {week}")
    lines.append(f"\n> 生成时间：{today}（北京时间）| 共 {len(repos)} 个仓库\n")

    # 概览表格
    lines.append("## 概览\n")
    lines.append("| # | 仓库 | Stars | 语言 | 描述 |")
    lines.append("|---|------|-------|------|------|")
    for i, repo in enumerate(repos, 1):
        desc = (repo.get("description") or "").replace("|", "\\|")[:60]
        lang = repo.get("language") or "N/A"
        lines.append(
            f"| {i} | [{repo['name']}]({repo['url']}) "
            f"| ⭐ {repo['stars']:,} | {lang} | {desc} |"
        )

    # 详细解读
    lines.append("\n## 详细解读\n")
    for i, repo in enumerate(repos, 1):
        content = llm_map.get(repo["url"], {})
        interpretation = content.get("仓库解读", "")
        quickstart = content.get("快速上手", "")
        lang = repo.get("language") or "N/A"

        lines.append(f"### {i}. [{repo['name']}]({repo['url']})\n")
        lines.append(
            f"**⭐ Stars：{repo['stars']:,}** | "
            f"**语言：{lang}** | "
            f"**首次入榜：{repo.get('first_seen', today)}**\n"
        )
        if repo.get("description"):
            lines.append(f"> {repo['description']}\n")
        if interpretation:
            lines.append(f"**仓库解读**\n\n{interpretation}\n")
        if quickstart:
            lines.append(f"**快速上手**\n\n{quickstart}\n")
        lines.append("---\n")

    path = REPORTS_DIR / f"{week}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)
