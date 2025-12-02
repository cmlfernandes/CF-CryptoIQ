from django.contrib import admin
from .models import Crypto, PriceHistory, TechnicalAnalysis, AppSettings


@admin.register(Crypto)
class CryptoAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'name', 'amount', 'purchase_price', 'purchase_date', 'created_at']
    list_filter = ['created_at', 'purchase_date']
    search_fields = ['symbol', 'name']


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ['crypto', 'timestamp', 'price', 'volume', 'created_at']
    list_filter = ['timestamp', 'created_at']
    search_fields = ['crypto__symbol', 'crypto__name']
    date_hierarchy = 'timestamp'


@admin.register(TechnicalAnalysis)
class TechnicalAnalysisAdmin(admin.ModelAdmin):
    list_display = ['crypto', 'analysis_date', 'recommendation', 'confidence_score', 'created_at']
    list_filter = ['recommendation', 'analysis_date', 'created_at']
    search_fields = ['crypto__symbol', 'crypto__name']
    date_hierarchy = 'analysis_date'


@admin.register(AppSettings)
class AppSettingsAdmin(admin.ModelAdmin):
    list_display = ['auto_update_prices', 'price_update_interval', 'auto_run_analysis', 'analysis_interval', 'ollama_model', 'updated_at']
    
    def has_add_permission(self, request):
        # Only allow one settings instance
        return not AppSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion of settings
        return False
