import requests
from django.conf import settings
from datetime import datetime
import time


class BinanceService:
    def __init__(self):
        self.base_url = settings.BINANCE_API_URL
        self.session = requests.Session()
        self.last_request_time = 0
        self.min_request_interval = 0.1  # Binance allows higher rate

    def _rate_limit(self):
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last_request)
        self.last_request_time = time.time()

    def _make_request(self, endpoint, params=None):
        self._rate_limit()
        url = f"{self.base_url}/{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                # Invalid symbol, try to get error message
                try:
                    error_data = e.response.json()
                    print(f"Binance API error for {params.get('symbol', 'unknown')}: {error_data.get('msg', str(e))}")
                except:
                    print(f"Binance API error: {e}")
            else:
                print(f"Binance API error: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Binance API error: {e}")
            return None

    def _symbol_to_binance(self, symbol):
        # Remove any spaces and convert to uppercase
        symbol_clean = symbol.strip().upper().replace(' ', '')
        return f"{symbol_clean}USDT"

    def get_ticker(self, symbol):
        binance_symbol = self._symbol_to_binance(symbol)
        endpoint = "ticker/24hr"
        params = {'symbol': binance_symbol}
        data = self._make_request(endpoint, params)
        if data:
            return {
                'symbol': symbol,
                'price': float(data.get('lastPrice', 0)),
                'open_price': float(data.get('openPrice', 0)),
                'high': float(data.get('highPrice', 0)),
                'low': float(data.get('lowPrice', 0)),
                'volume': float(data.get('volume', 0)),
                'quote_volume': float(data.get('quoteVolume', 0)),
                'price_change': float(data.get('priceChange', 0)),
                'price_change_percent': float(data.get('priceChangePercent', 0)),
                'count': int(data.get('count', 0))
            }
        return None

    def get_klines(self, symbol, interval='1d', limit=100):
        binance_symbol = self._symbol_to_binance(symbol)
        endpoint = "klines"
        params = {
            'symbol': binance_symbol,
            'interval': interval,
            'limit': limit
        }
        data = self._make_request(endpoint, params)
        if data:
            klines = []
            for kline in data:
                klines.append({
                    'timestamp': datetime.fromtimestamp(kline[0] / 1000),
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5]),
                    'close_time': datetime.fromtimestamp(kline[6] / 1000),
                    'quote_volume': float(kline[7]),
                    'trades': int(kline[8]),
                    'taker_buy_base': float(kline[9]),
                    'taker_buy_quote': float(kline[10])
                })
            return klines
        return None

    def get_24h_stats(self, symbol):
        return self.get_ticker(symbol)

