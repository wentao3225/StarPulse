# ⭐ StarPulse

每天自动抓取 GitHub 热门仓库，用 AI 生成仓库解读，自动提交 Markdown 周报到仓库；同时抓取每日 AI 资讯 + 全球资讯，通过 QQ 邮件推送。

## 功能

- 每天定时抓取 GitHub star 数最高的仓库（默认前 30 个）
- 支持按时间范围筛选：今天 / 本周 / 本月
- 自动抓取完整 README，调用 DeepSeek（JSON mode）生成：
  - **仓库解读**：口语化介绍，适合非技术读者，可直接用于自媒体内容
  - **快速上手**：结构化功能介绍 + 上手步骤，适合技术向读者
- **并发 AI 生成**：使用 `ThreadPoolExecutor` 并发调用 DeepSeek，大幅缩短等待时间
- 智能去重：同一仓库本周内只写入一次，star 涨幅超过 500 时自动更新
- **Markdown 周报**：每次运行自动生成 `reports/YYYY-WXX.md` 并提交到仓库，在 GitHub 上直接可读
- **每日资讯推送**：通过 RSS 无需 API Key 抓取 AI 资讯（10条）+ 全球资讯（10条），HTML 美化邮件发送至 QQ 邮箱
- 支持 GitHub Actions 每天自动运行，也可手动触发

## 效果预览

每次运行后自动生成 `reports/YYYY-WXX.md` 并提交到仓库，包含：

- 概览表格：仓库名、Stars、语言、描述
- 每个仓库的 AI 解读详情（仓库解读 + 快速上手）

## 快速开始

### 1. Fork 这个仓库

点击右上角 Fork，复制到你自己的 GitHub 账号下。

### 2. 开启 QQ 邮箱 SMTP（可选，仅资讯推送需要）

1. 登录 QQ 邮箱 → 设置 → 账户 → POP3/SMTP服务 → 开启
2. 按提示生成**授权码**（非登录密码），记录备用

### 3. 配置 GitHub Secrets

在你 Fork 的仓库中，进入 Settings → Secrets and variables → Actions，添加以下 Secret：

| 名称 | 必填 | 说明 |
|------|------|------|
| `DEEPSEEK_API_KEY` | 是 | DeepSeek API Key，[在此申请](https://platform.deepseek.com) |
| `QQ_EMAIL` | 否 | 你的 QQ 邮箱地址，如 `123456@qq.com` |
| `QQ_SMTP_PASSWORD` | 否 | QQ 邮箱授权码（非登录密码），不填则跳过邮件发送 |

> `GITHUB_TOKEN` 由 GitHub Actions 自动提供，无需手动添加。

### 4. 触发运行

进入 Actions 页面 → StarPulse Daily → Run workflow，手动触发一次验证配置是否正确。

之后每天北京时间早上 9 点会自动运行，报告自动提交到 `reports/` 目录。

## 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 复制配置文件
cp .env.example .env
# 编辑 .env，填入各项 Token

# 运行（dry-run 模式，不生成报告，不发邮件）
python main.py --dry-run

# 正常运行（生成 Markdown 周报）
python main.py --top 30 --period weekly

# 生成周报 + 发送每日资讯邮件
python main.py --top 30 --period weekly --news

# 只测试邮件推送（dry-run，打印资讯但不发送）
python main.py --dry-run --news

# 按语言筛选
python main.py --top 20 --period weekly --lang python
```

## 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--top` | 30 | 抓取前 N 个仓库 |
| `--period` | weekly | 时间范围：today / weekly / monthly |
| `--lang` | 不限 | 按编程语言筛选，如 python、javascript |
| `--news` | 关闭 | 开启每日资讯抓取 + QQ 邮件推送 |
| `--dry-run` | 关闭 | 只抓取，不生成报告，不发邮件 |

## 每日资讯 RSS 来源

| 类别 | 来源 |
|------|------|
| AI 资讯 | TechCrunch AI、VentureBeat AI、MIT Technology Review、The Verge AI、Wired AI |
| 全球资讯 | Reuters World、BBC 中文、36Kr、Hacker News、The Guardian World |

## 运行测试

```bash
pip install pytest
pytest tests/ -v
```

## License

MIT
