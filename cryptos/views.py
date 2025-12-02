from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils.safestring import mark_safe
from decimal import Decimal
import json
from .models import Crypto, PriceHistory, TechnicalAnalysis, AppSettings
from .services.api_manager import APIManager
from .services.technical_indicators import TechnicalIndicators
from .services.ollama_analyzer import OllamaAnalyzer
from .services.ollama_service import OllamaService
from .services.background_tasks import BackgroundTaskManager
import pandas as pd
from datetime import datetime, timedelta
from django.utils import timezone


def is_admin(user):
    """Check if user is admin/staff"""
    return user.is_authenticated and user.is_staff


def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('cryptos:analysis_overview')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username and password:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.username}!')
                next_url = request.GET.get('next', None)
                if next_url:
                    return redirect(next_url)
                return redirect('cryptos:analysis_overview')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Please provide both username and password.')
    
    return render(request, 'cryptos/login.html')


def logout_view(request):
    """User logout view"""
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('cryptos:login')


@login_required
@user_passes_test(is_admin)
def user_list(request):
    """List all users (admin only)"""
    users = User.objects.all().order_by('username')
    return render(request, 'cryptos/user_list.html', {'users': users})


@login_required
@user_passes_test(is_admin)
def user_add(request):
    """Add new user (admin only)"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email', '')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        is_staff = request.POST.get('is_staff') == 'on'
        is_superuser = request.POST.get('is_superuser') == 'on'
        
        if not username or not password:
            messages.error(request, 'Username and password are required.')
            return render(request, 'cryptos/user_add.html')
        
        if password != password_confirm:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'cryptos/user_add.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'cryptos/user_add.html')
        
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_staff=is_staff,
                is_superuser=is_superuser
            )
            messages.success(request, f'User {username} created successfully.')
            return redirect('cryptos:user_list')
        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')
    
    return render(request, 'cryptos/user_add.html')


@login_required
@user_passes_test(is_admin)
def user_edit(request, user_id):
    """Edit user (admin only)"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email', '')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        is_staff = request.POST.get('is_staff') == 'on'
        is_superuser = request.POST.get('is_superuser') == 'on'
        is_active = request.POST.get('is_active') == 'on'
        
        if not username:
            messages.error(request, 'Username is required.')
            return render(request, 'cryptos/user_edit.html', {'user_obj': user})
        
        if password and password != password_confirm:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'cryptos/user_edit.html', {'user_obj': user})
        
        if User.objects.filter(username=username).exclude(id=user_id).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'cryptos/user_edit.html', {'user_obj': user})
        
        try:
            user.username = username
            user.email = email
            user.is_staff = is_staff
            user.is_superuser = is_superuser
            user.is_active = is_active
            
            if password:
                user.set_password(password)
            
            user.save()
            messages.success(request, f'User {username} updated successfully.')
            return redirect('cryptos:user_list')
        except Exception as e:
            messages.error(request, f'Error updating user: {str(e)}')
    
    return render(request, 'cryptos/user_edit.html', {'user_obj': user})


@login_required
@user_passes_test(is_admin)
def user_delete(request, user_id):
    """Delete user (admin only)"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        if user == request.user:
            messages.error(request, 'You cannot delete your own account.')
            return redirect('cryptos:user_list')
        
        username = user.username
        user.delete()
        messages.success(request, f'User {username} deleted successfully.')
        return redirect('cryptos:user_list')
    
    return render(request, 'cryptos/user_delete.html', {'user_obj': user})


@login_required
def crypto_list(request):
    """List all registered cryptocurrencies"""
    cryptos = Crypto.objects.all()
    
    # Get current prices for all cryptos
    api_manager = APIManager()
    crypto_list_data = []
    for crypto in cryptos:
        try:
            price_data = api_manager.get_current_price(crypto.symbol)
            if price_data and price_data.get('price'):
                current_price = Decimal(str(price_data['price']))
                price_change_24h = float(price_data.get('change_24h', 0))
            else:
                current_price = Decimal('0')
                price_change_24h = 0
        except Exception as e:
            print(f"Error fetching price for {crypto.symbol}: {e}")
            current_price = Decimal('0')
            price_change_24h = 0
        
        current_value = crypto.amount * current_price if current_price > 0 else Decimal('0')
        profit_loss = current_value - (crypto.amount * crypto.purchase_price) if crypto.purchase_price > 0 else Decimal('0')
        
        crypto_list_data.append({
            'crypto': crypto,
            'current_price': current_price,
            'price_change_24h': price_change_24h,
            'current_value': current_value,
            'profit_loss': profit_loss
        })
    
    context = {
        'crypto_list_data': crypto_list_data
    }
    return render(request, 'cryptos/crypto_list.html', context)


@login_required
def crypto_add(request):
    """Add a new cryptocurrency"""
    if request.method == 'POST':
        symbol = request.POST.get('symbol', '').upper()
        name = request.POST.get('name', '')
        amount = request.POST.get('amount', 0)
        purchase_price = request.POST.get('purchase_price', 0)
        purchase_date = request.POST.get('purchase_date', '')
        
        try:
            crypto = Crypto.objects.create(
                symbol=symbol,
                name=name,
                amount=float(amount),
                purchase_price=float(purchase_price),
                purchase_date=datetime.fromisoformat(purchase_date) if purchase_date else timezone.now()
            )
            messages.success(request, f'Cryptocurrency {symbol} added successfully!')
            return redirect('cryptos:crypto_list')
        except Exception as e:
            messages.error(request, f'Error adding cryptocurrency: {str(e)}')
    
    return render(request, 'cryptos/crypto_add.html')


@login_required
def crypto_edit(request, crypto_id):
    """Edit an existing cryptocurrency"""
    crypto = get_object_or_404(Crypto, id=crypto_id)
    
    if request.method == 'POST':
        crypto.symbol = request.POST.get('symbol', '').upper()
        crypto.name = request.POST.get('name', '')
        crypto.amount = float(request.POST.get('amount', 0))
        crypto.purchase_price = float(request.POST.get('purchase_price', 0))
        purchase_date = request.POST.get('purchase_date', '')
        if purchase_date:
            crypto.purchase_date = datetime.fromisoformat(purchase_date)
        crypto.save()
        messages.success(request, f'Cryptocurrency {crypto.symbol} updated successfully!')
        return redirect('cryptos:crypto_list')
    
    context = {
        'crypto': crypto
    }
    return render(request, 'cryptos/crypto_edit.html', context)


@login_required
def crypto_delete(request, crypto_id):
    """Delete a cryptocurrency"""
    crypto = get_object_or_404(Crypto, id=crypto_id)
    if request.method == 'POST':
        symbol = crypto.symbol
        crypto.delete()
        messages.success(request, f'Cryptocurrency {symbol} deleted successfully!')
        return redirect('cryptos:crypto_list')
    
    context = {
        'crypto': crypto
    }
    return render(request, 'cryptos/crypto_delete.html', context)


@login_required
def crypto_analysis(request, crypto_id):
    """Detailed technical analysis for a cryptocurrency"""
    crypto = get_object_or_404(Crypto, id=crypto_id)
    app_settings = AppSettings.get_settings()
    
    # Get current price
    api_manager = APIManager()
    price_data = api_manager.get_current_price(crypto.symbol)
    current_price = float(price_data['price']) if price_data and price_data.get('price') else 0.0
    
    # Get historical data
    historical_data = api_manager.get_historical_data(crypto.symbol, days=app_settings.historical_days)
    
    # Get latest analysis
    latest_analysis = TechnicalAnalysis.objects.filter(crypto=crypto).first()
    
    # Check if we should update analysis
    should_update = False
    force_update = request.GET.get('refresh') == '1'  # Allow manual refresh
    
    if not latest_analysis:
        should_update = True
    elif force_update:
        should_update = True
    else:
        # Check if analysis is older than 1 hour
        time_since_analysis = timezone.now() - latest_analysis.analysis_date
        if time_since_analysis > timedelta(hours=1):
            should_update = True
        else:
            # Check if price changed significantly (>2%)
            if latest_analysis.indicators:
                old_price = latest_analysis.indicators.get('current_price', 0)
                if old_price > 0:
                    price_change_pct = abs((current_price - old_price) / old_price) * 100
                    if price_change_pct > 2.0:  # Price changed more than 2%
                        should_update = True
    
    # Calculate technical indicators
    indicators_data = None
    if historical_data and 'data' in historical_data:
        if historical_data['source'] == 'binance':
            # Convert Binance klines to DataFrame
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
            # Convert CoinGecko data to DataFrame
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
        
        if not df.empty:
            tech_indicators = TechnicalIndicators(df)
            indicators_data = tech_indicators.get_latest_values()
            
            # Calculate historical indicators for chart
            all_indicators_series = tech_indicators.calculate_all_indicators()
            historical_indicators = {}
            
            # Convert Series to lists, handling NaN values and forward-filling to extend to today
            for key in ['sma_20', 'sma_50', 'bb_upper', 'bb_middle', 'bb_lower']:
                series = all_indicators_series.get(key, pd.Series())
                if isinstance(series, pd.Series) and len(series) > 0:
                    # Forward fill NaN values to extend indicators to the end
                    series_filled = series.ffill().bfill()
                    # Convert to list, using last valid value for any remaining NaN
                    series_list = series_filled.tolist()
                    # Ensure all values extend to the end - use last valid value if needed
                    last_valid = None
                    for i, val in enumerate(series_list):
                        if pd.notna(val):
                            last_valid = float(val)
                        elif last_valid is not None:
                            series_list[i] = last_valid
                    historical_indicators[key] = [float(x) if pd.notna(x) else (last_valid if last_valid is not None else None) for x in series_list]
                else:
                    historical_indicators[key] = []
            
            # Add current price to indicators for comparison
            if indicators_data:
                indicators_data['current_price'] = current_price
            
            # Run Ollama analysis only if needed
            if indicators_data and should_update:
                try:
                    ollama_analyzer = OllamaAnalyzer(
                        base_url=app_settings.ollama_base_url,
                        model=app_settings.ollama_model
                    )
                    analysis_result = ollama_analyzer.analyze_with_ollama(
                        indicators_data,
                        crypto.symbol,
                        current_price
                    )
                    
                    # Save or update analysis
                    if latest_analysis:
                        latest_analysis.indicators = indicators_data
                        latest_analysis.recommendation = analysis_result['recommendation']
                        latest_analysis.confidence_score = analysis_result['confidence_score']
                        latest_analysis.ollama_reasoning = analysis_result['reasoning']
                        latest_analysis.analysis_date = timezone.now()
                        latest_analysis.save()
                    else:
                        latest_analysis = TechnicalAnalysis.objects.create(
                            crypto=crypto,
                            indicators=indicators_data,
                            recommendation=analysis_result['recommendation'],
                            confidence_score=analysis_result['confidence_score'],
                            ollama_reasoning=analysis_result['reasoning']
                        )
                except Exception as e:
                    # If Ollama fails, still save indicators but with default analysis
                    if not latest_analysis:
                        latest_analysis = TechnicalAnalysis.objects.create(
                            crypto=crypto,
                            indicators=indicators_data,
                            recommendation='hold',
                            confidence_score=0,
                            ollama_reasoning=f'Ollama analysis unavailable: {str(e)}'
                        )
            elif indicators_data and latest_analysis:
                # Update indicators but keep existing analysis
                latest_analysis.indicators = indicators_data
                latest_analysis.save(update_fields=['indicators'])
    
    # Get price history for chart
    price_history = PriceHistory.objects.filter(crypto=crypto).order_by('timestamp')[:100]
    
    # Initialize historical_indicators if not set
    if 'historical_indicators' not in locals():
        historical_indicators = {}
    
    # Prepare indicator explanations and scales
    indicator_info = {}
    if indicators_data:
        indicator_info = {
            'rsi': {
                'name': 'RSI (Relative Strength Index)',
                'value': indicators_data.get('rsi'),
                'scale': '0-100',
                'explanation': 'Measures the speed and magnitude of price changes. Indicates overbought (>70) or oversold (<30) conditions.',
                'interpretation': 'Oversold (<30): Potential buy signal. Overbought (>70): Potential sell signal. Neutral (30-70): No clear signal.',
                'color': 'success' if (indicators_data.get('rsi') is not None and indicators_data.get('rsi') < 30) else 'danger' if (indicators_data.get('rsi') is not None and indicators_data.get('rsi') > 70) else 'muted'
            },
            'macd': {
                'name': 'MACD (Moving Average Convergence Divergence)',
                'value': indicators_data.get('macd'),
                'signal': indicators_data.get('macd_signal'),
                'histogram': indicators_data.get('macd_histogram'),
                'scale': 'Positive/Negative',
                'explanation': 'Shows the relationship between two moving averages. MACD crossing above Signal is bullish, below is bearish.',
                'interpretation': 'MACD > Signal: Bullish trend. MACD < Signal: Bearish trend. Histogram shows momentum strength.',
                'color': 'success' if (indicators_data.get('macd') is not None and indicators_data.get('macd_signal') is not None and indicators_data.get('macd', 0) > indicators_data.get('macd_signal', 0)) else 'danger' if (indicators_data.get('macd') is not None and indicators_data.get('macd_signal') is not None) else 'muted'
            },
            'sma_20': {
                'name': 'SMA 20 (Simple Moving Average - 20 periods)',
                'value': indicators_data.get('sma_20'),
                'scale': 'Price level',
                'explanation': 'Average price over the last 20 periods. Price above SMA indicates uptrend, below indicates downtrend.',
                'interpretation': 'Price > SMA: Bullish. Price < SMA: Bearish. Compare with SMA 50 for trend confirmation.',
                'color': 'success' if (indicators_data.get('sma_20') is not None and current_price > indicators_data.get('sma_20', 0)) else 'danger' if (indicators_data.get('sma_20') is not None) else 'muted'
            },
            'sma_50': {
                'name': 'SMA 50 (Simple Moving Average - 50 periods)',
                'value': indicators_data.get('sma_50'),
                'scale': 'Price level',
                'explanation': 'Average price over the last 50 periods. Longer-term trend indicator compared to SMA 20.',
                'interpretation': 'SMA 20 > SMA 50: Bullish crossover. SMA 20 < SMA 50: Bearish crossover.',
                'color': 'success' if (indicators_data.get('sma_20') is not None and indicators_data.get('sma_50') is not None and indicators_data.get('sma_20', 0) > indicators_data.get('sma_50', 0)) else 'danger' if (indicators_data.get('sma_20') is not None and indicators_data.get('sma_50') is not None) else 'muted'
            },
            'bb_upper': {
                'name': 'Bollinger Bands',
                'upper': indicators_data.get('bb_upper'),
                'middle': indicators_data.get('bb_middle'),
                'lower': indicators_data.get('bb_lower'),
                'scale': 'Price levels (Upper/Middle/Lower)',
                'explanation': 'Volatility bands around a moving average. Upper and lower bands represent standard deviations from the middle band.',
                'interpretation': 'Price touches upper band: Overbought. Price touches lower band: Oversold. Narrow bands: Low volatility. Wide bands: High volatility.',
                'color': 'danger' if (indicators_data.get('bb_upper') is not None and current_price > indicators_data.get('bb_upper', 0)) else 'success' if (indicators_data.get('bb_lower') is not None and current_price < indicators_data.get('bb_lower', 0)) else 'muted'
            },
            'stoch_k': {
                'name': 'Stochastic Oscillator',
                'k': indicators_data.get('stoch_k'),
                'd': indicators_data.get('stoch_d'),
                'scale': '0-100',
                'explanation': 'Compares closing price to price range over a period. Measures momentum and identifies overbought/oversold conditions.',
                'interpretation': 'K > 80: Overbought (sell signal). K < 20: Oversold (buy signal). K crosses above D: Bullish. K crosses below D: Bearish.',
                'color': 'danger' if (indicators_data.get('stoch_k') is not None and indicators_data.get('stoch_k', 50) > 80) else 'success' if (indicators_data.get('stoch_k') is not None and indicators_data.get('stoch_k', 50) < 20) else 'muted'
            },
            'adx': {
                'name': 'ADX (Average Directional Index)',
                'value': indicators_data.get('adx'),
                'scale': '0-100',
                'explanation': 'Measures trend strength regardless of direction. Higher values indicate stronger trends.',
                'interpretation': 'ADX > 25: Strong trend. ADX < 20: Weak or no trend. ADX 20-25: Moderate trend. Does not indicate direction, only strength.',
                'color': 'success' if (indicators_data.get('adx') is not None and indicators_data.get('adx', 0) > 25) else 'warning' if (indicators_data.get('adx') is not None and indicators_data.get('adx', 0) > 20) else 'muted'
            },
            'volume_ratio': {
                'name': 'Volume Ratio',
                'value': indicators_data.get('volume_ratio'),
                'scale': 'Multiplier (x)',
                'explanation': 'Compares current volume to average volume. High volume confirms price movements.',
                'interpretation': '> 1.5x: High volume (confirms trend). < 0.5x: Low volume (weak trend). 0.5-1.5x: Normal volume.',
                'color': 'success' if (indicators_data.get('volume_ratio') is not None and indicators_data.get('volume_ratio', 1) > 1.5) else 'danger' if (indicators_data.get('volume_ratio') is not None and indicators_data.get('volume_ratio', 1) < 0.5) else 'muted'
            },
            'support': {
                'name': 'Support & Resistance',
                'support': indicators_data.get('support'),
                'resistance': indicators_data.get('resistance'),
                'scale': 'Price levels',
                'explanation': 'Support is a price level where buying pressure is strong. Resistance is where selling pressure is strong.',
                'interpretation': 'Price near support: Potential bounce up. Price near resistance: Potential pullback. Breakthrough indicates trend continuation.',
                'color': 'success' if (indicators_data.get('support') is not None and current_price < indicators_data.get('support', 0) * 1.02) else 'danger' if (indicators_data.get('resistance') is not None and current_price > indicators_data.get('resistance', 0) * 0.98) else 'muted'
            }
        }
    
    # Prepare historical data for chart (use historical_data if available, otherwise use price_history)
    chart_data = {
        'labels': mark_safe(json.dumps([])),
        'timestamps': mark_safe(json.dumps([])),
        'prices': mark_safe(json.dumps([])),
        'sma_20': mark_safe(json.dumps([])),
        'sma_50': mark_safe(json.dumps([])),
        'bb_upper': mark_safe(json.dumps([])),
        'bb_middle': mark_safe(json.dumps([])),
        'bb_lower': mark_safe(json.dumps([]))
    }
    
    if historical_data and 'data' in historical_data:
        if historical_data['source'] == 'binance':
            klines = historical_data['data']
            labels_list = []
            timestamps_full = []
            for kline in klines:
                timestamp = kline['timestamp']
                if hasattr(timestamp, 'strftime'):
                    labels_list.append(timestamp.strftime('%H:%M'))
                    timestamps_full.append({
                        'date': timestamp.strftime('%Y-%m-%d'),
                        'time': timestamp.strftime('%H:%M'),
                        'datetime': timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)
                    })
                elif isinstance(timestamp, str):
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        labels_list.append(dt.strftime('%H:%M'))
                        timestamps_full.append({
                            'date': dt.strftime('%Y-%m-%d'),
                            'time': dt.strftime('%H:%M'),
                            'datetime': dt.isoformat()
                        })
                    except:
                        if ' ' in timestamp:
                            time_part = timestamp.split(' ')[-1][:5]
                            date_part = timestamp.split(' ')[0]
                            labels_list.append(time_part)
                            timestamps_full.append({
                                'date': date_part,
                                'time': time_part,
                                'datetime': timestamp
                            })
                        else:
                            labels_list.append(timestamp)
                            timestamps_full.append({
                                'date': '',
                                'time': timestamp,
                                'datetime': timestamp
                            })
                else:
                    labels_list.append(str(timestamp))
                    timestamps_full.append({
                        'date': '',
                        'time': str(timestamp),
                        'datetime': timestamp
                    })
            prices_list = [float(kline['close']) for kline in klines]
            chart_data['labels'] = mark_safe(json.dumps(labels_list))
            chart_data['timestamps'] = mark_safe(json.dumps(timestamps_full))
            chart_data['prices'] = mark_safe(json.dumps(prices_list))
        else:
            prices = historical_data['data'].get('prices', [])
            labels_list = []
            timestamps_full = []
            for price_point in prices:
                timestamp = price_point['timestamp']
                if hasattr(timestamp, 'strftime'):
                    labels_list.append(timestamp.strftime('%H:%M'))
                    timestamps_full.append({
                        'date': timestamp.strftime('%Y-%m-%d'),
                        'time': timestamp.strftime('%H:%M'),
                        'datetime': timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp)
                    })
                elif isinstance(timestamp, str):
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        labels_list.append(dt.strftime('%H:%M'))
                        timestamps_full.append({
                            'date': dt.strftime('%Y-%m-%d'),
                            'time': dt.strftime('%H:%M'),
                            'datetime': dt.isoformat()
                        })
                    except:
                        if ' ' in timestamp:
                            time_part = timestamp.split(' ')[-1][:5]
                            date_part = timestamp.split(' ')[0]
                            labels_list.append(time_part)
                            timestamps_full.append({
                                'date': date_part,
                                'time': time_part,
                                'datetime': timestamp
                            })
                        else:
                            labels_list.append(timestamp)
                            timestamps_full.append({
                                'date': '',
                                'time': timestamp,
                                'datetime': timestamp
                            })
                else:
                    labels_list.append(str(timestamp))
                    timestamps_full.append({
                        'date': '',
                        'time': str(timestamp),
                        'datetime': timestamp
                    })
            prices_list = [float(price_point['price']) for price_point in prices]
            chart_data['labels'] = mark_safe(json.dumps(labels_list))
            chart_data['timestamps'] = mark_safe(json.dumps(timestamps_full))
            chart_data['prices'] = mark_safe(json.dumps(prices_list))
        
        # Add historical indicators
        if historical_indicators:
            chart_data['sma_20'] = mark_safe(json.dumps([x for x in historical_indicators.get('sma_20', []) if x is not None]))
            chart_data['sma_50'] = mark_safe(json.dumps([x for x in historical_indicators.get('sma_50', []) if x is not None]))
            chart_data['bb_upper'] = mark_safe(json.dumps([x for x in historical_indicators.get('bb_upper', []) if x is not None]))
            chart_data['bb_middle'] = mark_safe(json.dumps([x for x in historical_indicators.get('bb_middle', []) if x is not None]))
            chart_data['bb_lower'] = mark_safe(json.dumps([x for x in historical_indicators.get('bb_lower', []) if x is not None]))
    elif price_history:
        labels_list = []
        timestamps_full = []
        for ph in price_history:
            if hasattr(ph.timestamp, 'strftime'):
                labels_list.append(ph.timestamp.strftime('%H:%M'))
                timestamps_full.append({
                    'date': ph.timestamp.strftime('%Y-%m-%d'),
                    'time': ph.timestamp.strftime('%H:%M'),
                    'datetime': ph.timestamp.isoformat() if hasattr(ph.timestamp, 'isoformat') else str(ph.timestamp)
                })
            else:
                labels_list.append(str(ph.timestamp))
                timestamps_full.append({
                    'date': '',
                    'time': str(ph.timestamp),
                    'datetime': ph.timestamp
                })
        prices_list = [float(ph.price) for ph in price_history]
        chart_data['labels'] = mark_safe(json.dumps(labels_list))
        chart_data['timestamps'] = mark_safe(json.dumps(timestamps_full))
        chart_data['prices'] = mark_safe(json.dumps(prices_list))
    
    context = {
        'crypto': crypto,
        'current_price': current_price,
        'indicators': indicators_data,
        'indicator_info': indicator_info,
        'analysis': latest_analysis,
        'price_history': price_history,
        'historical_data': historical_data,
        'historical_indicators': historical_indicators,
        'chart_data': chart_data
    }
    return render(request, 'cryptos/crypto_analysis.html', context)


@login_required
def analysis_overview(request):
    """Overview of all technical analyses"""
    cryptos = Crypto.objects.all()
    analyses = []
    
    for crypto in cryptos:
        analysis = TechnicalAnalysis.objects.filter(crypto=crypto).first()
        if analysis:
            api_manager = APIManager()
            price_data = api_manager.get_current_price(crypto.symbol)
            current_price = float(price_data['price']) if price_data and price_data.get('price') else 0.0
            
            analyses.append({
                'crypto': crypto,
                'analysis': analysis,
                'current_price': current_price
            })
    
    context = {
        'analyses': analyses
    }
    return render(request, 'cryptos/analysis_overview.html', context)


@login_required
@require_http_methods(["POST"])
def update_price(request, crypto_id):
    """Update price for a cryptocurrency (AJAX endpoint)"""
    crypto = get_object_or_404(Crypto, id=crypto_id)
    api_manager = APIManager()
    
    price_data = api_manager.get_current_price(crypto.symbol)
    if price_data:
        # Save to PriceHistory
        PriceHistory.objects.create(
            crypto=crypto,
            timestamp=timezone.now(),
            price=price_data['price'],
            volume=price_data.get('volume_24h', 0),
            high=price_data.get('high_24h', price_data['price']),
            low=price_data.get('low_24h', price_data['price']),
            open_price=price_data['price'],
            close_price=price_data['price']
        )
        return JsonResponse({'success': True, 'price': price_data['price']})
    
    return JsonResponse({'success': False, 'error': 'Failed to fetch price'})


@login_required
@require_http_methods(["GET", "POST"])
def get_price(request, symbol=None):
    """Get current price for a symbol (used for auto-fill in add form)"""
    if request.method == 'POST':
        # Try to get symbol from POST body (JSON or form data)
        import json
        try:
            body = json.loads(request.body)
            symbol = body.get('symbol', '')
        except:
            symbol = request.POST.get('symbol', '')
    else:
        symbol = symbol or request.GET.get('symbol', '')
    
    if not symbol:
        return JsonResponse({'success': False, 'error': 'Symbol required'})
    
    api_manager = APIManager()
    price_data = api_manager.get_current_price(symbol.strip().upper())
    
    if price_data and price_data.get('price'):
        return JsonResponse({'success': True, 'price': price_data['price']})
    
    return JsonResponse({'success': False, 'error': 'Failed to fetch price'})


@login_required
def settings_view(request):
    """View and update application settings"""
    settings = AppSettings.get_settings()
    
    # Load available Ollama models (silently fail if connection fails)
    available_models = []
    default_model = 'plutus'
    try:
        ollama_service = OllamaService(base_url=settings.ollama_base_url)
        available_models = ollama_service.list_models()
        
        # Check if Plutus exists, if not use first available model
        if available_models:
            model_names = [m.get('name', '').lower() for m in available_models]
            if 'plutus' in model_names or any('plutus' in m.get('name', '').lower() for m in available_models):
                # Find exact Plutus model name
                for m in available_models:
                    if 'plutus' in m.get('name', '').lower():
                        default_model = m.get('name', 'plutus')
                        break
            else:
                # Use first available model
                default_model = available_models[0].get('name', 'plutus')
            
            # If current model is not in available models, update to default
            current_model_names = [m.get('name', '') for m in available_models]
            if settings.ollama_model not in current_model_names:
                settings.ollama_model = default_model
                settings.save(update_fields=['ollama_model'])
    except Exception as e:
        # Connection error - models will be empty, user can refresh
        pass
    
    if request.method == 'POST':
        # Update settings
        settings.auto_update_prices = request.POST.get('auto_update_prices') == 'on'
        settings.price_update_interval = int(request.POST.get('price_update_interval', 60))
        settings.auto_run_analysis = request.POST.get('auto_run_analysis') == 'on'
        settings.analysis_interval = int(request.POST.get('analysis_interval', 360))
        settings.ollama_base_url = request.POST.get('ollama_base_url', 'http://localhost:11434')
        settings.ollama_model = request.POST.get('ollama_model', default_model)
        settings.historical_days = int(request.POST.get('historical_days', 30))
        settings.save()
        
        # Restart background tasks
        task_manager = BackgroundTaskManager()
        task_manager.restart()
        
        messages.success(request, 'Settings updated successfully!')
        return redirect('cryptos:settings')
    
    context = {
        'settings': settings,
        'available_models': available_models
    }
    return render(request, 'cryptos/settings.html', context)


@require_http_methods(["POST"])
@login_required
def load_models_ajax(request):
    """AJAX endpoint to load Ollama models"""
    try:
        data = json.loads(request.body)
        base_url = data.get('base_url', 'http://localhost:11434')
        
        ollama_service = OllamaService(base_url=base_url)
        models = ollama_service.list_models()
        
        if models:
            return JsonResponse({
                'success': True,
                'models': models
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'No models found or connection failed. Please check the Ollama server URL.',
                'models': []
            })
    except Exception as e:
        error_msg = str(e)
        if '10061' in error_msg or 'connection' in error_msg.lower():
            error_msg = 'Cannot connect to Ollama server. Please check the URL and ensure the server is running.'
        return JsonResponse({
            'success': False,
            'error': error_msg,
            'models': []
        })
