import pandas as pd
import numpy as np
import mplfinance as mpf
import datetime

data = [
    {"Open": 100, "High": 110, "Low": 90, "Close": 105},
    {"Open": 105, "High": 120, "Low": 100, "Close": 115},
    {"Open": 115, "High": 118, "Low": 108, "Close": 110},
    {"Open": 110, "High": 120, "Low": 105, "Close": 115},
    {"Open": 115, "High": 125, "Low": 110, "Close": 120},
]

def get_timestamp():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def plot_with_mpf(data):
    df = pd.DataFrame(data)
    df.index = pd.date_range(start="2026-02-03 00:00:00", periods=len(df), freq="1h")

    df["buy"] = np.nan
    df["sell"] = np.nan

    df.loc[df.index[0], "buy"] = 100
    df.loc[df.index[2], "sell"] = 110

    apds = [
        mpf.make_addplot(
            df["buy"], type="scatter", marker="^", color="lime", edgecolors="black", markersize=200, linewidths=1.5
        ),
        mpf.make_addplot(
            df["sell"], type="scatter", marker="v", color="red", edgecolors="black", markersize=200, linewidths=1.5
        ),
    ]

    title = "BTC/USDT 1h candle chart"
    mpf.plot(
        df,
        type="candle",
        style="charles",
        addplot=apds,
        datetime_format="%m-%d %H:%M",
        xrotation=30,
        title=title,
        savefig=dict(
            fname=f"chart_{get_timestamp()}.png",
            dpi=150,
            bbox_inches="tight"
        ),
    )


if __name__ == "__main__":
    plot_with_mpf(data)
