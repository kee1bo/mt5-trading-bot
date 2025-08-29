import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
from .base_strategy import BaseStrategy

class StochasticMomentumStrategy(BaseStrategy):
    """
    Stochastic Oscillator Momentum Strategy.
    
    This momentum indicator helps identify overbought/oversold conditions:
    - BUY Signal: Stochastic %K crosses above %D in oversold region (< 20)
    - SELL Signal: Stochastic %K crosses below %D in overbought region (> 80)
    
    Best for: Ranging markets with predictable support and resistance levels
    """
    
    def __init__(self, parameters: Dict[str, Any] = None):
        default_params = {
            'k_period': 14,
            'd_period': 3,
            'smooth_k': 3,
            'overbought': 80,
            'oversold': 20,
            'atr_period': 14,
            'stop_loss_atr_multiplier': 1.0,
            'take_profit_atr_multiplier': 2.0,
            'momentum_confirmation': True,  # Require momentum confirmation
            'rsi_filter': True,  # Use RSI as additional filter
            'rsi_period': 14,
        }
        
        if parameters:
            default_params.update(parameters)
            
        super().__init__("Stochastic_Momentum", default_params)
    
    def get_signal(self, data: pd.DataFrame) -> Optional[str]:
        """Generate trading signal based on Stochastic crossover."""
        if len(data) < self.get_minimum_bars():
            return None
        
        try:
            # Calculate Stochastic Oscillator
            k_period = self.parameters['k_period']
            d_period = self.parameters['d_period']
            smooth_k = self.parameters['smooth_k']
            
            stoch_data = self._calculate_stochastic(data, k_period, d_period, smooth_k)
            data['stoch_k'] = stoch_data['k']
            data['stoch_d'] = stoch_data['d']
            
            # Calculate ATR
            atr_period = self.parameters['atr_period']
            data['atr'] = self._calculate_atr(data, atr_period)
            
            # Calculate RSI if filter is enabled
            if self.parameters['rsi_filter']:
                rsi_period = self.parameters['rsi_period']
                data['rsi'] = self._calculate_rsi(data['close'], rsi_period)
            
            last_candle = data.iloc[-1]
            previous_candle = data.iloc[-2]
            
            overbought = self.parameters['overbought']
            oversold = self.parameters['oversold']
            
            # Check for BUY signal (oversold crossover)
            if (self._check_stoch_crossover(data, 'BUY') and 
                last_candle['stoch_k'] < oversold):
                
                if self._confirm_signal(data, 'BUY'):
                    signal = 'BUY'
                    if self.validate_signal(data, signal):
                        self.logger.info(f"Stochastic BUY signal: K={last_candle['stoch_k']:.1f}, "
                                       f"D={last_candle['stoch_d']:.1f}")
                        return signal
            
            # Check for SELL signal (overbought crossover)
            elif (self._check_stoch_crossover(data, 'SELL') and 
                  last_candle['stoch_k'] > overbought):
                
                if self._confirm_signal(data, 'SELL'):
                    signal = 'SELL'
                    if self.validate_signal(data, signal):
                        self.logger.info(f"Stochastic SELL signal: K={last_candle['stoch_k']:.1f}, "
                                       f"D={last_candle['stoch_d']:.1f}")
                        return signal
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error in Stochastic signal generation: {e}")
            return None
    
    def get_stop_loss(self, data: pd.DataFrame, signal: str, entry_price: float) -> Optional[float]:
        """Calculate stop loss based on recent swing points and ATR."""
        try:
            # Calculate ATR
            atr_period = self.parameters['atr_period']
            atr_multiplier = self.parameters['stop_loss_atr_multiplier']
            data['atr'] = self._calculate_atr(data, atr_period)
            
            current_atr = data['atr'].iloc[-1]
            
            if pd.isna(current_atr) or current_atr == 0:
                return self._get_percentage_stop_loss(entry_price, signal, 0.0015)  # 0.15%
            
            # Find recent swing points for tighter stops
            if signal == 'BUY':
                swing_low = self._find_recent_swing_low(data)
                if swing_low:
                    swing_based_sl = swing_low - (current_atr * 0.3)
                    atr_based_sl = entry_price - (current_atr * atr_multiplier)
                    stop_loss = max(swing_based_sl, atr_based_sl)
                else:
                    stop_loss = entry_price - (current_atr * atr_multiplier)
            else:  # SELL
                swing_high = self._find_recent_swing_high(data)
                if swing_high:
                    swing_based_sl = swing_high + (current_atr * 0.3)
                    atr_based_sl = entry_price + (current_atr * atr_multiplier)
                    stop_loss = min(swing_based_sl, atr_based_sl)
                else:
                    stop_loss = entry_price + (current_atr * atr_multiplier)
            
            return round(stop_loss, 5)
            
        except Exception as e:
            self.logger.error(f"Error calculating stop loss: {e}")
            return self._get_percentage_stop_loss(entry_price, signal, 0.0015)
    
    def get_take_profit(self, data: pd.DataFrame, signal: str, entry_price: float) -> Optional[float]:
        """Calculate take profit based on opposite Stochastic level and ATR."""
        try:
            # Calculate ATR
            atr_period = self.parameters['atr_period']
            atr_multiplier = self.parameters['take_profit_atr_multiplier']
            data['atr'] = self._calculate_atr(data, atr_period)
            
            current_atr = data['atr'].iloc[-1]
            
            if pd.isna(current_atr) or current_atr == 0:
                return self._get_percentage_take_profit(entry_price, signal, 0.003)  # 0.3%
            
            # Calculate target based on ATR
            if signal == 'BUY':
                take_profit = entry_price + (current_atr * atr_multiplier)
            else:  # SELL
                take_profit = entry_price - (current_atr * atr_multiplier)
            
            return round(take_profit, 5)
            
        except Exception as e:
            self.logger.error(f"Error calculating take profit: {e}")
            return self._get_percentage_take_profit(entry_price, signal, 0.003)
    
    def should_exit(self, data: pd.DataFrame, position: Dict[str, Any]) -> bool:
        """Check if position should be closed based on Stochastic reversal."""
        try:
            if len(data) < self.get_minimum_bars():
                return False
            
            # Calculate Stochastic
            k_period = self.parameters['k_period']
            d_period = self.parameters['d_period']
            smooth_k = self.parameters['smooth_k']
            
            stoch_data = self._calculate_stochastic(data, k_period, d_period, smooth_k)
            current_k = stoch_data['k'].iloc[-1]
            current_d = stoch_data['d'].iloc[-1]
            
            position_type = position.get('type', '')
            overbought = self.parameters['overbought']
            oversold = self.parameters['oversold']
            
            # Exit BUY position if Stochastic becomes overbought and crosses down
            if (position_type == 'BUY' and current_k > overbought and 
                self._check_stoch_crossover(data, 'SELL')):
                self.logger.info("Exit signal: BUY position, Stochastic overbought crossover")
                return True
            
            # Exit SELL position if Stochastic becomes oversold and crosses up
            if (position_type == 'SELL' and current_k < oversold and 
                self._check_stoch_crossover(data, 'BUY')):
                self.logger.info("Exit signal: SELL position, Stochastic oversold crossover")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking exit condition: {e}")
            return False
    
    def get_minimum_bars(self) -> int:
        """Get minimum bars required for Stochastic calculation."""
        return max(50, self.parameters['k_period'] * 2, self.parameters['atr_period'] * 2)
    
    def _check_stoch_crossover(self, data: pd.DataFrame, signal_type: str) -> bool:
        """Check for Stochastic %K and %D crossover."""
        try:
            if len(data) < 2:
                return False
            
            current_k = data['stoch_k'].iloc[-1]
            current_d = data['stoch_d'].iloc[-1]
            prev_k = data['stoch_k'].iloc[-2]
            prev_d = data['stoch_d'].iloc[-2]
            
            if signal_type == 'BUY':
                # %K crosses above %D
                return prev_k <= prev_d and current_k > current_d
            else:  # SELL
                # %K crosses below %D
                return prev_k >= prev_d and current_k < current_d
                
        except Exception as e:
            self.logger.error(f"Error checking Stochastic crossover: {e}")
            return False
    
    def _confirm_signal(self, data: pd.DataFrame, signal: str) -> bool:
        """Confirm signal with additional filters."""
        try:
            # Momentum confirmation
            if self.parameters['momentum_confirmation']:
                if not self._check_momentum_confirmation(data, signal):
                    self.logger.debug("Signal rejected: momentum not confirmed")
                    return False
            
            # RSI filter
            if self.parameters['rsi_filter']:
                if not self._check_rsi_filter(data, signal):
                    self.logger.debug("Signal rejected: RSI filter")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error confirming signal: {e}")
            return False
    
    def _check_momentum_confirmation(self, data: pd.DataFrame, signal: str) -> bool:
        """Check for price momentum confirmation."""
        try:
            if len(data) < 3:
                return True
            
            # Check last 3 candles for momentum
            recent_closes = data['close'].iloc[-3:]
            
            if signal == 'BUY':
                # For BUY, check for upward momentum
                return recent_closes.iloc[-1] > recent_closes.iloc[-3]
            else:  # SELL
                # For SELL, check for downward momentum
                return recent_closes.iloc[-1] < recent_closes.iloc[-3]
                
        except Exception as e:
            self.logger.error(f"Error checking momentum: {e}")
            return True
    
    def _check_rsi_filter(self, data: pd.DataFrame, signal: str) -> bool:
        """Check RSI filter for additional confirmation."""
        try:
            current_rsi = data['rsi'].iloc[-1]
            
            if signal == 'BUY':
                # For BUY, RSI should not be overbought
                return current_rsi < 70
            else:  # SELL
                # For SELL, RSI should not be oversold
                return current_rsi > 30
                
        except Exception as e:
            self.logger.error(f"Error checking RSI filter: {e}")
            return True
    
    def _find_recent_swing_low(self, data: pd.DataFrame, lookback: int = 7) -> Optional[float]:
        """Find recent swing low for stop loss calculation."""
        try:
            if len(data) < lookback + 2:
                return None
            
            recent_data = data.iloc[-lookback:]
            return recent_data['low'].min()
            
        except Exception as e:
            self.logger.error(f"Error finding swing low: {e}")
            return None
    
    def _find_recent_swing_high(self, data: pd.DataFrame, lookback: int = 7) -> Optional[float]:
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
        """Get Stochastic momentum strategy information."""
        info = super().get_strategy_info()
        info.update({
            'strategy_type': 'Oscillator',
            'timeframe_suitability': ['M5', 'M15', 'M30'],
            'market_condition': 'Ranging/Sideways',
            'risk_level': 'Medium',
            'description': 'Stochastic oscillator strategy for mean reversion in ranging markets'
        })
        return info
