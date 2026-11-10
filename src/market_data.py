from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import requests
import yfinance as yf

log = logging.getLogger(__name__)


def get_history(ticker: str, period: str | None = None):
    # 2y so SMA(200) has ~250 valid bars and golden/death crosses can be detected.
    period = period or os.getenv("DATA_PERIOD", "2y")
    try:
        frame = yf.download(ticker, period=period, interval="1d", auto_adjust=True,
                            progress=False, threads=False)
    except Exception as exc:
        log.warning("Price download failed for %s: %s", ticker, exc)
        return None
    if frame is None or frame.empty:
        return frame
    # yfinance may return MultiIndex columns for a single ticker.
    if getattr(frame.columns, "nlevels", 1) > 1:
        frame.columns = frame.columns.get_level_values(0)
    return frame.dropna(subset=["Close"])


@lru_cache(maxsize=None)
def get_currency(ticker: str) -> str | None:
    """Trading currency of a ticker, e.g. 'DKK', 'EUR', 'USD'."""
    try:
        return yf.Ticker(ticker).fast_info["currency"]
    except Exception as exc:
        log.warning("Currency lookup failed for %s: %s", ticker, exc)
        return None


@lru_cache(maxsize=None)
def get_fx(ccy: str | None, base: str):
    """(latest, previous) rate converting 1 unit of ccy into base, or None."""
    if not ccy or ccy == base:
        return 1.0, 1.0
    frame = get_history(f"{ccy}{base}=X", period="5d")
    if frame is None or frame.empty or len(frame) < 2:
        log.warning("No FX rate for %s->%s", ccy, base)
        return None
    return float(frame["Close"].iloc[-1]), float(frame["Close"].iloc[-2])


def _newsapi(query: str, limit: int, key: str):
    base = os.getenv("NEWS_API_BASE_URL", "https://newsapi.org/v2").rstrip("/")
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    q = f'"{query}"' if " " in query else query
    response = requests.get(
        f"{base}/everything",
        params={"q": q, "from": since, "sortBy": "publishedAt",
                "language": "en", "pageSize": limit, "apiKey": key},
        timeout=20,
    )
    response.raise_for_status()
    return [{
        "title": a.get("title", ""),
        "description": a.get("description", ""),
        "source": (a.get("source") or {}).get("name", "Unknown"),
        "published_at": a.get("publishedAt", ""),
        "url": a.get("url", ""),
    } for a in response.json().get("articles", [])[:limit]]


def _yfinance_news(ticker: str, limit: int):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    out = []
    for item in yf.Ticker(ticker).news or []:
        c = item.get("content", item)  # newer yfinance nests under "content"
        ts = c.get("pubDate") or item.get("providerPublishTime")
        try:
            when = (datetime.fromtimestamp(ts, timezone.utc) if isinstance(ts, (int, float))
                    else datetime.fromisoformat(ts.replace("Z", "+00:00")))
        except Exception:
            continue
        if when < cutoff:
            continue
        provider = c.get("provider")
        source = provider.get("displayName") if isinstance(provider, dict) else item.get("publisher")
        url = (c.get("canonicalUrl") or {}).get("url") if isinstance(c.get("canonicalUrl"), dict) else item.get("link")
        out.append({"title": c.get("title", ""), "description": (c.get("summary") or "")[:300],
                    "source": source or "Unknown", "published_at": when.isoformat(),
                    "url": url or ""})
        if len(out) >= limit:
            break
    return out


def get_news(ticker: str, limit: int = 5, query: str | None = None):
    """Last-24h news. NewsAPI (searched by company name if given), yfinance as fallback.
    Always returns a list of articles; failures are logged, never returned as items."""
    articles = []
    key = os.getenv("NEWS_API_KEY")
    if key:
        try:
            articles = _newsapi(query or ticker, limit, key)
        except Exception as exc:
            log.warning("NewsAPI failed for %s: %s", ticker, exc)
    if not articles:
        try:
            articles = _yfinance_news(ticker, limit)
        except Exception as exc:
            log.warning("yfinance news failed for %s: %s", ticker, exc)
    return articles
