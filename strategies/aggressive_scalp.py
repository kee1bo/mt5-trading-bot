#!/usr/bin/env python3
"""
Aggressive Scalping Strategy - Very sensitive to small price movements
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
from strategies.base_strategy import BaseStrategy

class AggressiveScalpStrategy(BaseStrategy):
    """
    Ultra-aggressive scalping strategy that trades on minimal price movements.
    Designed to generate frequent signals.
    """
    
    def __init__(self, parameters: Dict[str, Any] = None):
        default_params = {
            'min_price_change': 0.01,  # Minimum price change in points
            'momentum_periods': 3,     # Very short momentum calculation
            'volume_threshold': 0.8,   # Low volume threshold
            'atr_multiplier': 0.5,     # Very tight ATR-based stops
            'signal_cooldown': 1,      # Only 1 second cooldown
            'risk_reward_ratio': 1.5,  # 1:1.5 risk/reward
        }
        
        if parameters:
            default_params.update(parameters)
            
        super().__init__("Aggressive_Scalp", default_params)
        self.last_signal_time = 0
    
    def get_signal(self, data: pd.DataFrame) -> Optional[str]:
        """Generate signals on minimal price movements."""
        if len(data) < 10:
            return None
        
        try:
            import time
            current_time = time.time()
            
            # Check cooldown
            if current_time - self.last_signal_time < self.parameters['signal_cooldown']:
                return None
            
            # Get recent price action
            current = data.iloc[-1]
            previous = data.iloc[-2]
            
            # Calculate short-term momentum
            momentum_periods = self.parameters['momentum_periods']
            recent_data = data.tail(momentum_periods)
            
            price_change = current['close'] - previous['close']
            momentum = (current['close'] - recent_data['close'].iloc[0]) / recent_data['close'].iloc[0]
            
            # Very sensitive thresholds
            min_change = self.parameters['min_price_change'] / 10000  # Convert to decimal
            
            # BUY signal: Small upward movement
            if price_change > min_change and momentum > 0:
                self.last_signal_time = current_time
                self.logger.info(f"Aggressive scalp BUY: price_change={price_change:.5f}, momentum={momentum:.5f}")
                return 'BUY'
            
            # SELL signal: Small downward movement  
            elif price_change < -min_change and momentum < 0:
                self.last_signal_time = current_time
                self.logger.info(f"Aggressive scalp SELL: price_change={price_change:.5f}, momentum={momentum:.5f}")
                return 'SELL'
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error in aggressive scalp signal: {e}")
            return None
    
    def get_stop_loss(self, data: pd.DataFrame, signal: str, entry_price: float) -> Optional[float]:
        """Very tight stop losses."""
        try:
            # Use very small percentage stops
            stop_percentage = 0.0002  # 0.02%
            
            if signal == 'BUY':
                return entry_price * (1 - stop_percentage)
            else:
                return entry_price * (1 + stop_percentage)
                
        except Exception as e:
            self.logger.error(f"Error calculating aggressive stop loss: {e}")
            return None
    
    def get_take_profit(self, data: pd.DataFrame, signal: str, entry_price: float) -> Optional[float]:
        """Quick profit targets."""
        try:
            profit_percentage = 0.0003  # 0.03%
            
            if signal == 'BUY':
                return entry_price * (1 + profit_percentage)
            else:
                return entry_price * (1 - profit_percentage)
                
        except Exception as e:
            self.logger.error(f"Error calculating aggressive take profit: {e}")
            return None
    
    def get_minimum_bars(self) -> int:
        return 10
