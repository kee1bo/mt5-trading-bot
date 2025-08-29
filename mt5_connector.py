import MetaTrader5 as mt5
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from config import MT5_SETTINGS, TRADING_SETTINGS

class MT5Connector:
    """Handles connection and basic interaction with MetaTrader 5."""
    
    def __init__(self):
        self.connected = False
        self.logger = logging.getLogger(__name__)
        
    def connect(self) -> bool:
        """
        Establish connection to MT5 terminal.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Initialize MT5 connection
            if not mt5.initialize(
                login=MT5_SETTINGS['login'],
                password=MT5_SETTINGS['password'],
                server=MT5_SETTINGS['server'],
                path=MT5_SETTINGS.get('path', None),
                timeout=MT5_SETTINGS['timeout']
            ):
                self.logger.error(f"Failed to initialize MT5: {mt5.last_error()}")
                return False
            
            # Verify connection
            account_info = mt5.account_info()
            if account_info is None:
                self.logger.error("Failed to get account info")
                return False
            
            self.connected = True
            self.logger.info(f"Successfully connected to MT5. Account: {account_info.login}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error connecting to MT5: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from MT5 terminal."""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            self.logger.info("Disconnected from MT5")
    
    def is_connected(self) -> bool:
        """Check if connected to MT5."""
        return self.connected and mt5.terminal_info() is not None
    
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """
        Get account information.
        
        Returns:
            Optional[Dict]: Account information or None if error
        """
        if not self.is_connected():
            self.logger.error("Not connected to MT5")
            return None
        
        try:
            account_info = mt5.account_info()
            if account_info is None:
                self.logger.error("Failed to get account info")
                return None
            
            return {
                'login': account_info.login,
                'balance': account_info.balance,
                'equity': account_info.equity,
                'margin': account_info.margin,
                'free_margin': account_info.margin_free,
                'margin_level': account_info.margin_level,
                'profit': account_info.profit,
                'currency': account_info.currency,
                'leverage': account_info.leverage,
                'server': account_info.server,
                'trade_allowed': account_info.trade_allowed,
            }
            
        except Exception as e:
            self.logger.error(f"Error getting account info: {e}")
            return None
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get symbol information.
        
        Args:
            symbol (str): Symbol name (e.g., 'EURUSD')
            
        Returns:
            Optional[Dict]: Symbol information or None if error
        """
        if not self.is_connected():
            self.logger.error("Not connected to MT5")
            return None
        
        try:
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                self.logger.error(f"Symbol {symbol} not found")
                return None
            
            return {
                'name': symbol_info.name,
                'bid': symbol_info.bid,
                'ask': symbol_info.ask,
                'spread': symbol_info.spread,
                'digits': symbol_info.digits,
                'point': symbol_info.point,
                'minimum_lot': symbol_info.volume_min,
                'maximum_lot': symbol_info.volume_max,
                'lot_step': symbol_info.volume_step,
                'contract_size': symbol_info.trade_contract_size,
                'trade_allowed': symbol_info.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL,
            }
            
        except Exception as e:
            self.logger.error(f"Error getting symbol info for {symbol}: {e}")
            return None
    
    def get_market_data(self, symbol: str, timeframe: str, count: int = 500) -> Optional[pd.DataFrame]:
        """
        Get historical market data.
        
        Args:
            symbol (str): Symbol name
            timeframe (str): Timeframe (M1, M5, M15, M30, H1, H4, D1)
            count (int): Number of bars to retrieve
            
        Returns:
            Optional[pd.DataFrame]: Market data or None if error
        """
        if not self.is_connected():
            self.logger.error("Not connected to MT5")
            return None
        
        # Map timeframe strings to MT5 constants
        timeframe_map = {
            'M1': mt5.TIMEFRAME_M1,
            'M5': mt5.TIMEFRAME_M5,
            'M15': mt5.TIMEFRAME_M15,
            'M30': mt5.TIMEFRAME_M30,
            'H1': mt5.TIMEFRAME_H1,
            'H4': mt5.TIMEFRAME_H4,
            'D1': mt5.TIMEFRAME_D1,
        }
        
        if timeframe not in timeframe_map:
            self.logger.error(f"Unsupported timeframe: {timeframe}")
            return None
        
        try:
            # Get rates
            rates = mt5.copy_rates_from_pos(symbol, timeframe_map[timeframe], 0, count)
            
            if rates is None or len(rates) == 0:
                self.logger.error(f"No data received for {symbol} {timeframe}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            
            # Rename columns to standard format
            df.rename(columns={
                'open': 'open',
                'high': 'high', 
                'low': 'low',
                'close': 'close',
                'tick_volume': 'volume'
            }, inplace=True)
            
            return df[['open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            self.logger.error(f"Error getting market data for {symbol}: {e}")
            return None
    
    def get_current_price(self, symbol: str) -> Optional[Dict[str, float]]:
        """
        Get current bid/ask prices for a symbol.
        
        Args:
            symbol (str): Symbol name
            
        Returns:
            Optional[Dict]: Current prices or None if error
        """
        if not self.is_connected():
            self.logger.error("Not connected to MT5")
            return None
        
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                self.logger.error(f"Failed to get tick for {symbol}")
                return None
            
            return {
                'bid': tick.bid,
                'ask': tick.ask,
                'spread': tick.ask - tick.bid,
                'time': datetime.fromtimestamp(tick.time)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting current price for {symbol}: {e}")
            return None
    
    def get_positions(self, symbol: str = None) -> Optional[list]:
        """
        Get open positions.
        
        Args:
            symbol (str, optional): Filter by symbol
            
        Returns:
            Optional[list]: List of positions or None if error
        """
        if not self.is_connected():
            self.logger.error("Not connected to MT5")
            return None
        
        try:
            if symbol:
                positions = mt5.positions_get(symbol=symbol)
            else:
                positions = mt5.positions_get()
            
            if positions is None:
                return []
            
            return [
                {
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': 'BUY' if pos.type == mt5.ORDER_TYPE_BUY else 'SELL',
                    'volume': pos.volume,
                    'price_open': pos.price_open,
                    'price_current': pos.price_current,
                    'profit': pos.profit,
                    'sl': pos.sl,
                    'tp': pos.tp,
                    'time': datetime.fromtimestamp(pos.time),
                    'comment': pos.comment,
                }
                for pos in positions
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting positions: {e}")
            return None
    
    def get_orders(self, symbol: str = None) -> Optional[list]:
        """
        Get pending orders.
        
        Args:
            symbol (str, optional): Filter by symbol
            
        Returns:
            Optional[list]: List of orders or None if error
        """
        if not self.is_connected():
            self.logger.error("Not connected to MT5")
            return None
        
        try:
            if symbol:
                orders = mt5.orders_get(symbol=symbol)
            else:
                orders = mt5.orders_get()
            
            if orders is None:
                return []
            
            return [
                {
                    'ticket': order.ticket,
                    'symbol': order.symbol,
                    'type': self._order_type_to_string(order.type),
                    'volume': order.volume_initial,
                    'price_open': order.price_open,
                    'sl': order.sl,
                    'tp': order.tp,
                    'time_setup': datetime.fromtimestamp(order.time_setup),
                    'comment': order.comment,
                }
                for order in orders
            ]
            
        except Exception as e:
            self.logger.error(f"Error getting orders: {e}")
            return None
    
    def _order_type_to_string(self, order_type: int) -> str:
        """Convert MT5 order type constant to string."""
        type_map = {
            mt5.ORDER_TYPE_BUY: 'BUY',
            mt5.ORDER_TYPE_SELL: 'SELL',
            mt5.ORDER_TYPE_BUY_LIMIT: 'BUY_LIMIT',
            mt5.ORDER_TYPE_SELL_LIMIT: 'SELL_LIMIT',
            mt5.ORDER_TYPE_BUY_STOP: 'BUY_STOP',
            mt5.ORDER_TYPE_SELL_STOP: 'SELL_STOP',
        }
        return type_map.get(order_type, 'UNKNOWN')
