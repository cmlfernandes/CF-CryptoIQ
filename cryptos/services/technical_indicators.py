import pandas as pd
import numpy as np
from typing import Dict, List, Optional


class TechnicalIndicators:
    def __init__(self, price_data: pd.DataFrame):
        """
        Initialize with price data DataFrame.
        Expected columns: timestamp, open, high, low, close, volume
        """
        self.df = price_data.copy()
        if 'timestamp' in self.df.columns:
            self.df.set_index('timestamp', inplace=True)
        self.df.sort_index(inplace=True)
        
        # Ensure we have the required columns
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in self.df.columns:
                if col == 'open':
                    self.df['open'] = self.df['close']
                elif col == 'high':
                    self.df['high'] = self.df['close']
                elif col == 'low':
                    self.df['low'] = self.df['close']
                elif col == 'volume':
                    self.df['volume'] = 0

    def calculate_sma(self, period: int = 20) -> pd.Series:
        """Simple Moving Average"""
        return self.df['close'].rolling(window=period).mean()

    def calculate_ema(self, period: int = 20) -> pd.Series:
        """Exponential Moving Average"""
        return self.df['close'].ewm(span=period, adjust=False).mean()

    def calculate_rsi(self, period: int = 14) -> pd.Series:
        """Relative Strength Index"""
        delta = self.df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_macd(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Dict:
        """Moving Average Convergence Divergence"""
        ema_fast = self.df['close'].ewm(span=fast_period, adjust=False).mean()
        ema_slow = self.df['close'].ewm(span=slow_period, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }

    def calculate_bollinger_bands(self, period: int = 20, std_dev: int = 2) -> Dict:
        """Bollinger Bands"""
        sma = self.calculate_sma(period)
        std = self.df['close'].rolling(window=period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return {
            'middle': sma,
            'upper': upper_band,
            'lower': lower_band
        }

    def calculate_stochastic(self, k_period: int = 14, d_period: int = 3) -> Dict:
        """Stochastic Oscillator"""
        low_min = self.df['low'].rolling(window=k_period).min()
        high_max = self.df['high'].rolling(window=k_period).max()
        k_percent = 100 * ((self.df['close'] - low_min) / (high_max - low_min))
        d_percent = k_percent.rolling(window=d_period).mean()
        
        return {
            'k': k_percent,
            'd': d_percent
        }

    def calculate_adx(self, period: int = 14) -> pd.Series:
        """Average Directional Index"""
        high_diff = self.df['high'].diff()
        low_diff = -self.df['low'].diff()
        
        plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
        minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)
        
        tr = self._calculate_true_range()
        atr = tr.rolling(window=period).mean()
        
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
        
        dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di))
        adx = dx.rolling(window=period).mean()
        
        return adx

    def _calculate_true_range(self) -> pd.Series:
        """Calculate True Range"""
        high_low = self.df['high'] - self.df['low']
        high_close = abs(self.df['high'] - self.df['close'].shift())
        low_close = abs(self.df['low'] - self.df['close'].shift())
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr

    def calculate_volume_indicators(self) -> Dict:
        """Volume-based indicators"""
        volume_sma = self.df['volume'].rolling(window=20).mean()
        volume_ratio = self.df['volume'] / volume_sma
        
        # On Balance Volume
        obv = (np.sign(self.df['close'].diff()) * self.df['volume']).fillna(0).cumsum()
        
        return {
            'volume_sma': volume_sma,
            'volume_ratio': volume_ratio,
            'obv': obv
        }

    def calculate_support_resistance(self, window: int = 20) -> Dict:
        """Calculate Support and Resistance levels"""
        recent_data = self.df.tail(window)
        
        # Find local maxima and minima
        highs = recent_data['high']
        lows = recent_data['low']
        
        resistance = highs.max()
        support = lows.min()
        
        # Calculate pivot points
        pivot = (recent_data['high'].iloc[-1] + recent_data['low'].iloc[-1] + recent_data['close'].iloc[-1]) / 3
        r1 = 2 * pivot - recent_data['low'].iloc[-1]
        s1 = 2 * pivot - recent_data['high'].iloc[-1]
        r2 = pivot + (recent_data['high'].iloc[-1] - recent_data['low'].iloc[-1])
        s2 = pivot - (recent_data['high'].iloc[-1] - recent_data['low'].iloc[-1])
        
        return {
            'support': support,
            'resistance': resistance,
            'pivot': pivot,
            'r1': r1,
            'r2': r2,
            's1': s1,
            's2': s2
        }

    def calculate_all_indicators(self) -> Dict:
        """Calculate all technical indicators"""
        indicators = {}
        
        # Moving Averages
        indicators['sma_20'] = self.calculate_sma(20)
        indicators['sma_50'] = self.calculate_sma(50)
        indicators['ema_12'] = self.calculate_ema(12)
        indicators['ema_26'] = self.calculate_ema(26)
        
        # RSI
        indicators['rsi'] = self.calculate_rsi(14)
        
        # MACD
        macd_data = self.calculate_macd()
        indicators['macd'] = macd_data['macd']
        indicators['macd_signal'] = macd_data['signal']
        indicators['macd_histogram'] = macd_data['histogram']
        
        # Bollinger Bands
        bb_data = self.calculate_bollinger_bands()
        indicators['bb_upper'] = bb_data['upper']
        indicators['bb_middle'] = bb_data['middle']
        indicators['bb_lower'] = bb_data['lower']
        
        # Stochastic
        stoch_data = self.calculate_stochastic()
        indicators['stoch_k'] = stoch_data['k']
        indicators['stoch_d'] = stoch_data['d']
        
        # ADX
        indicators['adx'] = self.calculate_adx(14)
        
        # Volume indicators
        volume_data = self.calculate_volume_indicators()
        indicators['volume_sma'] = volume_data['volume_sma']
        indicators['volume_ratio'] = volume_data['volume_ratio']
        indicators['obv'] = volume_data['obv']
        
        # Support/Resistance
        sr_data = self.calculate_support_resistance()
        indicators['support'] = sr_data['support']
        indicators['resistance'] = sr_data['resistance']
        indicators['pivot'] = sr_data['pivot']
        
        return indicators

    def get_latest_values(self) -> Dict:
        """Get the latest values of all indicators"""
        all_indicators = self.calculate_all_indicators()
        latest_values = {}
        
        for key, value in all_indicators.items():
            if isinstance(value, pd.Series):
                latest_values[key] = float(value.iloc[-1]) if not pd.isna(value.iloc[-1]) else None
            elif isinstance(value, (int, float)):
                latest_values[key] = float(value) if not pd.isna(value) else None
            else:
                latest_values[key] = value
        
        # Add current price
        latest_values['current_price'] = float(self.df['close'].iloc[-1])
        latest_values['current_volume'] = float(self.df['volume'].iloc[-1])
        
        return latest_values

