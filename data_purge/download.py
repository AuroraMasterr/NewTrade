import os
import requests
import argparse
from datetime import datetime, timedelta
from tqdm import tqdm


def get_base_url(mode, freq):
    """
    Binance Api
    mode: [spot, futures_um, futures_cm] 现货 / U本位合约 / 币本位合约
    freq: [monthly, daily]
    """
    return f"https://data.binance.vision/data/{mode.replace("_", "/")}/{freq}/klines"


def download(url, file):
    print(f"Download URL: {url} for {file}")
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
    print(f"[OK] Completed: {filename}")


def binance_download(year, month, day, symbol, interval, mode, freq):
    m = str(month).zfill(2)
    d = str(day).zfill(2)
    filename = f"{symbol}-{interval}-{year}-{m}-{d}.zip"
    save_dir = f"raw_data/{symbol}/{interval}"
    os.makedirs(save_dir, exist_ok=True)
    file = os.path.join(save_dir, filename)
    if os.path.exists(file):
        print(f"Skip, Already exists: {filename}")
        return
    BASE_URL = get_base_url(mode, freq)
    url = f"{BASE_URL}/{symbol}/{interval}/{filename}"
    download(url, file)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", type=str, default="BTCUSDT")
    parser.add_argument("--interval", type=str, required=True)
    # 起始/结束时间，YYYY-MM-DD
    parser.add_argument("--start", type=str, required=True)
    parser.add_argument("--end", type=str, required=True)
    parser.add_argument(
        "--mode",
        type=str,
        default="futures_um",
        choices=["spot", "futures_um", "futures_cm"],
    )
    parser.add_argument(
        "--freq",
        type=str,
        default="daily",
        choices=["monthly", "daily"],
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    start_time = datetime.strptime(args.start, "%Y-%m-%d").date()
    end_time = datetime.strptime(args.end, "%Y-%m-%d").date()
    if start_time > end_time:
        raise ValueError("start time must be before end time")
    while start_time <= end_time:
        binance_download(
            start_time.year,
            start_time.month,
            start_time.day,
            args.symbol,
            args.interval,
            args.mode,
            args.freq,
        )
        start_time += timedelta(days=1)
