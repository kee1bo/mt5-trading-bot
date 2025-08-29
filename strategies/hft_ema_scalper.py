#!/usr/bin/env python3
"""
Optimized High-Frequency Trading Strategy - Ultra-Fast EMA Scalper
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
from strategies.base_strategy import BaseStrategy

class HFTEMAScalper(BaseStrategy):
    """
    Ultra-fast EMA scalping strategy optimized for high-frequency trading.
    
    Features:
    - 3-period EMA for ultra-fast signals
    - Micro stop losses and take profits
    - No confirmation delays
    - Optimized for 1-minute or tick data
    """
    
    def __init__(self, parameters: Dict[str, Any] = None):
        default_params = {
            'fast_ema': 3,
            'slow_ema': 8,
            'atr_period': 10,
            'stop_loss_atr_multiplier': 0.8,
            'take_profit_atr_multiplier': 1.2,
            'min_atr_filter': 0.00001,
            'signal_cooldown': 0,  # No cooldown for HFT
            'momentum_threshold': 0.0001,  # Minimum price movement
            'volume_filter': False,  # Disable for speed
        }
        
        if parameters:
            default_params.update(parameters)
            
        super().__init__("HFT_EMA_Scalper", default_params)
        self.last_signal_time = 0
        self.signal_cache = {}
    
    def get_signal(self, data: pd.DataFrame) -> Optional[str]:
        """Ultra-fast signal generation for HFT."""
        try:
            if len(data) < self.get_minimum_bars():
                return None
            
            # Get current timestamp for cooldown
            current_time = data.index[-1].timestamp()
            
            # Check signal cooldown
            if current_time - self.last_signal_time < self.parameters['signal_cooldown']:
                return None
            
            # Calculate EMAs
            fast_ema = self.parameters['fast_ema']
            slow_ema = self.parameters['slow_ema']
            
            data['ema_fast'] = data['close'].ewm(span=fast_ema, adjust=False).mean()
            data['ema_slow'] = data['close'].ewm(span=slow_ema, adjust=False).mean()
            
            # Calculate ATR for filters
            atr_period = self.parameters['atr_period']
            data['atr'] = self._calculate_atr(data, atr_period)
            
            # Get latest values
            current = data.iloc[-1]
            previous = data.iloc[-2]
            
            # ATR filter
            if current['atr'] < self.parameters['min_atr_filter']:
                return None
            
            # Momentum filter
            price_change = abs(current['close'] - previous['close'])
            if price_change < self.parameters['momentum_threshold']:
                return None
            
            # EMA crossover signals
            fast_current = current['ema_fast']
            fast_previous = previous['ema_fast']
            slow_current = current['ema_slow']
            slow_previous = previous['ema_slow']
            
            # BUY: Fast EMA crosses above Slow EMA
            if (fast_previous <= slow_previous and fast_current > slow_current):
                # Additional momentum confirmation
                if current['close'] > previous['close']:
                    self.last_signal_time = current_time
                    return 'BUY'
            
            # SELL: Fast EMA crosses below Slow EMA
            elif (fast_previous >= slow_previous and fast_current < slow_current):
                # Additional momentum confirmation
                if current['close'] < previous['close']:
                    self.last_signal_time = current_time
                    return 'SELL'
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error in HFT signal generation: {e}")
            return None
    
    def get_stop_loss(self, data: pd.DataFrame, signal: str, entry_price: float) -> Optional[float]:
        """Micro stop loss for HFT."""
        try:
            atr_period = self.parameters['atr_period']
            atr_multiplier = self.parameters['stop_loss_atr_multiplier']
            
            data['atr'] = self._calculate_atr(data, atr_period)
            current_atr = data['atr'].iloc[-1]
            
            if pd.isna(current_atr) or current_atr == 0:
                # Ultra-tight percentage-based SL for HFT
                percentage = 0.0005  # 0.05%
                if signal == 'BUY':
                    return entry_price * (1 - percentage)
                else:
                    return entry_price * (1 + percentage)
            
            # ATR-based stop loss
            atr_distance = current_atr * atr_multiplier
            
            if signal == 'BUY':
                stop_loss = entry_price - atr_distance
            else:
                stop_loss = entry_price + atr_distance
            
            return round(stop_loss, 5)
            
        except Exception as e:
            self.logger.error(f"Error calculating HFT stop loss: {e}")
            # Fallback to tight percentage
            percentage = 0.0005
            if signal == 'BUY':
                return entry_price * (1 - percentage)
            else:
                return entry_price * (1 + percentage)
    
    def get_take_profit(self, data: pd.DataFrame, signal: str, entry_price: float) -> Optional[float]:
        """Micro take profit for HFT."""
        try:
            atr_period = self.parameters['atr_period']
            atr_multiplier = self.parameters['take_profit_atr_multiplier']
            
            data['atr'] = self._calculate_atr(data, atr_period)
            current_atr = data['atr'].iloc[-1]
            
            if pd.isna(current_atr) or current_atr == 0:
                # Ultra-tight percentage-based TP for HFT
                percentage = 0.001  # 0.1%
                if signal == 'BUY':
                    return entry_price * (1 + percentage)
                else:
                    return entry_price * (1 - percentage)
            
            # ATR-based take profit
            atr_distance = current_atr * atr_multiplier
            
            if signal == 'BUY':
                take_profit = entry_price + atr_distance
            else:
                take_profit = entry_price - atr_distance
            
            return round(take_profit, 5)
            
        except Exception as e:
            self.logger.error(f"Error calculating HFT take profit: {e}")
            # Fallback to tight percentage
            percentage = 0.001
            if signal == 'BUY':
                return entry_price * (1 + percentage)
            else:
                return entry_price * (1 - percentage)
    
    def should_exit(self, data: pd.DataFrame, position: Dict[str, Any]) -> bool:
        """Fast exit conditions for HFT."""
        try:
            if len(data) < 5:
                return False
            
            # Calculate EMAs
            fast_ema = self.parameters['fast_ema']
            slow_ema = self.parameters['slow_ema']
            
            data['ema_fast'] = data['close'].ewm(span=fast_ema, adjust=False).mean()
            data['ema_slow'] = data['close'].ewm(span=slow_ema, adjust=False).mean()
            
            current = data.iloc[-1]
            position_type = position.get('type', '')
            
            # Exit on opposite crossover
            if position_type == 'BUY':
                if current['ema_fast'] < current['ema_slow']:
                    return True
            elif position_type == 'SELL':
                if current['ema_fast'] > current['ema_slow']:
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error in HFT exit check: {e}")
            return False
    
    def get_minimum_bars(self) -> int:
        """Minimum bars for HFT strategy."""
        return max(20, self.parameters['slow_ema'] * 2)
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Strategy information."""
        info = super().get_strategy_info()
        info.update({
            'strategy_type': 'High-Frequency Scalping',
            'timeframe_suitability': ['M1', 'Tick'],
            'market_condition': 'Any (optimized for volatility)',
            'risk_level': 'High',
            'frequency': 'Very High',
            'description': 'Ultra-fast EMA scalping for high-frequency trading'
        })
        return info
