import requests
import urllib.parse

ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiJBVjMwNjgiLCJqdGkiOiI2OTg1YTM1NTJjZTdiODdhOTAyZWQ4ZDQiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6dHJ1ZSwiaWF0IjoxNzcwMzY1NzgxLCJpc3MiOiJ1ZGFwaS1nYXRld2F5LXNlcnZpY2UiLCJleHAiOjE3NzA0MTUyMDB9.5hJRckhM7Dm0YI0Q8zka_MNC8ClJqAyIWD4dd9q9eNs"

headers = {
    'Authorization': f'Bearer {ACCESS_TOKEN}',
    'Accept': 'application/json'
}

# Try different MCX formats - current month futures
mcx_formats = [
    # Feb 2025 expiry formats
    "MCX_FO|GOLDM25FEBFUT",
    "MCX_FO|GOLDM25FEB25FUT",
    "MCX_FO|GOLDM25-02-2025",
    "MCX_FO|438103",  # Try numeric instrument token
    
    # Try crude
    "MCX_FO|CRUDEOIL25FEBFUT",
    "MCX_FO|CRUDEOILM25FEBFUT",
    
    # Try with instrument search API
]

print("Testing MCX formats...\n")
for key in mcx_formats:
    encoded = urllib.parse.quote(key, safe='')
    url = f"https://api.upstox.com/v2/market-quote/ltp?instrument_key={encoded}"
    resp = requests.get(url, headers=headers)
    data = resp.json()
    if data.get('data') and len(data['data']) > 0:
        print(f"✅ FOUND: {key}")
        for k, v in data['data'].items():
            print(f"   LTP: {v.get('last_price')}")
    else:
        print(f"❌ {key}")

# Try getting instrument list from Upstox
print("\n\nSearching instrument master...")
# Download instrument master for MCX
import io
url = "https://assets.upstox.com/market-quote/instruments/exchange/MCX.json.gz"
try:
    import gzip
    resp = requests.get(url)
    if resp.status_code == 200:
        import json
        data = gzip.decompress(resp.content)
        instruments = json.loads(data)
        
        # Find GOLD futures
        print("\nMCX GOLD Instruments:")
        gold_found = [i for i in instruments if 'GOLD' in i.get('trading_symbol', '') and 'FUT' in i.get('instrument_type', '')][:5]
        for inst in gold_found:
            print(f"  {inst.get('trading_symbol')} -> {inst.get('instrument_key')}")
        
        # Find CRUDE futures
        print("\nMCX CRUDE Instruments:")
        crude_found = [i for i in instruments if 'CRUDE' in i.get('trading_symbol', '') and 'FUT' in i.get('instrument_type', '')][:5]
        for inst in crude_found:
            print(f"  {inst.get('trading_symbol')} -> {inst.get('instrument_key')}")
            
        # Find SILVER futures
        print("\nMCX SILVER Instruments:")
        silver_found = [i for i in instruments if 'SILVER' in i.get('trading_symbol', '') and 'FUT' in i.get('instrument_type', '')][:5]
        for inst in silver_found:
            print(f"  {inst.get('trading_symbol')} -> {inst.get('instrument_key')}")
except Exception as e:
    print(f"Error: {e}")
