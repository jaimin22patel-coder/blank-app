import engine as SmartMoney
import time

# Define your custom watchlist of liquid Indian equities
WATCHLIST = ['RELIANCE', 'TCS', 'HDFCBANK', 'SBIN', 'ICICIBANK', 'INFY']

print("====================================================")
print("🏦 ACTION STATION: TRADINGVIEW PRICE ACTION ENGINE ")
print("====================================================\n")

for stock in WATCHLIST:
    print(f"📡 Downloading data stream for: {stock}...")
    df = SmartMoney.fetch_tradingview_data(ticker=stock, exchange='NSE', bars=150)
    
    if df is None or df.empty:
        continue
        
    # Calculate 20-period Average Volume for validation (Rule 3.a)
    df['vol_ma'] = df['volume'].rolling(window=20).mean()
    
    # Reference points for current and historical candles
    c_live = df.iloc[-1]
    c_prev = df.iloc[-2]
    c_prev2 = df.iloc[-3]
    
    current_price = c_live['close']
    
    # Step 1 & 2: Map out market structure levels
    zones = SmartMoney.find_sr_levels(df, current_price, pct_threshold=0.04)
    
    print(f"📍 S&R Levels near current market rate (₹{current_price:.2f}):")
    if not zones:
        print("  - No significant structural order blocks detected within threshold.")
        
    for zone in zones:
        lvl_price = zone['price']
        print(f"  • Zone: ₹{lvl_price} | Configuration: {zone['type']} | Structural Rejections: {zone['rejections']}")
        
        # Rule 3.a: Volume confirmation validator (Volume must beat average by 20%+)
        high_volume = c_prev['volume'] > (c_prev['vol_ma'] * 1.20)
        vol_text = "💥 WITH INSTITUTIONAL VOLUME" if high_volume else "⚠️ WEAK RETAIL VOLUME"
        
        # Rule 3: Breakout Analysis
        if c_prev['close'] > lvl_price and c_prev2['close'] <= lvl_price:
            print(f"    🚀 [BREAKOUT DETECTED] Closed above resistance at ₹{lvl_price} -> {vol_text}")
            
        # Rule 3: Breakdown Analysis
        elif c_prev['close'] < lvl_price and c_prev2['close'] >= lvl_price:
            print(f"    📉 [BREAKDOWN DETECTED] Closed below support at ₹{lvl_price} -> {vol_text}")
            
        # Rule 3.b & 4: Retest Confirmation along with Candlestick Holds/Rejections
        # Bullish Retest Configuration
        if c_prev2['close'] > lvl_price and c_live['low'] <= lvl_price and c_live['close'] >= lvl_price:
            print(f"    🔄 [RETEST IN PLAY] Current candle testing broken support at ₹{lvl_price}...")
            pattern = SmartMoney.scan_candle_pattern(c_live, c_prev, c_prev2)
            if pattern:
                print(f"    🔥 [PRICE HOLD CONFIRMED] Institutional signature: {pattern}")
                
        # Bearish Retest Configuration
        if c_prev2['close'] < lvl_price and c_live['high'] >= lvl_price and c_live['close'] <= lvl_price:
            print(f"    🔄 [RETEST IN PLAY] Current candle testing broken resistance at ₹{lvl_price}...")
            pattern = SmartMoney.scan_candle_pattern(c_live, c_prev, c_prev2)
            if pattern:
                print(f"    🔥 [PRICE REJECT CONFIRMED] Institutional signature: {pattern}")
                
    print("-" * 52)
    time.sleep(1.5) # Safe sleep interval to respect TradingView endpoints

print("\n================ SCAN COMPLETE ================")
