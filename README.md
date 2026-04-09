# ⭐ StarPulse

每隔三天自动抓取 GitHub 热门仓库，用 AI 生成仓库解读；同时抓取每日 AI 资讯 + 全球资讯（全程简体中文），一封邮件合并推送至 QQ 邮箱。

## 功能

- 每隔三天定时抓取 GitHub star 数最高的仓库（默认前 20 个）
- 支持按时间范围筛选：今天 / 本周 / 本月
- 自动抓取完整 README，调用 DeepSeek（JSON mode）生成：
  - **仓库解读**：口语化介绍，适合非技术读者，可直接用于自媒体内容
  - **快速上手**：结构化功能介绍 + 上手步骤，适合技术向读者
- **并发 AI 生成**：使用 `ThreadPoolExecutor` 并发调用 DeepSeek，大幅缩短等待时间
- 智能去重：同一仓库本周内只写入一次，star 涨幅超过 500 时自动更新
- **合并邮件推送**：热门仓库报告 + AI 资讯 + 全球资讯，一封 HTML 美化邮件发送至 QQ 邮箱
- **全简体中文展示**：国际资讯（英文等）由 DeepSeek 自动翻译为简体中文后推送
- 支持 GitHub Actions 自动运行，也可手动触发

## 快速开始

### 1. Fork 这个仓库

点击右上角 Fork，复制到你自己的 GitHub 账号下。

### 2. 开启 QQ 邮箱 SMTP

1. 登录 QQ 邮箱 → 设置 → 账户 → POP3/SMTP服务 → 开启
2. 按提示生成**授权码**（非登录密码），记录备用

### 3. 配置 GitHub Secrets

在你 Fork 的仓库中，进入 **Settings → Secrets and variables → Actions**，在 **Repository secrets**（非 Environment secrets）中添加：

| 名称 | 必填 | 说明 |
|------|------|------|
| `DEEPSEEK_API_KEY` | 是 | DeepSeek API Key，[在此申请](https://platform.deepseek.com) |
| `QQ_EMAIL` | 是 | 你的 QQ 邮箱地址，如 `123456@qq.com` |
| `QQ_SMTP_PASSWORD` | 是 | QQ 邮箱授权码（非登录密码） |

> `GITHUB_TOKEN` 由 GitHub Actions 自动提供，无需手动添加。

### 4. 触发运行

进入 Actions 页面 → StarPulse Daily → Run workflow，手动触发一次验证配置是否正确。

之后每隔三天北京时间早上 9 点会自动运行，报告与资讯合并通过邮件推送。

## 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 创建 .env 文件并填入配置
# DEEPSEEK_API_KEY=sk-xxx
# QQ_EMAIL=123456@qq.com
# QQ_SMTP_PASSWORD=xxxxx

# dry-run 模式（只抓取，不发邮件）
python main.py --dry-run

# 正常运行（抓取仓库，不发邮件）
python main.py --top 20 --period weekly

# 抓取仓库 + 资讯，合并发送邮件
python main.py --top 20 --period weekly --news

# dry-run + 打印资讯（不发送）
python main.py --dry-run --news

# 按语言筛选
python main.py --top 20 --period weekly --lang python
```

## 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--top` | 20 | 抓取前 N 个仓库 |
| `--period` | weekly | 时间范围：today / weekly / monthly |
| `--lang` | 不限 | 按编程语言筛选，如 python、javascript |
| `--news` | 关闭 | 开启每日资讯抓取 + 合并邮件推送 |
| `--dry-run` | 关闭 | 只抓取，不生成报告，不发邮件 |

## 资讯 RSS 来源

| 类别 | 来源 |
|------|------|
| AI 资讯 | TechCrunch AI、VentureBeat AI、MIT Technology Review、The Verge AI、Wired AI |
| 全球资讯 | Reuters World、BBC 中文、36Kr、Hacker News、The Guardian World |

## License

MIT
