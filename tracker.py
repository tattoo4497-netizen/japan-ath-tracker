import os
import json
import requests
from datetime import datetime

# TradingViewのScanner APIエンドポイント（日本株上場来高値）
TV_SCANNER_URL = "https://scanner.tradingview.com/japan/scan"

DATA_FILE = "ath_data.json"

def get_tradingview_ath_stocks():
    """TradingViewから上場来高値（ATH）更新銘柄（個別株のみ）を取得"""
    payload = {
        "filter": [
            {"left": "High.All", "operation": "equal", "right": "high"}, # 当日高値 ＝ 上場来高値
            {"left": "type", "operation": "equal", "right": "stock"},    # 個別株のみ（ETFや基金等を除外）
            {"left": "submarket", "operation": "nequal", "right": "etf"} # ETFサブマーケットを除外
        ],
        "options": {"lang": "ja"},
        "symbols": {"query": {"types": []}, "tickers": []},
        "columns": ["name", "description", "close", "change", "volume", "sector"],
        "sort": {"sortBy": "change", "sortOrder": "desc"},
        "range": [0, 300]
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    response = requests.post(TV_SCANNER_URL, json=payload, headers=headers)
    if response.status_code != 200:
        print(f"Error fetching data: {response.status_code}")
        return []
        
    data = response.json()
    stocks = []
    for item in data.get("data", []):
        code = item["s"].replace("TSE:", "") # 銘柄コード
        cols = item["d"]
        
        # 前日比(cols[3])がNoneの場合は0.0にする安全処理
        raw_change = cols[3]
        change_val = round(raw_change, 2) if raw_change is not None else 0.0
        
        stocks.append({
            "code": code,
            "name": cols[1] or code, # 銘柄名
            "price": cols[2] or 0,  # 終値
            "change": change_val,  # 前日比(%)
            "volume": cols[4] or 0, # 出来高
            "sector": cols[5] or "その他"
        })
    return stocks

def update_ath_history(today_stocks):
    """過去のデータと照合して連続更新日数を計算"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # 既存データの読み込み
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            try:
                history = json.load(f)
            except Exception:
                history = {"last_updated": "", "stocks": {}}
    else:
        history = {"last_updated": "", "stocks": {}}
        
    prev_stocks = history.get("stocks", {})
    new_stocks = {}
    
    for stock in today_stocks:
        code = stock["code"]
        # 前回もATHリストに存在していれば連続日数+1、新規なら1日目
        prev_consecutive = prev_stocks.get(code, {}).get("consecutive_days", 0)
        consecutive_days = prev_consecutive + 1
        
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
        "stocks": new_stocks
    }
    
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
        
    print(f"[{today_str}] 更新完了: {len(new_stocks)} 銘柄がATH更新")
    return result_data

if __name__ == "__main__":
    today_ath = get_tradingview_ath_stocks()
    update_ath_history(today_ath)
