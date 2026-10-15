import os
import json
import requests
from datetime import datetime

TV_SCANNER_URL = "https://scanner.tradingview.com/japan/scan"
DATA_FILE = "ath_data.json"
HISTORY_DIR = "history"

def get_tradingview_ath_stocks():
    """TradingViewから上場来高値（ATH）銘柄を安全に取得"""
    payload = {
        "filter": [
            {"left": "High.All", "operation": "equal", "right": "high"},
            {"left": "type", "operation": "equal", "right": "stock"}
        ],
        "options": {"lang": "ja"},
        "symbols": {"query": {"types": ["stock"]}, "tickers": []},
        "columns": ["name", "description", "close", "change", "volume", "sector", "type"],
        "sort": {"sortBy": "change", "sortOrder": "desc"},
        "range": [0, 500]
    }
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        response = requests.post(TV_SCANNER_URL, json=payload, headers=headers)
        print(f"Status Code: {response.status_code}")
        if response.status_code != 200:
            print(f"Error response: {response.text}")
            return []
            
        data = response.json()
        stocks = []
        
        for item in data.get("data", []):
            code = item["s"].replace("TSE:", "")
            cols = item["d"]
            
            sector_name = cols[5] or ""
            item_type = cols[6] or ""
            
            if item_type != "stock" or "ETF" in sector_name or "Fund" in sector_name:
                continue
                
            name = cols[1] or code
            if "ETF" in name or "iシェアーズ" in name or "上場投信" in name or "ETN" in name:
                continue

            raw_change = cols[3]
            change_val = round(raw_change, 2) if raw_change is not None else 0.0
            
            stocks.append({
                "code": code,
                "name": name,
                "price": cols[2] or 0,
                "change": change_val,
                "volume": cols[4] or 0,
                "sector": sector_name or "その他"
            })
            
        print(f"取得成功: {len(stocks)} 銘柄")
        return stocks
    except Exception as e:
        print(f"例外発生: {e}")
        return []

def update_ath_history(today_stocks):
    """過去のデータと照合して連続日数を計算し、保存"""
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    current_time_str = now.strftime("%H:%M")
    
    os.makedirs(HISTORY_DIR, exist_ok=True)
    
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                history = json.load(f)
            except Exception:
                history = {"last_updated": "", "stocks": {}}
    else:
        history = {"last_updated": "", "stocks": {}}
        
    last_updated_date = history.get("last_updated", "")
    prev_stocks = history.get("stocks", {})
    new_stocks = {}
    
    for stock in today_stocks:
        code = stock["code"]
        prev_data = prev_stocks.get(code, {})
        prev_consecutive = prev_data.get("consecutive_days", 0)
        
        if last_updated_date == today_str:
            consecutive_days = prev_consecutive if prev_consecutive > 0 else 1
        else:
            consecutive_days = prev_consecutive + 1 if prev_consecutive > 0 else 1
        
        new_stocks[code] = {
            "name": stock["name"],
            "price": stock["price"],
            "change": stock["change"],
            "volume": stock["volume"],
            "sector": stock["sector"],
            "consecutive_days": consecutive_days,
            "last_date": today_str
        }
        
    result_data = {
        "last_updated": today_str,
        "last_updated_time": current_time_str,
        "stocks": new_stocks
    }
    
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
        
    daily_file = os.path.join(HISTORY_DIR, f"{today_str}.json")
    with open(daily_file, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
        
    print(f"[{today_str} {current_time_str}] 保存完了: {len(new_stocks)} 銘柄")
    return result_data

if __name__ == "__main__":
    today_ath = get_tradingview_ath_stocks()
    update_ath_history(today_ath)
