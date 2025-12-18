import yfinance as yf
import pandas as pd
import requests
import os
import datetime
import pytz

# ================= CONFIGURATION =================
# TOP 50 STOCKS
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
        # Fetch 6 months of data for reliable trend calculation
        df = yf.download(symbol, period="6mo", interval="1h", progress=False)
        if len(df) < 200: return None
        
        # Calculate Indicators (50/100 EMA)
        df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['EMA_100'] = df['Close'].ewm(span=100, adjust=False).mean() # Changed to 100 as per optimization
        
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # --- LOGIC ---
        
        # 1. INITIAL ENTRY (Golden Cross)
        if prev['EMA_50'] <= prev['EMA_100'] and current['EMA_50'] > current['EMA_100']:
            return f"🚀 *INIT BUY: {symbol}*\nGolden Cross (50 > 100)!\nStart New Position.\nPrice: {current['Close']:.2f}"

        # 2. PYRAMID ADD (Dip to 50 EMA)
        # Condition: Trend is UP (50 > 100)
        if current['EMA_50'] > current['EMA_100']:
            
            # Logic: Low touched 50 EMA, but Close is above it (Bounce)
            # And Previous candle was NOT touching it (to avoid spamming on every candle of a dip)
            
            # Simple "Dip Zone": Price is close to EMA 50 (within 1%) but above it
            dist_to_50 = (current['Close'] - current['EMA_50']) / current['EMA_50']
            
            # If price dipped near EMA 50 (0% to 1.5% buffer) and is green (Close > Open)
            # This confirms support
            if 0 < dist_to_50 < 0.015 and current['Close'] > current['Open']:
                 # Check if we weren't already here last hour (simple de-bounce)
                 if (prev['Close'] - prev['EMA_50']) / prev['EMA_50'] > 0.015:
                    return f"💰 *PYRAMID ADD: {symbol}*\nDip to 50 EMA detected.\nAdd to Winners!\nPrice: {current['Close']:.2f}"

            # 3. EXIT (15% Trail)
            # Look back 300 candles for Highest High
            recent = df.iloc[-300:]
            highest_high = recent['High'].max()
            stop_level = highest_high * 0.85 # 15% Trail
            
            if prev['Close'] >= stop_level and current['Close'] < stop_level:
                 return f"🛑 *SELL ALL: {symbol}*\n15% Trail Hit.\nClose All Positions.\nHigh: {highest_high:.2f} | Stop: {stop_level:.2f}\nCurrent: {current['Close']:.2f}"
                 
        return None
    except Exception as e:
        return None

def main():
    print("--- ☁️ Cloud Sentinel (Pyramid Edition) ---")
    
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.datetime.now(ist)
    current_hour = now_ist.hour
    current_minute = now_ist.minute
    
    print(f"🕒 Time (IST): {now_ist.strftime('%H:%M')}")
    
    alerts = []
    for stock in STOCKS:
        msg = check_stock(stock)
        if msg: alerts.append(msg)
    
    if alerts:
        final_msg = "\n\n".join(alerts)
        send_telegram(final_msg)
        print("✅ Signals sent.")
        
    # Health Check (9:30, 11:30, 1:30, 3:30) at xx:30 mark
    health_hours = [9, 11, 13, 15]
    if current_hour in health_hours and 28 <= current_minute <= 32:
        if not alerts:
            health_msg = f"💚 *Sentinel Active*\nTime: {now_ist.strftime('%H:%M')}\nStatus: Monitoring for Dips & Crosses."
            send_telegram(health_msg)

if __name__ == "__main__":
    main()