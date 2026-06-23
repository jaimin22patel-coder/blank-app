import pandas as pd
import numpy as np
from tvDatafeed import TvDatafeed, Interval

def fetch_tradingview_data(ticker: str, exchange: str = 'NSE', bars: int = 150):
    """Fetches raw market candles directly from TradingView."""
    try:
        tv = TvDatafeed()
        df = tv.get_hist(symbol=ticker, exchange=exchange, interval=Interval.in_daily, n_bars=bars)
        if df is not None and not df.empty:
            return df.reset_index()
        return None
    except Exception as e:
        print(f"❌ Error downloading data for {ticker}: {str(e)}")
        return None

def identify_market_structure(df, window=5):
    """Identifies institutional Swing Highs and Swing Lows."""
    df['swing_high'] = df['high'] == df['high'].rolling(window=2*window+1, center=True).max()
    df['swing_low'] = df['low'] == df['low'].rolling(window=2*window+1, center=True).min()
    return df

def find_sr_levels(df, current_price, pct_threshold=0.035):
    """
    Finds Support & Resistance lines based on your 4 strict rules:
    a. Multiple rejections (2+ touches)
    b. Strong move away from swing turning points
    c. Role reversal (can act as both Support & Resistance)
    d. Near current market price
    """
    df = identify_market_structure(df)
    levels = []
    
    high_swings = df[df['swing_high']]['high'].tolist()
    low_swings = df[df['swing_low']]['low'].tolist()
    all_swings = high_swings + low_swings
    
    for price in all_swings:
        # Rule D: Level must be near current price
        if abs(price - current_price) / current_price > pct_threshold:
            continue
            
        rejections = 0
        is_support = False
        is_resistance = False
        
        for idx, row in df.iterrows():
            # Rule A & C: Check rejections and role-reversal markers
            if abs(row['high'] - price) / price < 0.006:
                rejections += 1
                is_resistance = True
            if abs(row['low'] - price) / price < 0.006:
                rejections += 1
                is_support = True
                
        # Rule A: Multiple rejections threshold check
        if rejections >= 2:
            role = "SR_Flip" if (is_support and is_resistance) else ("Support" if is_support else "Resistance")
            
            # De-duplicate zones that are extremely close to one another
            if not any(abs(l['price'] - price) / price < 0.012 for l in levels):
                levels.append({
                    'price': round(price, 2),
                    'rejections': rejections,
                    'type': role
                })
    return levels

def scan_candle_pattern(row, prev_row, prev2_row):
    """
    Rule 4.a: Identifies Institutional Rejection/Hold Formations:
    Hammer, Shooting Star, Bullish/Bearish Engulfing, Morning/Evening Star.
    """
    body = abs(row['close'] - row['open'])
    candle_range = row['high'] - row['low']
    if candle_range == 0: return None
    
    upper_wick = row['high'] - max(row['close'], row['open'])
    lower_wick = min(row['close'], row['open']) - row['low']
    is_green = row['close'] >= row['open']
    
    # Single Candle Triggers (Rejections)
    if lower_wick > (body * 2) and upper_wick < (body * 0.5):
        return "Hammer (Bullish Hold/Reject)"
    if upper_wick > (body * 2) and lower_wick < (body * 0.5):
        return "Shooting Star (Bearish Hold/Reject)"
        
    # Multi-Candle Triggers (Engulfings & Stars)
    prev_body = abs(prev_row['close'] - prev_row['open'])
    prev_is_green = prev_row['close'] >= prev_row['open']
    
    if not prev_is_green and is_green and row['close'] > prev_row['open'] and row['open'] < prev_row['close']:
        return "Bullish Engulfing (Institutional Buying Impulse)"
    if prev_is_green and not is_green and row['close'] < prev_row['open'] and row['open'] > prev_row['close']:
        return "Bearish Engulfing (Institutional Selling Impulse)"
        
    # Morning Star
    if not prev2_row['close'] >= prev2_row['open'] and prev_body < (abs(prev2_row['close'] - prev2_row['open']) * 0.5) and is_green and row['close'] > (prev2_row['open'] + prev2_row['close'])/2:
        return "Morning Star (Institutional Accumulation)"
        
    # Evening Star
    if prev2_row['close'] >= prev2_row['open'] and prev_body < (abs(prev2_row['close'] - prev2_row['open']) * 0.5) and not is_green and row['close'] < (prev2_row['open'] + prev2_row['close'])/2:
        return "Evening Star (Institutional Distribution)"
        
    return None
