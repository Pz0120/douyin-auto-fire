from __future__ import annotations

import asyncio
import os
import smtplib
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from app.models import TargetResult

NOTIFY_TIMEZONE = timezone(timedelta(hours=8), name="Asia/Shanghai")


async def send_email_notification(
    smtp_server: str,
    smtp_port: int,
    sender_email: str,
    sender_password: str,
    recipient_email: str,
    task_id: str,
    dry_run: bool,
    results: list[TargetResult],
    screenshots: list[Path],
) -> None:
    """Send an email notification summarizing task execution results."""
    subject, body_html, body_text = _build_email_content(task_id, dry_run, results, screenshots)
    await asyncio.to_thread(
        _send_email,
        smtp_server,
        smtp_port,
        sender_email,
        sender_password,
        recipient_email,
        subject,
        body_html,
        body_text,
    )


def _send_email(
    smtp_server: str,
    smtp_port: int,
    sender_email: str,
    sender_password: str,
    recipient_email: str,
    subject: str,
    body_html: str,
    body_text: str,
) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    if smtp_port == 465:
        server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30)
    else:
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
        try:
            server.starttls()
        except Exception:
            pass

    with server:
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())


def _build_email_content(
    task_id: str,
    dry_run: bool,
    results: list[TargetResult],
    screenshots: list[Path],
) -> tuple[str, str, str]:
    successes = [r for r in results if r.status == "success"]
    failures = [r for r in results if r.status == "failed"]
    status = "全部成功" if not failures else "存在失败"
    mode = "检查模式（未发送消息）" if dry_run else "正式发送"
    finished = datetime.now(timezone.utc).astimezone(NOTIFY_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S %z")
    title = f"抖音自动发送：{status}"
    subject = f"[{task_id}] {status} - 成功 {len(successes)} 人，失败 {len(failures)} 人"

    text_lines = [
        title,
        "",
        f"任务 ID: {task_id}",
        f"模式: {mode}",
        f"完成时间: {finished}",
        f"结果: 成功 {len(successes)} 人，失败 {len(failures)} 人",
        "",
    ]
    if successes:
        text_lines.append(f"=== 成功名单（{len(successes)}人）===")
        for i, r in enumerate(successes, 1):
            detail = "已验证" if dry_run else f"已发送 {r.sent} 条"
            text_lines.append(f"{i}. {r.target} - {detail}")
        text_lines.append("")
    if failures:
        text_lines.append(f"=== 失败名单（{len(failures)}人）===")
        for i, r in enumerate(failures, 1):
            sent_info = f"，已发送 {r.sent} 条" if r.sent else ""
            text_lines.append(f"{i}. {r.target}{sent_info}")
            text_lines.append(f"   - 原因: {r.error or '未知错误'}")
        text_lines.append("")
    if screenshots:
        text_lines.append(f"=== 失败截图（{len(screenshots)}张）===")
        for p in screenshots:
            text_lines.append(f"- {p.name}")
        run_url = _github_run_url()
        if run_url:
            text_lines.append("")
            text_lines.append(f"打开本次 GitHub Actions 执行并下载截图: {run_url}")
    body_text = "\n".join(text_lines)

    color = "#52c41a" if not failures else "#ff4d4f"
    icon = "✅" if not failures else "❌"
    html_parts = [
        '<html><head><meta charset="utf-8"></head>',
        '<body style="font-family: -apple-system, BlinkMacSystemFont,Segoe UI, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">',
        f'<h2 style="color: {color};">{icon} {title}</h2>',
        '<table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">',
        f'<tr><td style="padding: 8px; color: #666;">任务 ID</td><td style="padding: 8px;"><b>{_esc(task_id)}</b></td></tr>',
        f'<tr><td style="padding: 8px; color: #666;">模式</td><td style="padding: 8px;">{_esc(mode)}</td></tr>',
        f'<tr><td style="padding: 8px; color: #666;">完成时间</td><td style="padding: 8px;">{_esc(finished)}</td></tr>',
        f'<tr><td style="padding: 8px; color: #666;">结果</td><td style="padding: 8px;">✅ 成功 <b>{len(successes)}</b> 人，❌ 失败 <b>{len(failures)}</b> 人</td></tr>',
        '</table>',
    ]
    if successes:
        html_parts.append(f'<h3 style="color: #52c41a;">✅ 成功名单（{len(successes)}人）</h3>')
        html_parts.append("<ul>")
        for r in successes:
            detail = "已验证" if dry_run else f"已发送 {r.sent} 条"
            html_parts.append(f'<li><b>{_esc(r.target)}</b> — {_esc(detail)}</li>')
        html_parts.append("</ul>")
    if failures:
        html_parts.append(f'<h3 style="color: #ff4d4f;">❌ 失败名单（{len(failures)}人）</h3>')
        html_parts.append("<ul>")
        for r in failures:
            sent_info = f"，已发送 {r.sent} 条" if r.sent else ""
            html_parts.append(f'<li><b>{_esc(r.target)}</b>{_esc(sent_info)}<br>')
            html_parts.append(f'<span style="color: #666; font-size: 14px;">原因: {_esc(r.error or "未知错误")}</span></li>')
        html_parts.append("</ul>")
    if screenshots:
        html_parts.append(f"<h3>📸 失败截图（{len(screenshots)}张）</h3>")
        html_parts.append("<ul>")
        for p in screenshots:
            html_parts.append(f"<li><code>{_esc(p.name)}</code></li>")
        html_parts.append("</ul>")
        run_url = _github_run_url()
        if run_url:
            html_parts.append(f'<p><a href="{run_url}" style="color: #1890ff;">打开本次 GitHub Actions 执行并下载截图</a></p>')
            html_parts.append('<p style="color: #999; font-size: 12px;">截图将在任务产物生成后在此次执行的 Artifacts 中找到。</p>')
    html_parts.append('<hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">')
    html_parts.append('<p style="color: #999; font-size: 12px;">本邮件由 douyin-auto-fire 自动发送，请勿直接回复。</p>')
    html_parts.append("</body></html>")
    body_html = "\n".join(html_parts)

    return subject, body_html, body_text


def _github_run_url() -> str | None:
    server = os.getenv("GITHUB_SERVER_URL")
    repository = os.getenv("GITHUB_REPOSITORY")
    run_id = os.getenv("GITHUB_RUN_ID")
    if not server or not repository or not run_id:
        return None
    return f"{server.rstrip('/')}/{repository}/actions/runs/{run_id}"


def _esc(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
