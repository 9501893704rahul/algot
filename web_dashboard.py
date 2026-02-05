"""
Web-based Real-Time Dashboard for Algo Trader
This provides a browser-based alternative to the PyQt6 desktop application
with fast data refresh and modern UI
"""
import json
import random
import threading
import time
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socketserver

# Generate sample data for demonstration
class TradingDataSimulator:
    def __init__(self):
        self.nifty_price = 25200.50
        self.banknifty_price = 52800.75
        self.positions = [
            {"symbol": "NIFTY24FEB25200CE", "type": "LONG", "qty": 50, "avg_price": 150.0, "source": "PAPER"},
            {"symbol": "BANKNIFTY24FEB52800PE", "type": "SHORT", "qty": 25, "avg_price": 280.0, "source": "PAPER"},
            {"symbol": "RELIANCE", "type": "LONG", "qty": 100, "avg_price": 2950.0, "source": "PAPER"},
        ]
        self.trades_today = 5
        self.realized_pnl = 2500.0
        self.last_update = datetime.now()
        
    def update(self):
        """Simulate price movements"""
        # Random walk for indices
        self.nifty_price += random.uniform(-20, 20)
        self.banknifty_price += random.uniform(-50, 50)
        
        # Update position LTPs
        for pos in self.positions:
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
        
        self.last_update = datetime.now()
        
    def get_data(self):
        """Get current market data as JSON"""
        total_unrealized = sum(p.get('pnl', 0) for p in self.positions)
        total_pnl = self.realized_pnl + total_unrealized
        
        return {
            "timestamp": self.last_update.strftime("%H:%M:%S"),
            "nifty": {
                "price": round(self.nifty_price, 2),
                "change": round(self.nifty_price - 25200.50, 2),
                "change_pct": round((self.nifty_price - 25200.50) / 25200.50 * 100, 2)
            },
            "banknifty": {
                "price": round(self.banknifty_price, 2),
                "change": round(self.banknifty_price - 52800.75, 2),
                "change_pct": round((self.banknifty_price - 52800.75) / 52800.75 * 100, 2)
            },
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
                    "source": p['source']
                }
                for p in self.positions
            ]
        }

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
            
            // Update positions table
            const tableBody = document.getElementById('positionsTable');
            tableBody.innerHTML = '';
            
            data.positions.forEach((pos, idx) => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td><strong>${pos.symbol}</strong></td>
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

def run_server(port=12000):
    """Run the web dashboard server"""
    with socketserver.TCPServer(("", port), DashboardHandler) as httpd:
        print(f"\n{'='*60}")
        print(f"🚀 Algo Trader Real-Time Dashboard")
        print(f"{'='*60}")
        print(f"✅ Server running on port {port}")
        print(f"🌐 Open in browser: https://work-1-bbacfugwhxrjvjab.prod-runtime.all-hands.dev")
        print(f"{'='*60}")
        print(f"\n📊 Features:")
        print(f"   - Real-time data refresh every 1 second")
        print(f"   - Live P&L tracking with color indicators")
        print(f"   - Data freshness indicator")
        print(f"   - Price change animations")
        print(f"   - Auto-refresh toggle")
        print(f"\nPress Ctrl+C to stop the server...")
        print(f"{'='*60}\n")
        httpd.serve_forever()

if __name__ == "__main__":
    run_server()
