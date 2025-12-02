import threading
import time
from django.utils import timezone
from datetime import timedelta
from cryptos.models import AppSettings, Crypto, PriceHistory, TechnicalAnalysis
from cryptos.services.api_manager import APIManager
from cryptos.services.technical_indicators import TechnicalIndicators
from cryptos.services.ollama_analyzer import OllamaAnalyzer
import pandas as pd
import os


class BackgroundTaskManager:
    _instance = None
    _lock = threading.Lock()
    _price_update_thread = None
    _analysis_thread = None
    _running = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self._running = False

    def start(self):
        """Start background tasks"""
        if self._running:
            return
        
        self._running = True
        settings = AppSettings.get_settings()
        
        # Start price update thread if enabled
        if settings.auto_update_prices:
            self._start_price_updates()
        
        # Start analysis thread if enabled
        if settings.auto_run_analysis:
            self._start_analysis()

    def stop(self):
        """Stop background tasks"""
        self._running = False
        if self._price_update_thread:
            self._price_update_thread.join(timeout=5)
        if self._analysis_thread:
            self._analysis_thread.join(timeout=5)

    def _start_price_updates(self):
        """Start price update background thread"""
        def price_update_loop():
            api_manager = APIManager()
            while self._running:
                try:
                    settings = AppSettings.get_settings()
                    if not settings.auto_update_prices:
                        break
                    
                    # Update prices for all cryptos
                    cryptos = Crypto.objects.all()
                    for crypto in cryptos:
                        try:
                            price_data = api_manager.get_current_price(crypto.symbol)
                            if price_data:
                                market_data = api_manager.get_market_data(crypto.symbol)
                                
                                price = price_data['price']
                                high = market_data.get('high_24h', price) if market_data else price
                                low = market_data.get('low_24h', price) if market_data else price
                                volume = price_data.get('volume_24h', 0)
                                
                                PriceHistory.objects.create(
                                    crypto=crypto,
                                    timestamp=timezone.now(),
                                    price=price,
                                    volume=volume,
                                    high=high,
                                    low=low,
                                    open_price=price,
                                    close_price=price
                                )
                        except Exception as e:
                            print(f"Error updating price for {crypto.symbol}: {e}")
                    
                    # Update last update time
                    settings.last_price_update = timezone.now()
                    settings.save(update_fields=['last_price_update'])
                    
                    # Wait for next interval
                    interval_seconds = settings.price_update_interval * 60
                    for _ in range(interval_seconds):
                        if not self._running:
                            break
                        time.sleep(1)
                        
                except Exception as e:
                    print(f"Error in price update loop: {e}")
                    time.sleep(60)  # Wait 1 minute before retrying
        
        self._price_update_thread = threading.Thread(target=price_update_loop, daemon=True)
        self._price_update_thread.start()

    def _start_analysis(self):
        """Start analysis background thread"""
        def analysis_loop():
            api_manager = APIManager()
            ollama_analyzer = OllamaAnalyzer()
            
            while self._running:
                try:
                    settings = AppSettings.get_settings()
                    if not settings.auto_run_analysis:
                        break
                    
                    # Update Ollama settings from AppSettings
                    ollama_analyzer.update_config(
                        base_url=settings.ollama_base_url,
                        model=settings.ollama_model
                    )
                    
                    # Run analysis for all cryptos
                    cryptos = Crypto.objects.all()
                    for crypto in cryptos:
                        try:
                            # Get current price
                            price_data = api_manager.get_current_price(crypto.symbol)
                            if not price_data:
                                continue
                            
                            current_price = price_data['price']
                            
                            # Get historical data
                            historical_data = api_manager.get_historical_data(crypto.symbol, days=settings.historical_days)
                            if not historical_data or 'data' not in historical_data:
                                continue
                            
                            # Convert to DataFrame
                            if historical_data['source'] == 'binance':
                                klines = historical_data['data']
                                df_data = []
                                for kline in klines:
                                    df_data.append({
                                        'timestamp': kline['timestamp'],
                                        'open': kline['open'],
                                        'high': kline['high'],
                                        'low': kline['low'],
                                        'close': kline['close'],
                                        'volume': kline['volume']
                                    })
                                df = pd.DataFrame(df_data)
                            else:
                                prices = historical_data['data'].get('prices', [])
                                df_data = []
                                for price_point in prices:
                                    df_data.append({
                                        'timestamp': price_point['timestamp'],
                                        'open': price_point['price'],
                                        'high': price_point['price'],
                                        'low': price_point['price'],
                                        'close': price_point['price'],
                                        'volume': 0
                                    })
                                df = pd.DataFrame(df_data)
                            
                            if df.empty:
                                continue
                            
                            # Calculate indicators
                            tech_indicators = TechnicalIndicators(df)
                            indicators = tech_indicators.get_latest_values()
                            
                            if not indicators:
                                continue
                            
                            # Run Ollama analysis
                            try:
                                analysis_result = ollama_analyzer.analyze_with_ollama(
                                    indicators,
                                    crypto.symbol,
                                    current_price
                                )
                                
                                # Save analysis
                                TechnicalAnalysis.objects.update_or_create(
                                    crypto=crypto,
                                    defaults={
                                        'indicators': indicators,
                                        'recommendation': analysis_result['recommendation'],
                                        'confidence_score': analysis_result['confidence_score'],
                                        'ollama_reasoning': analysis_result['reasoning'],
                                        'analysis_date': timezone.now()
                                    }
                                )
                            except Exception as e:
                                # If Ollama fails, save indicators with default analysis
                                TechnicalAnalysis.objects.update_or_create(
                                    crypto=crypto,
                                    defaults={
                                        'indicators': indicators,
                                        'recommendation': 'hold',
                                        'confidence_score': 0,
                                        'ollama_reasoning': f'Ollama analysis unavailable: {str(e)}',
                                        'analysis_date': timezone.now()
                                    }
                                )
                        except Exception as e:
                            print(f"Error analyzing {crypto.symbol}: {e}")
                    
                    # Update last analysis time
                    settings.last_analysis_run = timezone.now()
                    settings.save(update_fields=['last_analysis_run'])
                    
                    # Wait for next interval
                    interval_seconds = settings.analysis_interval * 60
                    for _ in range(interval_seconds):
                        if not self._running:
                            break
                        time.sleep(1)
                        
                except Exception as e:
                    print(f"Error in analysis loop: {e}")
                    time.sleep(300)  # Wait 5 minutes before retrying
        
        self._analysis_thread = threading.Thread(target=analysis_loop, daemon=True)
        self._analysis_thread.start()

    def restart(self):
        """Restart background tasks with current settings"""
        self.stop()
        time.sleep(1)
        self.start()

