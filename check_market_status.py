import requests
from datetime import datetime
import pytz

ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiJBVjMwNjgiLCJqdGkiOiI2OTg1YTM1NTJjZTdiODdhOTAyZWQ4ZDQiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6dHJ1ZSwiaWF0IjoxNzcwMzY1NzgxLCJpc3MiOiJ1ZGFwaS1nYXRld2F5LXNlcnZpY2UiLCJleHAiOjE3NzA0MTUyMDB9.5hJRckhM7Dm0YI0Q8zka_MNC8ClJqAyIWD4dd9q9eNs"

headers = {
    'Authorization': f'Bearer {ACCESS_TOKEN}',
    'Accept': 'application/json'
}

# Check market status
print("Checking Market Status...")
url = "https://api.upstox.com/v2/market/status/MCX"
resp = requests.get(url, headers=headers)
print(f"MCX Status: {resp.json()}")

# Get current IST time
ist = pytz.timezone('Asia/Kolkata')
now_ist = datetime.now(ist)
print(f"\nCurrent IST Time: {now_ist.strftime('%H:%M:%S')}")

print(f"""
Market Timings:
- NSE/BSE: 9:15 AM - 3:30 PM (CLOSED)
- MCX Morning: 9:00 AM - 5:00 PM (CLOSED)
- MCX Evening: 5:00 PM - 11:30 PM (Will open at 5 PM)

Current Time: {now_ist.strftime('%I:%M %p')} IST
""")
