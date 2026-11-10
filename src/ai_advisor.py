import json, os

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
        client = genai.Client(api_key=key)
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        compact = {k: v for k, v in report.items() if k not in ("analyses",)}
        prompt = (
            "You are a cautious market research summarizer, not a financial adviser. "
            "Use only the supplied JSON. Do not invent facts, prices, events, or sources. "
            "Do not issue personalized buy/sell instructions or promise returns. "
            "Explain portfolio movement in 2-3 sentences, then summarize each ticker's "
            "news as Positive, Neutral, or Negative only when supported; otherwise Unknown. "
            "Mention uncertainty and distinguish technical signals from fundamentals. "
            "Return concise JSON with keys executive_summary and news_sentiment. Data:\n"
            + json.dumps(compact, default=str)[:28000]
        )
        response = client.models.generate_content(model=model, contents=prompt)
        report["ai_output"] = response.text
    except Exception as exc:
        report["ai_error"] = str(exc)
        report["ai_output"] = "AI analysis unavailable; use the quantitative report."
    return report
