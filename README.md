# AI Stock Tracker & Advisory Dashboard

A configurable, educational portfolio-monitoring project with:
- Portfolio P&L and benchmark comparison
- RSI(14), SMA(50), SMA(200), and volume context
- Recent company news with optional Gemini summaries/sentiment
- A Streamlit dashboard
- Weekday GitHub Actions digest delivery to Telegram
- No brokerage connection and no automatic trading

> **Important:** Signals are informational, not personalized investment advice. The discovery module is a watchlist-ranking prototype, not a promise of returns or a buy/sell instruction. Verify prices, corporate actions, and news with primary sources before making decisions.

## 1. Quick start

### Requirements
- Python 3.11+
- API keys (see below)
- Telegram bot + chat ID for scheduled notifications (optional)

### Local setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and `config/portfolio.json`, then run:

```bash
python -m src.daily_report
streamlit run app/dashboard.py
```

The first run downloads market history using `yfinance`. This is convenient for prototyping but is not an exchange-authorized data feed and may be delayed, incomplete, rate-limited, or change without notice. For production use, replace `src/market_data.py` with a licensed provider adapter.

## 2. Configuration

`config/portfolio.json` contains holdings, watchlist symbols, benchmark, and strategy profile. Quantities and cost basis are examples only; replace them with your own values. Use ticker symbols supported by the data provider (for example `MSFT`, `AAPL`, `SPY`).

The application calculates market value as latest close × shares and unrealized P&L as market value − cost basis × shares. For multiple tax lots, add lots separately or extend the schema.

## 3. API keys

| Variable | Required? | Purpose |
|---|---:|---|
| `GEMINI_API_KEY` | No | Optional AI-generated narrative and news sentiment |
| `GEMINI_MODEL` | No | Defaults to `gemini-2.5-flash` |
| `TELEGRAM_BOT_TOKEN` | No | Telegram digest delivery |
| `TELEGRAM_CHAT_ID` | No | Telegram destination |
| `NEWS_API_KEY` | No | Optional NewsAPI headlines |
| `NEWS_API_BASE_URL` | No | Defaults to NewsAPI |
| `DATA_PERIOD` | No | History period; defaults to `1y` |

Without Gemini, the report uses deterministic summaries and rules-based labels. Without NewsAPI, it still produces technical and portfolio analysis.

## 4. Dashboard

Run `streamlit run app/dashboard.py`. The dashboard reads `data/latest_report.json`; run the daily report once first. You can deploy the dashboard to Streamlit Community Cloud by pointing it at this repository and adding secrets as environment variables. Keep the repository private if you ever add non-public configuration; never commit `.env` or real account data.

## 5. GitHub Actions scheduling

The workflow checks twice each weekday, at 20:30 and 21:30 UTC. A timezone-aware guard runs the report only when New York time is approximately 16:30. This covers both US daylight-saving regimes while keeping the requested 4:30 PM Eastern schedule. GitHub scheduled jobs can start late, so this is best-effort rather than an exact-time guarantee.

Add these GitHub repository secrets:
- `GEMINI_API_KEY` (optional)
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `NEWS_API_KEY` (optional)

Edit `config/portfolio.json` in the repository to change holdings and watchlist.

## 6. Data and calculation notes

- RSI uses Wilder-style exponential smoothing via `ewm(alpha=1/14)`.
- SMAs are simple rolling means over 50 and 200 daily closes.
- Daily return is measured against the previous available close.
- Portfolio day change is estimated from held share quantities and daily price changes. Deposits, withdrawals, dividends, fees, FX conversion, splits, and tax are not included.
- Benchmark comparison uses the benchmark's daily percentage return, not a currency-adjusted portfolio benchmark.
- NewsAPI coverage and availability depend on its plan and licensing.
- `yfinance` data is for personal research/prototyping; review the provider's terms and use a licensed feed for production.

## 7. Safety and reliability

- No credentials are stored in source code.
- No order placement, brokerage login, or auto-trading.
- Missing data is reported rather than silently treated as zero.
- AI output is constrained to explain supplied data and flag uncertainty; it must not invent prices or sources.
- Always cross-check critical information with company filings, exchange notices, and reputable financial publishers.

## 8. Project layout

```text
app/dashboard.py              Streamlit dashboard
src/market_data.py             Historical prices and news ingestion
src/indicators.py              RSI and moving averages
src/analysis.py                Portfolio metrics and signal labels
src/ai_advisor.py              Optional Gemini narrative/sentiment
src/notifications.py           Telegram delivery
src/daily_report.py            End-to-end report runner
config/portfolio.json          Portfolio and watchlist configuration
.github/workflows/daily.yml    Weekday scheduled job
tests/                          Indicator tests
```
