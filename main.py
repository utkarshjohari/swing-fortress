import yfinance as yf
import pandas as pd
import requests
import os
import datetime
import pytz
import warnings
import time

# Mute warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

# ================= CONFIGURATION =================
# STRATEGY: Power of Stocks (5EMA + BB 1.5SD)
# TF: Daily (End-of-Day Scan)

STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", 
    "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "BAJFINANCE.NS", "AXISBANK.NS",
    "KOTAKBANK.NS", "LT.NS", "HINDUNILVR.NS", "TATASTEEL.NS",
    "MARUTI.NS", "TITAN.NS", "ULTRACEMCO.NS", "ASIANPAINT.NS", "SUNPHARMA.NS",
    "M&M.NS", "NTPC.NS", "POWERGRID.NS", "BAJAJFINSV.NS", "HCLTECH.NS",
    "ONGC.NS", "WIPRO.NS", "COALINDIA.NS", "JSWSTEEL.NS", "ADANIENT.NS",
    "ADANIPORTS.NS", "BPCL.NS", "GRASIM.NS", "HEROMOTOCO.NS", "HINDALCO.NS",
    "TECHM.NS", "TATACONSUM.NS", "INDUSINDBK.NS", "CIPLA.NS", "APOLLOHOSP.NS",
    "NESTLEIND.NS", "SHREECEM.NS", "DRREDDY.NS", "EICHERMOT.NS",
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
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error sending Telegram: {e}")

# ================= ROBUST DATA FETCHING =================
def fetch_data_with_retry(symbol, retries=3):
    for attempt in range(retries):
        try:
            df = yf.download(symbol, period='6mo', interval='1d', progress=False, threads=False)
            if not df.empty and len(df) > 20:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                return df
        except Exception:
            time.sleep(2)
    return None

# ================= NATIVE INDICATORS =================
def calculate_indicators(df):
    try:
        # 1. 5 EMA
        df['EMA_5'] = df['Close'].ewm(span=5, adjust=False).mean()
        
        # 2. Bollinger Bands (20, 1.5)
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['STD_20'] = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['SMA_20'] + (1.5 * df['STD_20'])
        df['BB_Lower'] = df['SMA_20'] - (1.5 * df['STD_20'])
        
        # 3. Volume Avg
        df['Vol_Avg'] = df['Volume'].rolling(window=20).mean()
        
        return df
    except Exception:
        return None

# ================= STRATEGY LOGIC =================
def check_power_of_stocks(symbol):
    try:
        df = fetch_data_with_retry(symbol)
        if df is None: return None

        df = calculate_indicators(df)
        if df is None: return None

        last = df.iloc[-1]
        
        # --- CRITICAL FIX: EXTRACT CANDLE DATE ---
        candle_date = last.name.strftime('%d-%b') # e.g., "23-Jan"
        
        if pd.isna(last['BB_Upper']) or pd.isna(last['EMA_5']):
            return None
            
        clean_sym = symbol.replace('.NS', '')
        tv_link = f"https://in.tradingview.com/chart/?symbol=NSE:{clean_sym}"
        kite_link = f"https://kite.zerodha.com/chart/ext/tvc/NSE/{clean_sym}"

        vol_tag = ""
        if last['Volume'] > (last['Vol_Avg'] * 2):
            vol_tag = "🔥 *HIGH VOL*"

        # SHORT ALERT
        if (last['Low'] > last['BB_Upper']) and (last['Low'] > last['EMA_5']):
            trigger = last['Low']
            sl = last['High']
            risk = sl - trigger
            return (f"🔴 *SHORT: {clean_sym}* ({candle_date})\n"
                    f"Entry: `{trigger:.2f}`\n"
                    f"SL: `{sl:.2f}`\n"
                    f"Target 1:5: `{trigger - (risk*5):.2f}`\n"
                    f"[Chart]({tv_link}) {vol_tag}")

        # LONG ALERT
        if (last['High'] < last['BB_Lower']) and (last['High'] < last['EMA_5']):
            trigger = last['High']
            sl = last['Low']
            risk = trigger - sl
            return (f"🟢 *LONG: {clean_sym}* ({candle_date})\n"
                    f"Entry: `{trigger:.2f}`\n"
                    f"SL: `{sl:.2f}`\n"
                    f"Target 1:5: `{trigger + (risk*5):.2f}`\n"
                    f"[Chart]({tv_link}) {vol_tag}")
            
        return None

    except Exception:
        return None

# ================= MAIN EXECUTION =================
def main():
    print("--- ☁️ Power of Stocks Scanner ---")
    
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.datetime.now(ist)
    
    alerts = []
    
    for stock in STOCKS:
        msg = check_power_of_stocks(stock)
        if msg:
            alerts.append(msg)
    
    if alerts:
        # Header now shows Run Date
        header = f"🚨 *DAILY SIGNALS* ({now_ist.strftime('%d-%b')})\n\n"
        body = "\n\n".join(alerts)
        footer = "\n\n⚠️ _Check Candle Date above!_"
        final_msg = header + body + footer
        send_telegram(final_msg)
    else:
        print("No signals.")
        send_telegram(f"✅ *Scan Complete*\nStatus: No Signals Found")

if __name__ == "__main__":
    main()