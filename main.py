import yfinance as yf
import pandas as pd
import requests
import os
import datetime
import pytz
import warnings

# Mute warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

# ================= CONFIGURATION =================
# THE FORTRESS CONFIG (Stable & Tested)
EMA_FAST_LEN = 50
EMA_SLOW_LEN = 100
TRAIL_PERCENT = 0.15  # 15% Drop from High

STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", 
    "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "BAJFINANCE.NS", "AXISBANK.NS",
    "KOTAKBANK.NS", "LT.NS", "HINDUNILVR.NS","TATASTEEL.NS",
    "MARUTI.NS", "TITAN.NS", "ULTRACEMCO.NS", "ASIANPAINT.NS", "SUNPHARMA.NS",
    "M&M.NS", "NTPC.NS", "POWERGRID.NS", "BAJAJFINSV.NS", "HCLTECH.NS",
    "ONGC.NS", "WIPRO.NS", "COALINDIA.NS", "JSWSTEEL.NS", "ADANIENT.NS",
    "ADANIPORTS.NS", "BPCL.NS", "GRASIM.NS", "HINDALCO.NS", "DRREDDY.NS",
    "CIPLA.NS", "TECHM.NS", "SBILIFE.NS", "BRITANNIA.NS", "INDUSINDBK.NS",
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
        # Fetch Data (1y is enough)
        df = yf.download(symbol, period="1y", interval="1h", progress=False, auto_adjust=True)
        if len(df) < 200: return None
        
        # --- CALCULATE INDICATORS ---
        df['EMA_FAST'] = df['Close'].ewm(span=EMA_FAST_LEN, adjust=False).mean()
        df['EMA_SLOW'] = df['Close'].ewm(span=EMA_SLOW_LEN, adjust=False).mean()
        
        # --- ROBUST LOGIC (Scan Last 4 Candles) ---
        # This covers a 3-4 hour window, ensuring we don't miss a signal 
        # even if the bot runs every 2 hours.
        
        recent_data = df.tail(5) # Look at last 5 rows
        
        # Check INIT BUY (Golden Cross) in the recent window
        # We iterate to find the EXACT moment of cross
        for i in range(1, len(recent_data)):
            prev = recent_data.iloc[i-1]
            curr = recent_data.iloc[i]
            
            # Check transition from Bearish/Neutral to Bullish
            if prev['EMA_FAST'] <= prev['EMA_SLOW'] and curr['EMA_FAST'] > curr['EMA_SLOW']:
                # Found a cross!
                timestamp_str = curr.name.strftime('%Y-%m-%d %H:%M')
                return f"🚀 *INIT BUY: {symbol}*\nGolden Cross (50 > 100)!\nTime: {timestamp_str}\nPrice: {curr['Close']:.2f}"

        # Get Current Data for Management
        current = df.iloc[-1]
        prev_candle = df.iloc[-2]
        
        # Check PYRAMID ADD (Dip to 50 EMA)
        if current['EMA_FAST'] > current['EMA_SLOW']:
            touched_ema = current['Low'] <= current['EMA_FAST']
            held_support = current['Close'] > current['EMA_FAST']
            green_candle = current['Close'] > current['Open']
            
            if touched_ema and held_support and green_candle:
                 # Debounce: Make sure previous candle didn't already trigger
                 prev_bounce = (prev_candle['Low'] <= prev_candle['EMA_FAST']) and (prev_candle['Close'] > prev_candle['EMA_FAST'])
                 if not prev_bounce:
                    return f"💰 *PYRAMID ADD: {symbol}*\nDip to 50 EMA.\nPrice: {current['Close']:.2f}"

            # Check SELL ALL (15% Trail)
            recent = df.iloc[-500:] 
            highest_high = recent['High'].max()
            stop_level = highest_high * (1.0 - TRAIL_PERCENT)
            
            if prev_candle['Close'] >= stop_level and current['Close'] < stop_level:
                 return f"🛑 *SELL ALL: {symbol}*\n15% Trail Hit.\nStop: {stop_level:.2f}\nCurrent: {current['Close']:.2f}"
                 
        return None
    except Exception as e:
        # print(f"Error checking {symbol}: {e}")
        return None

def main():
    print("--- ☁️ Cloud Sentinel (Fortress 50/100 - Deep Scan) ---")
    
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
        
    # Health Check (9:30, 11:30, 1:30, 3:30)
    health_hours = [9, 11, 13, 15]
    if current_hour in health_hours and 25 <= current_minute <= 35:
        if not alerts:
            health_msg = f"💚 *Sentinel Active*\nTime: {now_ist.strftime('%H:%M')}\nStrategy: Fortress 50/100"
            send_telegram(health_msg)
            print("✅ Health Check sent.")

if __name__ == "__main__":
    main()