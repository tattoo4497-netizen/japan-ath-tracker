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
            {"left": "type", "operation": "equal", "right": "stock"}     # 個別株のみ
        ],
        "options": {"lang": "ja"},
        "symbols": {"query": {"types": ["stock"]}, "tickers": []}, # 明示的にstockのみ指定
        "columns": ["name", "description", "close", "change", "volume", "sector", "type"],
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
        
        # セクターやタイプがETF/REIT/Fund/基金等のものをPython側でも二重に除外
        sector_name = cols[5] or ""
        item_type = cols[6] or ""
        
        if item_type != "stock" or "ETF" in sector_name or "Fund" in sector_name:
            continue
            
        # 銘柄名に「ETF」や「iシェアーズ」などが含まれる場合も除外
        name = cols[1] or code
        if "ETF" in name or "iシェアーズ" in name or "上場投信" in name:
            continue

        # 前日比(cols[3])がNoneの場合は0.0にする安全処理
        raw_change = cols[3]
        change_val = round(raw_change, 2) if raw_change is not None else 0.0
        
        stocks.append({
            "code": code,
            "name": name,
            "price": cols[2] or 0,   # 終値
            "change": change_val,   # 前日比(%)
            "volume": cols[4] or 0,  # 出来高
            "sector": sector_name or "その他"
        })
    return stocks

def update_ath_history(today_stocks):
    """過去のデータと照合して連続更新日数を計算"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    today_codes = {s["code"] for s in today_stocks}
    new_stocks = {}
    
    for stock in today_stocks:
        code = stock["code"]
        # 今回取得した個別株のみを新規登録・更新
        new_stocks[code] = {
            "name": stock["name"],
            "price": stock["price"],
            "change": stock["change"],
            "volume": stock["volume"],
            "sector": stock["sector"],
            "consecutive_days": 1, # 本日時点で連続1日目
            "last_date": today_str
        }
        
    result_data = {
        "last_updated": today_str,
        "stocks": new_stocks
    }
    
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
        
    print(f"[{today_str}] 更新完了: {len(new_stocks)} 銘柄がATH更新（個別株のみ）")
    return result_data

if __name__ == "__main__":
    today_ath = get_tradingview_ath_stocks()
    update_ath_history(today_ath)
