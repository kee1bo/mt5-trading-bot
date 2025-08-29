#!/usr/bin/env python3
"""
Cross-Platform Multi-Strategy Trading Bot for macOS
Includes simulation mode for testing and development.
"""

import time
import logging
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional
import signal
import sys
import json
import os
import platform

# Cross-platform imports
from mac_mt5_connector import MacMT5Connector

# Import compatible modules
try:
    import pandas as pd
    import numpy as np
except ImportError as e:
    print(f"⚠️  Missing dependency: {e}")
    print("💡 Install with: pip install pandas numpy")
    sys.exit(1)

class MacCompatibleTradeManager:
    """
    Cross-platform trade manager with macOS support.
    """
    
    def __init__(self, mt5_connector):
        self.mt5_connector = mt5_connector
        self.logger = logging.getLogger(__name__)
    
    def place_market_order(self, symbol: str, order_type: str, volume: float,
                          stop_loss: float = None, take_profit: float = None,
                          comment: str = "") -> Optional[Dict[str, Any]]:
        """
        Place market order with cross-platform support.
        """
        try:
            return self.mt5_connector.place_order(
                symbol=symbol,
                order_type=order_type,
                volume=volume,
                sl=stop_loss,
                tp=take_profit,
                comment=comment
            )
        except Exception as e:
            self.logger.error(f"Error placing market order: {e}")
            return None

class MacCompatibleRiskManager:
    """
    Cross-platform risk manager.
    """
    
    def __init__(self, mt5_connector, trade_manager):
        self.mt5_connector = mt5_connector
        self.trade_manager = trade_manager
        self.logger = logging.getLogger(__name__)
    
    def check_trading_allowed(self, strategy_name: str = None, 
                            max_strategy_positions: int = 5) -> bool:
        """
        Check if trading is allowed based on risk parameters.
        """
        try:
            # Get account info
            account_info = self.mt5_connector.get_account_info()
            if not account_info:
                return False
            
            # Check if trading is allowed
            if not account_info.get('trade_allowed', False):
                self.logger.warning("Trading not allowed on account")
                return False
            
            # Check position limits
            positions = self.mt5_connector.get_positions()
            total_positions = len(positions) if positions else 0
            
            if total_positions >= 20:  # Global limit
                return False
            
            # Strategy-specific limits
            if strategy_name and max_strategy_positions:
                strategy_positions = [
                    pos for pos in positions 
                    if pos.get('comment', '').startswith(strategy_name)
                ]
                if len(strategy_positions) >= max_strategy_positions:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error in risk check: {e}")
            return False

class MacCompatibleStrategy:
    """
    Base strategy class for macOS compatibility.
    """
    
    def __init__(self, name: str, params: Dict[str, Any]):
        self.name = name
        self.params = params
        self.logger = logging.getLogger(__name__)
        self.last_signal_time = None
        self.signal_cooldown = params.get('signal_cooldown', 10)  # seconds
    
    def _is_signal_too_recent(self) -> bool:
        """Check if last signal was too recent."""
        if self.last_signal_time is None:
            return False
        
        current_time = datetime.now()
        
        # Handle different time formats
        if isinstance(self.last_signal_time, datetime):
            time_diff = (current_time - self.last_signal_time).total_seconds()
        else:
            # Assume timestamp
            time_diff = current_time.timestamp() - float(self.last_signal_time)
        
        return time_diff < self.signal_cooldown
    
    def _record_signal(self):
        """Record when signal was generated."""
        self.last_signal_time = datetime.now()
    
    def get_signal(self, data: pd.DataFrame) -> Optional[str]:
        """Override in subclasses."""
        return None
    
    def get_stop_loss(self, data: pd.DataFrame, signal: str, entry_price: float) -> float:
        """Override in subclasses."""
        stop_pct = 0.001  # 0.1%
        if signal == 'BUY':
            return entry_price * (1 - stop_pct)
        else:
            return entry_price * (1 + stop_pct)
    
    def get_take_profit(self, data: pd.DataFrame, signal: str, entry_price: float) -> float:
        """Override in subclasses."""
        target_pct = 0.002  # 0.2%
        if signal == 'BUY':
            return entry_price * (1 + target_pct)
        else:
            return entry_price * (1 - target_pct)

class SimpleEMAStrategy(MacCompatibleStrategy):
    """
    Simple EMA crossover strategy for macOS testing.
    """
    
    def __init__(self, params: Dict[str, Any]):
        super().__init__("Simple_EMA", params)
        self.fast_period = params.get('fast_period', 5)
        self.slow_period = params.get('slow_period', 10)
    
    def get_signal(self, data: pd.DataFrame) -> Optional[str]:
        """Generate EMA crossover signals."""
        try:
            if len(data) < self.slow_period + 5:
                return None
            
            if self._is_signal_too_recent():
                return None
            
            close = data['close']
            
            # Calculate EMAs
            ema_fast = close.ewm(span=self.fast_period).mean()
            ema_slow = close.ewm(span=self.slow_period).mean()
            
            # Current and previous values
            fast_current = ema_fast.iloc[-1]
            fast_prev = ema_fast.iloc[-2]
            slow_current = ema_slow.iloc[-1]
            slow_prev = ema_slow.iloc[-2]
            
            # Crossover detection
            bullish_cross = fast_prev <= slow_prev and fast_current > slow_current
            bearish_cross = fast_prev >= slow_prev and fast_current < slow_current
            
            if bullish_cross:
                self._record_signal()
                return 'BUY'
            elif bearish_cross:
                self._record_signal()
                return 'SELL'
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error in {self.name} get_signal: {e}")
            return None

class MacMultiStrategyBot:
    """
    Cross-platform multi-strategy trading bot for macOS.
    """
    
    def __init__(self):
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Platform detection
        self.platform = platform.system()
        print(f"🖥️  Platform detected: {self.platform}")
        
        # Core components
        self.mt5_connector = MacMT5Connector()
        self.trade_manager = MacCompatibleTradeManager(self.mt5_connector)
        self.risk_manager = MacCompatibleRiskManager(self.mt5_connector, self.trade_manager)
        
        # Strategies
        self.strategies = self.initialize_strategies()
        self.running = False
        
        # Statistics
        self.stats = {
            'start_time': None,
            'total_loops': 0,
            'signals': 0,
            'trades': 0,
            'successful_trades': 0,
            'failed_trades': 0
        }
        
        # Signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def setup_logging(self):
        """Setup cross-platform logging."""
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler('logs/mac_multi_strategy.log'),
                logging.StreamHandler()
            ]
        )
    
    def initialize_strategies(self) -> Dict[str, Any]:
        """Initialize cross-platform strategies."""
        strategies = {}
        
        # Simple EMA strategy for testing
        strategies['simple_ema'] = {
            'instance': SimpleEMAStrategy({
                'fast_period': 5,
                'slow_period': 15,
                'signal_cooldown': 10
            }),
            'enabled': True,
            'max_positions': 3,
            'risk_per_trade': 0.3,
            'priority': 1
        }
        
        return strategies
    
    def start(self):
        """Start the cross-platform trading bot."""
        print("🚀 Starting Cross-Platform Multi-Strategy Trading Bot")
        print("=" * 60)
        print(f"🖥️  Platform: {self.platform}")
        
        # Connect to MT5 (or simulation)
        if not self.mt5_connector.connect():
            print("❌ Failed to connect to MT5")
            return False
        
        # Display connection info
        account_info = self.mt5_connector.get_account_info()
        if account_info:
            if self.mt5_connector.simulation_mode:
                print("🔄 Running in SIMULATION mode")
            print(f"🏛️  Account: {account_info['login']}")
            print(f"💰 Balance: {account_info['balance']:.2f}")
        
        print("✅ Cross-platform bot initialized successfully")
        print(f"📊 Active Strategies: {len([s for s in self.strategies.values() if s['enabled']])}")
        print("=" * 60)
        
        self.running = True
        self.stats['start_time'] = datetime.now()
        
        return self.run_main_loop()
    
    def run_main_loop(self):
        """Main trading loop."""
        print("🔄 Starting main trading loop...")
        
        symbol = 'XAUUSD'
        timeframe = 'M1'
        lookback_periods = 50
        
        last_status_time = time.time()
        
        try:
            while self.running:
                loop_start = time.time()
                
                # Get market data
                data = self.mt5_connector.get_market_data(symbol, timeframe, lookback_periods)
                if data is None or len(data) < 30:
                    time.sleep(0.5)
                    continue
                
                # Process strategies
                for strategy_name, config in self.strategies.items():
                    if not config['enabled']:
                        continue
                    
                    try:
                        # Check position limits
                        current_positions = self.get_strategy_positions(strategy_name)
                        if len(current_positions) >= config['max_positions']:
                            continue
                        
                        # Get signal
                        strategy = config['instance']
                        signal = strategy.get_signal(data)
                        
                        if signal:
                            self.stats['signals'] += 1
                            print(f"🚦 {strategy.name}: {signal} signal at {data['close'].iloc[-1]:.2f}")
                            
                            # Execute trade
                            if self.execute_trade(strategy_name, signal, data, symbol):
                                self.stats['trades'] += 1
                                self.stats['successful_trades'] += 1
                                print(f"✅ {strategy.name}: Trade executed successfully")
                            else:
                                self.stats['failed_trades'] += 1
                                print(f"❌ {strategy.name}: Trade execution failed")
                    
                    except Exception as e:
                        self.logger.error(f"Error in strategy {strategy_name}: {e}")
                
                self.stats['total_loops'] += 1
                
                # Status update every 120 seconds
                if time.time() - last_status_time >= 120:
                    self.print_status()
                    last_status_time = time.time()
                
                # Sleep
                loop_time = time.time() - loop_start
                time.sleep(max(0.1, 1.0 - loop_time))
                
        except KeyboardInterrupt:
            print("\n🛑 Shutdown requested...")
        except Exception as e:
            print(f"❌ Main loop error: {e}")
            self.logger.error(f"Main loop error: {e}")
        finally:
            self.stop()
    
    def execute_trade(self, strategy_name: str, signal: str, data: pd.DataFrame, symbol: str) -> bool:
        """Execute trade with cross-platform support."""
        try:
            config = self.strategies[strategy_name]
            strategy = config['instance']
            
            # Risk check
            if not self.risk_manager.check_trading_allowed(strategy_name, config['max_positions']):
                return False
            
            # Get current price
            price_info = self.mt5_connector.get_current_price(symbol)
            if not price_info:
                return False
            
            entry_price = price_info['ask'] if signal == 'BUY' else price_info['bid']
            
            # Calculate stops
            stop_loss = strategy.get_stop_loss(data, signal, entry_price)
            take_profit = strategy.get_take_profit(data, signal, entry_price)
            
            # Volume
            volume = 0.01
            
            # Execute trade
            result = self.trade_manager.place_market_order(
                symbol=symbol,
                order_type=signal,
                volume=volume,
                stop_loss=stop_loss,
                take_profit=take_profit,
                comment=f"{strategy_name}_{signal}_mac"
            )
            
            return result is not None
            
        except Exception as e:
            self.logger.error(f"Error executing trade for {strategy_name}: {e}")
            return False
    
    def get_strategy_positions(self, strategy_name: str) -> List:
        """Get positions for a specific strategy."""
        try:
            all_positions = self.mt5_connector.get_positions()
            if not all_positions:
                return []
            
            strategy_positions = [
                pos for pos in all_positions 
                if pos.get('comment', '').startswith(strategy_name)
            ]
            
            return strategy_positions
            
        except Exception as e:
            self.logger.error(f"Error getting {strategy_name} positions: {e}")
            return []
    
    def print_status(self):
        """Print status information."""
        runtime = datetime.now() - self.stats['start_time']
        
        print(f"\n📊 STATUS | Runtime: {runtime}")
        print(f"🔄 Loops: {self.stats['total_loops']}")
        print(f"🎯 Signals: {self.stats['signals']}")
        print(f"💰 Trades: {self.stats['trades']}")
        
        # Efficiency
        efficiency = (self.stats['trades'] / max(1, self.stats['signals']) * 100)
        print(f"📈 Efficiency: {efficiency:.1f}%")
        
        # Account info
        account_info = self.mt5_connector.get_account_info()
        if account_info:
            print(f"💼 Balance: {account_info['balance']:.2f} | Equity: {account_info['equity']:.2f}")
        
        if self.mt5_connector.simulation_mode:
            print("🔄 (SIMULATION MODE)")
    
    def stop(self):
        """Stop the bot."""
        print("\n🛑 Stopping Cross-Platform Multi-Strategy Bot...")
        self.running = False
        
        # Final statistics
        if self.stats['start_time']:
            runtime = datetime.now() - self.stats['start_time']
            print(f"\n📈 FINAL STATISTICS:")
            print(f"⏰ Total Runtime: {runtime}")
            print(f"🔄 Total Loops: {self.stats['total_loops']}")
            print(f"🎯 Total Signals: {self.stats['signals']}")
            print(f"💰 Total Trades: {self.stats['trades']}")
            print(f"✅ Successful: {self.stats['successful_trades']}")
            print(f"❌ Failed: {self.stats['failed_trades']}")
            
            efficiency = (self.stats['trades'] / max(1, self.stats['signals']) * 100)
            print(f"📊 Final Efficiency: {efficiency:.1f}%")
        
        # Disconnect
        self.mt5_connector.disconnect()
        print("✅ Cross-platform bot stopped successfully")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\n🚨 Received signal {signum}, shutting down...")
        self.running = False

def main():
    """Main entry point."""
    print("🚀 CROSS-PLATFORM MULTI-STRATEGY TRADING BOT")
    print("=" * 60)
    print("🍎 macOS Compatible | 🪟 Windows Compatible")
    print("🔄 Simulation Mode Available")
    print("=" * 60)
    
    mac_bot = MacMultiStrategyBot()
    
    try:
        success = mac_bot.start()
        if not success:
            print("❌ Failed to start cross-platform bot")
            sys.exit(1)
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
