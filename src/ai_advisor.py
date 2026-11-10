import json
import os

KEEP = ("date", "currency", "close", "daily_change_pct", "rsi_14", "sma_50", "sma_200",
        "volume_ratio_20d", "cross_signal", "signal", "technical_context")


def _compact(report: dict) -> dict:
    """What Gemini sees: portfolio, per-ticker indicators and news. No price history."""
    portfolio = report["portfolio"]
    held = {row["ticker"] for row in portfolio.get("holdings", [])}
    analyses = {}
    for ticker, a in report.get("analyses", {}).items():
        item = {k: a[k] for k in KEEP if a.get(k) is not None}
        if a.get("error"):
            item["error"] = a["error"]
        item["held"] = ticker in held
        item["news"] = [
            {"title": n.get("title"), "description": (n.get("description") or "")[:200],
             "source": n.get("source"), "published_at": n.get("published_at")}
            for n in a.get("news", [])[:5]
        ]
        analyses[ticker] = item
    return {
        "portfolio_name": report.get("portfolio_name"),
        "currency": report.get("currency"),
        "strategy_profile": report.get("strategy_profile"),
        "portfolio": portfolio,
        "analyses": analyses,
    }


def _format(ai: dict) -> str:
    lines = [str(ai.get("executive_summary", "")).strip(), "", "NEWS SENTIMENT"]
    for ticker, v in (ai.get("news_sentiment") or {}).items():
        if isinstance(v, dict):
            lines.append(f"{ticker}: {v.get('label', 'Unknown')} - {v.get('driver', '')}".rstrip(" -"))
        else:
            lines.append(f"{ticker}: {v}")
    return "\n".join(lines).strip()


PROMPT = (
    "You are a cautious market research summarizer, not a financial adviser. "
    "Use only the supplied JSON. Do not invent facts, prices, events, or sources. "
    "Do not issue personalized buy/sell instructions or promise returns. "
    "Explain portfolio movement in 2-3 sentences. Then, for each ticker that has news items, "
    "classify the news as Positive, Neutral, or Negative only when the headlines support it; "
    "otherwise Unknown, with a short driver (e.g. earnings, regulation, product). "
    "Skip tickers without news. Mention uncertainty and distinguish technical signals from fundamentals. "
    'Return JSON only: {"executive_summary": str, '
    '"news_sentiment": {TICKER: {"label": str, "driver": str}}}\nData:\n'
)


def enrich_with_ai(report: dict) -> dict:
    """Optional Gemini narrative. Returns report unchanged if no key or API failure."""
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        report["ai_summary"] = (
            "AI narrative is disabled. Review the quantitative metrics, technical context, "
            "and source-linked headlines below."
        )
        return report
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=key)
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        response = client.models.generate_content(
            model=model,
            contents=PROMPT + json.dumps(_compact(report), default=str),
            config=types.GenerateContentConfig(response_mime_type="application/json",
                                               temperature=0.2),
        )
        try:
            ai = json.loads(response.text)
            report["ai"] = ai
            report["ai_output"] = _format(ai)
        except ValueError:
            report["ai_output"] = response.text  # model ignored the JSON format
    except Exception as exc:
        report["ai_error"] = str(exc)
        report["ai_output"] = "AI analysis unavailable; use the quantitative report."
    return report
