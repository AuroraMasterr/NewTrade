import backtrader as bt
import pandas as pd
import argparse
import os
from strategy import MyStrategy


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input_dir",
        type=str,
        required=True,
    )
    # YYYYMMDD 格式指定日期
    parser.add_argument("--start_date", type=str, default="00000000")
    parser.add_argument("--end_date", type=str, default="99999999")
    return parser.parse_args()


def get_data(input_dir, start_date, end_date):
    dfs = []
    for file in os.listdir(input_dir):
        date_str = file.split(".")[0]
        if start_date <= date_str <= end_date:
            df = pd.read_parquet(os.path.join(input_dir, file))
            dfs.append(df)
    if not dfs:
        raise ValueError("No data files found in the specified date range.")
    return (
        pd.concat(dfs)
        .sort_values("timestamp")
        .drop_duplicates("timestamp")
        .set_index("timestamp")
    )


def run_backtest(df, starting_cash):
    cerebro = bt.Cerebro()
    data = bt.feeds.PandasData(
        dataname=df,
        timeframe=bt.TimeFrame.Minutes,
        compression=60,
    )
    cerebro.adddata(data)
    cerebro.addstrategy(MyStrategy)
    cerebro.broker.setcash(starting_cash)
    print(f"初始资金: {cerebro.broker.getvalue():.2f}")
    cerebro.run()
    print(f"最终资金: {cerebro.broker.getvalue():.2f}")
    cerebro.plot()


if __name__ == "__main__":
    args = parse_args()
    df = get_data(args.input_dir, args.start_date, args.end_date)
    starting_cash = 100000
    run_backtest(df, starting_cash)
