from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, Union

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

import random


class CandlestickDrawer:
    REQUIRED_KEYS = ("timestamp", "open", "high", "low", "close")

    @staticmethod
    def _setup_plot_style() -> None:
        plt.rcParams["font.sans-serif"] = ["PingFang SC", "Heiti SC", "Arial Unicode MS", "DejaVu Sans"]
        plt.rcParams["axes.unicode_minus"] = False

    @staticmethod
    def _parse_timestamp(value: Union[str, int, float, datetime]) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            if value > 1_000_000_000_000:
                value /= 1000
            return datetime.fromtimestamp(value)
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        raise TypeError("timestamp 必须是 datetime、时间戳或 ISO 时间字符串")

    @classmethod
    def _normalize_candles(cls, candles: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        if not candles:
            raise ValueError("candles 不能为空")
        rows = []
        for i, candle in enumerate(candles):
            missing = [key for key in cls.REQUIRED_KEYS if key not in candle]
            if missing:
                raise ValueError(f"第 {i} 条数据缺少字段: {', '.join(missing)}")
            op = float(candle["open"])
            hi = float(candle["high"])
            lo = float(candle["low"])
            cl = float(candle["close"])
            if hi < max(op, cl) or lo > min(op, cl) or hi < lo:
                raise ValueError(f"第 {i} 条数据的 OHLC 不合法")
            rows.append({"dt": cls._parse_timestamp(candle["timestamp"]), "open": op, "high": hi, "low": lo, "close": cl})
        rows.sort(key=lambda x: x["dt"])
        return rows

    @staticmethod
    def _calc_width(x_vals: list[float]) -> float:
        if len(x_vals) < 2:
            return 0.02
        return max(min(x_vals[i] - x_vals[i - 1] for i in range(1, len(x_vals))) * 0.7, 0.0005)

    @classmethod
    def plot(
        cls,
        candles: Sequence[Mapping[str, Any]],
        title: str = "蜡烛图",
        save_path: Optional[Union[str, Path]] = None,
        show: bool = True,
    ) -> Optional[str]:
        rows = cls._normalize_candles(candles)
        cls._setup_plot_style()

        fig, ax = plt.subplots(figsize=(14, 7))
        x_vals = [mdates.date2num(row["dt"]) for row in rows]
        width = cls._calc_width(x_vals)

        for x, row in zip(x_vals, rows):
            color = "#16a34a" if row["close"] >= row["open"] else "#dc2626"
            ax.vlines(x, row["low"], row["high"], color=color, linewidth=1)
            body_low = min(row["open"], row["close"])
            body_h = abs(row["close"] - row["open"]) or max((row["high"] - row["low"]) * 0.02, 1e-6)
            ax.add_patch(Rectangle((x - width / 2, body_low), width, body_h, facecolor=color, edgecolor=color, linewidth=1))

        ax.set_title(title)
        ax.set_xlabel("时间")
        ax.set_ylabel("价格")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
        ax.grid(alpha=0.2)
        fig.autofmt_xdate()
        plt.tight_layout()

        output = None
        if save_path:
            out = Path(save_path).expanduser()
            out.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(out, dpi=150)
            output = str(out.resolve())
        if show:
            plt.show()
        plt.close(fig)
        return output


def plot_candlestick(
    candles: Sequence[Mapping[str, Any]],
    title: str = "蜡烛图",
    save_path: Optional[Union[str, Path]] = None,
    show: bool = True,
) -> Optional[str]:
    return CandlestickDrawer.plot(candles=candles, title=title, save_path=save_path, show=show)

def make_dict():
    return {
        "timestamp": datetime.now(),
        "open": 100000+random.uniform(-100, 100),
        "low": 10000+random.uniform(-100, 100),
        "close": 10000,
    }

if __name__ == "__main__":
    klines = [make_dict() for _ in range(10)]
    plot_candlestick(klines)
