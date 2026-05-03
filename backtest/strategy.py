import backtrader as bt
import logging


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
        self.order = None                   # 主订单
        self.bracket_orders = None          # [主订单, 止盈单, 止损单]
        self.close_order = None             # 超时平仓订单

        self.entry_bar = None               # 开仓 K 线 index
        self.entry_side = None              # 开仓方向 "开多" / "开空"
        self.entry_price = None
        
        self.bar_executed = None
        self.entry_dt = None
        self.tp_price = None  # 止盈价
        self.sl_price = None  # 止损价
        self.pending_trade_logs = []

    def close_timeout(self):
        # 超时平仓
        if self.position and len(self) - self.bar_executed >= self.p.max_hold:
            for order in self.bracket_orders:
                if order and order.alive():
                    self.cancel(order)
            self.bracket_orders = None
            self.close_order = self.close()

    def open_position(self, price, is_buy):
        # 开仓
        if self.position:
            return
        size = self._calc_full_size(price)
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


    def calc_full_size(self, price):
        cash = self.broker.getcash() * 0.999
        unit_cost = price * ((1 / self.p.leverage) + self.p.commission_rate)
        return cash / unit_cost if unit_cost > 0 else 0.0

    def _format_dt(self, ago=0):
        # Backtrader 的 datetime 需要手动转成 Python datetime 才好打印
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
        print("交易区间前后2h K线:")
        for bar_no in range(trade_log["start_bar"], trade_log["end_bar"] + 1):
            print(self._get_bar_text(bar_no))

    def _flush_pending_trade_logs(self, force=False):
        # 平仓后要等 2 根 1h K 线走完，才能拿到“后 2h”的K线
        remaining_logs = []
        for trade_log in self.pending_trade_logs:
            if force or len(self) >= trade_log["end_bar"]:
                self._print_trade_log(trade_log)
            else:
                remaining_logs.append(trade_log)
        self.pending_trade_logs = remaining_logs

    def next(self):
        self._flush_pending_trade_logs()

        if self.bracket_orders:
            return

        o = self.data.open[0]
        h = self.data.high[0]
        l = self.data.low[0]
        c = self.data.close[0]

        self.close_timeout()

        amplitude = h - l
        # 过滤振幅过短的信号
        if amplitude <= self.p.threshold * o:
            return

        size = self.calc_full_size(c)
        if size <= 0:
            return

        upper_shadow = h - max(o, c)
        lower_shadow = min(o, c) - l
        if upper_shadow > (2 / 3) * amplitude:
            # 上影线长，开空
            self.open_position(price=c, is_buy=False)
        elif lower_shadow > (2 / 3) * amplitude:
            # 下影线长，开多
            self.open_position(price=c, is_buy=True)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        entry_order, sl_order, tp_order = self.bracket_orders if self.bracket_orders else (None, None, None)

        if order == entry_order:
            if order.status == order.Completed:
                if self.position:
                    self.entry_price = order.executed.price
                    self.bar_executed = len(self) - 1
                    self.entry_dt = self._format_dt(ago=-1)
                    self.entry_bar = len(self) - 1
                    self.entry_side = "开多" if order.isbuy() else "开空"
                    print(
                        f"开仓成交: side={self.entry_side}, time={self.entry_dt}, price={self.entry_price:.2f}, size={order.executed.size:.6f}"
                    )
                else:
                    exit_dt = self._format_dt(ago=-1)
                    exit_bar = len(self) - 1
                    print(
                        f"平仓成交: time={exit_dt}, price={order.executed.price:.2f}, size={order.executed.size:.6f}"
                    )
                    self.pending_trade_logs.append(
                        {
                            "side": self.entry_side,
                            "entry_dt": self.entry_dt,
                            "entry_price": self.entry_price,
                            "exit_dt": exit_dt,
                            "exit_price": order.executed.price,
                            "tp_price": self.tp_price,
                            "sl_price": self.sl_price,
                            "start_bar": max(1, self.entry_bar - 2),
                            "end_bar": exit_bar + 2,
                        }
                    )
                    self.entry_price = None
                    self.bar_executed = None
                    self.entry_dt = None
                    self.entry_bar = None
                    self.entry_side = None
                    self.tp_price = None
                    self.sl_price = None
            if order.status in [order.Canceled, order.Margin, order.Rejected]:
                logging.error(f"主订单被取消/拒绝/保证金不足: {order}")
        elif order == tp_order or order == sl_order:
            if order.status == order.Completed:
                exit_dt = self._format_dt()
                exit_bar = len(self)
                print(
                    f"平仓成交: time={exit_dt}, price={order.executed.price:.2f}, size={order.executed.size:.6f}"
                )
                self.pending_trade_logs.append(
                    {
                        "side": self.entry_side,
                        "entry_dt": self.entry_dt,
                        "entry_price": self.entry_price,
                        "exit_dt": exit_dt,
                        "exit_price": order.executed.price,
                        "tp_price": self.tp_price,
                        "sl_price": self.sl_price,
                        "start_bar": max(1, self.entry_bar - 2),
                        "end_bar": exit_bar + 2,
                    }
                )
                self.entry_price = None
                self.bar_executed = None
                self.entry_dt = None
                self.entry_bar = None
                self.entry_side = None
                self.tp_price = None
                self.sl_price = None
                self.tp_order = None
                self.sl_order = None
            elif order.status in [order.Canceled, order.Margin, order.Rejected]:
                if order == self.tp_order:
                    self.tp_order = None
                    logging.info(f"止盈单被取消/拒绝/保证金不足: {order}")
                else:
                    self.sl_order = None
                    logging.info(f"止损单被取消/拒绝/保证金不足: {order}")
        elif order == self.close_order:
            pass
        else:
            assert False, "未知订单"

    def stop(self):
        # 如果回测结束时还没等满“后 2h”，这里强制把剩余日志打出来
        self._flush_pending_trade_logs(force=True)
