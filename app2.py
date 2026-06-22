import yfinance as yf
import pandas as pd
import numpy as np

def fetch_and_prepare_data(ticker):
    """
    Fetches daily stock data and splits it into Long-Term and Short-Term chunks.
    """
    # Fetch 1.5 years of daily data to ensure we have enough lookback for a 250-day trend
    stock = yf.Ticker(ticker)
    df = stock.history(period="2y", interval="1d")
    
    if df.empty:
        raise ValueError(f"No data found for ticker {ticker}")
        
    # Standardize columns
    df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
    
    # Track A: Long-Term Context (Last 250 trading days)
    long_term_df = df.iloc[-250:].copy()
    
    # Track B: Short-Term Scenario (Last 20 trading days)
    short_term_df = df.iloc[-20:].copy()
    
    return long_term_df, short_term_df
