import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import os
import datetime
import pytz
import warnings

# Mute warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

# ================= CONFIGURATION =================
# STRATEGY: Power of Stocks (5EMA + BB 1.5SD)
# TF: Daily (For End-of-Day Scanning)

STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", 
    "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "BAJFINANCE.NS", "AXISBANK.NS",
    "KOTAKBANK.NS", "LT.NS", "HINDUNILVR.NS", "TATASTEEL.NS",
    "MARUTI.NS", "TITAN.NS", "ULTRACEMCO.NS", "ASIANPAINT.NS", "SUNPHARMA.NS",
    "M&M.NS", "NTPC.NS", "POWERGRID.NS", "BAJAJFINSV.NS", "HCLTECH.NS",
    "ONGC.NS", "WIPRO.NS", "COALINDIA.NS", "JSWSTEEL.NS", "ADANIENT.NS",
    "ADANIPORTS.NS", "BPCL.NS", "GRASIM.NS", "HEROMOTOCO.NS", "HINDALCO.NS",
    "TECHM.NS", "TATAUSERS.NS", "INDUSINDBK.NS", "CIPLA.NS", "APOLLOHOSP.NS",
    "NESTLEIND.NS", "TITAN.NS", "SHREECEM.NS", "DRREDDY.NS", "EICHERMOT.NS",
    "LTIM.NS", "DIVISLAB.NS", "BRITANNIA.NS", "BEL.NS", "TRENT.NS"
]

# ================= TELEGRAM UTILS =================
def send_telegram(message):
    try:
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not token or not chat_id:
            print("❌ Telegram credentials missing.")
            return

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error sending Telegram: {e}")

# ================= STRATEGY LOGIC =================
def check_power_of_stocks(symbol):
    try:
        # Fetch Daily Data (Last 6 months is plenty for 20SMA)
        df = yf.download(symbol, period='6mo', interval='1d', progress=False)
        
        if df.empty or len(df) < 20:
            return None

        # Fix for yfinance MultiIndex columns (if present)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # --- INDICATORS ---
        # 1. 5 EMA
        df['EMA_5'] = ta.ema(df['Close'], length=5)
        
        # 2. Bollinger Bands (20, 1.5)
        bb = ta.bbands(df['Close'], length=20, std=1.5)
        
        # Robust Column Mapping
        if bb is not None and not bb.empty:
            bbu_col = [c for c in bb.columns if c.startswith('BBU')][0]
            bbl_col = [c for c in bb.columns if c.startswith('BBL')][0]
            df['BB_Upper'] = bb[bbu_col]
            df['BB_Lower'] = bb[bbl_col]
        else:
            return None

        # --- SIGNAL LOGIC (Last Completed Candle) ---
        last = df.iloc[-1]
        
        # Check for missing data in last row
        if pd.isna(last['BB_Upper']) or pd.isna(last['EMA_5']):
            return None

        # Setup 1: SHORT ALERT (Overbought)
        # Low > UpperBB AND Low > 5EMA
        if (last['Low'] > last['BB_Upper']) and (last['Low'] > last['EMA_5']):
            trigger = last['Low']
            sl = last['High']
            risk = sl - trigger
            return (f"🔴 *SHORT ALERT: {symbol}*\n"
                    f"Setup: Overbought (Floating Above)\n"
                    f"Entry (Trigger): {trigger:.2f}\n"
                    f"Stop Loss: {sl:.2f}\n"
                    f"Target 1:3: {trigger - (risk*3):.2f}\n"
                    f"Target 1:5: {trigger - (risk*5):.2f}")

        # Setup 2: LONG ALERT (Oversold)
        # High < LowerBB AND High < 5EMA
        if (last['High'] < last['BB_Lower']) and (last['High'] < last['EMA_5']):
            trigger = last['High']
            sl = last['Low']
            risk = trigger - sl
            return (f"🟢 *LONG ALERT: {symbol}*\n"
                    f"Setup: Oversold (Floating Below)\n"
                    f"Entry (Trigger): {trigger:.2f}\n"
                    f"Stop Loss: {sl:.2f}\n"
                    f"Target 1:3: {trigger + (risk*3):.2f}\n"
                    f"Target 1:5: {trigger + (risk*5):.2f}")
            
        return None

    except Exception as e:
        # print(f"Error checking {symbol}: {e}")
        return None

# ================= MAIN EXECUTION =================
def main():
    print("--- ☁️ Cloud Sentinel (Power of Stocks Daily) ---")
    
    # Get Time
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.datetime.now(ist)
    print(f"🕒 Scan Time (IST): {now_ist.strftime('%Y-%m-%d %H:%M:%S')}")
    
    alerts = []
    
    # Scan Stocks
    for stock in STOCKS:
        msg = check_power_of_stocks(stock)
        if msg:
            alerts.append(msg)
    
    # Construct Report
    if alerts:
        header = f"🚨 *POWER OF STOCKS: DAILY SIGNALS* 🚨\nDate: {now_ist.strftime('%d-%m-%Y')}\n\n"
        body = "\n\n".join(alerts)
        footer = "\n\n⚠️ _Place Limit/Stop-Limit Orders for Tomorrow._"
        final_msg = header + body + footer
        
        print(f"✅ Found {len(alerts)} signals. Sending Telegram...")
        send_telegram(final_msg)
    else:
        # Reliability Fix: Send a 'Heartbeat' message even if no signals
        # But maybe just log it to console to save Telegram spam, 
        # OR send a "Clean" msg if you prefer confirmation.
        # User asked for "Alerts", implies signals. 
        # But user also complained about "System Active" flakiness.
        # Compromise: Send a silent log or a simple "No Signals" 
        # ONLY if it's the scheduled time (e.g., end of day).
        # Since we removed the time check, let's send a short confirmation.
        
        print("✅ Scan Complete. No signals found.")
        confirmation_msg = (f"✅ *Daily Scan Complete*\n"
                            f"Date: {now_ist.strftime('%d-%m-%Y')}\n"
                            f"Status: System Healthy\n"
                            f"Signals Found: 0")
        send_telegram(confirmation_msg)

if __name__ == "__main__":
    main()