import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
from .base_strategy import BaseStrategy

class RSIDivergenceStrategy(BaseStrategy):
    """
    RSI Divergence Strategy for Scalping.
    
    This strategy looks for divergence between price and RSI to anticipate reversals:
    - BUY Signal (Bullish Divergence): Price makes lower low, RSI makes higher low
    - SELL Signal (Bearish Divergence): Price makes higher high, RSI makes lower high
    
    Best for: Catching short-term reversals in ranging or trending markets
    """
    
    def __init__(self, parameters: Dict[str, Any] = None):
        default_params = {
            'rsi_period': 14,
            'lookback_candles': 10,
            'rsi_overbought': 70,
            'rsi_oversold': 30,
            'min_divergence_strength': 5,  # Minimum RSI difference for divergence
            'atr_period': 14,
            'stop_loss_atr_multiplier': 1.0,
            'take_profit_atr_multiplier': 2.0,
            'volume_confirmation': True,  # Require volume confirmation
        }
        
        if parameters:
            default_params.update(parameters)
            
        super().__init__("RSI_Divergence", default_params)
    
    def get_signal(self, data: pd.DataFrame) -> Optional[str]:
        """Generate trading signal based on RSI divergence."""
        if len(data) < self.get_minimum_bars():
            return None
        
        try:
            # Calculate RSI
            rsi_period = self.parameters['rsi_period']
            data['rsi'] = self._calculate_rsi(data['close'], rsi_period)
            
            # Calculate ATR for position sizing
            atr_period = self.parameters['atr_period']
            data['atr'] = self._calculate_atr(data, atr_period)
            
            lookback_period = self.parameters['lookback_candles']
            
            # Check for bullish divergence (BUY signal)
            bullish_div = self._check_bullish_divergence(data, lookback_period)
            if bullish_div:
                signal = 'BUY'
                if self.validate_signal(data, signal):
                    self.logger.info(f"RSI Bullish Divergence signal generated")
                    return signal
            
            # Check for bearish divergence (SELL signal)
            bearish_div = self._check_bearish_divergence(data, lookback_period)
            if bearish_div:
                signal = 'SELL'
                if self.validate_signal(data, signal):
                    self.logger.info(f"RSI Bearish Divergence signal generated")
                    return signal
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error in RSI divergence signal generation: {e}")
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
            
            # For divergence strategy, use tighter stops
            if signal == 'BUY':
                # Find recent low for BUY signal
                recent_low = self._find_recent_swing_low(data)
                if recent_low:
                    swing_based_sl = recent_low - (current_atr * 0.5)
                    atr_based_sl = entry_price - (current_atr * atr_multiplier)
                    stop_loss = max(swing_based_sl, atr_based_sl)  # Use the higher (less risk)
                else:
                    stop_loss = entry_price - (current_atr * atr_multiplier)
            else:  # SELL
                # Find recent high for SELL signal
                recent_high = self._find_recent_swing_high(data)
                if recent_high:
                    swing_based_sl = recent_high + (current_atr * 0.5)
                    atr_based_sl = entry_price + (current_atr * atr_multiplier)
                    stop_loss = min(swing_based_sl, atr_based_sl)  # Use the lower (less risk)
                else:
                    stop_loss = entry_price + (current_atr * atr_multiplier)
            
            return round(stop_loss, 5)
            
        except Exception as e:
            self.logger.error(f"Error calculating stop loss: {e}")
            return self._get_percentage_stop_loss(entry_price, signal, 0.0015)
    
    def get_take_profit(self, data: pd.DataFrame, signal: str, entry_price: float) -> Optional[float]:
        """Calculate take profit based on RSI levels and ATR."""
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
        """Check if position should be closed based on RSI reversal."""
        try:
            if len(data) < self.get_minimum_bars():
                return False
            
            # Calculate RSI
            rsi_period = self.parameters['rsi_period']
            data['rsi'] = self._calculate_rsi(data['close'], rsi_period)
            
            current_rsi = data['rsi'].iloc[-1]
            position_type = position.get('type', '')
            
            overbought = self.parameters['rsi_overbought']
            oversold = self.parameters['rsi_oversold']
            
            # Exit BUY position if RSI becomes overbought
            if position_type == 'BUY' and current_rsi >= overbought:
                self.logger.info("Exit signal: BUY position, RSI overbought")
                return True
            
            # Exit SELL position if RSI becomes oversold
            if position_type == 'SELL' and current_rsi <= oversold:
                self.logger.info("Exit signal: SELL position, RSI oversold")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking exit condition: {e}")
            return False
    
    def get_minimum_bars(self) -> int:
        """Get minimum bars required for RSI divergence analysis."""
        return max(100, self.parameters['rsi_period'] * 3, self.parameters['lookback_candles'] * 2)
    
    def _check_bullish_divergence(self, data: pd.DataFrame, lookback_period: int) -> bool:
        """Check for bullish divergence pattern."""
        try:
            if len(data) < lookback_period + 5:
                return False
            
            # Get recent data
            recent_data = data.iloc[-(lookback_period + 1):]
            
            # Find the lowest price in lookback period
            current_low_idx = recent_data['low'].idxmin()
            current_low_price = recent_data.loc[current_low_idx, 'low']
            current_low_rsi = recent_data.loc[current_low_idx, 'rsi']
            
            # Look for a previous low before the current one
            data_before_current = recent_data.loc[:current_low_idx].iloc[:-1]
            if len(data_before_current) < 3:
                return False
            
            prev_low_idx = data_before_current['low'].idxmin()
            prev_low_price = data_before_current.loc[prev_low_idx, 'low']
            prev_low_rsi = data_before_current.loc[prev_low_idx, 'rsi']
            
            # Check for bullish divergence
            price_makes_lower_low = current_low_price < prev_low_price
            rsi_makes_higher_low = current_low_rsi > prev_low_rsi
            
            min_divergence = self.parameters['min_divergence_strength']
            rsi_divergence_strength = current_low_rsi - prev_low_rsi
            
            # Confirm divergence conditions
            divergence_exists = (price_makes_lower_low and rsi_makes_higher_low and 
                               rsi_divergence_strength >= min_divergence)
            
            # Additional filter: RSI should be in oversold area
            rsi_oversold_condition = current_low_rsi < self.parameters['rsi_oversold'] + 10
            
            # Volume confirmation if enabled
            volume_confirmed = True
            if self.parameters['volume_confirmation']:
                volume_confirmed = self._check_volume_confirmation(recent_data, 'BUY')
            
            return divergence_exists and rsi_oversold_condition and volume_confirmed
            
        except Exception as e:
            self.logger.error(f"Error checking bullish divergence: {e}")
            return False
    
    def _check_bearish_divergence(self, data: pd.DataFrame, lookback_period: int) -> bool:
        """Check for bearish divergence pattern."""
        try:
            if len(data) < lookback_period + 5:
                return False
            
            # Get recent data
            recent_data = data.iloc[-(lookback_period + 1):]
            
            # Find the highest price in lookback period
            current_high_idx = recent_data['high'].idxmax()
            current_high_price = recent_data.loc[current_high_idx, 'high']
            current_high_rsi = recent_data.loc[current_high_idx, 'rsi']
            
            # Look for a previous high before the current one
            data_before_current = recent_data.loc[:current_high_idx].iloc[:-1]
            if len(data_before_current) < 3:
                return False
            
            prev_high_idx = data_before_current['high'].idxmax()
            prev_high_price = data_before_current.loc[prev_high_idx, 'high']
            prev_high_rsi = data_before_current.loc[prev_high_idx, 'rsi']
            
            # Check for bearish divergence
            price_makes_higher_high = current_high_price > prev_high_price
            rsi_makes_lower_high = current_high_rsi < prev_high_rsi
            
            min_divergence = self.parameters['min_divergence_strength']
            rsi_divergence_strength = prev_high_rsi - current_high_rsi
            
            # Confirm divergence conditions
            divergence_exists = (price_makes_higher_high and rsi_makes_lower_high and 
                               rsi_divergence_strength >= min_divergence)
            
            # Additional filter: RSI should be in overbought area
            rsi_overbought_condition = current_high_rsi > self.parameters['rsi_overbought'] - 10
            
            # Volume confirmation if enabled
            volume_confirmed = True
            if self.parameters['volume_confirmation']:
                volume_confirmed = self._check_volume_confirmation(recent_data, 'SELL')
            
            return divergence_exists and rsi_overbought_condition and volume_confirmed
            
        except Exception as e:
            self.logger.error(f"Error checking bearish divergence: {e}")
            return False
    
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
    
    def _check_volume_confirmation(self, data: pd.DataFrame, signal: str) -> bool:
        """Check for volume confirmation of the signal."""
        try:
            if 'volume' not in data.columns:
                return True  # Skip volume check if no volume data
            
            # Compare recent volume to average volume
            avg_volume = data['volume'].rolling(window=10).mean().iloc[-1]
            recent_volume = data['volume'].iloc[-1]
            
            # Require above average volume for confirmation
            return recent_volume > avg_volume * 1.2
            
        except Exception as e:
            self.logger.error(f"Error checking volume confirmation: {e}")
            return True
    
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
        """Get RSI divergence strategy information."""
        info = super().get_strategy_info()
        info.update({
            'strategy_type': 'Mean Reversion',
            'timeframe_suitability': ['M5', 'M15', 'M30'],
            'market_condition': 'Ranging/Reversal',
            'risk_level': 'Medium',
            'description': 'RSI divergence strategy for catching short-term reversals'
        })
        return info
