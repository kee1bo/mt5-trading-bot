import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
from .base_strategy import BaseStrategy

class EMACrossoverStrategy(BaseStrategy):
    """
    5 EMA Crossover Strategy for Scalping.
    
    This strategy uses a 5-period Exponential Moving Average to generate signals.
    - BUY Signal: Price closes above the 5 EMA
    - SELL Signal: Price closes below the 5 EMA
    
    Best for: Trending markets on very low timeframes (M1, M5)
    """
    
    def __init__(self, parameters: Dict[str, Any] = None):
        default_params = {
            'ema_period': 5,
            'confirmation_candles': 1,
            'atr_period': 14,
            'stop_loss_atr_multiplier': 1.5,
            'take_profit_atr_multiplier': 2.5,
            'min_atr_filter': 0.0001,  # Minimum ATR to avoid low volatility periods
        }
        
        if parameters:
            default_params.update(parameters)
            
        super().__init__("EMA_Crossover", default_params)
    
    def get_signal(self, data: pd.DataFrame) -> Optional[str]:
        """Generate trading signal based on 5 EMA crossover."""
        if len(data) < self.get_minimum_bars():
            return None
        
        try:
            # Calculate 5 EMA
            ema_period = self.parameters['ema_period']
            data['ema'] = self._calculate_ema(data['close'], ema_period)
            
            # Calculate ATR for volatility filter
            atr_period = self.parameters['atr_period']
            data['atr'] = self._calculate_atr(data, atr_period)
            
            # Get recent data
            last_candle = data.iloc[-1]
            previous_candle = data.iloc[-2]
            
            # Check volatility filter
            if last_candle['atr'] < self.parameters['min_atr_filter']:
                self.logger.debug("Signal filtered out due to low volatility")
                return None
            
            # Check for EMA crossover
            confirmation_candles = self.parameters['confirmation_candles']
            
            # BUY Signal: Price crossed above EMA
            if (previous_candle['close'] <= previous_candle['ema'] and 
                last_candle['close'] > last_candle['ema']):
                
                # Additional confirmation if required
                if confirmation_candles > 1:
                    if not self._check_trend_confirmation(data, 'BUY', confirmation_candles):
                        return None
                
                signal = 'BUY'
                if self.validate_signal(data, signal):
                    self.logger.info(f"EMA Crossover BUY signal generated at {last_candle['close']}")
                    return signal
            
            # SELL Signal: Price crossed below EMA
            elif (previous_candle['close'] >= previous_candle['ema'] and 
                  last_candle['close'] < last_candle['ema']):
                
                # Additional confirmation if required
                if confirmation_candles > 1:
                    if not self._check_trend_confirmation(data, 'SELL', confirmation_candles):
                        return None
                
                signal = 'SELL'
                if self.validate_signal(data, signal):
                    self.logger.info(f"EMA Crossover SELL signal generated at {last_candle['close']}")
                    return signal
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error in EMA crossover signal generation: {e}")
            return None
    
    def get_stop_loss(self, data: pd.DataFrame, signal: str, entry_price: float) -> Optional[float]:
        """Calculate stop loss based on ATR."""
        try:
            # Calculate ATR
            atr_period = self.parameters['atr_period']
            atr_multiplier = self.parameters['stop_loss_atr_multiplier']
            
            data['atr'] = self._calculate_atr(data, atr_period)
            current_atr = data['atr'].iloc[-1]
            
            if pd.isna(current_atr) or current_atr == 0:
                # Fallback to percentage-based SL
                return self._get_percentage_stop_loss(entry_price, signal, 0.001)  # 0.1%
            
            if signal == 'BUY':
                stop_loss = entry_price - (current_atr * atr_multiplier)
            else:  # SELL
                stop_loss = entry_price + (current_atr * atr_multiplier)
            
            return round(stop_loss, 5)
            
        except Exception as e:
            self.logger.error(f"Error calculating stop loss: {e}")
            return self._get_percentage_stop_loss(entry_price, signal, 0.001)
    
    def get_take_profit(self, data: pd.DataFrame, signal: str, entry_price: float) -> Optional[float]:
        """Calculate take profit based on ATR."""
        try:
            # Calculate ATR
            atr_period = self.parameters['atr_period']
            atr_multiplier = self.parameters['take_profit_atr_multiplier']
            
            data['atr'] = self._calculate_atr(data, atr_period)
            current_atr = data['atr'].iloc[-1]
            
            if pd.isna(current_atr) or current_atr == 0:
                # Fallback to percentage-based TP
                return self._get_percentage_take_profit(entry_price, signal, 0.002)  # 0.2%
            
            if signal == 'BUY':
                take_profit = entry_price + (current_atr * atr_multiplier)
            else:  # SELL
                take_profit = entry_price - (current_atr * atr_multiplier)
            
            return round(take_profit, 5)
            
        except Exception as e:
            self.logger.error(f"Error calculating take profit: {e}")
            return self._get_percentage_take_profit(entry_price, signal, 0.002)
    
    def should_exit(self, data: pd.DataFrame, position: Dict[str, Any]) -> bool:
        """Check if position should be closed based on EMA reversal."""
        try:
            if len(data) < self.get_minimum_bars():
                return False
            
            # Calculate EMA
            ema_period = self.parameters['ema_period']
            data['ema'] = self._calculate_ema(data['close'], ema_period)
            
            current_price = data['close'].iloc[-1]
            current_ema = data['ema'].iloc[-1]
            position_type = position.get('type', '')
            
            # Exit BUY position if price closes below EMA
            if position_type == 'BUY' and current_price < current_ema:
                self.logger.info("Exit signal: BUY position, price below EMA")
                return True
            
            # Exit SELL position if price closes above EMA
            if position_type == 'SELL' and current_price > current_ema:
                self.logger.info("Exit signal: SELL position, price above EMA")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking exit condition: {e}")
            return False
    
    def get_minimum_bars(self) -> int:
        """Get minimum bars required for EMA calculation."""
        return max(50, self.parameters['ema_period'] * 3, self.parameters['atr_period'] * 2)
    
    def _check_trend_confirmation(self, data: pd.DataFrame, signal: str, 
                                 confirmation_candles: int) -> bool:
        """Check for trend confirmation over multiple candles."""
        try:
            if len(data) < confirmation_candles + 1:
                return False
            
            # Check the last N candles for trend confirmation
            recent_data = data.iloc[-(confirmation_candles + 1):]
            
            if signal == 'BUY':
                # For BUY signal, check if recent candles show upward momentum
                return all(
                    recent_data['close'].iloc[i] >= recent_data['close'].iloc[i-1] 
                    for i in range(1, len(recent_data))
                )
            else:  # SELL
                # For SELL signal, check if recent candles show downward momentum
                return all(
                    recent_data['close'].iloc[i] <= recent_data['close'].iloc[i-1] 
                    for i in range(1, len(recent_data))
                )
                
        except Exception as e:
            self.logger.error(f"Error checking trend confirmation: {e}")
            return False
    
    def _get_percentage_stop_loss(self, entry_price: float, signal: str, percentage: float) -> float:
        """Calculate percentage-based stop loss."""
        if signal == 'BUY':
            return entry_price * (1 - percentage)
        else:  # SELL
            return entry_price * (1 + percentage)
    
    def _get_percentage_take_profit(self, entry_price: float, signal: str, percentage: float) -> float:
        """Calculate percentage-based take profit."""
        if signal == 'BUY':
            return entry_price * (1 + percentage)
        else:  # SELL
            return entry_price * (1 - percentage)
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get EMA crossover strategy information."""
        info = super().get_strategy_info()
        info.update({
            'strategy_type': 'Trend Following',
            'timeframe_suitability': ['M1', 'M5'],
            'market_condition': 'Trending',
            'risk_level': 'High',
            'description': 'Fast EMA crossover strategy for scalping trending markets'
        })
        return info
