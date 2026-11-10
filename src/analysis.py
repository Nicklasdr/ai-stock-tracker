from __future__ import annotations

import math

from .indicators import add_indicators
from .market_data import get_currency, get_fx, get_history, get_news


def _num(value):
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def _cross_state(df, lookback: int = 10):
    """'golden_cross' / 'death_cross' if SMA50 crossed SMA200 in the last `lookback` bars."""
    if "SMA_50" not in df or "SMA_200" not in df:
        return None
    diff = (df["SMA_50"] - df["SMA_200"]).dropna().tail(lookback + 1)
    if len(diff) < 2:
        return None
    if diff.iloc[0] < 0 < diff.iloc[-1]:
        return "golden_cross"
    if diff.iloc[0] > 0 > diff.iloc[-1]:
        return "death_cross"
    return None


def analyze_ticker(ticker: str, name: str | None = None):
    """`name` (company name) improves news search; optional, old call style still works."""
    raw = get_history(ticker)
    if raw is None or raw.empty or len(raw) < 2:
        return {"ticker": ticker, "error": "Insufficient price history",
                "news": get_news(ticker, query=name)}
    df = add_indicators(raw)
    last, prev = df.iloc[-1], df.iloc[-2]
    close, prior = _num(last["Close"]), _num(prev["Close"])
    daily_pct = ((close / prior) - 1) * 100 if close and prior else None
    rsi = _num(last.get("RSI_14"))
    sma50, sma200 = _num(last.get("SMA_50")), _num(last.get("SMA_200"))
    vol_ratio = _num(last.get("VOLUME_RATIO"))
    cross = _cross_state(df)

    tags = []
    if rsi is not None:
        tags.append("RSI overbought zone" if rsi > 70 else "RSI oversold zone" if rsi < 30 else "RSI neutral zone")
    if sma50 and sma200:
        tags.append("50-day above 200-day" if sma50 > sma200 else "50-day below 200-day")
    if close and sma50:
        tags.append("Above 50-day SMA" if close > sma50 else "Below 50-day SMA")
    if cross == "golden_cross":
        tags.append("Golden cross in last 10 days")
    elif cross == "death_cross":
        tags.append("Death cross in last 10 days")

    if rsi is not None and rsi < 30 and close and sma50 and close > sma50:
        signal = "Bullish watch"
    elif rsi is not None and rsi > 70 and close and sma50 and close < sma50:
        signal = "Caution"
    elif cross == "death_cross" or (close and sma50 and sma200 and close < sma50 < sma200):
        signal = "Bearish"
    elif cross == "golden_cross" or (close and sma50 and sma200 and close > sma50 > sma200):
        signal = "Positive trend"
    elif close and sma50 and close < sma50:
        signal = "Trend caution"
    else:
        signal = "Neutral / monitor"

    return {
        "ticker": ticker, "date": str(df.index[-1].date()),
        "currency": get_currency(ticker), "close": close,
        "previous_close": prior, "daily_change_pct": daily_pct,
        "rsi_14": rsi, "sma_50": sma50, "sma_200": sma200,
        "volume": _num(last.get("Volume")), "volume_ratio_20d": vol_ratio,
        "cross_signal": cross, "signal": signal, "technical_context": tags,
        "news": get_news(ticker, query=name),
        # For the dashboard only: strip before sending the dict to the LLM prompt.
        "history": [{"date": str(idx.date()), "close": _num(row["Close"])}
                    for idx, row in df.tail(260).iterrows()],
    }


def build_portfolio(config: dict, analyses: dict):
    """All values in config['currency'] (default USD). cost_basis_per_share is
    assumed to already be in that base currency."""
    base = config.get("currency", "USD")
    rows, skipped = [], []
    total_value = total_cost = day_change = 0.0
    for holding in config.get("holdings", []):
        ticker = holding["ticker"].upper()
        item = analyses.get(ticker, {})
        shares = float(holding.get("shares", 0))
        cost = float(holding.get("cost_basis_per_share", 0))
        price, prev = item.get("close"), item.get("previous_close")
        rate = get_fx(item.get("currency"), base)
        if price is None or rate is None:
            skipped.append(ticker)
            rows.append({"ticker": ticker, "shares": shares,
                         "error": item.get("error", "No price or FX rate")})
            continue
        fx_now, fx_prev = rate
        value, invested = price * fx_now * shares, cost * shares
        change = value - prev * fx_prev * shares if prev is not None else 0.0
        total_value += value
        total_cost += invested
        day_change += change
        rows.append({
            "ticker": ticker, "shares": shares, "currency": item.get("currency"),
            "price_local": price, "price": price * fx_now,
            "market_value": value, "cost_basis": invested,
            "unrealized_pl": value - invested,
            "unrealized_pl_pct": ((value / invested) - 1) * 100 if invested else None,
            "day_change": change, "day_change_pct": item.get("daily_change_pct"),
            "target_allocation_pct": holding.get("target_allocation_pct"),
            "actual_allocation_pct": None,
        })
    for row in rows:
        if row.get("market_value") is not None and total_value:
            row["actual_allocation_pct"] = row["market_value"] / total_value * 100
    benchmark = analyses.get(config.get("benchmark", "SPY"), {})
    return {
        "base_currency": base, "skipped": skipped,
        "holdings": rows, "total_value": total_value, "total_cost": total_cost,
        "total_unrealized_pl": total_value - total_cost,
        "total_unrealized_pl_pct": ((total_value / total_cost) - 1) * 100 if total_cost else None,
        "day_change": day_change,
        "day_change_pct_estimate": day_change / (total_value - day_change) * 100 if total_value != day_change else None,
        "benchmark": config.get("benchmark", "SPY"),
        "benchmark_daily_pct": benchmark.get("daily_change_pct"),
    }
