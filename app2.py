import yfinance as yf
import pandas as pd

def get_stock_data(ticker, timeframe, period):
    """
    Fetches historical stock data from Yahoo Finance.
    """
    print(f"\nFetching data for {ticker} ({timeframe} intervals over the last {period})...")
    try:
        # yfinance expects intervals like '1d', '1wk', '1h' and periods like '1y', '6mo'
        data = yf.download(tickers=ticker, period=period, interval=timeframe)
        
        if data.empty:
            print("Error: No data found. Please check the ticker symbol and parameters.")
            return None
        
        return data
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def analyze_market_structure(df):
    """
    Placeholder for our structure analysis engine.
    This will eventually calculate Swing Highs/Lows and Trends.
    """
    if df is None:
        return
    
    print("\n--- Market Structure Analysis Results ---")
    print(f"Total Candlesticks Loaded: {len(df)}")
    
    # Get the latest close price safely, considering potential multi-index columns from yfinance
    if isinstance(df['Close'], pd.DataFrame):
        latest_close = float(df['Close'].iloc[-1].iloc[0])
    else:
        latest_close = float(df['Close'].iloc[-1])
        
    print(f"Latest Closing Price: ${latest_close:.2f}")
    print("-----------------------------------------")
    
    # TODO: Implement peak/trough detection algorithms here

def main():
    print("=== Stock Structure Analysis Tool ===")
    
    # User Inputs
    ticker = input("Enter Stock Ticker (e.g., AAPL, TSLA): ").strip().upper()
    
    print("\nCommon Timeframes: 1h (1 Hour), 1d (1 Day), 1wk (1 Week)")
    timeframe = input("Enter Timeframe: ").strip().lower()
    
    print("\nCommon Periods: 1mo, 3mo, 6mo, 1y (1 Year), 5y")
    period = input("Enter Time Period to analyze: ").strip().lower()
    
    # Execute Fetching
    df = get_stock_data(ticker, timeframe, period)
    
    # Execute Analysis
    analyze_market_structure(df)

if __name__ == "__main__":
    main()
