import requests
import urllib.parse

ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiJBVjMwNjgiLCJqdGkiOiI2OTg1YTM1NTJjZTdiODdhOTAyZWQ4ZDQiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6dHJ1ZSwiaWF0IjoxNzcwMzY1NzgxLCJpc3MiOiJ1ZGFwaS1nYXRld2F5LXNlcnZpY2UiLCJleHAiOjE3NzA0MTUyMDB9.5hJRckhM7Dm0YI0Q8zka_MNC8ClJqAyIWD4dd9q9eNs"

headers = {
    'Authorization': f'Bearer {ACCESS_TOKEN}',
    'Accept': 'application/json'
}

# Correct MCX instrument keys
mcx_keys = {
    "GOLDM": "MCX_FO|472781",       # GOLDM FUT 05 MAR 26
    "CRUDEOIL": "MCX_FO|472789",    # CRUDEOIL FUT 19 MAR 26
    "SILVERM": "MCX_FO|451669",     # SILVERM FUT 27 FEB 26
}

print("🛢️ LIVE MCX DATA:\n")
for name, key in mcx_keys.items():
    encoded = urllib.parse.quote(key, safe='')
    url = f"https://api.upstox.com/v2/market-quote/ltp?instrument_key={encoded}"
    resp = requests.get(url, headers=headers)
    data = resp.json()
    if data.get('data') and len(data['data']) > 0:
        for k, v in data['data'].items():
            print(f"✅ {name}: ₹{v.get('last_price')}")
    else:
        print(f"❌ {name}: No data")

# Also test NIFTY and BANKNIFTY
print("\n📊 INDEX DATA:\n")
index_keys = {
    "NIFTY": "NSE_INDEX|Nifty 50",
    "BANKNIFTY": "NSE_INDEX|Nifty Bank",
}
for name, key in index_keys.items():
    encoded = urllib.parse.quote(key, safe='')
    url = f"https://api.upstox.com/v2/market-quote/ltp?instrument_key={encoded}"
    resp = requests.get(url, headers=headers)
    data = resp.json()
    if data.get('data') and len(data['data']) > 0:
        for k, v in data['data'].items():
            print(f"✅ {name}: ₹{v.get('last_price')}")
