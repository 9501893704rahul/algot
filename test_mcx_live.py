import requests
import urllib.parse

ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiJBVjMwNjgiLCJqdGkiOiI2OTg1YTM1NTJjZTdiODdhOTAyZWQ4ZDQiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6dHJ1ZSwiaWF0IjoxNzcwMzY1NzgxLCJpc3MiOiJ1ZGFwaS1nYXRld2F5LXNlcnZpY2UiLCJleHAiOjE3NzA0MTUyMDB9.5hJRckhM7Dm0YI0Q8zka_MNC8ClJqAyIWD4dd9q9eNs"

headers = {
    'Authorization': f'Bearer {ACCESS_TOKEN}',
    'Accept': 'application/json'
}

# Test different MCX instrument key formats
test_keys = [
    "MCX_FO|GOLDM25FEBFUT",
    "MCX_FO|GOLD25FEBFUT", 
    "MCX_FO|CRUDEOIL25FEBFUT",
    "MCX_FO|SILVERM25MARFUT",
    "NSE_INDEX|Nifty 50",
    "NSE_INDEX|Nifty Bank",
]

print("Testing MCX instrument keys...\n")
for key in test_keys:
    encoded = urllib.parse.quote(key, safe='')
    url = f"https://api.upstox.com/v2/market-quote/ltp?instrument_key={encoded}"
    resp = requests.get(url, headers=headers)
    data = resp.json()
    print(f"{key}")
    print(f"  Status: {resp.status_code}")
    if data.get('data'):
        for k, v in data['data'].items():
            print(f"  LTP: {v.get('last_price', 'N/A')}")
    else:
        print(f"  Response: {data}")
    print()
