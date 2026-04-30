import argparse
import pandas as pd
import os
import zipfile

COLUMNS = [
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "trades",  # 成交笔数
    "taker_buy_base",  # 买方吃单量
    "taker_buy_quote",  # 买方吃单成交额
    "ignore",
]
# trades, taker_buy_base, taker_buy_quote, ignore 先删掉，在需要情绪分析时再用
USE_COLS = ["timestamp", "open", "high", "low", "close", "volume"]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", type=str, required=True)
    parser.add_argument("--output_dir", type=str, required=True)
    return parser.parse_args()


def clean_data(input_file, output_dir):
    with zipfile.ZipFile(input_file, "r") as z:
        csv_name = z.namelist()[0]
        with z.open(csv_name) as f:
            df = pd.read_csv(f, names=COLUMNS)
    df = df[USE_COLS]
    # 有的文件有表头，有的没有，所以统一过滤掉表头行（如果存在的话）
    df = df[df["timestamp"] != "open_time"]
    df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype("float32")
    df = df.sort_values("timestamp").drop_duplicates("timestamp")  # 排序 + 去重

    filename = os.path.basename(input_file)
    date_str = filename.split("-")[-3:]
    date_fmt = "".join(date_str).replace(".zip", "")

    year = date_fmt[:4]
    output_dir = os.path.join(output_dir, year)
    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(output_dir, f"{date_fmt}.parquet")
    df.to_parquet(output_file, index=False)
    print(f"Cleaned data saved to {output_file}")


if __name__ == "__main__":
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    for file in os.listdir(args.input_dir):
        clean_data(os.path.join(args.input_dir, file), args.output_dir)
