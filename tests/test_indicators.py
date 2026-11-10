import pandas as pd
from src.indicators import add_indicators

def test_sma_50():
    idx = pd.date_range("2024-01-01", periods=60, freq="D")
    df = pd.DataFrame({"Close": range(1, 61), "Volume": [100] * 60}, index=idx)
    out = add_indicators(df)
    assert round(out["SMA_50"].iloc[-1], 6) == 35.5
    assert pd.isna(out["SMA_200"].iloc[-1])
