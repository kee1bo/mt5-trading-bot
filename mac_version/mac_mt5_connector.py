"""
MT5 Connector for MacOS - Cross-Platform Trading Bot
Handles MetaTrader 5 connectivity on macOS systems using Wine or alternatives.
"""

import time
import logging
from typing import Dict, List, Optional, Any
import pandas as pd
from datetime import datetime, timedelta
import os
import sys
import subprocess

# Platform detection
import platform
IS_MAC = platform.system() == "Darwin"
IS_WINDOWS = platform.system() == "Windows"

if IS_MAC:
    print("🍎 macOS detected - Using Wine/alternative MT5 integration")
    # Try different import methods for Mac
    try:
        # Method 1: Direct import (if MT5 is installed via Wine)
        import MetaTrader5 as mt5
        print("✅ MetaTrader5 module imported directly")
    except ImportError:
        try:
            # Method 2: Wine-based import
            sys.path.append('/Applications/MetaTrader 5/Platforms')
            import MetaTrader5 as mt5
            print("✅ MetaTrader5 module imported via Wine path")
        except ImportError:
            print("⚠️  MetaTrader5 module not found - using simulation mode")
            mt5 = None
else:
    import MetaTrader5 as mt5

class MacMT5Connector:
    """
    Cross-platform MT5 connector with macOS support.
    Falls back to simulation mode if MT5 is not available.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.connected = False
        self.simulation_mode = False
        self.account_info = None
        
        # Mac-specific settings
        if IS_MAC:
            self.mt5_path = self.find_mt5_path_mac()
            self.wine_prefix = os.path.expanduser("~/.wine")
        
        # Simulation data for testing
        self.sim_balance = 10000.0
        self.sim_equity = 10000.0
        self.sim_positions = []
        self.sim_price = 2000.0  # XAUUSD starting price
    
    def find_mt5_path_mac(self) -> Optional[str]:
        """Find MT5 installation on macOS."""
        possible_paths = [
            "/Applications/MetaTrader 5/terminal64.exe",
            "/Applications/MetaTrader 5.app/Contents/Resources/terminal64.exe",
            f"{os.path.expanduser('~')}/Applications/MetaTrader 5/terminal64.exe",
            f"{self.wine_prefix}/drive_c/Program Files/MetaTrader 5/terminal64.exe",
            f"{self.wine_prefix}/drive_c/Program Files (x86)/MetaTrader 5/terminal64.exe"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                print(f"✅ Found MT5 at: {path}")
                return path
        
        print("⚠️  MT5 installation not found on macOS")
        return None
    
    def connect(self, 
                login: Optional[int] = None, 
                password: Optional[str] = None, 
                server: Optional[str] = None) -> bool:
        """
        Connect to MT5 terminal with cross-platform support.
        """
        try:
            if mt5 is None:
                print("🔄 MT5 module not available - entering simulation mode")
                return self.connect_simulation()
            
            if IS_MAC and self.mt5_path:
                # Initialize MT5 with Wine on macOS
                if not mt5.initialize(path=self.mt5_path):
                    print("⚠️  Failed to initialize MT5 via Wine - trying simulation mode")
                    return self.connect_simulation()
            else:
                # Standard Windows initialization
                if not mt5.initialize():
                    print("⚠️  Failed to initialize MT5 - trying simulation mode")
                    return self.connect_simulation()
            
            # Login if credentials provided
            if login and password and server:
                if not mt5.login(login, password, server):
                    print(f"⚠️  Login failed: {mt5.last_error()}")
                    return self.connect_simulation()
            
            # Verify connection
            account_info = mt5.account_info()
            if account_info is None:
                print("⚠️  No account info - trying simulation mode")
                return self.connect_simulation()
            
            self.account_info = account_info._asdict()
            self.connected = True
            
            print(f"✅ Connected to MT5 successfully")
            print(f"🏛️  Account: {self.account_info['login']}")
            print(f"💰 Balance: {self.account_info['balance']:.2f}")
            print(f"💼 Equity: {self.account_info['equity']:.2f}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            print(f"❌ Connection failed: {e}")
            return self.connect_simulation()
    
    def connect_simulation(self) -> bool:
        """
        Connect in simulation mode for testing without MT5.
        """
        print("🔄 Connecting in SIMULATION mode...")
        
        self.simulation_mode = True
        self.connected = True
        self.account_info = {
            'login': 999999999,
            'trade_mode': 0,
            'leverage': 100,
            'limit_orders': 200,
            'margin_so_mode': 0,
            'trade_allowed': True,
            'trade_expert': True,
            'margin_mode': 0,
            'currency_digits': 2,
            'fifo_close': False,
            'balance': self.sim_balance,
            'credit': 0.0,
            'profit': 0.0,
            'equity': self.sim_equity,
            'margin': 0.0,
            'margin_free': self.sim_equity,
            'margin_level': 0.0,
            'margin_so_call': 50.0,
            'margin_so_so': 30.0,
            'margin_initial': 0.0,
            'margin_maintenance': 0.0,
            'assets': 0.0,
            'liabilities': 0.0,
            'commission_blocked': 0.0,
            'name': 'Simulation Account',
            'server': 'Simulation-Server',
            'currency': 'USD',
            'company': 'Simulation Company'
        }
        
        print("✅ Simulation mode connected successfully")
        print(f"🔄 Account: {self.account_info['login']} (SIMULATION)")
        print(f"💰 Balance: {self.account_info['balance']:.2f}")
        
        return True
    
    def get_market_data(self, symbol: str, timeframe: str, count: int) -> Optional[pd.DataFrame]:
        """
        Get market data with cross-platform support.
        """
        try:
            if self.simulation_mode:
                return self.get_simulation_data(symbol, timeframe, count)
            
            # Convert timeframe string to MT5 constant
            tf_map = {
                'M1': mt5.TIMEFRAME_M1,
                'M5': mt5.TIMEFRAME_M5,
                'M15': mt5.TIMEFRAME_M15,
                'M30': mt5.TIMEFRAME_M30,
                'H1': mt5.TIMEFRAME_H1,
                'H4': mt5.TIMEFRAME_H4,
                'D1': mt5.TIMEFRAME_D1
            }
            
            mt5_timeframe = tf_map.get(timeframe, mt5.TIMEFRAME_M1)
            
            # Get rates
            rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, count)
            
            if rates is None or len(rates) == 0:
                self.logger.warning(f"No market data for {symbol}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error getting market data: {e}")
            return None
    
    def get_simulation_data(self, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
        """
        Generate realistic simulation data for testing.
        """
        try:
            # Generate realistic XAUUSD-like data
            dates = pd.date_range(end=datetime.now(), periods=count, freq='1min')
            
            # Simulate realistic price movement
            base_price = self.sim_price
            price_changes = np.random.normal(0, 0.5, count)  # Small random changes
            prices = base_price + np.cumsum(price_changes)
            
            # Update simulation price
            self.sim_price = prices[-1]
            
            # Create OHLC data
            df = pd.DataFrame({
                'time': dates,
                'open': prices + np.random.normal(0, 0.1, count),
                'high': prices + np.abs(np.random.normal(0.2, 0.1, count)),
                'low': prices - np.abs(np.random.normal(0.2, 0.1, count)),
                'close': prices,
                'tick_volume': np.random.randint(100, 1000, count),
                'spread': np.random.randint(1, 5, count),
                'real_volume': np.random.randint(0, 100, count)
            })
            
            # Ensure OHLC logic
            for i in range(len(df)):
                high = max(df.loc[i, 'open'], df.loc[i, 'close'])
                low = min(df.loc[i, 'open'], df.loc[i, 'close'])
                df.loc[i, 'high'] = max(df.loc[i, 'high'], high)
                df.loc[i, 'low'] = min(df.loc[i, 'low'], low)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error generating simulation data: {e}")
            return None
    
    def get_current_price(self, symbol: str) -> Optional[Dict[str, float]]:
        """
        Get current price with cross-platform support.
        """
        try:
            if self.simulation_mode:
                spread = 0.5
                return {
                    'ask': self.sim_price + spread/2,
                    'bid': self.sim_price - spread/2,
                    'last': self.sim_price,
                    'time': datetime.now()
                }
            
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return None
            
            return {
                'ask': tick.ask,
                'bid': tick.bid,
                'last': tick.last,
                'time': datetime.fromtimestamp(tick.time)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting current price: {e}")
            return None
    
    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """
        Get account information.
        """
        if not self.connected:
            return None
        
        return self.account_info
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get current positions with cross-platform support.
        """
        try:
            if self.simulation_mode:
                return self.sim_positions
            
            positions = mt5.positions_get()
            if positions is None:
                return []
            
            return [pos._asdict() for pos in positions]
            
        except Exception as e:
            self.logger.error(f"Error getting positions: {e}")
            return []
    
    def place_order(self, symbol: str, order_type: str, volume: float, 
                   price: float = None, sl: float = None, tp: float = None,
                   comment: str = "") -> Optional[Dict[str, Any]]:
        """
        Place order with cross-platform support.
        """
        try:
            if self.simulation_mode:
                return self.place_simulation_order(symbol, order_type, volume, price, sl, tp, comment)
            
            # Convert order type
            if order_type.upper() == 'BUY':
                action = mt5.TRADE_ACTION_DEAL
                type_filling = mt5.ORDER_FILLING_IOC
                order_type_mt5 = mt5.ORDER_TYPE_BUY
                price = price or mt5.symbol_info_tick(symbol).ask
            else:  # SELL
                action = mt5.TRADE_ACTION_DEAL
                type_filling = mt5.ORDER_FILLING_IOC
                order_type_mt5 = mt5.ORDER_TYPE_SELL
                price = price or mt5.symbol_info_tick(symbol).bid
            
            # Prepare request
            request = {
                "action": action,
                "symbol": symbol,
                "volume": volume,
                "type": order_type_mt5,
                "price": price,
                "type_filling": type_filling,
                "type_time": mt5.ORDER_TIME_GTC,
                "comment": comment
            }
            
            # Add stop loss and take profit if provided
            if sl:
                request["sl"] = sl
            if tp:
                request["tp"] = tp
            
            # Send order
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.error(f"Order failed: {result.retcode} - {result.comment}")
                return None
            
            return {
                'order': result.order,
                'deal': result.deal,
                'retcode': result.retcode,
                'comment': result.comment
            }
            
        except Exception as e:
            self.logger.error(f"Error placing order: {e}")
            return None
    
    def place_simulation_order(self, symbol: str, order_type: str, volume: float,
                             price: float = None, sl: float = None, tp: float = None,
                             comment: str = "") -> Dict[str, Any]:
        """
        Place simulated order for testing.
        """
        try:
            order_id = len(self.sim_positions) + 1
            current_price = price or self.sim_price
            
            # Create position
            position = {
                'ticket': order_id,
                'time': int(datetime.now().timestamp()),
                'type': 0 if order_type.upper() == 'BUY' else 1,
                'magic': 0,
                'identifier': order_id,
                'reason': 0,
                'volume': volume,
                'price_open': current_price,
                'sl': sl or 0.0,
                'tp': tp or 0.0,
                'price_current': current_price,
                'swap': 0.0,
                'profit': 0.0,
                'symbol': symbol,
                'comment': comment,
                'external_id': ''
            }
            
            self.sim_positions.append(position)
            
            print(f"📋 SIMULATION: {order_type} order placed")
            print(f"   Symbol: {symbol}, Volume: {volume}, Price: {current_price:.2f}")
            
            return {
                'order': order_id,
                'deal': order_id,
                'retcode': 10009,  # TRADE_RETCODE_DONE
                'comment': 'Simulation order executed'
            }
            
        except Exception as e:
            self.logger.error(f"Error in simulation order: {e}")
            return None
    
    def disconnect(self):
        """
        Disconnect from MT5.
        """
        try:
            if self.simulation_mode:
                print("🔄 Disconnecting from simulation mode")
            else:
                if mt5:
                    mt5.shutdown()
                print("✅ Disconnected from MT5")
            
            self.connected = False
            
        except Exception as e:
            self.logger.error(f"Error disconnecting: {e}")

# Import numpy for simulation data
try:
    import numpy as np
except ImportError:
    print("⚠️  NumPy not found - limited simulation functionality")
    np = None
