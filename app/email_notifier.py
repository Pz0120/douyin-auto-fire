from __future__ import annotations

import asyncio
import os
import smtplib
from datetime import datetime, timedelta, timezone
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
    subject, body = _build_email_content(task_id, dry_run, results, screenshots)
    await asyncio.to_thread(
        _send_email,
        smtp_server,
        smtp_port,
        sender_email,
        sender_password,
        recipient_email,
        subject,
        body,
    )


def _send_email(
    smtp_server: str,
    smtp_port: int,
    sender_email: str,
    sender_password: str,
    recipient_email: str,
    subject: str,
    body: str,
) -> None:
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = recipient_email

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
        server.sendmail(sender_email, [recipient_email], msg.as_string())


def _build_email_content(
    task_id: str,
    dry_run: bool,
    results: list[TargetResult],
    screenshots: list[Path],
) -> tuple[str, str]:
    successes = [r for r in results if r.status == "success"]
    failures = [r for r in results if r.status == "failed"]

    finished = datetime.now(timezone.utc).astimezone(NOTIFY_TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")

    if failures:
        status_emoji = "❌"
        status_text = "失败"
    else:
        status_emoji = "✅"
        status_text = "成功"

    subject = f"[{task_id}] {status_text} - 成功 {len(successes)} 人，失败 {len(failures)} 人"

    lines = [
        f"{status_emoji} 抖音自动续火花",
        "",
        f"任务: {task_id}",
        f"状态: {status_emoji} {status_text}",
        f"时间: {finished}",
        "",
    ]

    if dry_run:
        lines.append("模式: 空跑（未实际发送消息）")
        lines.append("")

    lines.append("=" * 50)
    lines.append("执行结果:")
    lines.append("=" * 50)
    lines.append("")

    if successes:
        for r in successes:
            if dry_run:
                lines.append(f"  ✅ {r.target} — 已找到")
            else:
                lines.append(f"  ✅ {r.target} — 已发送 {r.sent} 条消息")

    if failures:
        for r in failures:
            error_msg = r.error or "未知错误"
            lines.append(f"  ❌ {r.target} — {error_msg}")

    lines.append("")
    lines.append("=" * 50)
    lines.append(f"成功: {len(successes)}")
    lines.append(f"失败: {len(failures)}")

    # 如果有截图/日志链接
    if screenshots or _is_github_actions():
        lines.append("")
        lines.append("=" * 50)
        lines.append("诊断信息:")
        lines.append("=" * 50)
        run_url = _github_run_url()
        if run_url:
            lines.append(f"  运行日志: {run_url}")
        for p in screenshots:
            lines.append(f"  截图: {p.name}")

    lines.append("")
    lines.append("=" * 50)
    lines.append("本邮件由 douyin-auto-fire 自动发送")

    body = "\n".join(lines)
    return subject, body


def _github_run_url() -> str | None:
    server = os.getenv("GITHUB_SERVER_URL")
    repository = os.getenv("GITHUB_REPOSITORY")
    run_id = os.getenv("GITHUB_RUN_ID")
    if not server or not repository or not run_id:
        return None
    return f"{server.rstrip('/')}/{repository}/actions/runs/{run_id}"


def _is_github_actions() -> bool:
    return os.getenv("GITHUB_ACTIONS") == "true"
