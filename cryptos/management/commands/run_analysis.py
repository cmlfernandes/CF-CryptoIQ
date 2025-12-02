from django.core.management.base import BaseCommand
from cryptos.models import Crypto, TechnicalAnalysis
from cryptos.services.api_manager import APIManager
from cryptos.services.technical_indicators import TechnicalIndicators
from cryptos.services.ollama_analyzer import OllamaAnalyzer
import pandas as pd
from django.utils import timezone


class Command(BaseCommand):
    help = 'Run technical analysis for all registered cryptocurrencies'

    def add_arguments(self, parser):
        parser.add_argument(
            '--symbol',
            type=str,
            help='Run analysis for a specific cryptocurrency symbol',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days of historical data to use (default: 30)',
        )

    def handle(self, *args, **options):
        api_manager = APIManager()
        ollama_analyzer = OllamaAnalyzer()
        
        if options['symbol']:
            cryptos = Crypto.objects.filter(symbol=options['symbol'].upper())
        else:
            cryptos = Crypto.objects.all()
        
        if not cryptos.exists():
            self.stdout.write(self.style.WARNING('No cryptocurrencies found to analyze.'))
            return
        
        days = options['days']
        analyzed_count = 0
        error_count = 0
        
        for crypto in cryptos:
            try:
                self.stdout.write(f'Analyzing {crypto.symbol}...')
                
                # Get current price
                price_data = api_manager.get_current_price(crypto.symbol)
                if not price_data:
                    self.stdout.write(
                        self.style.ERROR(f'Failed to fetch current price for {crypto.symbol}')
                    )
                    error_count += 1
                    continue
                
                current_price = price_data['price']
                
                # Get historical data
                historical_data = api_manager.get_historical_data(crypto.symbol, days=days)
                if not historical_data or 'data' not in historical_data:
                    self.stdout.write(
                        self.style.ERROR(f'Failed to fetch historical data for {crypto.symbol}')
                    )
                    error_count += 1
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
                    # CoinGecko data
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
                    self.stdout.write(
                        self.style.ERROR(f'No data available for {crypto.symbol}')
                    )
                    error_count += 1
                    continue
                
                # Calculate technical indicators
                tech_indicators = TechnicalIndicators(df)
                indicators = tech_indicators.get_latest_values()
                
                if not indicators:
                    self.stdout.write(
                        self.style.ERROR(f'Failed to calculate indicators for {crypto.symbol}')
                    )
                    error_count += 1
                    continue
                
                # Run Ollama analysis
                self.stdout.write(f'Running AI analysis for {crypto.symbol}...')
                analysis_result = ollama_analyzer.analyze_with_ollama(
                    indicators,
                    crypto.symbol,
                    current_price
                )
                
                # Save or update analysis
                analysis, created = TechnicalAnalysis.objects.update_or_create(
                    crypto=crypto,
                    defaults={
                        'indicators': indicators,
                        'recommendation': analysis_result['recommendation'],
                        'confidence_score': analysis_result['confidence_score'],
                        'ollama_reasoning': analysis_result['reasoning'],
                        'analysis_date': timezone.now()
                    }
                )
                
                analyzed_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Analysis complete for {crypto.symbol}: '
                        f'{analysis_result["recommendation"].upper()} '
                        f'({analysis_result["confidence_score"]}% confidence)'
                    )
                )
                
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'Error analyzing {crypto.symbol}: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nAnalysis complete: {analyzed_count} successful, {error_count} errors'
            )
        )

