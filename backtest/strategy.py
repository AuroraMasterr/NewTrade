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
        self.order = None  # 当前主订单
        self.tp_order = None  # 止盈单
        self.sl_order = None  # 止损单

        self.entry_price = None
        self.bar_executed = None
        self.entry_dt = None
        self.entry_bar = None
        self.entry_side = None
        self.tp_price = None  # 止盈价
        self.sl_price = None  # 止损价
        self.pending_trade_logs = []

    def _cancel_exit_orders(self):
        # 撤掉止盈止损单
        for order in (self.tp_order, self.sl_order):
            if order:
                self.cancel(order)
        self.tp_order = None
        self.sl_order = None

    def _place_exit_orders(self):
        # 设置止盈止损单
        tp_move = self.p.take_profit / self.p.leverage
        sl_move = self.p.stop_loss / self.p.leverage
        size = abs(self.position.size)
        if self.position.size > 0:
            self.tp_price = self.entry_price * (1 + tp_move)
            self.sl_price = self.entry_price * (1 - sl_move)
            self.tp_order = self.sell(
                size=size,
                exectype=bt.Order.Limit,
                price=self.tp_price,
            )
            self.sl_order = self.sell(
                size=size,
                exectype=bt.Order.Stop,
                price=self.sl_price,
                oco=self.tp_order,
            )
        else:
            self.tp_price = self.entry_price * (1 - tp_move)
            self.sl_price = self.entry_price * (1 + sl_move)
            self.tp_order = self.buy(
                size=size,
                exectype=bt.Order.Limit,
                price=self.tp_price,
            )
            self.sl_order = self.buy(
                size=size,
                exectype=bt.Order.Stop,
                price=self.sl_price,
                oco=self.tp_order,
            )

    def _calc_full_size(self, price):
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

        if self.order:
            return

        o = self.data.open[0]
        h = self.data.high[0]
        l = self.data.low[0]
        c = self.data.close[0]

        if self.position:
            if len(self) - self.bar_executed >= self.p.max_hold:
                self._cancel_exit_orders()
                self.order = self.close()
                return
            return

        amplitude = h - l
        # 过滤振幅过短的信号
        if amplitude <= self.p.threshold * o:
            return

        upper_shadow = h - max(o, c)
        lower_shadow = min(o, c) - l
        size = self._calc_full_size(c)
        if size <= 0:
            return

        if upper_shadow > (2 / 3) * amplitude:
            self.order = self.sell(size=size)
        elif lower_shadow > (2 / 3) * amplitude:
            self.order = self.buy(size=size)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order == self.order:
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
                    self._place_exit_orders()
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
                logging.info(f"主订单被取消/拒绝/保证金不足: {order}")
            self.order = None
        elif order == self.tp_order or order == self.sl_order:
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
        else:
            assert False, "未知订单"

    def stop(self):
        # 如果回测结束时还没等满“后 2h”，这里强制把剩余日志打出来
        self._flush_pending_trade_logs(force=True)
