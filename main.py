import yfinance as yf
import pandas as pd
import requests
import os
import time

# ================= CONFIGURATION =================
# NIFTY 50 LIST (Add .NS for Yahoo Finance)
STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", 
    "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "BAJFINANCE.NS", "AXISBANK.NS",
    "KOTAKBANK.NS", "LT.NS", "HINDUNILVR.NS", "TATAMOTORS.NS", "TATASTEEL.NS",
    "MARUTI.NS", "TITAN.NS", "ULTRACEMCO.NS", "ASIANPAINT.NS", "SUNPHARMA.NS",
    "M&M.NS", "NTPC.NS", "POWERGRID.NS", "BAJAJFINSV.NS", "HCLTECH.NS",
    "ONGC.NS", "WIPRO.NS", "COALINDIA.NS", "JSWSTEEL.NS", "ADANIENT.NS",
    "ADANIPORTS.NS", "BPCL.NS", "GRASIM.NS", "HINDALCO.NS", "DRREDDY.NS",
    "CIPLA.NS", "TECHM.NS", "SBI_LIFE.NS", "BRITANNIA.NS", "INDUSINDBK.NS",
    "TATACONSUM.NS", "EICHERMOT.NS", "NESTLEIND.NS", "APOLLOHOSP.NS", "DIVISLAB.NS",
    "HEROMOTOCO.NS", "LTIM.NS", "BEL.NS", "HAL.NS", "VBL.NS" 
]

# CREDENTIALS (Loaded from GitHub Secrets)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram(message):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ Telegram credentials missing")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, data=data)

def check_stock(symbol):
    try:
        # Fetch 60 days of 1h data (enough to find the cross)
        df = yf.download(symbol, period="3mo", interval="1h", progress=False)
        if len(df) < 200: return None
        
        # Calculate Indicators
        df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
        
        # Logic
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 1. GOLDEN CROSS (Buy Signal)
        # Condition: 50 just crossed above 200 in the last candle
        if prev['EMA_50'] <= prev['EMA_200'] and current['EMA_50'] > current['EMA_200']:
            return f"🚀 *BUY ALERT: {symbol}*\nGolden Cross Detected!\nPrice: {current['Close']:.2f}"
            
        # 2. TRAILING STOP (Sell Signal)
        # Condition: Currently in Uptrend (50 > 200)
        if current['EMA_50'] > current['EMA_200']:
            # Stateless Logic: Find the Highest High since the Cross happened
            # We look backwards to find when 50 was last below 200
            # Get the 'bull run' slice
            bull_mask = df['EMA_50'] > df['EMA_200']
            # Find the last time it flipped (start of this trend)
            # This is a bit heavy, simplified: Look at last 60 days.
            # If we are deep in trend, calculate High of last 300 bars
            lookback = 300
            if len(df) > lookback:
                recent_df = df.iloc[-lookback:]
            else:
                recent_df = df
            
            # Highest High in the recent period
            highest_high = recent_df['High'].max()
            stop_level = highest_high * 0.85
            
            # TRIGGER: Close crossed below Stop Level just now
            if prev['Close'] >= stop_level and current['Close'] < stop_level:
                 return f"🔻 *SELL ALERT: {symbol}*\n15% Trail Hit!\nHigh: {highest_high:.2f} | Stop: {stop_level:.2f}\nCurrent: {current['Close']:.2f}"
                 
        return None
    except Exception as e:
        return None

def main():
    print("--- ☁️ Cloud Sentinel Starting ---")
    alerts = []
    
    for stock in STOCKS:
        # print(f"Scanning {stock}...")
        msg = check_stock(stock)
        if msg:
            print(msg)
            alerts.append(msg)
    
    if alerts:
        final_msg = "\n\n".join(alerts)
        send_telegram(final_msg)
        print("✅ Alerts sent to Telegram.")
    else:
        print("💤 No signals found.")

if __name__ == "__main__":
    main()