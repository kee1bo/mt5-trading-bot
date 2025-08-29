#!/usr/bin/env python3
"""
Multi-Strategy Trading Bot - Runs multiple strategies simultaneously
"""

import time
import logging
import threading
from datetime import datetime
from typing import Dict, List, Any
import signal
import sys
import json

from mt5_connector import MT5Connector
from trade_manager import TradeManager
from risk_manager import RiskManager

# Import all strategies
from strategies.ema_crossover import EMACrossoverStrategy
from strategies.aggressive_scalp import AggressiveScalpStrategy
from strategies.momentum_breakout import MomentumBreakoutStrategy
from strategies.mean_reversion import MeanReversionStrategy
from strategies.hft_ema_scalper import HFTEMAScalper

class MultiStrategyTradingBot:
    """
    Multi-strategy trading bot that runs several strategies simultaneously.
    Each strategy operates independently with its own risk management.
    """
    
    def __init__(self):
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.mt5_connector = MT5Connector()
        self.trade_manager = TradeManager(self.mt5_connector)
        self.risk_manager = RiskManager(self.mt5_connector, self.trade_manager)
        
        # Strategy configurations
        self.strategies = self.initialize_strategies()
        self.running = False
        
        # Performance tracking
        self.stats = {
            'start_time': None,
            'total_loops': 0,
            'strategy_stats': {},
            'global_stats': {
                'signals': 0,
                'trades': 0,
                'successful_trades': 0,
                'failed_trades': 0
            }
        }
        
        # Initialize strategy stats
        for strategy_name in self.strategies.keys():
            self.stats['strategy_stats'][strategy_name] = {
                'signals': 0,
                'trades': 0,
                'last_signal_time': None,
                'avg_execution_time': 0,
            }
        
        # Signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def setup_logging(self):
        """Setup logging for multi-strategy bot."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('multi_strategy_bot.log'),
                logging.StreamHandler()
            ]
        )
    
    def initialize_strategies(self) -> Dict[str, Any]:
        """Initialize all trading strategies with optimized parameters."""
        strategies = {}
        
        # EMA Crossover - Conservative but reliable
        strategies['ema_crossover'] = {
            'instance': EMACrossoverStrategy({
                'ema_period': 8,
                'confirmation_candles': 0,
                'signal_cooldown': 10,
                'min_atr_filter': 0.00001,
            }),
            'enabled': True,
            'max_positions': 2,
            'risk_per_trade': 0.5,  # 0.5% risk per trade
        }
        
        # Aggressive Scalping - High frequency
        strategies['aggressive_scalp'] = {
            'instance': AggressiveScalpStrategy({
                'min_price_change': 0.005,
                'signal_cooldown': 2,
                'momentum_periods': 3,
            }),
            'enabled': True,
            'max_positions': 3,
            'risk_per_trade': 0.3,  # Lower risk due to frequency
        }
        
        # Momentum Breakout - Trend following
        strategies['momentum_breakout'] = {
            'instance': MomentumBreakoutStrategy({
                'momentum_period': 5,
                'breakout_threshold': 0.3,
                'signal_cooldown': 5,
            }),
            'enabled': True,
            'max_positions': 2,
            'risk_per_trade': 0.7,  # Higher risk for trend trades
        }
        
        # Mean Reversion - Counter-trend
        strategies['mean_reversion'] = {
            'instance': MeanReversionStrategy({
                'ma_period': 15,
                'std_multiplier': 1.2,
                'rsi_oversold': 35,
                'rsi_overbought': 65,
                'signal_cooldown': 8,
            }),
            'enabled': True,
            'max_positions': 2,
            'risk_per_trade': 0.6,
        }
        
        # HFT EMA Scalper - Ultra fast
        strategies['hft_ema'] = {
            'instance': HFTEMAScalper({
                'fast_ema': 3,
                'slow_ema': 7,
                'signal_cooldown': 1,
                'min_atr_filter': 0.00001,
            }),
            'enabled': True,
            'max_positions': 4,
            'risk_per_trade': 0.2,  # Very low risk due to high frequency
        }
        
        return strategies
    
    def start(self):
        """Start multi-strategy trading bot."""
        print("🚀 Starting Multi-Strategy Trading Bot")
        print("=" * 60)
        
        # Connect to MT5
        if not self.mt5_connector.connect():
            print("❌ Failed to connect to MT5")
            return False
        
        # Verify setup
        if not self.verify_setup():
            print("❌ Setup verification failed") 
            return False
        
        print("✅ Multi-Strategy Bot initialized successfully")
        print(f"📊 Active Strategies: {len([s for s in self.strategies.values() if s['enabled']])}")
        
        # Display strategy info
        for name, config in self.strategies.items():
            if config['enabled']:
                strategy = config['instance']
                print(f"  🎯 {strategy.name}: Max Positions={config['max_positions']}, Risk={config['risk_per_trade']}%")
        
        print("=" * 60)
        
        self.running = True
        self.stats['start_time'] = datetime.now()
        
        return self.run_multi_strategy_loop()
    
    def verify_setup(self) -> bool:
        """Verify trading setup."""
        try:
            account_info = self.mt5_connector.get_account_info()
            if not account_info:
                return False
            
            print(f"💰 Account: {account_info['login']} | Balance: {account_info['balance']}")
            
            if not account_info.get('trade_allowed', False):
                print("⚠️  WARNING: Trading not allowed on account!")
                input("Press Enter to continue anyway, or Ctrl+C to exit...")
            
            return True
            
        except Exception as e:
            print(f"❌ Setup verification error: {e}")
            return False
    
    def run_multi_strategy_loop(self):
        """Main multi-strategy trading loop."""
        print("🔄 Starting multi-strategy loop...")
        
        symbol = 'XAUUSD'
        timeframe = 'M1'  # Use M1 for all strategies
        lookback_periods = 200
        
        last_status_time = time.time()
        
        try:
            while self.running:
                loop_start = time.time()
                
                # Get market data once for all strategies
                data = self.mt5_connector.get_market_data(symbol, timeframe, lookback_periods)
                if data is None or len(data) < 50:
                    time.sleep(0.1)
                    continue
                
                # Check each strategy for signals
                for strategy_name, config in self.strategies.items():
                    if not config['enabled']:
                        continue
                    
                    strategy_start = time.time()
                    
                    try:
                        # Check if strategy has room for more positions
                        current_positions = self.get_strategy_positions(strategy_name)
                        if len(current_positions) >= config['max_positions']:
                            continue
                        
                        # Get signal from strategy
                        strategy = config['instance']
                        signal = strategy.get_signal(data)
                        
                        if signal:
                            self.stats['strategy_stats'][strategy_name]['signals'] += 1
                            self.stats['global_stats']['signals'] += 1
                            
                            print(f"🚦 {strategy.name}: {signal} signal at {data['close'].iloc[-1]:.2f}")
                            
                            # Execute trade
                            if self.execute_strategy_trade(strategy_name, signal, data, symbol):
                                self.stats['strategy_stats'][strategy_name]['trades'] += 1
                                self.stats['global_stats']['trades'] += 1
                                self.stats['global_stats']['successful_trades'] += 1
                                print(f"✅ {strategy.name}: Trade executed successfully")
                            else:
                                self.stats['global_stats']['failed_trades'] += 1
                                print(f"❌ {strategy.name}: Trade execution failed")
                    
                    except Exception as e:
                        self.logger.error(f"Error in strategy {strategy_name}: {e}")
                    
                    # Track strategy performance
                    strategy_time = time.time() - strategy_start
                    current_avg = self.stats['strategy_stats'][strategy_name]['avg_execution_time']
                    self.stats['strategy_stats'][strategy_name]['avg_execution_time'] = (current_avg + strategy_time) / 2
                
                self.stats['total_loops'] += 1
                
                # Status update every 30 seconds
                if time.time() - last_status_time >= 30:
                    self.print_multi_strategy_status()
                    last_status_time = time.time()
                
                # Small sleep to prevent excessive CPU usage
                loop_time = time.time() - loop_start
                time.sleep(max(0.05, 0.2 - loop_time))  # Target ~5 Hz
                
        except KeyboardInterrupt:
            print("\n🛑 Multi-strategy bot shutdown requested...")
        except Exception as e:
            print(f"❌ Multi-strategy loop error: {e}")
            self.logger.error(f"Multi-strategy loop error: {e}")
        finally:
            self.stop()
    
    def execute_strategy_trade(self, strategy_name: str, signal: str, data, symbol: str) -> bool:
        """Execute trade for specific strategy."""
        try:
            config = self.strategies[strategy_name]
            strategy = config['instance']
            
            # Get current price
            price_info = self.mt5_connector.get_current_price(symbol)
            if not price_info:
                return False
            
            entry_price = price_info['ask'] if signal == 'BUY' else price_info['bid']
            
            # Calculate stops
            stop_loss = strategy.get_stop_loss(data, signal, entry_price)
            take_profit = strategy.get_take_profit(data, signal, entry_price)
            
            # Calculate position size based on strategy risk
            volume = 0.01  # Default small size for testing
            
            # Quick risk check with strategy-specific limits
            if not self.risk_manager.check_trading_allowed(
                strategy_name=strategy_name, 
                max_strategy_positions=config['max_positions']
            ):
                return False
            
            # Execute trade with strategy-specific comment
            result = self.trade_manager.place_market_order(
                symbol=symbol,
                order_type=signal,
                volume=volume,
                stop_loss=stop_loss,
                take_profit=take_profit,
                comment=f"{strategy_name}_{signal}"
            )
            
            return result is not None
            
        except Exception as e:
            self.logger.error(f"Error executing {strategy_name} trade: {e}")
            return False
    
    def get_strategy_positions(self, strategy_name: str) -> List:
        """Get current positions for a specific strategy."""
        try:
            all_positions = self.mt5_connector.get_positions()
            if not all_positions:
                return []
            
            # Filter positions by strategy comment
            strategy_positions = [
                pos for pos in all_positions 
                if pos.get('comment', '').startswith(strategy_name)
            ]
            
            return strategy_positions
            
        except Exception as e:
            self.logger.error(f"Error getting {strategy_name} positions: {e}")
            return []
    
    def print_multi_strategy_status(self):
        """Print comprehensive status for all strategies."""
        runtime = datetime.now() - self.stats['start_time']
        
        print(f"\n📊 MULTI-STRATEGY STATUS | Runtime: {runtime}")
        print(f"🔄 Total Loops: {self.stats['total_loops']}")
        print(f"🎯 Global Signals: {self.stats['global_stats']['signals']}")
        print(f"💰 Global Trades: {self.stats['global_stats']['trades']}")
        print(f"✅ Success Rate: {(self.stats['global_stats']['successful_trades'] / max(1, self.stats['global_stats']['trades']) * 100):.1f}%")
        
        # Account info
        account_info = self.mt5_connector.get_account_info()
        if account_info:
            print(f"💼 Balance: {account_info['balance']:.2f} | Equity: {account_info['equity']:.2f}")
        
        # Strategy breakdown
        print("\n📈 STRATEGY BREAKDOWN:")
        for strategy_name, stats in self.stats['strategy_stats'].items():
            if self.strategies[strategy_name]['enabled']:
                positions = len(self.get_strategy_positions(strategy_name))
                print(f"  {strategy_name:18} | Signals: {stats['signals']:3d} | Trades: {stats['trades']:3d} | Positions: {positions}")
        
        # Signal rates
        total_signals = self.stats['global_stats']['signals']
        signal_rate = total_signals / runtime.total_seconds() * 60 if runtime.total_seconds() > 0 else 0
        print(f"📈 Signal Rate: {signal_rate:.1f}/min")
    
    def stop(self):
        """Stop multi-strategy bot."""
        print("\n🛑 Stopping Multi-Strategy Bot...")
        self.running = False
        
        # Final statistics
        if self.stats['start_time']:
            runtime = datetime.now() - self.stats['start_time']
            
            print(f"\n📈 FINAL MULTI-STRATEGY STATISTICS:")
            print(f"⏰ Total Runtime: {runtime}")
            print(f"🔄 Total Loops: {self.stats['total_loops']}")
            print(f"🎯 Total Signals: {self.stats['global_stats']['signals']}")
            print(f"💰 Total Trades: {self.stats['global_stats']['trades']}")
            print(f"✅ Successful Trades: {self.stats['global_stats']['successful_trades']}")
            print(f"❌ Failed Trades: {self.stats['global_stats']['failed_trades']}")
            
            # Strategy performance
            print(f"\n📊 STRATEGY PERFORMANCE:")
            for strategy_name, stats in self.stats['strategy_stats'].items():
                if self.strategies[strategy_name]['enabled']:
                    print(f"  {strategy_name:20} | Signals: {stats['signals']:3d} | Trades: {stats['trades']:3d}")
        
        # Save performance data
        self.save_performance_data()
        
        # Disconnect
        self.mt5_connector.disconnect()
        print("✅ Multi-Strategy Bot stopped successfully")
    
    def save_performance_data(self):
        """Save performance statistics to file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"multi_strategy_performance_{timestamp}.json"
            
            performance_data = {
                'timestamp': timestamp,
                'runtime_seconds': (datetime.now() - self.stats['start_time']).total_seconds(),
                'stats': self.stats,
                'strategy_configs': {
                    name: {
                        'enabled': config['enabled'],
                        'max_positions': config['max_positions'],
                        'risk_per_trade': config['risk_per_trade'],
                        'strategy_name': config['instance'].name
                    }
                    for name, config in self.strategies.items()
                }
            }
            
            with open(filename, 'w') as f:
                json.dump(performance_data, f, indent=2, default=str)
            
            print(f"💾 Performance data saved to {filename}")
            
        except Exception as e:
            self.logger.error(f"Error saving performance data: {e}")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\n🚨 Received signal {signum}, shutting down multi-strategy bot...")
        self.running = False

def main():
    """Main entry point for multi-strategy bot."""
    print("🚀 MULTI-STRATEGY TRADING BOT")
    print("=" * 60)
    print("⚠️  WARNING: Ensure AutoTrading is ENABLED in MT5!")
    print("⚠️  WARNING: This runs multiple strategies simultaneously!")
    print("=" * 60)
    
    multi_bot = MultiStrategyTradingBot()
    
    try:
        success = multi_bot.start()
        if not success:
            print("❌ Failed to start multi-strategy bot")
            sys.exit(1)
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
