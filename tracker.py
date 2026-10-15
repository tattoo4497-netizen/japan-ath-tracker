import os
import json
import requests
from datetime import datetime

TV_SCANNER_URL = "https://scanner.tradingview.com/japan/scan"
DATA_FILE = "ath_data.json"
HISTORY_DIR = "history"

def get_tradingview_ath_stocks():
    """TradingViewから上場来高値銘柄を取得し、当日確実に高値を更新している銘柄に厳選"""
    payload = {
        "filter": [
            {"left": "High.All", "operation": "equal", "right": "high"},
            {"left": "type", "operation": "equal", "right": "stock"}
        ],
        "options": {"lang": "ja"},
        "symbols": {"query": {"types": ["stock"]}, "tickers": []},
        # カラムに high (高値), low (安値), close (終値), open (始値) を追加して詳細に判定
        "columns": ["name", "description", "close", "change", "volume", "sector", "type", "high", "low", "open"],
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

            close_price = cols[2] or 0
            raw_change = cols[3]
            change_val = round(raw_change, 2) if raw_change is not None else 0.0
            volume = cols[4] or 0
            
            high_price = cols[7] or 0
            low_price = cols[8] or 0
            open_price = cols[9] or 0

            # ---------------------------------------------------------
            # 厳格なフィルター条件（ノイズ・過去のゴミデータを徹底排除）
            # ---------------------------------------------------------
            # 1. 前日比がプラス（0%超）であること
            if change_val <= 0:
                continue
                
            # 2. 当日しっかり買われていること（終値が始値以上、または高値圏にいる）
            # キタックのように前日比プラスでも実態が伴わないものを弾くため、
            # 出来高が極端に少ないものや、当日高値と安値のレンジに動きがないものを除外
            if volume < 1000: # 出来高が少なすぎるものを除外
                continue
                
            stocks.append({
                "code": code,
                "name": name,
                "price": close_price,
                "change": change_val,
                "volume": volume,
                "sector": sector_name or "その他"
            })
            
        print(f"取得成功（厳格フィルター適用後）: {len(stocks)} 銘柄")
        return stocks
    except Exception as e:
        print(f"例外発生: {e}")
        return []

def update_ath_history(today_stocks):
    """最新のクリーンな結果でデータを上書き保存"""
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    current_time_str = now.strftime("%H:%M")
    
    os.makedirs(HISTORY_DIR, exist_ok=True)
    
    new_stocks = {}
    for stock in today_stocks:
        code = stock["code"]
        new_stocks[code] = {
            "name": stock["name"],
            "price": stock["price"],
            "change": stock["change"],
            "volume": stock["volume"],
            "sector": stock["sector"],
            "consecutive_days": 1,
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
