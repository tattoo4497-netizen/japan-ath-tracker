import os
import json
import requests
from datetime import datetime

TV_SCANNER_URL = "https://scanner.tradingview.com/japan/scan"
DATA_FILE = "ath_data.json"
HISTORY_DIR = "history"

def get_tradingview_ath_stocks():
    """TradingViewから上場来高値銘柄を取得し、当日しっかり上昇・動意づいているものに厳選"""
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
        if response.status_code != 200:
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
            
            # ★重要：今日実際に高値を更新して買われている（前日比がプラス、または0%以上）銘柄に限定する
            # キタックのように今日下落している、あるいは動いていないものを除外します
            if change_val < 0:
                continue
            
            stocks.append({
                "code": code,
                "name": name,
                "price": cols[2] or 0,
                "change": change_val,
                "volume": cols[4] or 0,
                "sector": sector_name or "その他"
            })
            
        print(f"取得成功（厳選後）: {len(stocks)} 銘柄")
        return stocks
    except Exception as e:
        print(f"例外発生: {e}")
        return []

def update_ath_history(today_stocks):
    """データを完全にクリーンにして本日の結果だけで上書き保存"""
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    current_time_str = now.strftime("%H:%M")
    
    os.makedirs(HISTORY_DIR, exist_ok=True)
    
    # 過去データの引き継ぎによるゴミ残存を防ぐため、本日のスクリーナー結果をそのまま新規リストとします
    new_stocks = {}
    for stock in today_stocks:
        code = stock["code"]
        new_stocks[code] = {
            "name": stock["name"],
            "price": stock["price"],
            "change": stock["change"],
            "volume": stock["volume"],
            "sector": stock["sector"],
            "consecutive_days": 1,  # リセットして純粋な当日更新分としてカウント
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
