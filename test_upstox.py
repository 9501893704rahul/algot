import requests

# Correct Access Token
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiJBVjMwNjgiLCJqdGkiOiI2OTg1YTM1NTJjZTdiODdhOTAyZWQ4ZDQiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6dHJ1ZSwiaWF0IjoxNzcwMzY1NzgxLCJpc3MiOiJ1ZGFwaS1nYXRld2F5LXNlcnZpY2UiLCJleHAiOjE3NzA0MTUyMDB9.5hJRckhM7Dm0YI0Q8zka_MNC8ClJqAyIWD4dd9q9eNs"

headers = {
    'Authorization': f'Bearer {ACCESS_TOKEN}',
    'Accept': 'application/json'
}

# Test 1: User Profile
print("=" * 50)
print("Testing User Profile API...")
response = requests.get('https://api.upstox.com/v2/user/profile', headers=headers)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:300]}")

# Test 2: MCX Market Quote (GOLD)
print("\n" + "=" * 50)
print("Testing MCX GOLD Quote...")
import urllib.parse
instrument_key = urllib.parse.quote("MCX_FO|GOLD", safe='')
response = requests.get(f'https://api.upstox.com/v2/market-quote/ltp?instrument_key={instrument_key}', headers=headers)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:300]}")
