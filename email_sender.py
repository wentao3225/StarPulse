"""
email_sender.py — 通过 QQ 邮箱 SMTP 发送每日资讯 HTML 邮件
配置项：QQ_EMAIL（发件人/收件人）、QQ_SMTP_PASSWORD（授权码，非登录密码）
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta

from config import QQ_EMAIL, QQ_SMTP_PASSWORD
from news_fetcher import NewsItem


_SMTP_HOST = "smtp.qq.com"
_SMTP_PORT = 465  # QQ 邮箱 SSL 端口


def _build_news_section(title: str, items: list[NewsItem], accent: str) -> str:
    """渲染单个新闻板块的 HTML。"""
    rows = ""
    for i, item in enumerate(items, 1):
        published = f'<span style="color:#999;font-size:12px;">{item["published"]}</span>' if item["published"] else ""
        source_badge = (
            f'<span style="background:{accent};color:#fff;border-radius:3px;'
            f'padding:1px 6px;font-size:11px;margin-left:8px;">{item["source"]}</span>'
        )
        summary_html = (
            f'<p style="margin:4px 0 0 0;color:#555;font-size:13px;line-height:1.5;">{item["summary"]}</p>'
            if item["summary"]
            else ""
        )
        rows += f"""
        <tr>
          <td style="padding:12px 0;border-bottom:1px solid #f0f0f0;">
            <div>
              <span style="color:#888;font-size:13px;font-weight:bold;margin-right:6px;">{i:02d}</span>
              <a href="{item['link']}" style="color:#1a1a2e;font-size:15px;font-weight:600;text-decoration:none;">
                {item['title']}
              </a>
              {source_badge}
            </div>
            {summary_html}
            <div style="margin-top:4px;">{published}</div>
          </td>
        </tr>"""

    return f"""
    <div style="margin-bottom:32px;">
      <h2 style="margin:0 0 12px 0;padding:8px 14px;background:{accent};color:#fff;
                 border-radius:6px;font-size:16px;letter-spacing:1px;">
        {title}
      </h2>
      <table style="width:100%;border-collapse:collapse;">
        {rows}
      </table>
    </div>"""


def _build_html(ai_news: list[NewsItem], global_news: list[NewsItem]) -> str:
    tz_cst = timezone(timedelta(hours=8))
    today_str = datetime.now(tz_cst).strftime("%Y年%m月%d日")

    ai_section = _build_news_section("🤖 AI 资讯", ai_news, "#4a6cf7")
    global_section = _build_news_section("🌍 全球资讯", global_news, "#27ae60")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f5f6fa;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <div style="max-width:680px;margin:24px auto;background:#fff;border-radius:12px;
              box-shadow:0 2px 16px rgba(0,0,0,.08);overflow:hidden;">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 60%,#0f3460 100%);
                padding:32px 32px 24px;text-align:center;">
      <div style="font-size:28px;font-weight:800;color:#fff;letter-spacing:2px;">⭐ StarPulse</div>
      <div style="color:#a0aec0;margin-top:6px;font-size:14px;">{today_str} 每日简报</div>
    </div>

    <!-- Body -->
    <div style="padding:28px 32px;">
      {ai_section}
      {global_section}
    </div>

    <!-- Footer -->
    <div style="background:#f8f9fc;padding:16px 32px;text-align:center;
                color:#aaa;font-size:12px;border-top:1px solid #eee;">
      由 <strong>StarPulse</strong> 自动生成 · {today_str} ·
      数据来源：多家 RSS 订阅源
    </div>
  </div>
</body>
</html>"""


def send_daily_news(ai_news: list[NewsItem], global_news: list[NewsItem]) -> None:
    """发送每日资讯邮件（收发同一个 QQ 邮箱）。"""
    if not QQ_EMAIL or not QQ_SMTP_PASSWORD:
        print("[警告] QQ_EMAIL 或 QQ_SMTP_PASSWORD 未配置，跳过邮件发送。")
        return

    tz_cst = timezone(timedelta(hours=8))
    today_str = datetime.now(tz_cst).strftime("%Y-%m-%d")
    subject = f"⭐ StarPulse 每日简报 {today_str} | AI资讯 & 全球资讯"

    html_body = _build_html(ai_news, global_news)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = QQ_EMAIL
    msg["To"] = QQ_EMAIL
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    print(f"[email_sender] 正在连接 {_SMTP_HOST}:{_SMTP_PORT}...")
    with smtplib.SMTP_SSL(_SMTP_HOST, _SMTP_PORT) as server:
        server.login(QQ_EMAIL, QQ_SMTP_PASSWORD)
        server.sendmail(QQ_EMAIL, [QQ_EMAIL], msg.as_bytes())

    print(f"[email_sender] 邮件已发送至 {QQ_EMAIL}")
