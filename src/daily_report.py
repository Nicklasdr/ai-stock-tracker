import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from .ai_advisor import enrich_with_ai
from .analysis import analyze_ticker, build_portfolio
from .notifications import send_telegram

ROOT = Path(__file__).resolve().parents[1]


def _f(x, nd=2, signed=False):
    if x is None:
        return "N/A"
    return f"{x:+,.{nd}f}" if signed else f"{x:,.{nd}f}"


def run():
    load_dotenv(ROOT / ".env")
    config = json.loads((ROOT / "config/portfolio.json").read_text())
    names = {k.upper(): v for k, v in config.get("names", {}).items()}
    bench = config.get("benchmark", "SPY").upper()
    tickers = sorted(set(
        [h["ticker"].upper() for h in config.get("holdings", [])]
        + [t.upper() for t in config.get("watchlist", [])]
        + [bench]
    ))
    analyses = {t: analyze_ticker(t, name=names.get(t)) for t in tickers}
    portfolio = build_portfolio(config, analyses)
    now = datetime.now(ZoneInfo("America/New_York"))
    report = {
        "generated_at": now.isoformat(),
        "portfolio_name": config.get("portfolio_name", "Portfolio"),
        "currency": config.get("currency", "USD"),
        "portfolio": portfolio,
        "analyses": analyses,
        "watchlist": config.get("watchlist", []),
        "strategy_profile": config.get("strategy_profile", "balanced"),
    }
    report = enrich_with_ai(report)
    out = ROOT / "data"
    out.mkdir(exist_ok=True)
    (out / "latest_report.json").write_text(json.dumps(report, indent=2, default=str))

    cur = report["currency"]
    bench_date = analyses.get(bench, {}).get("date")
    lines = [f"{report['portfolio_name']} - Daily market digest", f"Generated: {report['generated_at']}"]
    if bench_date and bench_date != now.date().isoformat():
        lines.append(f"WARNING: latest {bench} bar is {bench_date}, not today (market holiday or delayed data).")
    lines += [
        f"Portfolio value: {_f(portfolio['total_value'])} {cur}",
        f"Unrealized P/L: {_f(portfolio['total_unrealized_pl'], signed=True)} {cur} "
        f"({_f(portfolio['total_unrealized_pl_pct'], signed=True)}%)",
        f"Estimated daily change: {_f(portfolio['day_change'], signed=True)} {cur} "
        f"({_f(portfolio['day_change_pct_estimate'], signed=True)}%)",
        f"Benchmark {portfolio['benchmark']} daily: {_f(portfolio['benchmark_daily_pct'], signed=True)}%",
    ]
    if portfolio.get("skipped"):
        lines.append("WARNING: excluded from totals (no price/FX): " + ", ".join(portfolio["skipped"]))
    lines += ["", "AI SUMMARY", str(report.get("ai_output", report.get("ai_summary", ""))), "", "HOLDINGS"]
    for row in portfolio["holdings"]:
        if row.get("error"):
            lines.append(f"{row['ticker']}: {row['error']}")
        else:
            lines.append(
                f"{row['ticker']}: {_f(row['price_local'])} {row['currency']} | value {_f(row['market_value'], 0)} {cur} | "
                f"P/L {_f(row['unrealized_pl'], 0, True)} ({_f(row['unrealized_pl_pct'], 1, True)}%) | "
                f"day {_f(row['day_change_pct'], 2, True)}% | {analyses[row['ticker']].get('signal', '')}"
            )
    lines += ["", "WATCHLIST"]
    for ticker in report["watchlist"]:
        item = analyses.get(ticker.upper(), {})
        lines.append(f"{ticker}: {item.get('signal', item.get('error', 'No data'))}")
    send_telegram("\n".join(lines))
    print(f"Report saved to {out / 'latest_report.json'}")
    return report


if __name__ == "__main__":
    run()
