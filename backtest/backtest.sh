export PYTHONPATH=.
python backtest/backtest.py \
    --input_dir "data/crypto/binance/futures_um/BTCUSDT/1h/2026" \
    --start_date "20260101" \
    --end_date "20260131" \
    > backtest.log 2>&1
