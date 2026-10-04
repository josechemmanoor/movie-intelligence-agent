from __future__ import annotations
import argparse
import smtplib
from email.message import EmailMessage

from mcp.server.fastmcp import FastMCP

from .config import (
    SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, EMAIL_FROM
)

mcp = FastMCP("movie-email")

def send_email_impl(to: str, subject: str, body: str) -> str:
    if not SMTP_USERNAME or not SMTP_PASSWORD or not EMAIL_FROM:
        raise RuntimeError(
            "SMTP is not configured. Set SMTP_USERNAME, SMTP_PASSWORD and EMAIL_FROM in .env."
        )

    msg = EmailMessage()
    msg["From"] = EMAIL_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)

    return f"Email successfully sent to {to}."

@mcp.tool()
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email containing a movie scene summary or analysis."""
    return send_email_impl(to, subject, body)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", default="stdio", choices=["stdio", "sse"])
    args = parser.parse_args()
    mcp.run(transport=args.transport)
