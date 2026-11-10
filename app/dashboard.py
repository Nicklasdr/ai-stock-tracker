import json, sys
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
REPORT = ROOT / "data/latest_report.json"

st.set_page_config(page_title="AI Stock Tracker", page_icon="📈", layout="wide")
st.title("📈 AI Stock Tracker")
st.caption("Portfolio monitoring and market research — informational only, not investment advice.")

if not REPORT.exists():
    st.warning("No report found yet. Run `python -m src.daily_report` from the project root.")
    st.stop()

data = json.loads(REPORT.read_text())
p = data["portfolio"]
currency = data.get("currency", "USD")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Portfolio value", f"{p['total_value']:,.2f} {currency}")
c2.metric("Unrealized P/L", f"{p['total_unrealized_pl']:,.2f} {currency}",
          f"{p['total_unrealized_pl_pct'] or 0:.2f}%")
c3.metric("Estimated daily change", f"{p['day_change']:,.2f} {currency}")
bench = p.get("benchmark_daily_pct")
c4.metric(f"{p['benchmark']} daily return", "N/A" if bench is None else f"{bench:.2f}%")
st.caption(f"Last generated: {data.get('generated_at','Unknown')}")

st.subheader("Portfolio holdings")
holdings = pd.DataFrame(p.get("holdings", []))
if not holdings.empty:
    show = [c for c in ["ticker","shares","price","market_value","unrealized_pl","unrealized_pl_pct","day_change_pct","actual_allocation_pct", "currency", "price_local"] if c in holdings]
    st.dataframe(holdings[show], use_container_width=True, hide_index=True)
else:
    st.info("No holdings configured.")

st.subheader("Technical overview")
analyses = data.get("analyses", {})
rows = []
for ticker, a in analyses.items():
    if "error" not in a:
        rows.append({k: a.get(k) for k in ["ticker","close","daily_change_pct","rsi_14","sma_50","sma_200","volume_ratio_20d","signal", "cross_signal"]})
if rows:
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.subheader("Price history")
valid = [t for t,a in analyses.items() if a.get("history")]
if valid:
    ticker = st.selectbox("Choose a ticker", valid)
    hist = pd.DataFrame(analyses[ticker]["history"])
    fig = px.line(hist, x="date", y="close", title=f"{ticker} adjusted daily close")
    st.plotly_chart(fig, use_container_width=True)

st.subheader("News")
for ticker, a in analyses.items():
    news = a.get("news", [])
    if news:
        with st.expander(f"{ticker} — {len(news)} news items"):
            for article in news:
                if article.get("error"):
                    st.caption(article["error"])
                    continue
                st.markdown(f"**[{article.get('title','Untitled')}]({article.get('url','#')})**")
                st.caption(f"{article.get('source','Unknown')} · {article.get('published_at','')}")
                if article.get("description"):
                    st.write(article["description"])

st.subheader("AI briefing")
st.write(data.get("ai_output", data.get("ai_summary", "AI summary unavailable.")))
st.caption("Signals are rule-based technical context, not recommendations. Data can be delayed or incomplete.")
