import pandas as pd
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime

class BaseStrategy(ABC):
    """Base class for all trading strategies."""
    
    def __init__(self, name: str, parameters: Dict[str, Any] = None):
        self.name = name
        self.parameters = parameters or {}
        self.logger = logging.getLogger(f"{__name__}.{name}")
        self.last_signal = None
        self.last_signal_time = None
        self.signal_history = []
        
    @abstractmethod
    def get_signal(self, data: pd.DataFrame) -> Optional[str]:
        """
        Generate trading signal based on market data.
        
        Args:
            data (pd.DataFrame): Market data with OHLCV columns
            
        Returns:
            Optional[str]: 'BUY', 'SELL', or None
        """
        pass
    
    @abstractmethod
    def get_stop_loss(self, data: pd.DataFrame, signal: str, entry_price: float) -> Optional[float]:
        """
        Calculate stop loss price for a signal.
        
        Args:
            data (pd.DataFrame): Market data
            signal (str): Trading signal ('BUY' or 'SELL')
            entry_price (float): Entry price
            
        Returns:
            Optional[float]: Stop loss price
        """
        pass
    
    @abstractmethod
    def get_take_profit(self, data: pd.DataFrame, signal: str, entry_price: float) -> Optional[float]:
        """
        Calculate take profit price for a signal.
        
        Args:
            data (pd.DataFrame): Market data
            signal (str): Trading signal ('BUY' or 'SELL')
            entry_price (float): Entry price
            
        Returns:
            Optional[float]: Take profit price
        """
        pass
    
    def should_exit(self, data: pd.DataFrame, position: Dict[str, Any]) -> bool:
        """
        Check if an existing position should be closed.
        
        Args:
            data (pd.DataFrame): Current market data
            position (Dict[str, Any]): Position information
            
        Returns:
            bool: True if position should be closed
        """
        # Default implementation - override in specific strategies if needed
        return False
    
    def validate_signal(self, data: pd.DataFrame, signal: str) -> bool:
        """
        Validate a trading signal before execution.
        
        Args:
            data (pd.DataFrame): Market data
            signal (str): Trading signal
            
        Returns:
            bool: True if signal is valid
        """
        # Basic validation
        if signal not in ['BUY', 'SELL']:
            return False
        
        # Check for minimum data requirements
        if len(data) < self.get_minimum_bars():
            self.logger.warning(f"Insufficient data for {self.name} strategy")
            return False
        
        # Check for recent signal to avoid over-trading
        if self._is_signal_too_recent():
            self.logger.debug(f"Signal too recent for {self.name} strategy")
            return False
        
        return True
    
    def update_signal_history(self, signal: str) -> None:
        """Update signal history."""
        current_time = datetime.now()
        self.last_signal = signal
        self.last_signal_time = current_time
        
        # Keep only recent signals (last 100)
        self.signal_history.append({
            'signal': signal,
            'time': current_time
        })
        
        if len(self.signal_history) > 100:
            self.signal_history = self.signal_history[-100:]
    
    def get_minimum_bars(self) -> int:
        """
        Get minimum number of bars required for the strategy.
        
        Returns:
            int: Minimum bars required
        """
        # Default minimum - override in specific strategies
        return 50
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """
        Get strategy information and parameters.
        
        Returns:
            Dict[str, Any]: Strategy information
        """
        return {
            'name': self.name,
            'parameters': self.parameters,
            'minimum_bars': self.get_minimum_bars(),
            'last_signal': self.last_signal,
            'last_signal_time': self.last_signal_time,
            'total_signals': len(self.signal_history),
        }
    
    def _is_signal_too_recent(self, min_interval_minutes: int = 5) -> bool:
        """Check if the last signal was too recent."""
        if not self.last_signal_time:
            return False
        
        time_diff = datetime.now() - self.last_signal_time
        return time_diff.total_seconds() < (min_interval_minutes * 60)
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range (ATR).
        
        Args:
            data (pd.DataFrame): OHLC data
            period (int): ATR period
            
        Returns:
            pd.Series: ATR values
        """
        high_low = data['high'] - data['low']
        high_close = (data['high'] - data['close'].shift()).abs()
        low_close = (data['low'] - data['close'].shift()).abs()
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return true_range.rolling(window=period).mean()
    
    def _calculate_ema(self, data: pd.Series, period: int) -> pd.Series:
        """
        Calculate Exponential Moving Average.
        
        Args:
            data (pd.Series): Input data
            period (int): EMA period
            
        Returns:
            pd.Series: EMA values
        """
        return data.ewm(span=period, adjust=False).mean()
    
    def _calculate_sma(self, data: pd.Series, period: int) -> pd.Series:
        """
        Calculate Simple Moving Average.
        
        Args:
            data (pd.Series): Input data
            period (int): SMA period
            
        Returns:
            pd.Series: SMA values
        """
        return data.rolling(window=period).mean()
    
    def _calculate_rsi(self, data: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate Relative Strength Index.
        
        Args:
            data (pd.Series): Price data
            period (int): RSI period
            
        Returns:
            pd.Series: RSI values
        """
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_bollinger_bands(self, data: pd.Series, period: int = 20, 
                                  std_dev: float = 2.0) -> Dict[str, pd.Series]:
        """
        Calculate Bollinger Bands.
        
        Args:
            data (pd.Series): Price data
            period (int): Period for moving average
            std_dev (float): Standard deviation multiplier
            
        Returns:
            Dict[str, pd.Series]: Upper, middle, and lower bands
        """
        sma = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()
        
        return {
            'upper': sma + (std * std_dev),
            'middle': sma,
            'lower': sma - (std * std_dev)
        }
    
    def _calculate_macd(self, data: pd.Series, fast: int = 12, slow: int = 26, 
                       signal: int = 9) -> Dict[str, pd.Series]:
        """
        Calculate MACD indicator.
        
        Args:
            data (pd.Series): Price data
            fast (int): Fast EMA period
            slow (int): Slow EMA period
            signal (int): Signal line EMA period
            
        Returns:
            Dict[str, pd.Series]: MACD line, signal line, and histogram
        """
        ema_fast = self._calculate_ema(data, fast)
        ema_slow = self._calculate_ema(data, slow)
        
        macd_line = ema_fast - ema_slow
        signal_line = self._calculate_ema(macd_line, signal)
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    def _calculate_stochastic(self, data: pd.DataFrame, k_period: int = 14, 
                             d_period: int = 3, smooth_k: int = 3) -> Dict[str, pd.Series]:
        """
        Calculate Stochastic Oscillator.
        
        Args:
            data (pd.DataFrame): OHLC data
            k_period (int): %K period
            d_period (int): %D period
            smooth_k (int): %K smoothing period
            
        Returns:
            Dict[str, pd.Series]: %K and %D lines
        """
        lowest_low = data['low'].rolling(window=k_period).min()
        highest_high = data['high'].rolling(window=k_period).max()
        
        k_percent = ((data['close'] - lowest_low) / (highest_high - lowest_low)) * 100
        k_percent_smooth = k_percent.rolling(window=smooth_k).mean()
        d_percent = k_percent_smooth.rolling(window=d_period).mean()
        
        return {
            'k': k_percent_smooth,
            'd': d_percent
        }
