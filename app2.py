import streamlit as st
import yfinance as yf
import pandas as pd

# Set page configuration to fit mobile screens beautifully
st.set_page_config(page_title="Stock Structure Tool", layout="centered")

st.title("📈 Stock Structure Analysis Engine")
st.write("Analyze trends and market structure phases.")

# --- Sidebar Inputs (Great for Mobile Layouts) ---
st.header("Parameters")
ticker = st.text_input("Stock Ticker", value="AAPL").strip().upper()

# Dropdowns for clean user selection
timeframe = st.selectbox(
    "Select Timeframe",
    options=["1h", "1d", "1wk"],
    index=1,
    help="1h = 1 Hour, 1d = 1 Day, 1wk = 1 Week"
)

period = st.selectbox(
    "Select Time Period",
    options=["1mo", "3mo", "6mo", "1y", "5y"],
    index=3,
    help="How far back to look historically"
)

# --- Analysis Button ---
if st.button("Run Structure Analysis", type="primary"):
    if ticker:
        with st.spinner(f"Fetching data for {ticker}..."):
            try:
                # Fetch data
                df = yf.download(tickers=ticker, period=period, interval=timeframe)
                
                if df.empty:
                    st.error("No data found. Please check the ticker symbol.")
                else:
                    # Success and Data summary
                    st.success(f"Successfully loaded {len(df)} candles!")
                    
                    # Safe extraction of latest close price
                    if isinstance(df['Close'], pd.DataFrame):
                        latest_close = float(df['Close'].iloc[-1].iloc[0])
                    else:
                        latest_close = float(df['Close'].iloc[-1])
                    
                    # --- Display Results ---
                    st.markdown("---")
                    st.subheader(f"Analysis Results for {ticker}")
                    
                    # Metrics Display
                    st.metric(label="Latest Closing Price", value=f"${latest_close:.2f}")
                    
                    # Placeholder for the upcoming engine logic
                    st.info("🔄 **Next Step Engine:** Swing High/Low & Trend detection will print here.")
                    
                    # Show raw data option
                    with st.expander("View Raw Candlestick Data"):
                        st.dataframe(df.tail(10))
                        
            except Exception as e:
                st.error(f"An error occurred: {e}")
    else:
        st.warning("Please enter a valid stock ticker.")
