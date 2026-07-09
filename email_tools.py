import email
import imaplib
import os
from email.header import decode_header

from langchain_core.tools import tool


def _decode(value: str) -> str:
    if not value:
        return ""
    decoded = ""
    for text, enc in decode_header(value):
        if isinstance(text, bytes):
            decoded += text.decode(enc or "utf-8", errors="replace")
        else:
            decoded += text
    return decoded


def _get_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            disposition = str(part.get("Content-Disposition") or "")
            if part.get_content_type() == "text/plain" and "attachment" not in disposition:
                charset = part.get_content_charset() or "utf-8"
                payload = part.get_payload(decode=True)
                return payload.decode(charset, errors="replace") if payload else ""
        return ""
    charset = msg.get_content_charset() or "utf-8"
    payload = msg.get_payload(decode=True)
    return payload.decode(charset, errors="replace") if payload else ""


def get_configured_email_count(default: int = 5) -> int:
    """Number of emails to fetch/summarize, from the EMAIL_COUNT env var."""
    raw = os.environ.get("EMAIL_COUNT", str(default))
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


@tool
def get_last_emails() -> str:
    """Fetch the most recent emails from the user's inbox via IMAP.

    Reads the newest messages (newest first) and returns each one's sender,
    subject, date, and body text (truncated to keep the result manageable).
    Login credentials are read from the EMAIL_ADDRESS, EMAIL_APP_PASSWORD,
    and IMAP_SERVER environment variables. This tool takes no arguments --
    the number of emails fetched is controlled entirely by the EMAIL_COUNT
    environment variable, not by the caller.
    """
    count = get_configured_email_count()
    imap_server = os.environ.get("IMAP_SERVER", "imap.gmail.com")
    email_address = os.environ.get("EMAIL_ADDRESS")
    app_password = os.environ.get("EMAIL_APP_PASSWORD")

    if not email_address or not app_password:
        return "Error: EMAIL_ADDRESS or EMAIL_APP_PASSWORD is not set in the environment."

    try:
        with imaplib.IMAP4_SSL(imap_server) as mail:
            mail.login(email_address, app_password)
            mail.select("INBOX")

            status, data = mail.search(None, "ALL")
            if status != "OK":
                return "Error: failed to search the inbox."

            ids = data[0].split()
            if not ids:
                return "No emails found in the inbox."

            last_ids = ids[-count:]
            last_ids.reverse()

            entries = []
            for i, msg_id in enumerate(last_ids, start=1):
                status, msg_data = mail.fetch(msg_id, "(RFC822)")
                if status != "OK" or not msg_data or not msg_data[0]:
                    continue
                msg = email.message_from_bytes(msg_data[0][1])
                subject = _decode(msg.get("Subject")) or "(no subject)"
                sender = _decode(msg.get("From")) or "(unknown sender)"
                date = msg.get("Date", "(no date)")
                body = " ".join(_get_body(msg).split())
                if len(body) > 600:
                    body = body[:600] + " ... [truncated]"
                entries.append(
                    f"--- Email {i} ---\nFrom: {sender}\nSubject: {subject}\n"
                    f"Date: {date}\nBody: {body or '(empty body)'}\n"
                )

            return "\n".join(entries) if entries else "No emails could be read."

    except imaplib.IMAP4.error as e:
        return (
            f"IMAP login/search failed: {e}. If using Gmail, make sure "
            "EMAIL_APP_PASSWORD is a 16-character App Password, not the "
            "regular account password."
        )
    except Exception as e:
        return f"Error fetching emails: {e}"
