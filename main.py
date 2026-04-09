import argparse
import sys
from fetcher import fetch_top_repos
from formatter import print_repos, console
from dedup import DedupState
from readme_fetcher import fetch_readme
from llm import generate_repo_content_batch
from markdown_reporter import save_report
from config import get_week_label


def run_github(args):
    """抓取 GitHub 热门仓库 → 去重 → AI 并发生成 → 写入 Markdown 周报"""
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

        # 生成 Markdown 周报
        path = save_report(week, to_write, llm_map)
        console.print(f"[green]已生成周报：{path}（共 {len(to_write)} 条）[/green]")
        dedup.save()
    elif args.dry_run:
        console.print("[yellow]dry-run 模式，跳过 README 抓取和报告生成（去重状态不保存）[/yellow]")


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
    parser.add_argument("--dry-run", action="store_true", help="只抓取和去重，不生成报告/不发送邮件")
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
