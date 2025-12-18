import yfinance as yf
import pandas as pd
import requests
import os
import datetime
import pytz # New library for Timezones

# ================= CONFIGURATION =================
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

TELEGRAM_TOKEN = os.environ.get("TG_TOKEN")
CHAT_ID = os.environ.get("TG_CHAT_ID")

def send_telegram(message):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ Telegram credentials missing")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, data=data)

def check_stock(symbol):
    try:
        df = yf.download(symbol, period="3mo", interval="1h", progress=False)
        if len(df) < 200: return None
        
        # Calculate Indicators
        df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
        
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # 1. GOLDEN CROSS (Buy Signal)
        if prev['EMA_50'] <= prev['EMA_200'] and current['EMA_50'] > current['EMA_200']:
            return f"🚀 *BUY ALERT: {symbol}*\nGolden Cross Detected!\nPrice: {current['Close']:.2f}"
            
        # 2. TRAILING STOP (Sell Signal)
        if current['EMA_50'] > current['EMA_200']:
            # Find Highest High since Cross
            # Simplified: Look at last 100 candles (approx 4 months of hourly data)
            lookback = 100
            recent = df.iloc[-lookback:]
            highest_high = recent['High'].max()
            stop_level = highest_high * 0.85 # 15% Trail
            
            if prev['Close'] >= stop_level and current['Close'] < stop_level:
                 return f"🔻 *SELL ALERT: {symbol}*\n15% Trail Hit!\nHigh: {highest_high:.2f} | Stop: {stop_level:.2f}\nCurrent: {current['Close']:.2f}"
                 
        return None
    except Exception as e:
        return None

def main():
    print("--- ☁️ Cloud Sentinel Starting ---")
    
    # 1. TIME CHECK (IST)
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.datetime.now(ist)
    current_hour = now_ist.hour
    current_minute = now_ist.minute
    
    print(f"🕒 Current Time (IST): {now_ist.strftime('%H:%M')}")
    
    alerts = []
    
    # 2. SCAN STOCKS
    for stock in STOCKS:
        msg = check_stock(stock)
        if msg: alerts.append(msg)
    
    # 3. SEND SIGNALS (Priority)
    if alerts:
        final_msg = "\n\n".join(alerts)
        send_telegram(final_msg)
        print("✅ Signals sent.")
        
    # 4. HEALTH CHECK (Every 2 Hours)
    # Trigger at 9:30, 11:30, 13:30 (1:30 PM), 15:30 (3:30 PM)
    # We check if minute is > 20 to account for small GitHub delays
    health_hours = [9, 11, 13, 15]
    
    if current_hour in health_hours and current_minute >= 20 and current_minute <= 50:
        # Only send health check if NO real signals were sent (to reduce spam)
        if not alerts:
            health_msg = f"💚 *Sentinel Active*\nTime: {now_ist.strftime('%H:%M')}\nScanned: 50 Stocks\nStatus: No Signals."
            send_telegram(health_msg)
            print("✅ Health Check sent.")

if __name__ == "__main__":
    main()