import os
import requests
import argparse
from datetime import datetime
from tqdm import tqdm

# Binance
BASE_URL = "https://data.binance.vision/data/spot/monthly/klines"


def download(url, file):
    filename = os.path.basename(file)
    response = requests.get(url, stream=True)
    response.raise_for_status()
    total_size = int(response.headers.get("content-length", 0))
    with open(file, "wb") as f, tqdm(
        desc=filename,
        total=total_size,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
                bar.update(len(chunk))
    print(f"✓ Completed: {filename}")


def binance_download(year, month, symbol, interval):
    m = str(month).zfill(2)
    filename = f"{symbol}-{interval}-{year}-{m}.zip"
    save_dir = f"raw_data/{symbol}/{interval}"
    os.makedirs(save_dir, exist_ok=True)
    file = os.path.join(save_dir, filename)
    if os.path.exists(file):
        print(f"Skip, Already exists: {filename}")
        return
    url = f"{BASE_URL}/{symbol}/{interval}/{filename}"
    print(f"Downloading: {filename}")
    download(url, file)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", type=str, default="BTCUSDT")
    parser.add_argument("--interval", type=str, required=True)
    # 起始/结束时间，YYYY-MM
    parser.add_argument("--start", type=str, required=True)
    parser.add_argument("--end", type=str, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    symbol = args.symbol
    interval = args.interval

    start_time = datetime.strptime(args.start, "%Y-%m").date()
    end_time = datetime.strptime(args.end, "%Y-%m").date()
    if start_time > end_time:
        raise ValueError("start time must be before end time")
    year, month = start_time.year, start_time.month
    end_year, end_month = end_time.year, end_time.month
    while (year, month) <= (end_year, end_month):
        binance_download(year, month, symbol, interval)
        month += 1
        if month > 12:
            month = 1
            year += 1
