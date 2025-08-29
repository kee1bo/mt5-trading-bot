import pandas as pd
import numpy as np
from typing import Optional, Dict, Any
from .base_strategy import BaseStrategy

class BollingerScalpStrategy(BaseStrategy):
    """
    Bollinger Bands Squeeze Scalping Strategy.
    
    This strategy capitalizes on the transition from low volatility (squeeze) to high volatility (breakout):
    - Squeeze Detection: Bollinger Bands width narrows significantly
    - BUY Signal: Price breaks above upper Bollinger Band after squeeze
    - SELL Signal: Price breaks below lower Bollinger Band after squeeze
    
    Best for: Breakout trading after periods of consolidation
    """
    
    def __init__(self, parameters: Dict[str, Any] = None):
        default_params = {
            'bb_period': 20,
            'bb_std': 2.0,
            'squeeze_threshold': 50,  # Lookback period for squeeze detection
            'squeeze_percentile': 20,  # Percentile for squeeze detection (lower = tighter squeeze)
            'atr_period': 14,
            'volume_threshold': 1.5,  # Volume multiplier for breakout confirmation
            'stop_loss_atr_multiplier': 1.0,
            'take_profit_atr_multiplier': 2.5,
            'trend_filter': True,  # Use trend filter with longer MA
            'trend_ma_period': 50,
        }
        
        if parameters:
            default_params.update(parameters)
            
        super().__init__("Bollinger_Scalp", default_params)
    
    def get_signal(self, data: pd.DataFrame) -> Optional[str]:
        """Generate trading signal based on Bollinger Bands squeeze breakout."""
        if len(data) < self.get_minimum_bars():
            return None
        
        try:
            # Calculate Bollinger Bands
            bb_period = self.parameters['bb_period']
            bb_std = self.parameters['bb_std']
            bb_data = self._calculate_bollinger_bands(data['close'], bb_period, bb_std)
            
            data['bb_upper'] = bb_data['upper']
            data['bb_middle'] = bb_data['middle']
            data['bb_lower'] = bb_data['lower']
            
            # Calculate Bollinger Bands width for squeeze detection
            data['bb_width'] = data['bb_upper'] - data['bb_lower']
            data['bb_width_pct'] = (data['bb_width'] / data['bb_middle']) * 100
            
            # Calculate ATR
            atr_period = self.parameters['atr_period']
            data['atr'] = self._calculate_atr(data, atr_period)
            
            # Apply trend filter if enabled
            if self.parameters['trend_filter']:
                trend_ma_period = self.parameters['trend_ma_period']
                data['trend_ma'] = self._calculate_sma(data['close'], trend_ma_period)
            
            # Check for squeeze condition
            if not self._is_squeeze_detected(data):
                return None
            
            last_candle = data.iloc[-1]
            previous_candle = data.iloc[-2]
            
            # Check for breakout above upper band (BUY signal)
            if (previous_candle['close'] <= previous_candle['bb_upper'] and 
                last_candle['close'] > last_candle['bb_upper']):
                
                # Additional confirmations
                if self._confirm_breakout_signal(data, 'BUY'):
                    signal = 'BUY'
                    if self.validate_signal(data, signal):
                        self.logger.info(f"Bollinger Bands breakout BUY signal at {last_candle['close']}")
                        return signal
            
            # Check for breakout below lower band (SELL signal)
            elif (previous_candle['close'] >= previous_candle['bb_lower'] and 
                  last_candle['close'] < last_candle['bb_lower']):
                
                # Additional confirmations
                if self._confirm_breakout_signal(data, 'SELL'):
                    signal = 'SELL'
                    if self.validate_signal(data, signal):
                        self.logger.info(f"Bollinger Bands breakout SELL signal at {last_candle['close']}")
                        return signal
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error in Bollinger Bands signal generation: {e}")
            return None
    
    def get_stop_loss(self, data: pd.DataFrame, signal: str, entry_price: float) -> Optional[float]:
        """Calculate stop loss based on Bollinger Bands and ATR."""
        try:
            # Calculate Bollinger Bands and ATR
            bb_period = self.parameters['bb_period']
            bb_std = self.parameters['bb_std']
            bb_data = self._calculate_bollinger_bands(data['close'], bb_period, bb_std)
            
            atr_period = self.parameters['atr_period']
            atr_multiplier = self.parameters['stop_loss_atr_multiplier']
            data['atr'] = self._calculate_atr(data, atr_period)
            
            current_atr = data['atr'].iloc[-1]
            bb_middle = bb_data['middle'].iloc[-1]
            
            if pd.isna(current_atr) or current_atr == 0:
                return self._get_percentage_stop_loss(entry_price, signal, 0.002)  # 0.2%
            
            if signal == 'BUY':
                # For BUY, place SL below middle BB or use ATR-based SL, whichever is closer
                bb_based_sl = bb_middle - (current_atr * 0.5)
                atr_based_sl = entry_price - (current_atr * atr_multiplier)
                stop_loss = max(bb_based_sl, atr_based_sl)
            else:  # SELL
                # For SELL, place SL above middle BB or use ATR-based SL, whichever is closer
                bb_based_sl = bb_middle + (current_atr * 0.5)
                atr_based_sl = entry_price + (current_atr * atr_multiplier)
                stop_loss = min(bb_based_sl, atr_based_sl)
            
            return round(stop_loss, 5)
            
        except Exception as e:
            self.logger.error(f"Error calculating stop loss: {e}")
            return self._get_percentage_stop_loss(entry_price, signal, 0.002)
    
    def get_take_profit(self, data: pd.DataFrame, signal: str, entry_price: float) -> Optional[float]:
        """Calculate take profit based on ATR and Bollinger Bands expansion."""
        try:
            # Calculate ATR
            atr_period = self.parameters['atr_period']
            atr_multiplier = self.parameters['take_profit_atr_multiplier']
            data['atr'] = self._calculate_atr(data, atr_period)
            
            current_atr = data['atr'].iloc[-1]
            
            if pd.isna(current_atr) or current_atr == 0:
                return self._get_percentage_take_profit(entry_price, signal, 0.004)  # 0.4%
            
            # More aggressive TP for breakout strategy
            if signal == 'BUY':
                take_profit = entry_price + (current_atr * atr_multiplier)
            else:  # SELL
                take_profit = entry_price - (current_atr * atr_multiplier)
            
            return round(take_profit, 5)
            
        except Exception as e:
            self.logger.error(f"Error calculating take profit: {e}")
            return self._get_percentage_take_profit(entry_price, signal, 0.004)
    
    def should_exit(self, data: pd.DataFrame, position: Dict[str, Any]) -> bool:
        """Check if position should be closed based on Bollinger Bands mean reversion."""
        try:
            if len(data) < self.get_minimum_bars():
                return False
            
            # Calculate Bollinger Bands
            bb_period = self.parameters['bb_period']
            bb_std = self.parameters['bb_std']
            bb_data = self._calculate_bollinger_bands(data['close'], bb_period, bb_std)
            
            current_price = data['close'].iloc[-1]
            bb_middle = bb_data['middle'].iloc[-1]
            position_type = position.get('type', '')
            
            # Exit BUY position if price moves back toward middle band
            if position_type == 'BUY' and current_price <= bb_middle:
                self.logger.info("Exit signal: BUY position, price back to BB middle")
                return True
            
            # Exit SELL position if price moves back toward middle band
            if position_type == 'SELL' and current_price >= bb_middle:
                self.logger.info("Exit signal: SELL position, price back to BB middle")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking exit condition: {e}")
            return False
    
    def get_minimum_bars(self) -> int:
        """Get minimum bars required for Bollinger Bands squeeze analysis."""
        return max(100, self.parameters['bb_period'] * 2, self.parameters['squeeze_threshold'])
    
    def _is_squeeze_detected(self, data: pd.DataFrame) -> bool:
        """Detect if Bollinger Bands are in a squeeze (low volatility)."""
        try:
            squeeze_threshold = self.parameters['squeeze_threshold']
            squeeze_percentile = self.parameters['squeeze_percentile']
            
            if len(data) < squeeze_threshold:
                return False
            
            # Get current and historical BB width
            current_width = data['bb_width_pct'].iloc[-1]
            historical_widths = data['bb_width_pct'].iloc[-squeeze_threshold:-1]
            
            # Check if current width is in the lower percentile of historical widths
            width_percentile = np.percentile(historical_widths, squeeze_percentile)
            
            is_squeeze = current_width <= width_percentile
            
            if is_squeeze:
                self.logger.debug(f"Squeeze detected: Current width {current_width:.4f} <= "
                                f"Percentile {squeeze_percentile} ({width_percentile:.4f})")
            
            return is_squeeze
            
        except Exception as e:
            self.logger.error(f"Error detecting squeeze: {e}")
            return False
    
    def _confirm_breakout_signal(self, data: pd.DataFrame, signal: str) -> bool:
        """Confirm breakout signal with additional filters."""
        try:
            last_candle = data.iloc[-1]
            
            # Volume confirmation
            if not self._check_volume_breakout(data):
                self.logger.debug("Breakout signal rejected: insufficient volume")
                return False
            
            # Trend filter confirmation
            if self.parameters['trend_filter']:
                if not self._check_trend_alignment(data, signal):
                    self.logger.debug("Breakout signal rejected: trend not aligned")
                    return False
            
            # Candle strength confirmation
            if not self._check_candle_strength(last_candle, signal):
                self.logger.debug("Breakout signal rejected: weak candle")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error confirming breakout signal: {e}")
            return False
    
    def _check_volume_breakout(self, data: pd.DataFrame) -> bool:
        """Check for volume confirmation of breakout."""
        try:
            if 'volume' not in data.columns:
                return True  # Skip volume check if no volume data
            
            volume_threshold = self.parameters['volume_threshold']
            current_volume = data['volume'].iloc[-1]
            avg_volume = data['volume'].rolling(window=20).mean().iloc[-1]
            
            return current_volume >= (avg_volume * volume_threshold)
            
        except Exception as e:
            self.logger.error(f"Error checking volume breakout: {e}")
            return True
    
    def _check_trend_alignment(self, data: pd.DataFrame, signal: str) -> bool:
        """Check if breakout aligns with longer-term trend."""
        try:
            current_price = data['close'].iloc[-1]
            trend_ma = data['trend_ma'].iloc[-1]
            
            if signal == 'BUY':
                return current_price > trend_ma  # BUY only if above trend MA
            else:  # SELL
                return current_price < trend_ma  # SELL only if below trend MA
                
        except Exception as e:
            self.logger.error(f"Error checking trend alignment: {e}")
            return True
    
    def _check_candle_strength(self, candle: pd.Series, signal: str) -> bool:
        """Check if the breakout candle shows strength."""
        try:
            candle_range = candle['high'] - candle['low']
            candle_body = abs(candle['close'] - candle['open'])
            
            # Require candle body to be at least 50% of the range
            body_ratio = candle_body / candle_range if candle_range > 0 else 0
            
            if body_ratio < 0.5:
                return False
            
            # Check candle direction matches signal
            if signal == 'BUY':
                return candle['close'] > candle['open']  # Bullish candle
            else:  # SELL
                return candle['close'] < candle['open']  # Bearish candle
                
        except Exception as e:
            self.logger.error(f"Error checking candle strength: {e}")
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
        """Get Bollinger Bands squeeze strategy information."""
        info = super().get_strategy_info()
        info.update({
            'strategy_type': 'Breakout',
            'timeframe_suitability': ['M1', 'M5', 'M15'],
            'market_condition': 'Low to High Volatility Transition',
            'risk_level': 'Medium-High',
            'description': 'Bollinger Bands squeeze breakout strategy for volatility expansion'
        })
        return info
