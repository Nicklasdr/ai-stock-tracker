import os

import requests

LIMIT = 4000  # Telegram max is 4096


def _chunks(text: str, limit: int = LIMIT):
    chunk = ""
    for line in text.split("\n"):
        while len(line) > limit:  # a single very long line
            if chunk:
                yield chunk
                chunk = ""
            yield line[:limit]
            line = line[limit:]
        if chunk and len(chunk) + len(line) + 1 > limit:
            yield chunk
            chunk = ""
        chunk += line + "\n"
    if chunk.strip():
        yield chunk


def send_telegram(text: str):
    token, chat_id = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Telegram not configured; skipping delivery.")
        return False
    for part in _chunks(text):
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": part, "disable_web_page_preview": True},
            timeout=20,
        )
        response.raise_for_status()
    return True
