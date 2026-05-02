import backtrader as bt


class MyStrategy(bt.Strategy):
    params = dict(
        leverage=30,
        take_profit=0.30,  # 30%
        stop_loss=0.10,  # 10%
        max_hold=4,  # 4根K线（1h → 4小时）
    )

    def __init__(self):
        self.order = None
        self.entry_price = None
        self.bar_executed = None
        self.threshold = 0.005  # 0.5% 振幅阈值, 忽略小于阈值的K线

    def next(self):
        # 如果有挂单，跳过
        if self.order:
            return

        o = self.data.open[0]
        h = self.data.high[0]
        l = self.data.low[0]
        c = self.data.close[0]

        # === 计算指标 ===
        amplitude = h - l
        if amplitude <= self.threshold * o:  # 振幅过小，跳过
            return

        upper_shadow = h - max(o, c)
        lower_shadow = min(o, c) - l

        # === 已持仓：检查止盈止损 + 持仓时间 ===
        if self.position:
            pnl = ((c - self.entry_price) / self.entry_price) * self.p.leverage

            # 多单
            if self.position.size > 0:
                if pnl >= self.p.take_profit or pnl <= -self.p.stop_loss:
                    self.close()
                    return

            # 空单
            else:
                pnl = (self.entry_price - c) / self.entry_price
                if pnl >= self.p.take_profit or pnl <= -self.p.stop_loss:
                    self.close()
                    return

            # 超时强平
            if len(self) - self.bar_executed >= self.p.max_hold:
                self.close()
                return

            return

        # === 无持仓：开仓信号 ===

        # 做空信号
        if upper_shadow > (2 / 3) * amplitude:
            self.order = self.sell()
            self.entry_price = c
            self.bar_executed = len(self)

        # 做多信号
        elif lower_shadow > (2 / 3) * amplitude:
            self.order = self.buy()
            self.entry_price = c
            self.bar_executed = len(self)

    def notify_order(self, order):
        if order.status in [order.Completed, order.Canceled, order.Margin]:
            self.order = None
