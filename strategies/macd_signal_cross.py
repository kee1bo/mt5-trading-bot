import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
from .base_strategy import BaseStrategy

class MACDSignalCrossStrategy(BaseStrategy):
    """
    MACD Signal Line Cross Strategy.
    
    Moving Average Convergence Divergence strategy for momentum trading:
    - BUY Signal: MACD line crosses above Signal line (preferably below zero)
    - SELL Signal: MACD line crosses below Signal line (preferably above zero)
    
    Best for: Identifying the start of new short-term trends
    """
    
    def __init__(self, parameters: Dict[str, Any] = None):
        default_params = {
            'fast_period': 12,
            'slow_period': 26,
            'signal_period': 9,
            'atr_period': 14,
            'stop_loss_atr_multiplier': 1.2,
            'take_profit_atr_multiplier': 2.4,
            'zero_line_filter': True,  # Prefer signals below/above zero line
            'histogram_confirmation': True,  # Require histogram confirmation
            'trend_filter': True,  # Use trend filter
            'trend_ema_period': 50,
        }
        
        if parameters:
            default_params.update(parameters)
            
        super().__init__("MACD_Signal_Cross", default_params)
    
    def get_signal(self, data: pd.DataFrame) -> Optional[str]:
        """Generate trading signal based on MACD signal line crossover."""
        if len(data) < self.get_minimum_bars():
            return None
        
        try:
            # Calculate MACD
            fast_period = self.parameters['fast_period']
            slow_period = self.parameters['slow_period']
            signal_period = self.parameters['signal_period']
            
            macd_data = self._calculate_macd(data['close'], fast_period, slow_period, signal_period)
            data['macd'] = macd_data['macd']
            data['macd_signal'] = macd_data['signal']
            data['macd_histogram'] = macd_data['histogram']
            
            # Calculate ATR
            atr_period = self.parameters['atr_period']
            data['atr'] = self._calculate_atr(data, atr_period)
            
            # Calculate trend filter if enabled
            if self.parameters['trend_filter']:
                trend_ema_period = self.parameters['trend_ema_period']
                data['trend_ema'] = self._calculate_ema(data['close'], trend_ema_period)
            
            last_candle = data.iloc[-1]
            previous_candle = data.iloc[-2]
            
            # Check for MACD crossover above signal line (BUY signal)
            if (previous_candle['macd'] <= previous_candle['macd_signal'] and 
                last_candle['macd'] > last_candle['macd_signal']):
                
                if self._confirm_signal(data, 'BUY'):
                    signal = 'BUY'
                    if self.validate_signal(data, signal):
                        self.logger.info(f"MACD BUY signal: MACD={last_candle['macd']:.5f}, "
                                       f"Signal={last_candle['macd_signal']:.5f}")
                        return signal
            
            # Check for MACD crossover below signal line (SELL signal)
            elif (previous_candle['macd'] >= previous_candle['macd_signal'] and 
                  last_candle['macd'] < last_candle['macd_signal']):
                
                if self._confirm_signal(data, 'SELL'):
                    signal = 'SELL'
                    if self.validate_signal(data, signal):
                        self.logger.info(f"MACD SELL signal: MACD={last_candle['macd']:.5f}, "
                                       f"Signal={last_candle['macd_signal']:.5f}")
                        return signal
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error in MACD signal generation: {e}")
            return None
    
    def get_stop_loss(self, data: pd.DataFrame, signal: str, entry_price: float) -> Optional[float]:
        """Calculate stop loss based on MACD levels and ATR."""
        try:
            # Calculate ATR
            atr_period = self.parameters['atr_period']
            atr_multiplier = self.parameters['stop_loss_atr_multiplier']
            data['atr'] = self._calculate_atr(data, atr_period)
            
            current_atr = data['atr'].iloc[-1]
            
            if pd.isna(current_atr) or current_atr == 0:
                return self._get_percentage_stop_loss(entry_price, signal, 0.002)  # 0.2%
            
            # Use ATR-based stop loss with consideration for recent swing points
            if signal == 'BUY':
                swing_low = self._find_recent_swing_low(data)
                if swing_low:
                    swing_based_sl = swing_low - (current_atr * 0.5)
                    atr_based_sl = entry_price - (current_atr * atr_multiplier)
                    stop_loss = max(swing_based_sl, atr_based_sl)
                else:
                    stop_loss = entry_price - (current_atr * atr_multiplier)
            else:  # SELL
                swing_high = self._find_recent_swing_high(data)
                if swing_high:
                    swing_based_sl = swing_high + (current_atr * 0.5)
                    atr_based_sl = entry_price + (current_atr * atr_multiplier)
                    stop_loss = min(swing_based_sl, atr_based_sl)
                else:
                    stop_loss = entry_price + (current_atr * atr_multiplier)
            
            return round(stop_loss, 5)
            
        except Exception as e:
            self.logger.error(f"Error calculating stop loss: {e}")
            return self._get_percentage_stop_loss(entry_price, signal, 0.002)
    
    def get_take_profit(self, data: pd.DataFrame, signal: str, entry_price: float) -> Optional[float]:
        """Calculate take profit based on MACD momentum and ATR."""
        try:
            # Calculate ATR
            atr_period = self.parameters['atr_period']
            atr_multiplier = self.parameters['take_profit_atr_multiplier']
            data['atr'] = self._calculate_atr(data, atr_period)
            
            current_atr = data['atr'].iloc[-1]
            
            if pd.isna(current_atr) or current_atr == 0:
                return self._get_percentage_take_profit(entry_price, signal, 0.004)  # 0.4%
            
            # Calculate target based on ATR
            if signal == 'BUY':
                take_profit = entry_price + (current_atr * atr_multiplier)
            else:  # SELL
                take_profit = entry_price - (current_atr * atr_multiplier)
            
            return round(take_profit, 5)
            
        except Exception as e:
            self.logger.error(f"Error calculating take profit: {e}")
            return self._get_percentage_take_profit(entry_price, signal, 0.004)
    
    def should_exit(self, data: pd.DataFrame, position: Dict[str, Any]) -> bool:
        """Check if position should be closed based on MACD reversal."""
        try:
            if len(data) < self.get_minimum_bars():
                return False
            
            # Calculate MACD
            fast_period = self.parameters['fast_period']
            slow_period = self.parameters['slow_period']
            signal_period = self.parameters['signal_period']
            
            macd_data = self._calculate_macd(data['close'], fast_period, slow_period, signal_period)
            current_macd = macd_data['macd'].iloc[-1]
            current_signal = macd_data['signal'].iloc[-1]
            previous_macd = macd_data['macd'].iloc[-2]
            previous_signal = macd_data['signal'].iloc[-2]
            
            position_type = position.get('type', '')
            
            # Exit BUY position if MACD crosses below signal line
            if (position_type == 'BUY' and 
                previous_macd >= previous_signal and current_macd < current_signal):
                self.logger.info("Exit signal: BUY position, MACD crossed below signal")
                return True
            
            # Exit SELL position if MACD crosses above signal line
            if (position_type == 'SELL' and 
                previous_macd <= previous_signal and current_macd > current_signal):
                self.logger.info("Exit signal: SELL position, MACD crossed above signal")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking exit condition: {e}")
            return False
    
    def get_minimum_bars(self) -> int:
        """Get minimum bars required for MACD calculation."""
        return max(100, self.parameters['slow_period'] * 2, self.parameters['trend_ema_period'])
    
    def _confirm_signal(self, data: pd.DataFrame, signal: str) -> bool:
        """Confirm MACD signal with additional filters."""
        try:
            last_candle = data.iloc[-1]
            
            # Zero line filter
            if self.parameters['zero_line_filter']:
                if not self._check_zero_line_filter(last_candle, signal):
                    self.logger.debug("Signal rejected: zero line filter")
                    return False
            
            # Histogram confirmation
            if self.parameters['histogram_confirmation']:
                if not self._check_histogram_confirmation(data, signal):
                    self.logger.debug("Signal rejected: histogram not confirmed")
                    return False
            
            # Trend filter
            if self.parameters['trend_filter']:
                if not self._check_trend_filter(data, signal):
                    self.logger.debug("Signal rejected: trend filter")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error confirming MACD signal: {e}")
            return False
    
    def _check_zero_line_filter(self, candle: pd.Series, signal: str) -> bool:
        """Check zero line filter for signal quality."""
        try:
            macd_value = candle['macd']
            
            if signal == 'BUY':
                # Prefer BUY signals when MACD is below zero (potential reversal)
                return macd_value <= 0
            else:  # SELL
                # Prefer SELL signals when MACD is above zero (potential reversal)
                return macd_value >= 0
                
        except Exception as e:
            self.logger.error(f"Error checking zero line filter: {e}")
            return True
    
    def _check_histogram_confirmation(self, data: pd.DataFrame, signal: str) -> bool:
        """Check histogram for momentum confirmation."""
        try:
            if len(data) < 2:
                return True
            
            current_hist = data['macd_histogram'].iloc[-1]
            previous_hist = data['macd_histogram'].iloc[-2]
            
            if signal == 'BUY':
                # For BUY, histogram should be increasing (momentum building)
                return current_hist > previous_hist
            else:  # SELL
                # For SELL, histogram should be decreasing (momentum building)
                return current_hist < previous_hist
                
        except Exception as e:
            self.logger.error(f"Error checking histogram confirmation: {e}")
            return True
    
    def _check_trend_filter(self, data: pd.DataFrame, signal: str) -> bool:
        """Check trend filter for signal alignment."""
        try:
            current_price = data['close'].iloc[-1]
            trend_ema = data['trend_ema'].iloc[-1]
            
            if signal == 'BUY':
                # For BUY, price should be above or near trend EMA
                return current_price >= trend_ema * 0.999  # Small tolerance
            else:  # SELL
                # For SELL, price should be below or near trend EMA
                return current_price <= trend_ema * 1.001  # Small tolerance
                
        except Exception as e:
            self.logger.error(f"Error checking trend filter: {e}")
            return True
    
    def _find_recent_swing_low(self, data: pd.DataFrame, lookback: int = 10) -> Optional[float]:
        """Find recent swing low for stop loss calculation."""
        try:
            if len(data) < lookback + 2:
                return None
            
            recent_data = data.iloc[-lookback:]
            return recent_data['low'].min()
            
        except Exception as e:
            self.logger.error(f"Error finding swing low: {e}")
            return None
    
    def _find_recent_swing_high(self, data: pd.DataFrame, lookback: int = 10) -> Optional[float]:
        """Find recent swing high for stop loss calculation."""
        try:
            if len(data) < lookback + 2:
                return None
            
            recent_data = data.iloc[-lookback:]
            return recent_data['high'].max()
            
        except Exception as e:
            self.logger.error(f"Error finding swing high: {e}")
            return None
    
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
        """Get MACD signal cross strategy information."""
        info = super().get_strategy_info()
        info.update({
            'strategy_type': 'Momentum',
            'timeframe_suitability': ['M5', 'M15', 'M30', 'H1'],
            'market_condition': 'Trending',
            'risk_level': 'Medium',
            'description': 'MACD signal line crossover strategy for momentum trading'
        })
        return info
