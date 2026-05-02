import backtrader as bt


class MyStrategy(bt.Strategy):
    params = dict(
        leverage=30,
        take_profit=0.25,
        stop_loss=0.10,
        max_hold=4,
        threshold=0.005,
        commission_rate=0.0001,
    )

    def __init__(self):
        self.order = None
        self.tp_order = None
        self.sl_order = None
        self.entry_price = None
        self.bar_executed = None

    def _cancel_exit_orders(self):
        # 撤掉止盈止损单
        for order in (self.tp_order, self.sl_order):
            if order:
                self.cancel(order)
        self.tp_order = None
        self.sl_order = None

    def _place_exit_orders(self):
        tp_move = self.p.take_profit / self.p.leverage
        sl_move = self.p.stop_loss / self.p.leverage
        # 设置止盈止损单
        if self.position.size > 0:
            size = self.position.size
            self.tp_order = self.sell(
                size=size,
                exectype=bt.Order.Limit,
                price=self.entry_price * (1 + tp_move),
            )
            self.sl_order = self.sell(
                size=size,
                exectype=bt.Order.Stop,
                price=self.entry_price * (1 - sl_move),
                oco=self.tp_order,
            )
        else:
            size = abs(self.position.size)
            self.tp_order = self.buy(
                size=size,
                exectype=bt.Order.Limit,
                price=self.entry_price * (1 - tp_move),
            )
            self.sl_order = self.buy(
                size=size,
                exectype=bt.Order.Stop,
                price=self.entry_price * (1 + sl_move),
                oco=self.tp_order,
            )

    def _calc_full_size(self, price):
        cash = self.broker.getcash()
        unit_cost = price * ((1 / self.p.leverage) + self.p.commission_rate)
        return cash / unit_cost if unit_cost > 0 else 0.0

    def next(self):
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
                    self.bar_executed = len(self)
                    self._place_exit_orders()
                else:
                    self.entry_price = None
                    self.bar_executed = None
            if order.status in [order.Completed, order.Canceled, order.Margin, order.Rejected]:
                self.order = None
            return

        if order == self.tp_order or order == self.sl_order:
            if order.status == order.Completed:
                self.entry_price = None
                self.bar_executed = None
                self.tp_order = None
                self.sl_order = None
            elif order.status in [order.Canceled, order.Margin, order.Rejected]:
                if order == self.tp_order:
                    self.tp_order = None
                else:
                    self.sl_order = None
