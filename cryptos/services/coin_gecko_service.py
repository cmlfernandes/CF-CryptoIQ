import requests
from django.conf import settings
from datetime import datetime, timedelta
import time
from .coin_id_mapper import get_coingecko_id


class CoinGeckoService:
    def __init__(self):
        self.base_url = settings.COINGECKO_API_URL
        self.session = requests.Session()
        self.last_request_time = 0
        self.min_request_interval = 2.0  # Rate limit: ~30 requests/minute (more conservative)

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
        except requests.exceptions.RequestException as e:
            print(f"CoinGecko API error: {e}")
            return None

    def _find_coin_id(self, symbol):
        """Try to find coin ID by searching if not in mapping"""
        coin_id = get_coingecko_id(symbol)
        # If it's just lowercase symbol, try to search for it
        if coin_id == symbol.lower():
            search_results = self.search_crypto(symbol)
            if search_results:
                # Find the best match - prefer exact symbol match
                symbol_upper = symbol.upper()
                for result in search_results:
                    result_symbol = result.get('symbol', '').upper()
                    if result_symbol == symbol_upper:
                        return result.get('id', coin_id)
                # If no exact match, return first result
                return search_results[0].get('id', coin_id)
        return coin_id

    def get_current_price(self, symbol):
        coin_id = self._find_coin_id(symbol)
        endpoint = "simple/price"
        params = {
            'ids': coin_id,
            'vs_currencies': 'usd',
            'include_24hr_change': 'true',
            'include_24hr_vol': 'true',
            'include_last_updated_at': 'true'
        }
        data = self._make_request(endpoint, params)
        if data and coin_id in data:
            price_data = data[coin_id]
            return {
                'price': price_data.get('usd', 0),
                'change_24h': price_data.get('usd_24h_change', 0),
                'volume_24h': price_data.get('usd_24h_vol', 0),
                'last_updated': price_data.get('last_updated_at', 0)
            }
        return None

    def get_historical_data(self, symbol, days=30):
        coin_id = self._find_coin_id(symbol)
        endpoint = f"coins/{coin_id}/market_chart"
        params = {
            'vs_currency': 'usd',
            'days': days,
            'interval': 'daily' if days > 90 else 'hourly'
        }
        data = self._make_request(endpoint, params)
        if data:
            prices = []
            volumes = []
            market_caps = []
            
            if 'prices' in data:
                for item in data['prices']:
                    timestamp = datetime.fromtimestamp(item[0] / 1000)
                    price = item[1]
                    prices.append({
                        'timestamp': timestamp,
                        'price': price
                    })
            
            if 'total_volumes' in data:
                for item in data['total_volumes']:
                    volumes.append(item[1])
            
            if 'market_caps' in data:
                for item in data['market_caps']:
                    market_caps.append(item[1])
            
            return {
                'prices': prices,
                'volumes': volumes,
                'market_caps': market_caps
            }
        return None

    def get_market_data(self, symbol):
        coin_id = self._find_coin_id(symbol)
        endpoint = f"coins/{coin_id}"
        params = {
            'localization': 'false',
            'tickers': 'false',
            'market_data': 'true',
            'community_data': 'false',
            'developer_data': 'false',
            'sparkline': 'false'
        }
        data = self._make_request(endpoint, params)
        if data and 'market_data' in data:
            market_data = data['market_data']
            return {
                'current_price': market_data.get('current_price', {}).get('usd', 0),
                'high_24h': market_data.get('high_24h', {}).get('usd', 0),
                'low_24h': market_data.get('low_24h', {}).get('usd', 0),
                'price_change_24h': market_data.get('price_change_24h', 0),
                'price_change_percentage_24h': market_data.get('price_change_percentage_24h', 0),
                'total_volume': market_data.get('total_volume', {}).get('usd', 0),
                'market_cap': market_data.get('market_cap', {}).get('usd', 0),
            }
        return None

    def search_crypto(self, query):
        endpoint = "search"
        params = {'query': query}
        data = self._make_request(endpoint, params)
        if data and 'coins' in data:
            return data['coins']
        return []

