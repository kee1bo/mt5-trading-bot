#!/usr/bin/env python3
"""
Mean Reversion Strategy - Trades when price deviates from mean
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
from strategies.base_strategy import BaseStrategy

class MeanReversionStrategy(BaseStrategy):
    """
    Mean reversion strategy that trades when price moves too far from average.
    """
    
    def __init__(self, parameters: Dict[str, Any] = None):
        default_params = {
            'ma_period': 10,           # Short moving average
            'std_multiplier': 1.0,     # Low multiplier for more signals
            'rsi_period': 7,           # Short RSI period
            'rsi_oversold': 40,        # Less extreme RSI levels
            'rsi_overbought': 60,
            'signal_cooldown': 3,
        }
        
        if parameters:
            default_params.update(parameters)
            
        super().__init__("Mean_Reversion", default_params)
        self.last_signal_time = 0
    
    def get_signal(self, data: pd.DataFrame) -> Optional[str]:
        """Generate mean reversion signals."""
        if len(data) < 30:
            return None
        
        try:
            import time
            current_time = time.time()
            
            # Check cooldown
            if current_time - self.last_signal_time < self.parameters['signal_cooldown']:
                return None
            
            # Calculate indicators
            ma_period = self.parameters['ma_period']
            data['ma'] = data['close'].rolling(window=ma_period).mean()
            data['std'] = data['close'].rolling(window=ma_period).std()
            
            # Bollinger-like bands
            std_multiplier = self.parameters['std_multiplier']
            data['upper_band'] = data['ma'] + (data['std'] * std_multiplier)
            data['lower_band'] = data['ma'] - (data['std'] * std_multiplier)
            
            # RSI
            data['rsi'] = self._calculate_rsi(data['close'], self.parameters['rsi_period'])
            
            current = data.iloc[-1]
            
            # BUY signal: Price below lower band AND RSI oversold
            if (current['close'] < current['lower_band'] and 
                current['rsi'] < self.parameters['rsi_oversold']):
                
                self.last_signal_time = current_time
                self.logger.info(f"Mean reversion BUY: price={current['close']:.2f}, lower_band={current['lower_band']:.2f}, rsi={current['rsi']:.1f}")
                return 'BUY'
            
            # SELL signal: Price above upper band AND RSI overbought
            elif (current['close'] > current['upper_band'] and 
                  current['rsi'] > self.parameters['rsi_overbought']):
                
                self.last_signal_time = current_time
                self.logger.info(f"Mean reversion SELL: price={current['close']:.2f}, upper_band={current['upper_band']:.2f}, rsi={current['rsi']:.1f}")
                return 'SELL'
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error in mean reversion signal: {e}")
            return None
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate RSI."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def get_stop_loss(self, data: pd.DataFrame, signal: str, entry_price: float) -> Optional[float]:
        """Stop loss at opposite band."""
        try:
            current = data.iloc[-1]
            
            if signal == 'BUY':
                # Stop loss slightly below the moving average
                return current['ma'] * 0.998
            else:
                # Stop loss slightly above the moving average
                return current['ma'] * 1.002
                
        except Exception as e:
            self.logger.error(f"Error calculating mean reversion stop loss: {e}")
            return None
    
    def get_take_profit(self, data: pd.DataFrame, signal: str, entry_price: float) -> Optional[float]:
        """Take profit at moving average."""
        try:
            current = data.iloc[-1]
            
            # Target the moving average
            return current['ma']
                
        except Exception as e:
            self.logger.error(f"Error calculating mean reversion take profit: {e}")
            return None
    
    def get_minimum_bars(self) -> int:
        return 30
