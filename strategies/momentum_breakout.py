#!/usr/bin/env python3
"""
Momentum Breakout Strategy - Trades on price momentum and volume
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
from strategies.base_strategy import BaseStrategy

class MomentumBreakoutStrategy(BaseStrategy):
    """
    Momentum breakout strategy that trades on price acceleration.
    """
    
    def __init__(self, parameters: Dict[str, Any] = None):
        default_params = {
            'momentum_period': 5,
            'volatility_period': 10,
            'breakout_threshold': 0.5,  # Low threshold for more signals
            'volume_multiplier': 1.2,
            'signal_cooldown': 2,
        }
        
        if parameters:
            default_params.update(parameters)
            
        super().__init__("Momentum_Breakout", default_params)
        self.last_signal_time = 0
    
    def get_signal(self, data: pd.DataFrame) -> Optional[str]:
        """Generate momentum breakout signals."""
        if len(data) < 20:
            return None
        
        try:
            import time
            current_time = time.time()
            
            # Check cooldown
            if current_time - self.last_signal_time < self.parameters['signal_cooldown']:
                return None
            
            # Calculate momentum indicators
            momentum_period = self.parameters['momentum_period']
            
            # Price momentum
            data['price_momentum'] = data['close'].pct_change(momentum_period)
            
            # Volatility (ATR-based)
            data['volatility'] = self._calculate_atr(data, self.parameters['volatility_period'])
            
            # Recent values
            current = data.iloc[-1]
            
            # Check for momentum breakout
            momentum = current['price_momentum']
            volatility = current['volatility']
            
            breakout_threshold = self.parameters['breakout_threshold'] / 100  # Convert to decimal
            
            # Normalize momentum by volatility if available
            if volatility > 0:
                normalized_momentum = abs(momentum) / (volatility / current['close'])
            else:
                normalized_momentum = abs(momentum)
            
            # BUY signal: Strong upward momentum
            if momentum > breakout_threshold / 100 and normalized_momentum > 0.1:
                self.last_signal_time = current_time
                self.logger.info(f"Momentum breakout BUY: momentum={momentum:.5f}")
                return 'BUY'
            
            # SELL signal: Strong downward momentum
            elif momentum < -breakout_threshold / 100 and normalized_momentum > 0.1:
                self.last_signal_time = current_time
                self.logger.info(f"Momentum breakout SELL: momentum={momentum:.5f}")
                return 'SELL'
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error in momentum breakout signal: {e}")
            return None
    
    def get_stop_loss(self, data: pd.DataFrame, signal: str, entry_price: float) -> Optional[float]:
        """ATR-based stop loss."""
        try:
            atr = self._calculate_atr(data, 10).iloc[-1]
            if pd.isna(atr) or atr == 0:
                stop_percentage = 0.0005
                if signal == 'BUY':
                    return entry_price * (1 - stop_percentage)
                else:
                    return entry_price * (1 + stop_percentage)
            
            stop_distance = atr * 1.0  # 1x ATR
            
            if signal == 'BUY':
                return entry_price - stop_distance
            else:
                return entry_price + stop_distance
                
        except Exception as e:
            self.logger.error(f"Error calculating momentum stop loss: {e}")
            return None
    
    def get_take_profit(self, data: pd.DataFrame, signal: str, entry_price: float) -> Optional[float]:
        """ATR-based take profit."""
        try:
            atr = self._calculate_atr(data, 10).iloc[-1]
            if pd.isna(atr) or atr == 0:
                profit_percentage = 0.001
                if signal == 'BUY':
                    return entry_price * (1 + profit_percentage)
                else:
                    return entry_price * (1 - profit_percentage)
            
            profit_distance = atr * 2.0  # 2x ATR
            
            if signal == 'BUY':
                return entry_price + profit_distance
            else:
                return entry_price - profit_distance
                
        except Exception as e:
            self.logger.error(f"Error calculating momentum take profit: {e}")
            return None
    
    def get_minimum_bars(self) -> int:
        return 20
