import os
import pandas as pd
import numpy as np
import mplfinance as mpf
import datetime

data = [
    {"Open": 100, "High": 110, "Low": 90, "Close": 105, "buy": np.nan, "sell": np.nan},
    {"Open": 105, "High": 120, "Low": 100, "Close": 115, "buy": np.nan, "sell": np.nan},
    {"Open": 115, "High": 118, "Low": 108, "Close": 110, "buy": np.nan, "sell": np.nan},
    {"Open": 110, "High": 120, "Low": 105, "Close": 115, "buy": np.nan, "sell": np.nan},
    {"Open": 115, "High": 125, "Low": 110, "Close": 120, "buy": np.nan, "sell": np.nan},
]


def get_timestamp():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def plot_with_mpf(df, title, file_name, profit_pct):
    df["buy"] = df["buy"] * 0.9998  # 视觉调整，使三角更贴线
    df["sell"] = df["sell"] * 1.0002
    apds = [
        mpf.make_addplot(
            df["buy"],
            type="scatter",
            marker="^",
            color="lime",
            edgecolors="black",
            markersize=100,
            linewidths=1.5,
        ),
        mpf.make_addplot(
            df["sell"],
            type="scatter",
            marker="v",
            color="red",
            edgecolors="black",
            markersize=100,
            linewidths=1.5,
        ),
    ]
    # classic style 也好看
    fig, axes = mpf.plot(
        df,
        type="candle",
        style="charles",
        addplot=apds,
        datetime_format="%m-%d %H:%M",
        xrotation=30,
        title=title,
        returnfig=True,
    )

    sign = "+" if profit_pct >= 0 else ""
    axes[0].text(
        1,
        1.1,
        f"{sign}{100 * profit_pct:.2f}%",
        transform=axes[0].transAxes,
        ha="right",
        va="top",
        fontsize=20,
        fontweight="bold",
        color="green" if profit_pct >= 0 else "red",
        zorder=20,
    )

    fig.savefig(file_name, dpi=150, bbox_inches="tight")


if __name__ == "__main__":
    df = pd.DataFrame(data)
    df.index = pd.date_range(start="2026-02-03 00:00:00", periods=len(df), freq="1h")
    df["buy"] = np.nan
    df["sell"] = np.nan
    df.loc[df.index[0], "buy"] = 100
    df.loc[df.index[2], "sell"] = 110
    file = os.path.join("pictures", f"chart_{get_timestamp()}.png")

    plot_with_mpf(df, "BTC/USDT 1h candle chart", file, 0.2888)
