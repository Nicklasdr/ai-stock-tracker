import os
from datetime import datetime, timedelta, timezone
import requests
import yfinance as yf

def get_history(ticker: str, period: str | None = None):
    period = period or os.getenv("DATA_PERIOD", "1y")
    frame = yf.download(ticker, period=period, interval="1d", auto_adjust=True,
                        progress=False, threads=False)
    if frame is None or frame.empty:
        return frame
    # yfinance may return MultiIndex columns for a single ticker.
    if getattr(frame.columns, "nlevels", 1) > 1:
        frame.columns = frame.columns.get_level_values(0)
    return frame.dropna(subset=["Close"])

def get_news(ticker: str, limit: int = 5):
    key = os.getenv("NEWS_API_KEY")
    if not key:
        return []
    base = os.getenv("NEWS_API_BASE_URL", "https://newsapi.org/v2").rstrip("/")
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    try:
        response = requests.get(
            f"{base}/everything",
            params={"q": ticker, "from": since, "sortBy": "publishedAt",
                    "language": "en", "pageSize": limit, "apiKey": key},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        return [{
            "title": a.get("title", ""),
            "description": a.get("description", ""),
            "source": (a.get("source") or {}).get("name", "Unknown"),
            "published_at": a.get("publishedAt", ""),
            "url": a.get("url", ""),
        } for a in payload.get("articles", [])[:limit]]
    except Exception as exc:
        return [{"error": f"News fetch failed: {exc}"}]
