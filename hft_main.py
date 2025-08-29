#!/usr/bin/env python3
"""
High-Frequency Trading Bot - Optimized for Speed and Performance
"""

import time
import logging
from datetime import datetime
from typing import Dict, Any
import signal
import sys

# Import HFT configuration
from config_hft import (
    TRADING_SETTINGS, STRATEGY_SETTINGS, TIME_SETTINGS, 
    LOGGING_SETTINGS, PERFORMANCE_SETTINGS, RISK_SETTINGS
)

from mt5_connector import MT5Connector
from trade_manager import TradeManager
from risk_manager import RiskManager
from strategies.hft_ema_scalper import HFTEMAScalper

class HighFrequencyTradingBot:
    """High-performance trading bot optimized for HFT."""
    
    def __init__(self):
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.mt5_connector = MT5Connector()
        self.trade_manager = TradeManager(self.mt5_connector)
        self.risk_manager = RiskManager(self.mt5_connector, self.trade_manager)
        
        # Initialize HFT strategy
        self.strategy = HFTEMAScalper(STRATEGY_SETTINGS.get('ema_crossover', {}))
        
        # HFT performance tracking
        self.running = False
        self.stats = {
            'start_time': None,
            'loops': 0,
            'signals': 0,
            'trades': 0,
            'last_trade_time': None,
            'avg_loop_time': 0,
            'max_loop_time': 0,
        }
        
        # Signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def setup_logging(self):
        """Setup optimized logging for HFT."""
        # Minimal logging for maximum speed
        logging.basicConfig(
            level=getattr(logging, LOGGING_SETTINGS['log_level']),
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(LOGGING_SETTINGS['log_file']),
            ]
        )
    
    def start(self):
        """Start HFT bot."""
        print("🚀 Starting High-Frequency Trading Bot...")
        print("=" * 60)
        
        # Connect to MT5
        if not self.mt5_connector.connect():
            print("❌ Failed to connect to MT5")
            return False
        
        # Verify setup
        if not self.verify_setup():
            print("❌ Setup verification failed")
            return False
        
        print("✅ HFT Bot initialized successfully")
        print(f"📊 Strategy: {self.strategy.name}")
        print(f"⚡ Update Interval: {STRATEGY_SETTINGS['update_interval']*1000:.1f}ms")
        print(f"📈 Symbol: {TRADING_SETTINGS['symbol']}")
        print(f"⏰ Timeframe: {TRADING_SETTINGS['timeframe']}")
        print("=" * 60)
        
        self.running = True
        self.stats['start_time'] = datetime.now()
        
        return self.run_hft_loop()
    
    def verify_setup(self) -> bool:
        """Quick setup verification."""
        try:
            account_info = self.mt5_connector.get_account_info()
            if not account_info:
                return False
            
            # Check if AutoTrading is enabled
            symbol_info = self.mt5_connector.get_symbol_info(TRADING_SETTINGS['symbol'])
            if not symbol_info:
                return False
            
            print(f"💰 Account: {account_info['login']} | Balance: {account_info['balance']}")
            print(f"🎯 Symbol: {TRADING_SETTINGS['symbol']} | Spread: {symbol_info.get('spread', 'N/A')}")
            
            if not account_info.get('trade_allowed', False):
                print("⚠️  WARNING: Trading not allowed on account!")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ Setup verification error: {e}")
            return False
    
    def run_hft_loop(self):
        """Main high-frequency trading loop."""
        print("🔄 Starting HFT loop...")
        
        update_interval = STRATEGY_SETTINGS['update_interval']
        symbol = TRADING_SETTINGS['symbol']
        timeframe = TRADING_SETTINGS['timeframe']
        lookback_periods = STRATEGY_SETTINGS['lookback_periods']
        
        last_status_time = time.time()
        loop_times = []
        
        try:
            while self.running:
                loop_start = time.time()
                
                # Get market data (optimized)
                data = self.mt5_connector.get_market_data(symbol, timeframe, lookback_periods)
                if data is None or len(data) < self.strategy.get_minimum_bars():
                    time.sleep(update_interval)
                    continue
                
                # Check for signals
                signal = self.strategy.get_signal(data)
                
                if signal:
                    self.stats['signals'] += 1
                    
                    # Execute trade immediately for HFT
                    if self.execute_hft_trade(signal, data, symbol):
                        self.stats['trades'] += 1
                        self.stats['last_trade_time'] = datetime.now()
                
                # Update loop performance
                loop_time = time.time() - loop_start
                loop_times.append(loop_time)
                self.stats['loops'] += 1
                
                # Keep only last 1000 loop times for performance
                if len(loop_times) > 1000:
                    loop_times = loop_times[-1000:]
                
                # Status update every 10 seconds
                if time.time() - last_status_time >= 10:
                    self.print_hft_status(loop_times)
                    last_status_time = time.time()
                
                # Sleep for remaining time
                sleep_time = max(0, update_interval - loop_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            print("\n🛑 HFT Bot shutdown requested...")
        except Exception as e:
            print(f"❌ HFT Loop error: {e}")
            self.logger.error(f"HFT Loop error: {e}")
        finally:
            self.stop()
    
    def execute_hft_trade(self, signal: str, data, symbol: str) -> bool:
        """Execute trade with HFT optimizations."""
        try:
            # Get current price quickly
            price_info = self.mt5_connector.get_current_price(symbol)
            if not price_info:
                return False
            
            entry_price = price_info['ask'] if signal == 'BUY' else price_info['bid']
            
            # Quick risk checks
            if not self.risk_manager.check_trading_allowed():
                return False
            
            # Calculate stops
            stop_loss = self.strategy.get_stop_loss(data, signal, entry_price)
            take_profit = self.strategy.get_take_profit(data, signal, entry_price)
            
            # Use fixed lot size for HFT speed
            volume = TRADING_SETTINGS['lot_size']
            
            # Quick validation
            validation = self.risk_manager.validate_trade(
                symbol, signal, volume, entry_price, stop_loss, take_profit
            )
            
            if not validation['valid']:
                return False
            
            # Execute trade
            result = self.trade_manager.place_market_order(
                symbol=symbol,
                order_type=signal,
                volume=volume,
                stop_loss=stop_loss,
                take_profit=take_profit,
                comment=f"HFT-{signal}"
            )
            
            return result is not None
            
        except Exception as e:
            self.logger.error(f"HFT trade execution error: {e}")
            return False
    
    def print_hft_status(self, loop_times):
        """Print HFT performance status."""
        runtime = datetime.now() - self.stats['start_time']
        avg_freq = self.stats['loops'] / runtime.total_seconds()
        
        if loop_times:
            avg_loop_time = sum(loop_times) / len(loop_times)
            max_loop_time = max(loop_times)
        else:
            avg_loop_time = 0
            max_loop_time = 0
        
        # Get account info
        account_info = self.mt5_connector.get_account_info()
        positions = self.mt5_connector.get_positions()
        
        print(f"\n📊 HFT STATUS | Runtime: {runtime}")
        print(f"⚡ Frequency: {avg_freq:.1f} Hz | Loops: {self.stats['loops']}")
        print(f"🎯 Signals: {self.stats['signals']} | Trades: {self.stats['trades']}")
        print(f"⏱️  Avg Loop: {avg_loop_time*1000:.1f}ms | Max: {max_loop_time*1000:.1f}ms")
        
        if account_info:
            print(f"💰 Balance: {account_info['balance']:.2f} | Positions: {len(positions) if positions else 0}")
        
        # Signal rate
        signal_rate = self.stats['signals'] / runtime.total_seconds() * 60
        print(f"📈 Signal Rate: {signal_rate:.1f}/min")
        
        if self.stats['trades'] > 0:
            trade_rate = self.stats['trades'] / runtime.total_seconds() * 60
            print(f"💹 Trade Rate: {trade_rate:.1f}/min")
    
    def stop(self):
        """Stop HFT bot."""
        print("\n🛑 Stopping HFT Bot...")
        self.running = False
        
        # Final statistics
        if self.stats['start_time']:
            runtime = datetime.now() - self.stats['start_time']
            avg_freq = self.stats['loops'] / runtime.total_seconds()
            
            print(f"\n📈 FINAL HFT STATISTICS:")
            print(f"⏰ Total Runtime: {runtime}")
            print(f"🔄 Total Loops: {self.stats['loops']}")
            print(f"⚡ Average Frequency: {avg_freq:.1f} Hz")
            print(f"🎯 Signals Generated: {self.stats['signals']}")
            print(f"💰 Trades Executed: {self.stats['trades']}")
            
            if self.stats['signals'] > 0:
                hit_rate = (self.stats['trades'] / self.stats['signals']) * 100
                print(f"🎯 Signal to Trade Rate: {hit_rate:.1f}%")
        
        # Disconnect
        self.mt5_connector.disconnect()
        print("✅ HFT Bot stopped successfully")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\n🚨 Received signal {signum}, shutting down HFT bot...")
        self.running = False

def main():
    """Main entry point for HFT bot."""
    print("🚀 HIGH-FREQUENCY TRADING BOT")
    print("=" * 60)
    print("⚠️  WARNING: Ensure AutoTrading is ENABLED in MT5!")
    print("⚠️  WARNING: This is aggressive HFT - use demo first!")
    print("=" * 60)
    
    hft_bot = HighFrequencyTradingBot()
    
    try:
        success = hft_bot.start()
        if not success:
            print("❌ Failed to start HFT bot")
            sys.exit(1)
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
