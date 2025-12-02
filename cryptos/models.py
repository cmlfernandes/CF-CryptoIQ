from django.db import models
from django.utils import timezone
import json


class Crypto(models.Model):
    symbol = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    purchase_price = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    purchase_date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['symbol']

    def __str__(self):
        return f"{self.symbol} - {self.name}"

    @property
    def current_value(self):
        latest_price = self.price_history.order_by('-timestamp').first()
        if latest_price:
            return self.amount * latest_price.price
        return 0

    @property
    def profit_loss(self):
        if self.purchase_price > 0:
            latest_price = self.price_history.order_by('-timestamp').first()
            if latest_price:
                current_value = self.amount * latest_price.price
                purchase_value = self.amount * self.purchase_price
                return current_value - purchase_value
        return 0


class PriceHistory(models.Model):
    crypto = models.ForeignKey(Crypto, on_delete=models.CASCADE, related_name='price_history')
    timestamp = models.DateTimeField()
    price = models.DecimalField(max_digits=20, decimal_places=8)
    volume = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    high = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    low = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    open_price = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    close_price = models.DecimalField(max_digits=20, decimal_places=8, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        unique_together = ['crypto', 'timestamp']
        indexes = [
            models.Index(fields=['crypto', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.crypto.symbol} - {self.timestamp} - {self.price}"


class TechnicalAnalysis(models.Model):
    RECOMMENDATION_CHOICES = [
        ('buy', 'Buy'),
        ('sell', 'Sell'),
        ('hold', 'Hold'),
    ]

    crypto = models.ForeignKey(Crypto, on_delete=models.CASCADE, related_name='technical_analyses')
    analysis_date = models.DateTimeField(default=timezone.now)
    indicators = models.JSONField(default=dict)
    recommendation = models.CharField(max_length=10, choices=RECOMMENDATION_CHOICES, default='hold')
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    ollama_reasoning = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-analysis_date']
        get_latest_by = 'analysis_date'

    def __str__(self):
        return f"{self.crypto.symbol} - {self.analysis_date} - {self.recommendation}"

    def get_indicators_dict(self):
        if isinstance(self.indicators, str):
            return json.loads(self.indicators)
        return self.indicators if isinstance(self.indicators, dict) else {}


class AppSettings(models.Model):
    """Singleton model for application settings"""
    # Background tasks settings
    auto_update_prices = models.BooleanField(default=False, help_text="Enable automatic price updates")
    price_update_interval = models.IntegerField(default=60, help_text="Price update interval in minutes")
    
    auto_run_analysis = models.BooleanField(default=False, help_text="Enable automatic technical analysis")
    analysis_interval = models.IntegerField(default=360, help_text="Analysis interval in minutes")
    
    # Ollama settings
    ollama_base_url = models.CharField(max_length=200, default='http://localhost:11434')
    ollama_model = models.CharField(max_length=100, default='plutus')
    
    # Analysis settings
    historical_days = models.IntegerField(default=30, help_text="Number of days of historical data for analysis")
    
    last_price_update = models.DateTimeField(null=True, blank=True)
    last_analysis_run = models.DateTimeField(null=True, blank=True)
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "App Settings"
        verbose_name_plural = "App Settings"

    def __str__(self):
        return "Application Settings"

    @classmethod
    def get_settings(cls):
        """Get or create singleton settings instance"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings

    def save(self, *args, **kwargs):
        """Ensure only one settings instance exists"""
        self.pk = 1
        super().save(*args, **kwargs)
