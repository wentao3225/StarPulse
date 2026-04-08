import argparse
import sys
from datetime import datetime
from fetcher import fetch_top_repos
from formatter import print_repos, console
from exporter import export_json, export_csv
from dedup import DedupState
from feishu import FeishuClient
from readme_fetcher import fetch_readme
from llm import generate_repo_content_batch
from config import get_week_label


def run_github(args):
    """抓取 GitHub 热门仓库 → 去重 → AI 并发生成 → 写入飞书"""
    console.print(
        f"[bold]正在抓取 GitHub 热门仓库...[/bold] period=[cyan]{args.period}[/cyan] top=[cyan]{args.top}[/cyan]"
    )

    try:
        repos = fetch_top_repos(top=args.top, period=args.period, lang=args.lang)
    except RuntimeError as e:
        console.print(f"[red]错误：{e}[/red]")
        sys.exit(1)

    print_repos(repos, period=args.period, lang=args.lang)

    week = get_week_label()
    dedup = DedupState()
    to_write = []

    for repo in repos:
        old_stars = dedup.get_stars(repo["url"], week)
        action = dedup.check_and_update(repo["url"], repo["stars"], week)
        if action == "skip":
            continue
        repo["_dedup_action"] = action
        repo["_star_increase"] = 0 if action == "new" else (repo["stars"] - old_stars)
        repo["first_seen"] = dedup.get_first_seen(repo["url"])
        to_write.append(repo)

    console.print(f"[dim]去重后待写入：{len(to_write)} 条（跳过 {len(repos) - len(to_write)} 条）[/dim]")

    if not args.dry_run and to_write:
        # 并发抓取所有 README
        console.print("[dim]并发抓取 README...[/dim]")
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=8) as executor:
            readme_map = dict(
                zip(
                    [r["name"] for r in to_write],
                    executor.map(lambda r: fetch_readme(r["name"]), to_write),
                )
            )
        for repo in to_write:
            repo["_readme"] = readme_map.get(repo["name"], "")

        # 并发调用 DeepSeek 生成内容
        console.print(f"[dim]并发生成 AI 解读（{len(to_write)} 条）...[/dim]")
        llm_map = generate_repo_content_batch(to_write)

        feishu = FeishuClient()
        table_id = feishu.get_or_create_table(week)
        feishu.ensure_fields(table_id, ["仓库解读", "快速上手"])
        today = datetime.utcnow().strftime("%Y-%m-%d")

        for repo in to_write:
            llm_content = llm_map.get(repo["url"], {"仓库解读": "", "快速上手": ""})
            fields = {
                "仓库名": repo["name"],
                "描述": repo["description"],
                "Stars": repo["stars"],
                "Star 涨幅": repo["_star_increase"],
                "语言": repo["language"],
                "链接": {"link": repo["url"], "text": repo["name"]},
                "首次入榜时间": repo["first_seen"],
                "最后更新时间": today,
                "仓库解读": llm_content["仓库解读"],
                "快速上手": llm_content["快速上手"],
            }
            record_id = None
            if repo["_dedup_action"] == "update" and dedup.is_loaded_from_file():
                record_id = feishu.find_record_id(table_id, repo["url"])
            feishu.upsert_record(table_id, fields, record_id=record_id)

        console.print(f"[green]已写入飞书表格 {week}，共 {len(to_write)} 条[/green]")
        dedup.save()
    elif args.dry_run:
        console.print("[yellow]dry-run 模式，跳过飞书写入（去重状态不保存）[/yellow]")

    if args.export == "json":
        path = export_json(repos, args.period)
        console.print(f"[green]已导出 JSON：{path}[/green]")
    elif args.export == "csv":
        path = export_csv(repos, args.period)
        console.print(f"[green]已导出 CSV：{path}[/green]")


def run_news(args):
    """抓取每日资讯 → 发送邮件"""
    from news_fetcher import fetch_ai_news, fetch_global_news
    from email_sender import send_daily_news

    ai_news = fetch_ai_news(limit=10)
    global_news = fetch_global_news(limit=10)

    if args.dry_run:
        console.print("[yellow]dry-run 模式，跳过邮件发送[/yellow]")
        console.print(f"[dim]AI 资讯 {len(ai_news)} 条，全球资讯 {len(global_news)} 条[/dim]")
        for item in ai_news + global_news:
            console.print(f"  [{item['source']}] {item['title']}")
        return

    send_daily_news(ai_news, global_news)


def main():
    parser = argparse.ArgumentParser(description="StarPulse — GitHub 热门追踪 & 每日资讯推送")
    parser.add_argument("--top", type=int, default=30, help="抓取前 N 个仓库（默认 30）")
    parser.add_argument("--period", choices=["today", "weekly", "monthly"], default="weekly")
    parser.add_argument("--lang", type=str, default=None, help="按编程语言筛选")
    parser.add_argument("--export", choices=["json", "csv"], default=None, help="同时导出本地文件")
    parser.add_argument("--dry-run", action="store_true", help="只抓取和去重，不写入飞书/不发送邮件")
    parser.add_argument("--token", type=str, default=None, help="GitHub Token（优先级高于 .env）")
    parser.add_argument(
        "--news",
        action="store_true",
        help="抓取每日 AI 资讯 + 全球资讯并通过 QQ 邮件推送（不影响 GitHub 热门抓取）",
    )
    args = parser.parse_args()

    if args.token:
        import config, fetcher
        config.GITHUB_TOKEN = args.token
        fetcher.GITHUB_TOKEN = args.token

    run_github(args)

    if args.news:
        run_news(args)


if __name__ == "__main__":
    main()
