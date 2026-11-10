import json, os
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from .analysis import analyze_ticker, build_portfolio
from .ai_advisor import enrich_with_ai
from .notifications import send_telegram

ROOT = Path(__file__).resolve().parents[1]

def run():
    load_dotenv(ROOT / ".env")
    config = json.loads((ROOT / "config/portfolio.json").read_text())
    tickers = sorted(set(
        [h["ticker"].upper() for h in config.get("holdings", [])]
        + [t.upper() for t in config.get("watchlist", [])]
        + [config.get("benchmark", "SPY").upper()]
    ))
    analyses = {ticker: analyze_ticker(ticker) for ticker in tickers}
    portfolio = build_portfolio(config, analyses)
    report = {
        "generated_at": datetime.now(ZoneInfo("America/New_York")).isoformat(),
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
    lines = [
        f"{report['portfolio_name']} — Daily market digest",
        f"Generated: {report['generated_at']}",
        f"Portfolio value: {portfolio['total_value']:,.2f} {report['currency']}",
        f"Unrealized P/L: {portfolio['total_unrealized_pl']:,.2f} ({portfolio['total_unrealized_pl_pct'] or 0:.2f}%)",
        f"Estimated daily change: {portfolio['day_change']:,.2f} {report['currency']}",
        f"Benchmark {portfolio['benchmark']} daily: {portfolio['benchmark_daily_pct'] if portfolio['benchmark_daily_pct'] is not None else 'N/A'}%",
        "",
        "HOLDINGS",
    ]
    for row in portfolio["holdings"]:
        if row.get("error"):
            lines.append(f"{row['ticker']}: {row['error']}")
        else:
            lines.append(f"{row['ticker']}: {row['price']:.2f} | P/L {row['unrealized_pl']:.2f} ({row['unrealized_pl_pct'] or 0:.2f}%) | day {row['day_change_pct'] if row['day_change_pct'] is not None else 'N/A'}%")
    lines += ["", "WATCHLIST"]
    for ticker in report["watchlist"]:
        item = analyses.get(ticker.upper(), {})
        lines.append(f"{ticker}: {item.get('signal', item.get('error', 'No data'))}")
    lines += ["", str(report.get("ai_output", report.get("ai_summary", "")))]
    send_telegram("\n".join(lines))
    print(f"Report saved to {out / 'latest_report.json'}")
    return report

if __name__ == "__main__":
    run()
