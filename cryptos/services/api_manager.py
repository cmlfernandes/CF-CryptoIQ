from .coin_gecko_service import CoinGeckoService
from .binance_service import BinanceService
from datetime import datetime, timedelta
from django.utils import timezone


class APIManager:
    def __init__(self):
        self.coingecko = CoinGeckoService()
        self.binance = BinanceService()
        self.cache = {}
        self.cache_duration = timedelta(minutes=5)

    def _get_from_cache(self, key):
        if key in self.cache:
            data, timestamp = self.cache[key]
            if timezone.now() - timestamp < self.cache_duration:
                return data
            else:
                del self.cache[key]
        return None

    def _set_cache(self, key, data):
        self.cache[key] = (data, timezone.now())

    def get_current_price(self, symbol):
        # Clean symbol - remove spaces and convert to uppercase
        symbol_clean = symbol.strip().upper().replace(' ', '')
        cache_key = f"price_{symbol_clean}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        # Try Binance first (faster, real-time)
        price_data = self.binance.get_ticker(symbol_clean)
        if price_data and price_data.get('price', 0) > 0:
            result = {
                'price': price_data['price'],
                'source': 'binance',
                'high_24h': price_data.get('high', 0),
                'low_24h': price_data.get('low', 0),
                'volume_24h': price_data.get('quote_volume', 0),
                'change_24h': price_data.get('price_change_percent', 0)
            }
            self._set_cache(cache_key, result)
            return result

        # Fallback to CoinGecko (with delay to avoid rate limits)
        import time
        time.sleep(0.5)  # Small delay before CoinGecko request
        price_data = self.coingecko.get_current_price(symbol_clean)
        if price_data and price_data.get('price', 0) > 0:
            result = {
                'price': price_data['price'],
                'source': 'coingecko',
                'high_24h': 0,
                'low_24h': 0,
                'volume_24h': price_data.get('volume_24h', 0),
                'change_24h': price_data.get('change_24h', 0)
            }
            self._set_cache(cache_key, result)
            return result

        return None

    def get_historical_data(self, symbol, days=30):
        # Clean symbol
        symbol_clean = symbol.strip().upper().replace(' ', '')
        cache_key = f"historical_{symbol_clean}_{days}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        # Try Binance first for recent data
        if days <= 30:
            interval_map = {
                1: '1h',
                7: '4h',
                30: '1d'
            }
            interval = interval_map.get(days, '1d')
            limit = min(days * 24 if interval == '1h' else days, 100)
            
            klines = self.binance.get_klines(symbol_clean, interval=interval, limit=limit)
            if klines:
                result = {
                    'data': klines,
                    'source': 'binance'
                }
                self._set_cache(cache_key, result)
                return result

        # Fallback to CoinGecko for longer history
        historical = self.coingecko.get_historical_data(symbol_clean, days=days)
        if historical:
            result = {
                'data': historical,
                'source': 'coingecko'
            }
            self._set_cache(cache_key, result)
            return result

        return None

    def get_market_data(self, symbol):
        # Clean symbol
        symbol_clean = symbol.strip().upper().replace(' ', '')
        cache_key = f"market_{symbol_clean}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        # Try Binance first
        ticker = self.binance.get_ticker(symbol_clean)
        if ticker:
            result = {
                'current_price': ticker['price'],
                'high_24h': ticker['high'],
                'low_24h': ticker['low'],
                'volume_24h': ticker['quote_volume'],
                'price_change_24h': ticker['price_change'],
                'price_change_percentage_24h': ticker['price_change_percent'],
                'source': 'binance'
            }
            self._set_cache(cache_key, result)
            return result

        # Fallback to CoinGecko
        market_data = self.coingecko.get_market_data(symbol_clean)
        if market_data:
            result = {
                **market_data,
                'source': 'coingecko'
            }
            self._set_cache(cache_key, result)
            return result

        return None

    def search_crypto(self, query):
        # Use CoinGecko for search as it has better search functionality
        return self.coingecko.search_crypto(query)

