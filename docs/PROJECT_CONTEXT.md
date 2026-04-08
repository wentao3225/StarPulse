# StarPulse — 项目上下文文档

> 本文档用于在新对话中快速了解项目全貌，包含架构、各模块职责、数据流、配置项及已完成的改造记录。
> 最后更新：2026-04-08

---

## 项目简介

**StarPulse**（原名 GitHub Star Tracker）是一个自动化每日简报工具，双线并行：

1. **GitHub 热门追踪**：每天抓取 star 数最高的仓库，并发调用 DeepSeek 生成 AI 解读，写入飞书多维表格（按周分表）。
2. **每日资讯推送**：通过 RSS（无需 API Key）抓取 AI 资讯 10 条 + 全球资讯 10 条，封装为 HTML 美化邮件，通过 QQ SMTP 发送。

运行环境：**Python 3.14.2**，可本地运行，也可通过 GitHub Actions 每天自动调度。

---

## 目录结构

```
StarPulse/
├── main.py              # 入口，编排两条主流程
├── config.py            # 所有环境变量统一读取
├── fetcher.py           # GitHub Search API 抓取仓库列表
├── readme_fetcher.py    # GitHub API 获取仓库完整 README
├── dedup.py             # 本地 JSON 去重状态管理
├── llm.py               # DeepSeek API（JSON mode + 并发）
├── feishu.py            # 飞书多维表格 Bitable API 封装
├── news_fetcher.py      # RSS 抓取 AI 资讯 + 全球资讯
├── email_sender.py      # QQ SMTP 发送 HTML 邮件
├── formatter.py         # 终端 Rich 表格美化输出
├── exporter.py          # JSON / CSV 本地导出
├── requirements.txt     # 依赖：requests / rich / python-dotenv / feedparser
├── .env.example         # 环境变量模板
├── dedup_state.json     # 运行时生成，去重状态持久化（勿手动编辑）
└── docs/                # 设计文档、实现计划（历史参考）
```

---

## 架构 & 数据流

### 流程一：GitHub 热门 → 飞书

```
GitHub Search API
      ↓  fetch_top_repos()         → repos[]（rank/name/stars/language/url 等）
      ↓  DedupState.check()        → 过滤 skip，标记 new / update
      ↓  fetch_readme()（并发×8） → 各仓库完整 README 文本
      ↓  generate_repo_content_batch()（并发×8，JSON mode）
         → {url: {"仓库解读": ..., "快速上手": ...}}
      ↓  FeishuClient.upsert_record()
         → 写入/更新飞书多维表格（按周建表，如 2026-W15）
      ↓  DedupState.save()         → 持久化 dedup_state.json
```

### 流程二：资讯 → 邮件（`--news` 参数触发）

```
RSS Feeds（多源）
      ↓  fetch_ai_news(limit=10)     → AI 资讯列表
      ↓  fetch_global_news(limit=10) → 全球资讯列表
      ↓  send_daily_news()           → 构建 HTML 邮件
      ↓  smtplib.SMTP_SSL (QQ:465)  → 发送至 QQ_EMAIL
```

---

## 各模块详解

### `config.py`
- `python-dotenv` 加载 `.env`
- 暴露常量：`GITHUB_TOKEN`、`FEISHU_*`、`DEEPSEEK_*`、`QQ_EMAIL`、`QQ_SMTP_PASSWORD`
- 工具函数：`get_since_date(period)` → 时间窗口起始日期；`get_week_label()` → `YYYY-WXX`

### `fetcher.py`
- `GET /search/repositories`，按 stars 降序，支持分页
- 参数：`top`（条数）、`period`（today/weekly/monthly）、`lang`（语言过滤）
- 处理 403 Rate Limit：读取 `X-RateLimit-Remaining` 响应头并抛出友好错误

### `dedup.py`
- 持久化文件：`dedup_state.json`，结构：`{"weekly": {"week:url": {"stars": N}}, "first_seen": {"url": "date"}}`
- 去重逻辑：`new`（本周首次）/ `update`（star 涨幅 ≥ 500）/ `skip`（跳过）
- 周隔离：key = `{week_label}:{url}`，跨周自动视为新条目

### `readme_fetcher.py`
- `GET /repos/{full_name}/readme`，base64 解码
- 返回**完整** README（无截断），失败静默返回空字符串

### `llm.py`
- **JSON mode**：`response_format: {"type": "json_object"}` + System prompt 约束，结构化输出 `{"仓库解读": "...", "快速上手": "..."}`
- **并发**：`generate_repo_content_batch(repos)` 使用 `ThreadPoolExecutor(max_workers=8)`，返回 `{url: content}` 映射
- 单条函数 `generate_repo_content()` 失败重试 1 次，最终失败返回空字段

### `feishu.py`
- Token 自动刷新（提前 60s 判断过期）
- `get_or_create_table(week_label)` → 按周建表（幂等）
- `ensure_fields()` → 字段幂等补充
- `upsert_record(table_id, fields, record_id=None)` → `record_id=None` 时 POST 新增，否则 PUT 更新
- `find_record_id(table_id, repo_url)` → 按链接字段反查 record_id

### `news_fetcher.py`
- **不需要任何 API Key**，纯 RSS（`feedparser` 库）
- 时区判断：将条目发布时间转为 UTC+8，优先取当天文章，不足则用最近文章补充
- AI 资讯源（英文为主）：TechCrunch AI、VentureBeat AI、MIT Technology Review、The Verge AI、Wired AI
- 全球资讯源（中英混合）：Reuters World、BBC 中文、36Kr、Hacker News、The Guardian World
- 返回类型：`list[NewsItem]`，每项含 `title / link / summary / source / published`

### `email_sender.py`
- QQ SMTP SSL（端口 465），收发同一邮箱
- `send_daily_news(ai_news, global_news)` 构建 HTML 邮件（暗色渐变头部 + 卡片列表排版）
- 依赖：`QQ_EMAIL`（完整邮箱地址）、`QQ_SMTP_PASSWORD`（授权码，非登录密码）

### `main.py`
- `run_github(args)` → 流程一
- `run_news(args)` → 流程二（仅 `--news` 时执行）
- `--dry-run`：不写飞书、不发邮件，只打印结果

---

## 环境变量配置（`.env`）

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `GITHUB_TOKEN` | 建议填 | 提升 API Rate Limit（无权限要求） |
| `FEISHU_APP_ID` | 是 | 飞书自建应用 ID |
| `FEISHU_APP_SECRET` | 是 | 飞书应用密钥 |
| `FEISHU_BITABLE_APP_TOKEN` | 是 | 飞书多维表格文档 ID（从 URL 取） |
| `DEEPSEEK_API_KEY` | 是 | DeepSeek API Key |
| `QQ_EMAIL` | `--news` 时必填 | QQ 邮箱地址，如 `123456@qq.com` |
| `QQ_SMTP_PASSWORD` | `--news` 时必填 | QQ 邮箱授权码（非登录密码） |

---

## 命令行参数

```bash
python main.py [选项]

--top N          抓取前 N 个仓库（默认 30）
--period         today / weekly / monthly（默认 weekly）
--lang           按语言筛选，如 python、javascript
--export         json / csv，导出本地文件
--news           开启资讯抓取 + 邮件推送
--dry-run        只抓取，不写飞书，不发邮件
--token TOKEN    手动指定 GitHub Token（优先于 .env）
```

### 常用组合

```bash
# 测试所有功能（不写入、不发送）
python main.py --dry-run --news

# 正式运行（写飞书 + 发邮件）
python main.py --top 30 --news

# 只写飞书，不发邮件
python main.py --top 30 --period weekly

# Python 筛选 + 导出 CSV
python main.py --top 20 --lang python --export csv
```

---

## 依赖

```
requests>=2.31.0
rich>=13.0.0
python-dotenv>=1.0.0
feedparser>=6.0.0
```

安装：`pip install -r requirements.txt`

---

## 飞书多维表格字段结构

| 字段名 | 类型（Bitable type） | 说明 |
|--------|----------------------|------|
| 仓库名 | 1（文本） | `owner/repo` 格式 |
| 描述 | 1（文本） | 仓库原始描述 |
| Stars | 2（数字） | 当前 star 数 |
| Star 涨幅 | 2（数字） | 与上次记录的差值 |
| 语言 | 1（文本） | 主要编程语言 |
| 链接 | 15（链接） | `{"link": url, "text": name}` |
| 首次入榜时间 | 1（文本） | 第一次被抓取的日期 |
| 最后更新时间 | 1（文本） | 最近一次更新日期 |
| 仓库解读 | 1（文本） | AI 生成口语化介绍 |
| 快速上手 | 1（文本） | AI 生成结构化上手指南 |

---

## 已完成的改造（相对原始版本）

| 改造点 | 状态 | 说明 |
|--------|------|------|
| 新增每日资讯功能 | ✅ | `news_fetcher.py` + `--news` 参数 |
| QQ 邮件推送 | ✅ | `email_sender.py`，HTML 美化模板 |
| LLM JSON mode | ✅ | 替换标记解析，结构化输出 |
| 并发调用 DeepSeek | ✅ | `ThreadPoolExecutor(max_workers=8)` |
| 并发抓取 README | ✅ | `main.py` 中同步并发 |
| 删除 README 截断 | ✅ | 传入完整 README 给 LLM |
| Python 版本 | ✅ | 3.14.2（本地） |
| 飞书功能 | ✅ 保留 | GitHub 热门仓库继续写飞书 |
| 项目重命名 | ✅ | GitHub Star Tracker → StarPulse |

---

## 注意事项

- `dedup_state.json` 是运行时自动生成的去重状态文件，**不要手动编辑或删除**（会导致重复写入飞书）
- QQ 邮箱 SMTP 授权码获取路径：QQ邮箱 → 设置 → 账户 → POP3/SMTP服务 → 开启 → 生成授权码
- GitHub Actions 运行时需通过 `actions/cache` 持久化 `dedup_state.json`（workflow 文件待补充）
- DeepSeek `json_object` mode 要求 System prompt 或 User prompt 中必须含有 `json` 关键词，当前已满足
