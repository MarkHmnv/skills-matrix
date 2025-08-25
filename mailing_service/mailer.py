import sqlite3
from contextlib import closing
from datetime import datetime, timezone, timedelta
import smtplib
from email.mime.text import MIMEText
import config


def _utcnow():
    """Return current UTC time."""
    return datetime.now(timezone.utc)


def init_db():
    """Create outbox table if missing."""
    with closing(sqlite3.connect(config.DB_PATH)) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS outbox (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                to_addr TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                send_after TEXT,
                sent_at TEXT
            )
            """
        )
        con.commit()


def enqueue_email(to_addr: str, subject: str, body: str, delay_seconds: int = 0):
    """Insert an email into outbox.

    Args:
        to_addr: Recipient.
        subject: Subject.
        body: Plain text body.
        delay_seconds: Delay before sending.
    """
    when = _utcnow() + timedelta(seconds=delay_seconds)
    with closing(sqlite3.connect(config.DB_PATH)) as con:
        con.execute(
            "INSERT INTO outbox (to_addr, subject, body, send_after, sent_at) VALUES (?, ?, ?, ?, NULL)",
            (to_addr, subject, body, when.isoformat()),
        )
        con.commit()


def fetch_due(limit: int = 100):
    """Fetch due, unsent emails.

    Args:
        limit: Max rows.

    Returns:
        List of dict rows.
    """
    now_iso = _utcnow().isoformat()
    with closing(sqlite3.connect(config.DB_PATH)) as con:
        con.row_factory = sqlite3.Row
        cur = con.execute(
            """
            SELECT id, to_addr, subject, body
            FROM outbox
            WHERE sent_at IS NULL
              AND (send_after IS NULL OR send_after <= ?)
            ORDER BY id
            LIMIT ?
            """,
            (now_iso, limit),
        )
        return [dict(r) for r in cur.fetchall()]


def mark_sent(row_id: int):
    """Mark an email as sent.

    Args:
        row_id: Row id.
    """
    with closing(sqlite3.connect(config.DB_PATH)) as con:
        con.execute(
            "UPDATE outbox SET sent_at = ? WHERE id = ?",
            (_utcnow().isoformat(), row_id),
        )
        con.commit()


def _smtp_client():
    """Create SMTP client."""
    client = smtplib.SMTP(host=config.SMTP_HOST, port=config.SMTP_PORT, timeout=30)
    if config.SMTP_USE_TLS:
        client.starttls()
    if config.SMTP_USERNAME:
        client.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
    return client


def send_email(row: dict):
    """Send a single email.

    Args:
        row: Row dict.

    Raises:
        smtplib.SMTPException: On SMTP failure.
    """
    msg = MIMEText(row["body"])
    msg["Subject"] = row["subject"]
    msg["From"] = config.FROM_ADDR
    msg["To"] = row["to_addr"]

    with _smtp_client() as client:
        client.sendmail(config.FROM_ADDR, [row["to_addr"]], msg.as_string())


if __name__ == "__main__":
    # Tiny CLI to enqueue a test email:
    #   python mailer.py --to alice@example.com --subject "Hi" --body "Hello" --delay 0
    import argparse

    parser = argparse.ArgumentParser(description="Enqueue an email.")
    parser.add_argument("--to", required=True, dest="to_addr")
    parser.add_argument("--subject", required=True)
    parser.add_argument("--body", required=True)
    parser.add_argument("--delay", type=int, default=0, help="Seconds to delay")
    args = parser.parse_args()

    init_db()
    enqueue_email(args.to_addr, args.subject, args.body, delay_seconds=args.delay)
    print("Enqueued.")
