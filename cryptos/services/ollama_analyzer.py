from django.conf import settings
from ollama import Client
import json
import re
import os


class OllamaAnalyzer:
    def __init__(self, base_url=None, model=None):
        # Use provided values or fallback to settings
        self.base_url = base_url or getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
        self.model = model or getattr(settings, 'OLLAMA_MODEL', 'plutus')
        self._setup_client()
    
    def _setup_client(self):
        """Setup Ollama client with proper URL"""
        # Normalize URL
        url = self.base_url.strip()
        if not url.startswith('http://') and not url.startswith('https://'):
            url = f'https://{url}'
        
        # Remove trailing slash
        url = url.rstrip('/')
        
        # Create client with explicit host
        try:
            self.client = Client(host=url)
        except Exception as e:
            print(f"Warning: Could not create Ollama client: {e}")
            # Fallback to default
            self.client = Client()
    
    def update_config(self, base_url=None, model=None):
        """Update Ollama configuration"""
        if base_url:
            self.base_url = base_url
        if model:
            self.model = model
        self._setup_client()

    def _format_indicators_for_prompt(self, indicators: dict, crypto_symbol: str, current_price: float) -> str:
        """Format technical indicators into a readable string for the LLM"""
        prompt_data = f"""
CRYPTO: {crypto_symbol}
CURRENT PRICE: ${current_price:.2f}

TECHNICAL INDICATORS:
"""
        if indicators.get('rsi') is not None:
            rsi = indicators['rsi']
            rsi_status = "OVERSOLD" if rsi < 30 else "OVERBOUGHT" if rsi > 70 else "NEUTRAL"
            prompt_data += f"- RSI (14): {rsi:.2f} ({rsi_status})\n"
        
        if indicators.get('macd') is not None and indicators.get('macd_signal') is not None:
            macd = indicators['macd']
            signal = indicators['macd_signal']
            histogram = indicators.get('macd_histogram', 0)
            macd_trend = "BULLISH" if macd > signal else "BEARISH"
            prompt_data += f"- MACD: {macd:.4f}, Signal: {signal:.4f}, Histogram: {histogram:.4f} ({macd_trend})\n"
        
        if indicators.get('sma_20') is not None and indicators.get('sma_50') is not None:
            sma20 = indicators['sma_20']
            sma50 = indicators['sma_50']
            ma_trend = "BULLISH" if sma20 > sma50 else "BEARISH"
            prompt_data += f"- SMA 20: ${sma20:.2f}, SMA 50: ${sma50:.2f} ({ma_trend})\n"
        
        if indicators.get('bb_upper') is not None and indicators.get('bb_lower') is not None:
            bb_upper = indicators['bb_upper']
            bb_lower = indicators['bb_lower']
            bb_middle = indicators.get('bb_middle', 0)
            if current_price > bb_upper:
                bb_position = "ABOVE UPPER BAND (Overbought)"
            elif current_price < bb_lower:
                bb_position = "BELOW LOWER BAND (Oversold)"
            else:
                bb_position = "WITHIN BANDS"
            prompt_data += f"- Bollinger Bands: Upper ${bb_upper:.2f}, Middle ${bb_middle:.2f}, Lower ${bb_lower:.2f} - Price is {bb_position}\n"
        
        if indicators.get('stoch_k') is not None and indicators.get('stoch_d') is not None:
            stoch_k = indicators['stoch_k']
            stoch_d = indicators['stoch_d']
            stoch_signal = "OVERSOLD" if stoch_k < 20 else "OVERBOUGHT" if stoch_k > 80 else "NEUTRAL"
            prompt_data += f"- Stochastic: K={stoch_k:.2f}, D={stoch_d:.2f} ({stoch_signal})\n"
        
        if indicators.get('adx') is not None:
            adx = indicators['adx']
            trend_strength = "STRONG" if adx > 25 else "WEAK" if adx < 20 else "MODERATE"
            prompt_data += f"- ADX: {adx:.2f} (Trend Strength: {trend_strength})\n"
        
        if indicators.get('volume_ratio') is not None:
            vol_ratio = indicators['volume_ratio']
            vol_status = "HIGH" if vol_ratio > 1.5 else "LOW" if vol_ratio < 0.5 else "NORMAL"
            prompt_data += f"- Volume Ratio: {vol_ratio:.2f}x ({vol_status} volume)\n"
        
        if indicators.get('support') is not None and indicators.get('resistance') is not None:
            support = indicators['support']
            resistance = indicators['resistance']
            prompt_data += f"- Support Level: ${support:.2f}\n"
            prompt_data += f"- Resistance Level: ${resistance:.2f}\n"
        
        return prompt_data

    def _create_analysis_prompt(self, indicators: dict, crypto_symbol: str, current_price: float) -> str:
        """Create the prompt for technical analysis"""
        indicators_text = self._format_indicators_for_prompt(indicators, crypto_symbol, current_price)
        
        prompt = f"""You are an expert cryptocurrency technical analyst with 20+ years of experience. Analyze the following technical indicators for {crypto_symbol} and provide a trading recommendation.

{indicators_text}

ANALYSIS RULES:
1. BUY recommendation requires:
   - RSI < 40 (oversold territory) OR
   - MACD bullish crossover (MACD > Signal) with positive histogram OR
   - Price below lower Bollinger Band (oversold) OR
   - Strong bullish trend (SMA 20 > SMA 50, ADX > 25)
   - At least 2 of the above conditions must be met

2. SELL recommendation requires:
   - RSI > 60 (overbought territory) OR
   - MACD bearish crossover (MACD < Signal) with negative histogram OR
   - Price above upper Bollinger Band (overbought) OR
   - Strong bearish trend (SMA 20 < SMA 50, ADX > 25)
   - At least 2 of the above conditions must be met

3. HOLD recommendation when:
   - Mixed signals or neutral indicators
   - No clear trend direction
   - Waiting for confirmation

4. Confidence Score Guidelines:
   - 80-100: Very strong signal, multiple indicators align
   - 60-79: Strong signal, 2-3 indicators align
   - 40-59: Moderate signal, some indicators align
   - 20-39: Weak signal, conflicting indicators
   - 0-19: Very weak or no clear signal

Based on these technical indicators, provide:
1. A clear recommendation: BUY, SELL, or HOLD
2. A confidence score from 0 to 100
3. A detailed reasoning explaining your decision based on the technical indicators

Format your response as JSON with the following structure:
{{
    "recommendation": "BUY|SELL|HOLD",
    "confidence_score": <number between 0 and 100>,
    "reasoning": "<detailed explanation of your analysis, mentioning specific indicator values and why they support your recommendation>"
}}

Be specific about which indicators support your recommendation. Consider:
- RSI levels (oversold <30, overbought >70)
- MACD crossovers and histogram
- Moving average relationships
- Bollinger Band position
- Stochastic oscillator levels
- ADX trend strength
- Volume patterns
- Support and resistance levels

Respond ONLY with valid JSON, no additional text."""
        
        return prompt

    def analyze_with_ollama(self, indicators: dict, crypto_symbol: str, current_price: float) -> dict:
        """Analyze technical indicators using Ollama LLM"""
        try:
            prompt = self._create_analysis_prompt(indicators, crypto_symbol, current_price)
            
            # Use client.generate instead of ollama.generate
            response = self.client.generate(
                model=self.model,
                prompt=prompt
            )
            
            # Extract the response text - client returns GenerateResponse object
            if hasattr(response, 'response'):
                response_text = response.response
            elif isinstance(response, dict):
                response_text = response.get('response', '')
            else:
                response_text = str(response)
            
            # Try to parse JSON from response
            json_match = re.search(r'\{[^{}]*"recommendation"[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                try:
                    result = json.loads(json_str)
                except json.JSONDecodeError:
                    # Fallback parsing
                    result = self._parse_response_fallback(response_text)
            else:
                result = self._parse_response_fallback(response_text)
            
            # Normalize recommendation
            recommendation = result.get('recommendation', 'HOLD').upper()
            if recommendation not in ['BUY', 'SELL', 'HOLD']:
                recommendation = 'HOLD'
            
            # Ensure confidence score is valid
            confidence = float(result.get('confidence_score', 50))
            confidence = max(0, min(100, confidence))
            
            reasoning = result.get('reasoning', response_text)
            
            return {
                'recommendation': recommendation.lower(),
                'confidence_score': confidence,
                'reasoning': reasoning,
                'raw_response': response_text
            }
            
        except Exception as e:
            # Log error but don't print to console in production
            error_msg = str(e)
            if '10061' in error_msg or 'connection' in error_msg.lower():
                # Connection error - Ollama server not available
                return {
                    'recommendation': 'hold',
                    'confidence_score': 0,
                    'reasoning': 'Ollama server is not available. Please check the connection settings in Settings page.',
                    'raw_response': ''
                }
            else:
                # Other error
                return {
                    'recommendation': 'hold',
                    'confidence_score': 0,
                    'reasoning': f'Error during analysis: {error_msg}. Please check Ollama configuration.',
                    'raw_response': ''
                }

    def _parse_response_fallback(self, response_text: str) -> dict:
        """Fallback parser for non-JSON responses"""
        result = {
            'recommendation': 'HOLD',
            'confidence_score': 50,
            'reasoning': response_text
        }
        
        # Try to extract recommendation
        if 'BUY' in response_text.upper():
            result['recommendation'] = 'BUY'
        elif 'SELL' in response_text.upper():
            result['recommendation'] = 'SELL'
        
        # Try to extract confidence score
        confidence_match = re.search(r'confidence[:\s]+(\d+)', response_text, re.IGNORECASE)
        if confidence_match:
            result['confidence_score'] = int(confidence_match.group(1))
        
        return result

