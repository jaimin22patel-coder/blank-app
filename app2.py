import yfinance as yf
import pandas as pd
import numpy as np

def fetch_data(ticker):
    """Stage 1: Fetch 1.5 years of Daily OHLCV data."""
    stock = yf.Ticker(ticker)
    df = stock.history(period="2y", interval="1d")
    if df.empty:
        raise ValueError(f"No data found for ticker {ticker}")
    return df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()


def analyze_market_structure(df, window=20):
    """Stage 2, Rule 1: Find structural trend based on recent pivots."""
    long_term_df = df.iloc[-250:].copy()
    
    # Calculate rolling peaks and troughs
    long_term_df['Peak'] = long_term_df['High'].rolling(window=window, center=True).max()
    long_term_df['Trough'] = long_term_df['Low'].rolling(window=window, center=True).min()
    
    # Extract clean pivot values
    highs = long_term_df.dropna(subset=['Peak'])['High'].drop_duplicates().tolist()[-3:]
    lows = long_term_df.dropna(subset=['Trough'])['Low'].drop_duplicates().tolist()[-3:]
    
    if len(highs) < 2 or len(lows) < 2:
        return "Sideways / Undefined"
    
    # Higher Highs + Higher Lows
    if highs[-1] > highs[-2] and lows[-1] > lows[-2]:
        return "Bullish (Uptrend)"
    # Lower Highs + Lower Lows
    elif highs[-1] < highs[-2] and lows[-1] < lows[-2]:
        return "Bearish (Downtrend)"
    else:
        return "Sideways / Consolidation"


def find_sr_zones(df, current_price, window=15, proximity_pct=0.10, cluster_pct=0.015):
    """
    Stage 2, Rules 2 & 3: Find Support & Resistance zones.
    Filters zones to be within proximity_pct (10%) of current price.
    Groups lines within cluster_pct (1.5%) into single zones.
    """
    long_term_df = df.iloc[-250:].copy()
    raw_levels = []
    
    # Rule 2: Find sharp turning points (Swing Highs and Lows)
    for i in range(window, len(long_term_df) - window):
        if long_term_df['Low'].iloc[i] == long_term_df['Low'].iloc[i-window:i+window+1].min():
            raw_levels.append(long_term_df['Low'].iloc[i])
        if long_term_df['High'].iloc[i] == long_term_df['High'].iloc[i-window:i+window+1].max():
            raw_levels.append(long_term_df['High'].iloc[i])
            
    # Rule 4: Proximity Filter (Only keep lines within 10% of current price)
    valid_levels = [lvl for lvl in raw_levels if abs(lvl - current_price) / current_price <= proximity_pct]
    valid_levels.sort()
    
    # Cluster lines that are very close (1.5% threshold) into Zones
    zones = []
    if not valid_levels:
        return zones
        
    current_zone = [valid_levels[0]]
    for lvl in valid_levels[1:]:
        if (lvl - current_zone[-1]) / current_zone[-1] <= cluster_pct:
            current_zone.append(lvl)
        else:
            zones.append(np.mean(current_zone))
            current_zone = [lvl]
    zones.append(np.mean(current_zone))
    
    return sorted(list(set(zones)))


def check_price_dynamics(short_term_df, zones):
    """
    Stage 2, Rule 4: Track Price Hold or Rejection patterns in the last 5 days.
    """
    last_5_days = short_term_df.tail(5)
    current_price = short_term_df['Close'].iloc[-1]
    
    dynamic_status = "No active zone setup"
    matched_zone = None
    setup_type = None

    for zone in zones:
        zone_upper = zone * 1.01
        zone_lower = zone * 0.99
        
        for idx, row in last_5_days.iterrows():
            # Check for Rejection (Long wick or engulfing hitting the zone)
            candle_body = abs(row['Close'] - row['Open'])
            total_range = row['High'] - row['Low']
            
            # Rejection Pattern Logic (Pin bar or sharp pushback)
            if row['Low'] <= zone_upper and row['High'] >= zone_lower:
                if total_range > 0 and (candle_body / total_range) < 0.4:
                    dynamic_status = "Price Rejection Detected (Big Players Defending Zone)"
                    matched_zone = zone
                    setup_type = "Rejection"
                    break
                    
            # Check for Hold (Consolidation/Retest keeping body flat outside the zone boundary)
            if abs(row['Close'] - zone) / zone <= 0.015 and candle_body < (short_term_df['Close'].pct_change().std() * row['Close']):
                dynamic_status = "Price Hold/Retest Detected (Structure Flipped & Holding)"
                matched_zone = zone
                setup_type = "Hold"
                break
                
    return dynamic_status, matched_zone, setup_type


def calculate_trade_setup(current_price, trend, zone, setup_type, zones):
    """Stage 3: Calculate execution entry, stop-loss, target, and verify R:R >= 1.5."""
    if not zone or not setup_type:
        return "No clear setup. Waiting for clear Price Action confirmation."
        
    # Isolate targets based on next available zones
    upper_zones = [z for z in zones if z > current_price]
    lower_zones = [z for z in zones if z < current_price]
    
    # We prioritize BUYING in a Bullish Trend, or selling Rejections at Key Support
    if "Bullish" in trend or (setup_type == "Rejection" and current_price >= zone):
        # Long Setup Logic
        entry = current_price
        # Stop loss goes safely below the dynamic zone where big players protect money
        stop_loss = zone * 0.985 
        # Target is the next key resistance zone up, or a fixed 4% move if none found
        target = upper_zones[0] if upper_zones else current_price * 1.05
        
        risk = entry - stop_loss
        reward = target - entry
        rr_ratio = reward / risk if risk > 0 else 0
        
        if rr_ratio >= 1.5:
            return f"🟢 VALID LONG SETUP\n -> Action: BUY near {entry:.2f}\n -> Stop-Loss: {stop_loss:.2f} (Protected by Liquidity Zone)\n -> Target: {target:.2f}\n -> Risk-to-Reward Ratio: 1:{rr_ratio:.2f}"
        else:
            return f"⚠️ Setup found, but discarded. R:R ratio is 1:{rr_ratio:.2f} (Fails strict >= 1:1.5 rule)"
            
    elif "Bearish" in trend or (setup_type == "Rejection" and current_price < zone):
        # Short Setup Logic
        entry = current_price
        stop_loss = zone * 1.015  # Stop loss goes right above the liquidity zone
        target = lower_zones[-1] if lower_zones else current_price * 0.95
        
        risk = stop_loss - entry
        reward = entry - target
        rr_ratio = reward / risk if risk > 0 else 0
        
        if rr_ratio >= 1.5:
            return f"🔴 VALID SHORT SETUP\n -> Action: SELL/SHORT near {entry:.2f}\n -> Stop-Loss: {stop_loss:.2f} (Protected by Liquidity Zone)\n -> Target: {target:.2f}\n -> Risk-to-Reward Ratio: 1:{rr_ratio:.2f}"
        else:
            return f"⚠️ Setup found, but discarded. R:R ratio is 1:{rr_ratio:.2f} (Fails strict >= 1:1.5 rule)"

    return "Market environment structure does not match current trade setup rules."


def run_price_action_tool(ticker):
    """Main Orchestrator Engine."""
    print("=" * 50)
    print(f"🤖 RUNNING AUTOMATED PRICE ACTION ENGINE FOR: {ticker.upper()}")
    print("=" * 50)
    
    try:
        # 1. Fetch & Chunk Data
        df = fetch_data(ticker)
        current_price = df['Close'].iloc[-1]
        short_term_df = df.iloc[-20:].copy()
        
        # 2. Extract Context and S&R Zones
        trend = analyze_market_structure(df)
        zones = find_sr_zones(df, current_price)
        
        # 3. Analyze Candle Behaviors against Zones
        dynamics, matched_zone, setup_type = check_price_dynamics(short_term_df, zones)
        
        # 4. Formulate Trade Setup
        trade_decision = calculate_trade_setup(current_price, trend, matched_zone, setup_type, zones)
        
        # Display Outputs
        print(f"📊 Market Trend   : {trend}")
        print(f"💰 Current Price   : {current_price:.2f}")
        print(f"🎯 Active S&R Zones: {[round(z, 2) for z in zones]}")
        print(f"⚡ Price Action Behavior: {dynamics}")
        if matched_zone:
            print(f"📍 Interacting Zone   : {matched_zone:.2f}")
        print("-" * 50)
        print(f"📣 STRATEGY OUTPUT:\n{trade_decision}")
        print("=" * 50)

    except Exception as e:
        print(f"❌ Error processing {ticker}: {e}")


# ---- EXECUTE ENGINE ----
if __name__ == "__main__":
    # Test with any ticker you want to analyze!
    run_price_action_tool("AAPL")
