"""
Web-based Real-Time Dashboard for Algo Trader
This provides a browser-based alternative to the PyQt6 desktop application
with fast data refresh and modern UI

Enhanced with MCX Commodity Support and Upstox API Integration
"""
import json
import random
import threading
import time
import os
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socketserver

# Try to import requests for API calls
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class UpstoxDataFetcher:
    """
    Fetches real-time data from Upstox API
    Supports NSE, BSE, and MCX exchanges
    """
    BASE_URL = "https://api.upstox.com/v2"
    
    def __init__(self, access_token=None):
        # Try environment variable first, then use hardcoded token
        self.access_token = access_token or os.environ.get('UPSTOX_ACCESS_TOKEN') or "eyJ0eXAiOiJKV1QiLCJrZXlfaWQiOiJza192MS4wIiwiYWxnIjoiSFMyNTYifQ.eyJzdWIiOiJBVjMwNjgiLCJqdGkiOiI2OTg1YTM1NTJjZTdiODdhOTAyZWQ4ZDQiLCJpc011bHRpQ2xpZW50IjpmYWxzZSwiaXNQbHVzUGxhbiI6dHJ1ZSwiaWF0IjoxNzcwMzY1NzgxLCJpc3MiOiJ1ZGFwaS1nYXRld2F5LXNlcnZpY2UiLCJleHAiOjE3NzA0MTUyMDB9.5hJRckhM7Dm0YI0Q8zka_MNC8ClJqAyIWD4dd9q9eNs"
        self.is_connected = False
        self.last_fetch_time = None
        
        # MCX Commodity instrument mappings (correct Upstox keys)
        self.mcx_instruments = {
            'CRUDEOIL': 'MCX_FO|472789',     # CRUDEOIL FUT 19 MAR 26
            'GOLD': 'MCX_FO|472784',          # GOLDTEN FUT 27 FEB 26
            'GOLDM': 'MCX_FO|472781',         # GOLDM FUT 05 MAR 26
            'SILVER': 'MCX_FO|464150',        # SILVER FUT 03 JUL 26
            'SILVERM': 'MCX_FO|451669',       # SILVERM FUT 27 FEB 26
            'NATURALGAS': 'MCX_FO|472791',    # NATURALGAS FUT
            'COPPER': 'MCX_FO|472793',        # COPPER FUT
        }
        
        # Index instrument mappings
        self.index_instruments = {
            'NIFTY': 'NSE_INDEX|Nifty 50',
            'BANKNIFTY': 'NSE_INDEX|Nifty Bank',
            'FINNIFTY': 'NSE_INDEX|Nifty Fin Service',
            'SENSEX': 'BSE_INDEX|SENSEX',
        }
        
    def _make_request(self, method, endpoint, data=None):
        """Make authenticated API request"""
        if not REQUESTS_AVAILABLE:
            return {'success': False, 'error': 'requests library not available'}
            
        if not self.access_token:
            return {'success': False, 'error': 'No access token configured'}
            
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=5)
            else:
                response = requests.post(url, headers=headers, json=data, timeout=5)
            
            result = response.json()
            
            if response.status_code == 200:
                self.is_connected = True
                self.last_fetch_time = datetime.now()
                return {'success': True, 'data': result.get('data', {})}
            else:
                return {'success': False, 'error': result.get('message', 'Unknown error')}
                
        except requests.Timeout:
            return {'success': False, 'error': 'Request timeout'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_market_quote(self, instrument_key):
        """Get market quote for an instrument"""
        import urllib.parse
        encoded_key = urllib.parse.quote(instrument_key, safe='')
        endpoint = f"/market-quote/ltp?instrument_key={encoded_key}"
        return self._make_request('GET', endpoint)
    
    def get_mcx_ltp(self, symbol):
        """Get LTP for MCX commodity"""
        instrument_key = self.mcx_instruments.get(symbol.upper())
        if not instrument_key:
            return None
        
        result = self.get_market_quote(instrument_key)
        if result.get('success') and result.get('data'):
            for key, quote in result['data'].items():
                return quote.get('last_price')
        return None
    
    def get_index_ltp(self, symbol):
        """Get LTP for index"""
        instrument_key = self.index_instruments.get(symbol.upper())
        if not instrument_key:
            return None
        
        result = self.get_market_quote(instrument_key)
        if result.get('success') and result.get('data'):
            for key, quote in result['data'].items():
                return quote.get('last_price')
        return None


class TradingDataSimulator:
    """
    Trading data simulator with MCX commodity support
    Uses real Upstox data when available, simulated data otherwise
    """
    def __init__(self):
        # Initialize Upstox fetcher
        self.upstox = UpstoxDataFetcher()
        
        # Index base prices
        self.nifty_base = 25200.50
        self.banknifty_base = 52800.75
        self.nifty_price = self.nifty_base
        self.banknifty_price = self.banknifty_base
        
        # MCX Commodity base prices (current levels - will be updated from API)
        self.mcx_prices = {
            'CRUDEOIL': {'price': 5755.0, 'base': 5755.0, 'lot_size': 100, 'unit': 'BBL'},
            'GOLD': {'price': 85000.0, 'base': 85000.0, 'lot_size': 100, 'unit': '10GM'},
            'GOLDM': {'price': 85200.0, 'base': 85200.0, 'lot_size': 10, 'unit': '1GM'},
            'SILVER': {'price': 95000.0, 'base': 95000.0, 'lot_size': 30, 'unit': 'KG'},
            'SILVERM': {'price': 95000.0, 'base': 95000.0, 'lot_size': 5, 'unit': 'KG'},
            'NATURALGAS': {'price': 280.0, 'base': 280.0, 'lot_size': 1250, 'unit': 'MMBTU'},
            'COPPER': {'price': 850.0, 'base': 850.0, 'lot_size': 2500, 'unit': 'KG'},
        }
        
        # Sample positions (mix of F&O and MCX)
        self.positions = [
            {"symbol": "CRUDEOIL25FEBFUT", "type": "LONG", "qty": 100, "avg_price": 6400.0, "source": "PAPER", "exchange": "MCX"},
            {"symbol": "GOLD25FEBFUT", "type": "LONG", "qty": 100, "avg_price": 78000.0, "source": "PAPER", "exchange": "MCX"},
            {"symbol": "SILVER25MARFUT", "type": "SHORT", "qty": 30, "avg_price": 93000.0, "source": "PAPER", "exchange": "MCX"},
        ]
        
        self.trades_today = 5
        self.realized_pnl = 2500.0
        self.last_update = datetime.now()
        self.use_real_data = False  # Toggle for real vs simulated data
        
    def update(self):
        """Update prices - uses real data if available, otherwise simulates"""
        # Try to fetch real data from Upstox
        if self.upstox.access_token:
            self._fetch_real_data()
        else:
            self._simulate_data()
        
        # Update position LTPs based on underlying
        self._update_positions()
        self.last_update = datetime.now()
    
    def _fetch_real_data(self):
        """Fetch real data from Upstox API"""
        # Fetch index data
        nifty_ltp = self.upstox.get_index_ltp('NIFTY')
        if nifty_ltp:
            self.nifty_price = float(nifty_ltp)
            self.use_real_data = True
        
        banknifty_ltp = self.upstox.get_index_ltp('BANKNIFTY')
        if banknifty_ltp:
            self.banknifty_price = float(banknifty_ltp)
        
        # Fetch MCX commodity data
        for symbol in self.mcx_prices:
            ltp = self.upstox.get_mcx_ltp(symbol)
            if ltp:
                self.mcx_prices[symbol]['price'] = float(ltp)
    
    def _simulate_data(self):
        """Simulate price movements when real data not available"""
        self.use_real_data = False
        
        # Random walk for indices
        self.nifty_price += random.uniform(-20, 20)
        self.banknifty_price += random.uniform(-50, 50)
        
        # Random walk for MCX commodities
        for symbol, data in self.mcx_prices.items():
            volatility = data['base'] * 0.002  # 0.2% volatility
            data['price'] += random.uniform(-volatility, volatility)
            data['price'] = max(data['base'] * 0.8, data['price'])  # Floor at 80% of base
    
    def _update_positions(self):
        """Update position LTPs and P&L"""
        for pos in self.positions:
            exchange = pos.get('exchange', 'NSE')
            symbol = pos['symbol']
            
            # Determine LTP based on exchange and underlying
            if exchange == 'MCX':
                # Extract underlying from symbol (e.g., CRUDEOIL25FEBFUT -> CRUDEOIL)
                underlying = ''.join([c for c in symbol if c.isalpha()]).replace('FUT', '')
                if underlying in self.mcx_prices:
                    pos['ltp'] = self.mcx_prices[underlying]['price']
                elif 'ltp' not in pos:
                    pos['ltp'] = pos['avg_price']
            else:
                if 'ltp' not in pos:
                    pos['ltp'] = pos['avg_price']
                pos['ltp'] = max(0.05, pos['ltp'] * (1 + random.uniform(-0.02, 0.02)))
            
            # Calculate P&L
            if pos['type'] == 'LONG':
                pos['pnl'] = (pos['ltp'] - pos['avg_price']) * pos['qty']
            else:
                pos['pnl'] = (pos['avg_price'] - pos['ltp']) * pos['qty']
            
            if pos['avg_price'] > 0:
                pos['pnl_pct'] = (pos['pnl'] / (pos['avg_price'] * pos['qty'])) * 100
            else:
                pos['pnl_pct'] = 0
                
            pos['change'] = pos['ltp'] - pos['avg_price']
            pos['change_pct'] = (pos['change'] / pos['avg_price'] * 100) if pos['avg_price'] > 0 else 0
        
    def get_data(self):
        """Get current market data as JSON"""
        total_unrealized = sum(p.get('pnl', 0) for p in self.positions)
        total_pnl = self.realized_pnl + total_unrealized
        
        # Calculate MCX data with changes
        mcx_data = {}
        for symbol, data in self.mcx_prices.items():
            change = data['price'] - data['base']
            change_pct = (change / data['base'] * 100) if data['base'] > 0 else 0
            mcx_data[symbol.lower()] = {
                "price": round(data['price'], 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "lot_size": data['lot_size'],
                "unit": data['unit']
            }
        
        return {
            "timestamp": self.last_update.strftime("%H:%M:%S"),
            "data_source": "LIVE" if self.use_real_data else "SIMULATED",
            "broker_connected": self.upstox.is_connected,
            "nifty": {
                "price": round(self.nifty_price, 2),
                "change": round(self.nifty_price - self.nifty_base, 2),
                "change_pct": round((self.nifty_price - self.nifty_base) / self.nifty_base * 100, 2)
            },
            "banknifty": {
                "price": round(self.banknifty_price, 2),
                "change": round(self.banknifty_price - self.banknifty_base, 2),
                "change_pct": round((self.banknifty_price - self.banknifty_base) / self.banknifty_base * 100, 2)
            },
            "mcx": mcx_data,
            "pnl": {
                "realized": round(self.realized_pnl, 2),
                "unrealized": round(total_unrealized, 2),
                "total": round(total_pnl, 2)
            },
            "stats": {
                "trades_today": self.trades_today,
                "win_rate": 60.0,
                "open_positions": len(self.positions)
            },
            "positions": [
                {
                    "symbol": p['symbol'],
                    "type": p['type'],
                    "qty": p['qty'],
                    "avg_price": round(p['avg_price'], 2),
                    "ltp": round(p.get('ltp', p['avg_price']), 2),
                    "change": round(p.get('change', 0), 2),
                    "change_pct": round(p.get('change_pct', 0), 2),
                    "pnl": round(p.get('pnl', 0), 2),
                    "pnl_pct": round(p.get('pnl_pct', 0), 2),
                    "source": p['source'],
                    "exchange": p.get('exchange', 'NSE')
                }
                for p in self.positions
            ]
        }
    
    def set_access_token(self, token):
        """Set Upstox access token for real data"""
        self.upstox.access_token = token
        self.use_real_data = True


simulator = TradingDataSimulator()

# HTML template for the dashboard
DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Algo Trader - Real-Time Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .header h1 { font-size: 24px; }
        .status-bar {
            display: flex;
            gap: 20px;
            align-items: center;
        }
        .live-indicator {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            background: rgba(76, 175, 80, 0.2);
            border: 1px solid #4CAF50;
            border-radius: 20px;
            font-weight: bold;
        }
        .live-dot {
            width: 10px;
            height: 10px;
            background: #4CAF50;
            border-radius: 50%;
            animation: pulse 1s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .data-age { color: #888; font-size: 14px; }
        .refresh-rate { color: #2196F3; font-size: 14px; }
        .clock {
            font-size: 24px;
            font-weight: bold;
            font-family: monospace;
            color: #2196F3;
            background: #1E1E1E;
            padding: 10px 20px;
            border-radius: 8px;
        }
        
        /* P&L Cards */
        .pnl-section {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }
        .pnl-card {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .pnl-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        .pnl-card.highlight {
            border: 2px solid #FFD700;
            background: rgba(255, 215, 0, 0.1);
        }
        .pnl-card h3 { font-size: 14px; color: #888; margin-bottom: 10px; }
        .pnl-value {
            font-size: 28px;
            font-weight: bold;
        }
        .pnl-value.positive { color: #4CAF50; }
        .pnl-value.negative { color: #F44336; }
        .pnl-value.neutral { color: #2196F3; }
        .pnl-value.orange { color: #FF9800; }
        .pnl-value.purple { color: #9C27B0; }
        
        /* Info Section */
        .info-section {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }
        .info-card {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .info-card h3 {
            font-size: 16px;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .info-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
        }
        .info-label { color: #888; }
        .info-value { font-weight: bold; }
        .info-value.green { color: #4CAF50; }
        .info-value.red { color: #F44336; }
        
        /* Index Prices */
        .index-price {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .price-main { font-size: 18px; font-weight: bold; }
        .price-change {
            font-size: 14px;
            padding: 2px 8px;
            border-radius: 4px;
        }
        .price-change.up { background: rgba(76, 175, 80, 0.2); color: #4CAF50; }
        .price-change.down { background: rgba(244, 67, 54, 0.2); color: #F44336; }
        
        /* Positions Table */
        .positions-section {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 20px;
        }
        .positions-section h3 {
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .live-badge {
            background: rgba(76, 175, 80, 0.2);
            color: #4CAF50;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        th {
            background: rgba(255,255,255,0.05);
            color: #888;
            font-weight: 500;
            font-size: 13px;
        }
        td { font-size: 14px; }
        .cell-positive { color: #4CAF50; }
        .cell-negative { color: #F44336; }
        .cell-paper { color: #FFD700; }
        .cell-live { color: #4CAF50; }
        .close-btn {
            background: #F44336;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
        }
        .close-btn:hover { background: #D32F2F; }
        
        /* Footer */
        .footer {
            display: flex;
            gap: 15px;
            align-items: center;
        }
        .refresh-btn {
            background: #2196F3;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            font-size: 14px;
        }
        .refresh-btn:hover { background: #1976D2; }
        .auto-refresh {
            display: flex;
            align-items: center;
            gap: 8px;
            color: #888;
        }
        .auto-refresh input { width: 18px; height: 18px; }
        
        /* Animation for price updates */
        @keyframes flash-green {
            0% { background: rgba(76, 175, 80, 0.3); }
            100% { background: transparent; }
        }
        @keyframes flash-red {
            0% { background: rgba(244, 67, 54, 0.3); }
            100% { background: transparent; }
        }
        .flash-up { animation: flash-green 0.5s ease-out; }
        .flash-down { animation: flash-red 0.5s ease-out; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Algo Trader - Real-Time Dashboard</h1>
        <div class="status-bar">
            <div class="live-indicator" id="liveIndicator">
                <div class="live-dot"></div>
                <span>LIVE</span>
            </div>
            <div class="data-age" id="dataAge">Data: 0s ago</div>
            <div class="refresh-rate">⚡ Refresh: 1s</div>
            <div class="clock" id="clock">00:00:00</div>
        </div>
    </div>
    
    <div class="pnl-section">
        <div class="pnl-card">
            <h3>Realized P&L</h3>
            <div class="pnl-value positive" id="realizedPnl">₹0.00</div>
        </div>
        <div class="pnl-card">
            <h3>Unrealized P&L</h3>
            <div class="pnl-value neutral" id="unrealizedPnl">₹0.00</div>
        </div>
        <div class="pnl-card highlight">
            <h3>Total P&L</h3>
            <div class="pnl-value" id="totalPnl">₹0.00</div>
        </div>
        <div class="pnl-card">
            <h3>Trades Today</h3>
            <div class="pnl-value orange" id="tradesToday">0</div>
        </div>
        <div class="pnl-card">
            <h3>Win Rate</h3>
            <div class="pnl-value purple" id="winRate">0%</div>
        </div>
    </div>
    
    <div class="info-section">
        <div class="info-card">
            <h3>📈 Account Summary</h3>
            <div class="info-row">
                <span class="info-label">Available Margin:</span>
                <span class="info-value green">₹5,00,000.00</span>
            </div>
            <div class="info-row">
                <span class="info-label">Used Margin:</span>
                <span class="info-value" style="color: #FF9800;">₹1,25,000.00</span>
            </div>
            <div class="info-row">
                <span class="info-label">Total Balance:</span>
                <span class="info-value" style="color: #2196F3;">₹6,25,000.00</span>
            </div>
            <div class="info-row">
                <span class="info-label">Broker Status:</span>
                <span class="info-value green">● Paper Trading</span>
            </div>
        </div>
        
        <div class="info-card">
            <h3>📊 Market Status (Live)</h3>
            <div class="info-row">
                <span class="info-label">Market:</span>
                <span class="info-value green">● Open</span>
            </div>
            <div class="info-row">
                <span class="info-label">NIFTY:</span>
                <div class="index-price">
                    <span class="price-main" id="niftyPrice">25,200.50</span>
                    <span class="price-change up" id="niftyChange">+0.00 (0.00%)</span>
                </div>
            </div>
            <div class="info-row">
                <span class="info-label">BANKNIFTY:</span>
                <div class="index-price">
                    <span class="price-main" id="bankniftyPrice">52,800.75</span>
                    <span class="price-change up" id="bankniftyChange">+0.00 (0.00%)</span>
                </div>
            </div>
            <div class="info-row">
                <span class="info-label">Last Update:</span>
                <span class="info-value" id="lastUpdate" style="color: #888;">--:--:--</span>
            </div>
            <div class="info-row">
                <span class="info-label">Data Source:</span>
                <span class="info-value" id="dataSource" style="color: #FFD700;">SIMULATED</span>
            </div>
        </div>
        
        <div class="info-card">
            <h3>📋 Quick Stats</h3>
            <div class="info-row">
                <span class="info-label">Open Positions:</span>
                <span class="info-value" id="openPositions">0</span>
            </div>
            <div class="info-row">
                <span class="info-label">Active Scanners:</span>
                <span class="info-value">0</span>
            </div>
            <div class="info-row">
                <span class="info-label">Active Strategies:</span>
                <span class="info-value">0</span>
            </div>
            <div class="info-row">
                <span class="info-label">Pending Orders:</span>
                <span class="info-value">0</span>
            </div>
        </div>
    </div>
    
    <!-- MCX Commodities Section -->
    <div class="info-section" style="margin-bottom: 20px;">
        <div class="info-card" style="grid-column: span 3;">
            <h3>🛢️ MCX Commodities (Real-Time)</h3>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px;">
                <div class="info-row" style="flex-direction: column; align-items: flex-start; background: rgba(255,152,0,0.1); padding: 12px; border-radius: 8px;">
                    <span class="info-label">CRUDE OIL</span>
                    <div class="index-price" style="margin-top: 5px;">
                        <span class="price-main" id="crudePrice">₹6,450.00</span>
                    </div>
                    <span class="price-change up" id="crudeChange" style="margin-top: 5px;">+0.00 (0.00%)</span>
                </div>
                <div class="info-row" style="flex-direction: column; align-items: flex-start; background: rgba(255,215,0,0.1); padding: 12px; border-radius: 8px;">
                    <span class="info-label">GOLD</span>
                    <div class="index-price" style="margin-top: 5px;">
                        <span class="price-main" id="goldPrice">₹78,500.00</span>
                    </div>
                    <span class="price-change up" id="goldChange" style="margin-top: 5px;">+0.00 (0.00%)</span>
                </div>
                <div class="info-row" style="flex-direction: column; align-items: flex-start; background: rgba(192,192,192,0.1); padding: 12px; border-radius: 8px;">
                    <span class="info-label">SILVER</span>
                    <div class="index-price" style="margin-top: 5px;">
                        <span class="price-main" id="silverPrice">₹92,500.00</span>
                    </div>
                    <span class="price-change up" id="silverChange" style="margin-top: 5px;">+0.00 (0.00%)</span>
                </div>
                <div class="info-row" style="flex-direction: column; align-items: flex-start; background: rgba(0,150,255,0.1); padding: 12px; border-radius: 8px;">
                    <span class="info-label">NATURAL GAS</span>
                    <div class="index-price" style="margin-top: 5px;">
                        <span class="price-main" id="natgasPrice">₹225.00</span>
                    </div>
                    <span class="price-change up" id="natgasChange" style="margin-top: 5px;">+0.00 (0.00%)</span>
                </div>
            </div>
        </div>
    </div>
    
    <div class="positions-section">
        <h3>Open Positions <span class="live-badge">Real-Time P&L</span></h3>
        <table>
            <thead>
                <tr>
                    <th>Symbol</th>
                    <th>Type</th>
                    <th>Qty</th>
                    <th>Avg Price</th>
                    <th>LTP</th>
                    <th>Change</th>
                    <th>P&L</th>
                    <th>P&L %</th>
                    <th>Source</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody id="positionsTable">
                <!-- Positions will be populated here -->
            </tbody>
        </table>
    </div>
    
    <div class="footer">
        <button class="refresh-btn" onclick="fetchData()">🔄 Refresh Now</button>
        <label class="auto-refresh">
            <input type="checkbox" id="autoRefresh" checked onchange="toggleAutoRefresh()">
            Auto-refresh (1s)
        </label>
    </div>
    
    <script>
        let autoRefreshInterval = null;
        let lastFetchTime = Date.now();
        let prevData = null;
        
        function updateClock() {
            const now = new Date();
            document.getElementById('clock').textContent = now.toLocaleTimeString('en-IN', { hour12: false });
        }
        
        function updateDataAge() {
            const age = Math.floor((Date.now() - lastFetchTime) / 1000);
            const ageEl = document.getElementById('dataAge');
            ageEl.textContent = `Data: ${age}s ago`;
            
            if (age < 3) {
                ageEl.style.color = '#4CAF50';
            } else if (age < 10) {
                ageEl.style.color = '#FF9800';
            } else {
                ageEl.style.color = '#F44336';
            }
        }
        
        function formatNumber(num, decimals = 2) {
            return num.toLocaleString('en-IN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
        }
        
        function updateUI(data) {
            // Update P&L
            const realizedEl = document.getElementById('realizedPnl');
            realizedEl.textContent = `₹${formatNumber(data.pnl.realized)}`;
            realizedEl.className = `pnl-value ${data.pnl.realized >= 0 ? 'positive' : 'negative'}`;
            
            const unrealizedEl = document.getElementById('unrealizedPnl');
            unrealizedEl.textContent = `₹${formatNumber(data.pnl.unrealized)}`;
            unrealizedEl.className = `pnl-value ${data.pnl.unrealized >= 0 ? 'positive' : 'negative'}`;
            
            const totalEl = document.getElementById('totalPnl');
            totalEl.textContent = `₹${formatNumber(data.pnl.total)}`;
            totalEl.className = `pnl-value ${data.pnl.total >= 0 ? 'positive' : 'negative'}`;
            
            // Update stats
            document.getElementById('tradesToday').textContent = data.stats.trades_today;
            document.getElementById('winRate').textContent = `${data.stats.win_rate}%`;
            document.getElementById('openPositions').textContent = data.stats.open_positions;
            
            // Update indices
            const niftyPriceEl = document.getElementById('niftyPrice');
            const prevNifty = prevData ? prevData.nifty.price : data.nifty.price;
            niftyPriceEl.textContent = formatNumber(data.nifty.price);
            if (data.nifty.price > prevNifty) {
                niftyPriceEl.classList.add('flash-up');
                setTimeout(() => niftyPriceEl.classList.remove('flash-up'), 500);
            } else if (data.nifty.price < prevNifty) {
                niftyPriceEl.classList.add('flash-down');
                setTimeout(() => niftyPriceEl.classList.remove('flash-down'), 500);
            }
            
            const niftyChangeEl = document.getElementById('niftyChange');
            niftyChangeEl.textContent = `${data.nifty.change >= 0 ? '+' : ''}${formatNumber(data.nifty.change)} (${data.nifty.change_pct >= 0 ? '+' : ''}${formatNumber(data.nifty.change_pct)}%)`;
            niftyChangeEl.className = `price-change ${data.nifty.change >= 0 ? 'up' : 'down'}`;
            
            const bankniftyPriceEl = document.getElementById('bankniftyPrice');
            bankniftyPriceEl.textContent = formatNumber(data.banknifty.price);
            
            const bankniftyChangeEl = document.getElementById('bankniftyChange');
            bankniftyChangeEl.textContent = `${data.banknifty.change >= 0 ? '+' : ''}${formatNumber(data.banknifty.change)} (${data.banknifty.change_pct >= 0 ? '+' : ''}${formatNumber(data.banknifty.change_pct)}%)`;
            bankniftyChangeEl.className = `price-change ${data.banknifty.change >= 0 ? 'up' : 'down'}`;
            
            // Update last update time
            document.getElementById('lastUpdate').textContent = data.timestamp;
            
            // Update data source indicator
            const dataSourceEl = document.getElementById('dataSource');
            if (data.data_source === 'LIVE') {
                dataSourceEl.textContent = 'LIVE (Upstox)';
                dataSourceEl.style.color = '#4CAF50';
            } else {
                dataSourceEl.textContent = 'SIMULATED';
                dataSourceEl.style.color = '#FFD700';
            }
            
            // Update MCX Commodities
            if (data.mcx) {
                // Crude Oil
                if (data.mcx.crudeoil) {
                    document.getElementById('crudePrice').textContent = `₹${formatNumber(data.mcx.crudeoil.price)}`;
                    const crudeChangeEl = document.getElementById('crudeChange');
                    crudeChangeEl.textContent = `${data.mcx.crudeoil.change >= 0 ? '+' : ''}${formatNumber(data.mcx.crudeoil.change)} (${data.mcx.crudeoil.change_pct >= 0 ? '+' : ''}${formatNumber(data.mcx.crudeoil.change_pct)}%)`;
                    crudeChangeEl.className = `price-change ${data.mcx.crudeoil.change >= 0 ? 'up' : 'down'}`;
                }
                
                // Gold
                if (data.mcx.gold) {
                    document.getElementById('goldPrice').textContent = `₹${formatNumber(data.mcx.gold.price)}`;
                    const goldChangeEl = document.getElementById('goldChange');
                    goldChangeEl.textContent = `${data.mcx.gold.change >= 0 ? '+' : ''}${formatNumber(data.mcx.gold.change)} (${data.mcx.gold.change_pct >= 0 ? '+' : ''}${formatNumber(data.mcx.gold.change_pct)}%)`;
                    goldChangeEl.className = `price-change ${data.mcx.gold.change >= 0 ? 'up' : 'down'}`;
                }
                
                // Silver
                if (data.mcx.silver) {
                    document.getElementById('silverPrice').textContent = `₹${formatNumber(data.mcx.silver.price)}`;
                    const silverChangeEl = document.getElementById('silverChange');
                    silverChangeEl.textContent = `${data.mcx.silver.change >= 0 ? '+' : ''}${formatNumber(data.mcx.silver.change)} (${data.mcx.silver.change_pct >= 0 ? '+' : ''}${formatNumber(data.mcx.silver.change_pct)}%)`;
                    silverChangeEl.className = `price-change ${data.mcx.silver.change >= 0 ? 'up' : 'down'}`;
                }
                
                // Natural Gas
                if (data.mcx.naturalgas) {
                    document.getElementById('natgasPrice').textContent = `₹${formatNumber(data.mcx.naturalgas.price)}`;
                    const natgasChangeEl = document.getElementById('natgasChange');
                    natgasChangeEl.textContent = `${data.mcx.naturalgas.change >= 0 ? '+' : ''}${formatNumber(data.mcx.naturalgas.change)} (${data.mcx.naturalgas.change_pct >= 0 ? '+' : ''}${formatNumber(data.mcx.naturalgas.change_pct)}%)`;
                    natgasChangeEl.className = `price-change ${data.mcx.naturalgas.change >= 0 ? 'up' : 'down'}`;
                }
            }
            
            // Update positions table
            const tableBody = document.getElementById('positionsTable');
            tableBody.innerHTML = '';
            
            data.positions.forEach((pos, idx) => {
                const row = document.createElement('tr');
                const exchangeBadge = pos.exchange === 'MCX' ? '<span style="color: #FF9800; font-size: 10px; margin-left: 5px;">[MCX]</span>' : '';
                row.innerHTML = `
                    <td><strong>${pos.symbol}</strong>${exchangeBadge}</td>
                    <td>${pos.type}</td>
                    <td>${pos.qty}</td>
                    <td>₹${formatNumber(pos.avg_price)}</td>
                    <td>₹${formatNumber(pos.ltp)}</td>
                    <td class="${pos.change >= 0 ? 'cell-positive' : 'cell-negative'}">${pos.change >= 0 ? '+' : ''}${formatNumber(pos.change)} (${pos.change_pct >= 0 ? '+' : ''}${formatNumber(pos.change_pct, 1)}%)</td>
                    <td class="${pos.pnl >= 0 ? 'cell-positive' : 'cell-negative'}">₹${formatNumber(pos.pnl)}</td>
                    <td class="${pos.pnl_pct >= 0 ? 'cell-positive' : 'cell-negative'}">${pos.pnl_pct >= 0 ? '+' : ''}${formatNumber(pos.pnl_pct)}%</td>
                    <td class="${pos.source === 'PAPER' ? 'cell-paper' : 'cell-live'}">${pos.source}</td>
                    <td><button class="close-btn" onclick="closePosition('${pos.symbol}')">Close</button></td>
                `;
                tableBody.appendChild(row);
            });
            
            prevData = data;
        }
        
        async function fetchData() {
            try {
                const response = await fetch('/api/data');
                const data = await response.json();
                lastFetchTime = Date.now();
                updateUI(data);
            } catch (error) {
                console.error('Error fetching data:', error);
            }
        }
        
        function closePosition(symbol) {
            alert(`Closing position: ${symbol}`);
        }
        
        function toggleAutoRefresh() {
            const checkbox = document.getElementById('autoRefresh');
            const indicator = document.getElementById('liveIndicator');
            
            if (checkbox.checked) {
                startAutoRefresh();
                indicator.innerHTML = '<div class="live-dot"></div><span>LIVE</span>';
                indicator.style.background = 'rgba(76, 175, 80, 0.2)';
                indicator.style.borderColor = '#4CAF50';
            } else {
                stopAutoRefresh();
                indicator.innerHTML = '<span>⏸️ PAUSED</span>';
                indicator.style.background = 'rgba(255, 152, 0, 0.2)';
                indicator.style.borderColor = '#FF9800';
            }
        }
        
        function startAutoRefresh() {
            if (autoRefreshInterval) clearInterval(autoRefreshInterval);
            autoRefreshInterval = setInterval(fetchData, 1000);
        }
        
        function stopAutoRefresh() {
            if (autoRefreshInterval) {
                clearInterval(autoRefreshInterval);
                autoRefreshInterval = null;
            }
        }
        
        // Initialize
        setInterval(updateClock, 1000);
        setInterval(updateDataAge, 1000);
        updateClock();
        fetchData();
        startAutoRefresh();
    </script>
</body>
</html>
'''

class DashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode())
        elif self.path == '/api/data':
            simulator.update()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(simulator.get_data()).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress HTTP request logs
        pass

class ReusableTCPServer(socketserver.TCPServer):
    """TCP Server that allows address reuse"""
    allow_reuse_address = True


def run_server(port=12000):
    """Run the web dashboard server"""
    with ReusableTCPServer(("", port), DashboardHandler) as httpd:
        print(f"\n{'='*60}")
        print(f"🚀 Algo Trader Real-Time Dashboard with MCX Support")
        print(f"{'='*60}")
        print(f"✅ Server running on port {port}")
        print(f"🌐 Open in browser: https://work-1-sszlqpxmyfyoffir.prod-runtime.all-hands.dev")
        print(f"{'='*60}")
        print(f"\n📊 Features:")
        print(f"   - Real-time data refresh every 1 second")
        print(f"   - MCX Commodities: CRUDE OIL, GOLD, SILVER, NATURAL GAS")
        print(f"   - Live P&L tracking with color indicators")
        print(f"   - Data freshness indicator")
        print(f"   - Upstox API integration ready")
        print(f"\nPress Ctrl+C to stop the server...")
        print(f"{'='*60}\n")
        httpd.serve_forever()


if __name__ == "__main__":
    run_server()
