from django.core.management.base import BaseCommand
from cryptos.models import Crypto, PriceHistory
from cryptos.services.api_manager import APIManager
from django.utils import timezone


class Command(BaseCommand):
    help = 'Update prices for all registered cryptocurrencies'

    def add_arguments(self, parser):
        parser.add_argument(
            '--symbol',
            type=str,
            help='Update price for a specific cryptocurrency symbol',
        )

    def handle(self, *args, **options):
        api_manager = APIManager()
        
        if options['symbol']:
            cryptos = Crypto.objects.filter(symbol=options['symbol'].upper())
        else:
            cryptos = Crypto.objects.all()
        
        if not cryptos.exists():
            self.stdout.write(self.style.WARNING('No cryptocurrencies found to update.'))
            return
        
        updated_count = 0
        error_count = 0
        
        for crypto in cryptos:
            try:
                self.stdout.write(f'Updating price for {crypto.symbol}...')
                price_data = api_manager.get_current_price(crypto.symbol)
                
                if price_data:
                    # Get market data for more complete information
                    market_data = api_manager.get_market_data(crypto.symbol)
                    
                    price = price_data['price']
                    high = market_data.get('high_24h', price) if market_data else price
                    low = market_data.get('low_24h', price) if market_data else price
                    volume = price_data.get('volume_24h', 0)
                    
                    # Create or update price history
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
                    
                    updated_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'Successfully updated {crypto.symbol}: ${price:.2f}')
                    )
                else:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f'Failed to fetch price for {crypto.symbol}')
                    )
                    
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'Error updating {crypto.symbol}: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nUpdate complete: {updated_count} successful, {error_count} errors'
            )
        )

