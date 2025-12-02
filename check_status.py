#!/usr/bin/env python
"""Script to check application status and logs"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cf_cryptoiq.settings')
django.setup()

from cryptos.models import AppSettings, Crypto, TechnicalAnalysis
from cryptos.services.ollama_service import OllamaService

print("=" * 60)
print("CRYPTO BOT STATUS CHECK")
print("=" * 60)

# Check AppSettings
print("\n1. App Settings:")
try:
    settings = AppSettings.get_settings()
    print(f"   [OK] Settings loaded")
    print(f"   - Ollama URL: {settings.ollama_base_url}")
    print(f"   - Ollama Model: {settings.ollama_model}")
    print(f"   - Auto Update Prices: {settings.auto_update_prices}")
    print(f"   - Auto Run Analysis: {settings.auto_run_analysis}")
    print(f"   - Price Update Interval: {settings.price_update_interval} minutes")
    print(f"   - Analysis Interval: {settings.analysis_interval} minutes")
    if settings.last_price_update:
        print(f"   - Last Price Update: {settings.last_price_update}")
    if settings.last_analysis_run:
        print(f"   - Last Analysis Run: {settings.last_analysis_run}")
except Exception as e:
    print(f"   [ERROR] Error loading settings: {e}")

# Check Cryptos
print("\n2. Registered Cryptos:")
try:
    cryptos = Crypto.objects.all()
    print(f"   [OK] Found {cryptos.count()} cryptocurrencies")
    for crypto in cryptos:
        print(f"   - {crypto.symbol} ({crypto.name})")
except Exception as e:
    print(f"   [ERROR] Error loading cryptos: {e}")

# Check Ollama Connection
print("\n3. Ollama Connection:")
try:
    settings = AppSettings.get_settings()
    ollama_service = OllamaService(base_url=settings.ollama_base_url)
    models = ollama_service.list_models()
    if models:
        print(f"   [OK] Connected to Ollama")
        print(f"   [OK] Found {len(models)} available models:")
        for model in models[:5]:  # Show first 5
            print(f"     - {model['name']}")
        if len(models) > 5:
            print(f"     ... and {len(models) - 5} more")
    else:
        print(f"   [WARNING] Connected but no models found")
except Exception as e:
    print(f"   [ERROR] Error connecting to Ollama: {e}")

# Check Technical Analyses
print("\n4. Technical Analyses:")
try:
    analyses = TechnicalAnalysis.objects.all()
    print(f"   [OK] Found {analyses.count()} analyses")
    if analyses.exists():
        latest = analyses.order_by('-analysis_date').first()
        print(f"   - Latest: {latest.crypto.symbol} - {latest.recommendation.upper()} ({latest.confidence_score}%)")
except Exception as e:
    print(f"   [ERROR] Error loading analyses: {e}")

print("\n" + "=" * 60)
print("Status check complete!")
print("=" * 60)

