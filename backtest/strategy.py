import backtrader as bt
import logging
import numpy as np
import pandas as pd
import os
from utils.drawer import plot_with_mpf
from utils.xlsx_writer import save_tradelog_to_xlsx


class MyStrategy(bt.Strategy):
    params = dict(
        leverage=None,
        take_profit=None,
        stop_loss=None,
        max_hold=None,
        threshold=None,
        commission_rate=None,
    )

    def __init__(self):
        self.bracket_orders = None  # [主订单, 止损单, 止盈单]
        self.close_order = None  # 超时平仓订单

        self.entry_bar = None  # 开仓 K 线 index
        self.entry_side = None  # 开仓方向 "开多" / "开空"
        self.entry_price = None  # 开仓价格
        self.entry_dt = None  # 开仓时间
        self.pinbar_amplitude = None  # 开仓信号振幅

        self.tp_price = None  # 止盈价
        self.sl_price = None  # 止损价

        self.trade_logs = []  # 日志

    def add_log(self, exit_dt, exit_price, exit_bar):
        self.trade_logs.append(
            {
                "side": self.entry_side,
                "entry_dt": self.entry_dt,
                "entry_price": self.entry_price,
                "start_bar": self.entry_bar,
                "exit_dt": exit_dt,
                "exit_price": exit_price,
                "exit_bar": exit_bar,
                "tp_price": self.tp_price,
                "sl_price": self.sl_price,
                "pinbar_amplitude": self.pinbar_amplitude,
                "leverage": self.p.leverage,
            }
        )

    def close_timeout(self):
        # 超时平仓
        if self.position and len(self) - self.entry_bar >= self.p.max_hold:
            for order in self.bracket_orders:
                if order and order.alive():
                    self.cancel(order)
            self.bracket_orders = None
            self.close_order = self.close()

    def open_position(self, price, is_buy, amplitude):
        # 开仓
        if self.position:
            return
        size = self.calc_full_size(price)
        if size <= 0:
            return
        if is_buy:
            self.tp_price = price * (1 + self.p.take_profit)
            self.sl_price = price * (1 - self.p.stop_loss)
            self.bracket_orders = self.buy_bracket(
                size=size,
                limitprice=self.tp_price,
                stopprice=self.sl_price,
            )
        else:
            self.tp_price = price * (1 - self.p.take_profit)
            self.sl_price = price * (1 + self.p.stop_loss)
            self.bracket_orders = self.sell_bracket(
                size=size,
                limitprice=self.tp_price,
                stopprice=self.sl_price,
            )
        self.entry_bar = len(self)
        self.entry_side = "开多" if is_buy else "开空"
        self.pinbar_amplitude = amplitude

    def calc_full_size(self, price):
        cash = self.broker.getcash() * 0.999
        unit_cost = price * (1 + self.p.commission_rate)
        return cash / unit_cost if unit_cost > 0 else 0.0

    def _format_dt(self, ago=0):
        return bt.num2date(self.data.datetime[ago]).strftime("%Y-%m-%d %H:%M:%S")

    def _get_bar_text(self, target_bar):
        # target_bar 用 len(self) 口径记录，转换成相对当前位置的 ago 后读取历史K线
        ago = target_bar - len(self)
        return (
            f"{self._format_dt(ago)} "
            f"O={self.data.open[ago]:.2f} H={self.data.high[ago]:.2f} "
            f"L={self.data.low[ago]:.2f} C={self.data.close[ago]:.2f}"
        )

    def _print_trade_log(self, trade_log):
        print("=" * 80)
        print(
            f"方向: {trade_log['side']} | 开仓时间: {trade_log['entry_dt']} | 开仓价格: {trade_log['entry_price']:.2f} | "
            f"平仓时间: {trade_log['exit_dt']} | 平仓价格: {trade_log['exit_price']:.2f}"
        )
        print(
            f"止盈线: {trade_log['tp_price']:.2f} | 止损线: {trade_log['sl_price']:.2f}"
        )
        print("交易区间 K线:")
        for bar_no in range(trade_log["start_bar"], trade_log["exit_bar"] + 1):
            print(self._get_bar_text(bar_no))

    def draw_graph(self, trade_log):
        klines = []
        for bar_no in range(
            max(1, trade_log["start_bar"] - 7), trade_log["exit_bar"] + 1
        ):
            ago = bar_no - len(self)
            kline = {
                "Open": self.data.open[ago],
                "High": self.data.high[ago],
                "Low": self.data.low[ago],
                "Close": self.data.close[ago],
                "buy": (
                    trade_log["entry_price"]
                    if bar_no == trade_log["start_bar"]
                    else np.nan
                ),
                "sell": (
                    trade_log["exit_price"]
                    if bar_no == trade_log["exit_bar"]
                    else np.nan
                ),
            }
            if bar_no == trade_log["start_bar"]:
                print(
                    "entry_price=",
                    trade_log["entry_price"],
                    "close_on_entry_bar=",
                    self.data.close[ago],
                )
            klines.append(kline)
        df = pd.DataFrame(klines)
        df.index = pd.date_range(
            start=trade_log["entry_dt"], periods=len(df), freq="1h"
        )
        file = os.path.join(
            "pictures", f"chart_{trade_log['entry_dt'].replace(' ', '_')}.png"
        )
        plot_with_mpf(df, f"BTC/USDT 1h candle chart", file)

    def next(self):
        self.close_timeout()

        if self.bracket_orders:
            return

        o = self.data.open[0]
        h = self.data.high[0]
        l = self.data.low[0]
        c = self.data.close[0]

        amplitude = h - l
        # 过滤振幅过短的信号
        if amplitude <= self.p.threshold * o:
            return

        upper_shadow = h - max(o, c)
        lower_shadow = min(o, c) - l
        if upper_shadow > (2 / 3) * amplitude:
            # 上影线长，开空
            self.open_position(price=c, is_buy=False, amplitude=amplitude)
        elif lower_shadow > (2 / 3) * amplitude:
            # 下影线长，开多
            self.open_position(price=c, is_buy=True, amplitude=amplitude)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        entry_order, sl_order, tp_order = (
            self.bracket_orders if self.bracket_orders else (None, None, None)
        )

        if order == entry_order:
            # 开仓单
            if order.status == order.Completed:
                assert self.position, "主订单成交但没有持仓了？"
                self.entry_dt = self._format_dt()
                self.entry_price = order.executed.price
                print(
                    f"开仓成交: side={self.entry_side}, time={self.entry_dt}, price={self.entry_price:.2f}, size={order.executed.size:.6f}"
                )
            else:
                logging.error(f"主订单被取消/拒绝/保证金不足: {order}")
        elif order == tp_order or order == sl_order:
            # 止盈/止损单
            order_type = "止盈单" if order == tp_order else "止损单"
            if order.status == order.Completed:
                exit_dt = self._format_dt()
                exit_bar = len(self)
                exit_price = order.executed.price
                print(
                    f"{order_type}成交: time={exit_dt}, price={order.executed.price:.2f}, size={order.executed.size:.6f}"
                )
                self.add_log(exit_dt, exit_price, exit_bar)
                self.bracket_orders = None
            elif order.status == order.Canceled:
                logging.info(f"{order_type}被取消: {order}")
            else:
                logging.error(f"{order_type}被拒绝/保证金不足: {order}")
        elif order == self.close_order:
            # 超时平仓单
            exit_dt = self._format_dt()
            exit_bar = len(self)
            exit_price = order.executed.price
            print(
                f"超时平仓成交: time={exit_dt}, price={order.executed.price:.2f}, size={order.executed.size:.6f}"
            )
            self.add_log(exit_dt, exit_price, exit_bar)
            self.entry_price = None
            self.entry_dt = None
            self.entry_bar = None
            self.entry_side = None
            self.tp_price = None
            self.sl_price = None
        elif order.status == order.Canceled:
            logging.info(f"oco订单被取消: {order}")
        else:
            logging.warning(f"未知订单: {order}")

    def stop(self):
        xlsx_file = "backtest_result.xlsx"
        if os.path.exists(xlsx_file):
            os.remove(xlsx_file)
        for trade_log in self.trade_logs:
            self._print_trade_log(trade_log)
            self.draw_graph(trade_log)
            save_tradelog_to_xlsx(trade_log, xlsx_file, "BTC/USDT 1h")
