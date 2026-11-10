import pandas as pd

def add_indicators(history: pd.DataFrame) -> pd.DataFrame:
    """Add RSI(14), SMA(50), SMA(200), and average-volume context."""
    if history is None or history.empty:
        return pd.DataFrame()
    df = history.copy().sort_index()
    close = df["Close"].astype(float)
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    df["RSI_14"] = 100 - (100 / (1 + rs))
    df.loc[(avg_loss == 0) & (avg_gain > 0), "RSI_14"] = 100
    df["SMA_50"] = close.rolling(50).mean()
    df["SMA_200"] = close.rolling(200).mean()
    if "Volume" in df:
        df["VOL_AVG_20"] = df["Volume"].rolling(20).mean()
        df["VOLUME_RATIO"] = df["Volume"] / df["VOL_AVG_20"]
    return df
