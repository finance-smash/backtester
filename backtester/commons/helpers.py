import pandas as pd



def get_ohlcv_data(domain, symbol, timeframe, data_dir = "/Users/dyodio/Documents/Projects/Finance-Smash/data"):
    try:
        data_path = f"{domain}/{symbol}/{timeframe}.csv"
        candles_csv_file_path = f"{data_dir}/{data_path}"
        candles_df = pd.read_csv(candles_csv_file_path).sort_values(by='Gmt time', ascending=True)
        candles_df = candles_df[candles_df['Close'].notna()]
        ohlcv_gmt_times = candles_df['Gmt time'].values
        ohlcv = candles_df[['Open', 'High', 'Low', 'Close', 'Volume']].values
        return ohlcv, ohlcv_gmt_times
    except Exception as e:
        print(f"Error loading data for {symbol} {timeframe}: {e}")
        return None, None