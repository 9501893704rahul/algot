import requests
import urllib.parse

ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiJBVjMwNjgiLCJqdGkiOiI2OTg1YTM1NTJjZTdiODdhOTAyZWQ4ZDQiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6dHJ1ZSwiaWF0IjoxNzcwMzY1NzgxLCJpc3MiOiJ1ZGFwaS1nYXRld2F5LXNlcnZpY2UiLCJleHAiOjE3NzA0MTUyMDB9.5hJRckhM7Dm0YI0Q8zka_MNC8ClJqAyIWD4dd9q9eNs"

headers = {
    'Authorization': f'Bearer {ACCESS_TOKEN}',
    'Accept': 'application/json'
}

# Search for instruments
print("Searching for MCX GOLD instruments...")
url = "https://api.upstox.com/v2/market-quote/quotes?instrument_key=MCX_FO%7CGOLD"
resp = requests.get(url, headers=headers)
print(resp.json())

# Try full market quote
print("\n\nTrying full quote for NIFTY...")
url = "https://api.upstox.com/v2/market-quote/quotes?instrument_key=NSE_INDEX%7CNifty%2050"
resp = requests.get(url, headers=headers)
data = resp.json()
print(f"Status: {data.get('status')}")
if data.get('data'):
    for k, v in data['data'].items():
        print(f"Key: {k}")
        print(f"LTP: {v.get('last_price')}")
        print(f"Open: {v.get('ohlc', {}).get('open')}")
        print(f"Close: {v.get('ohlc', {}).get('close')}")
