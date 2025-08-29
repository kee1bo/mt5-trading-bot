#!/usr/bin/env python3
"""
Optimized Multi-Strategy Trading Bot - Enhanced for higher position limits
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

class OptimizedMultiStrategyBot:
    """
    Optimized multi-strategy trading bot with enhanced position management.
    """
    
    def __init__(self):
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.mt5_connector = MT5Connector()
        self.trade_manager = TradeManager(self.mt5_connector)
        self.risk_manager = RiskManager(self.mt5_connector, self.trade_manager)
        
        # Strategy configurations with increased limits
        self.strategies = self.initialize_optimized_strategies()
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
                'failed_trades': 0,
                'position_limit_blocks': 0
            }
        }
        
        # Initialize strategy stats
        for strategy_name in self.strategies.keys():
            self.stats['strategy_stats'][strategy_name] = {
                'signals': 0,
                'trades': 0,
                'position_limit_blocks': 0,
                'last_signal_time': None,
                'avg_execution_time': 0,
            }
        
        # Signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def setup_logging(self):
        """Setup logging for optimized multi-strategy bot."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('optimized_multi_strategy.log'),
                logging.StreamHandler()
            ]
        )
    
    def initialize_optimized_strategies(self) -> Dict[str, Any]:
        """Initialize all trading strategies with optimized parameters for higher throughput."""
        strategies = {}
        
        # EMA Crossover - Conservative but reliable
        strategies['ema_crossover'] = {
            'instance': EMACrossoverStrategy({
                'ema_period': 8,
                'confirmation_candles': 0,
                'signal_cooldown': 8,
                'min_atr_filter': 0.00001,
            }),
            'enabled': True,
            'max_positions': 3,  # Increased from 2
            'risk_per_trade': 0.4,  # Reduced from 0.5% for more positions
        }
        
        # Aggressive Scalping - High frequency
        strategies['aggressive_scalp'] = {
            'instance': AggressiveScalpStrategy({
                'min_price_change': 0.008,  # Slightly increased threshold
                'signal_cooldown': 3,  # Increased cooldown
                'momentum_periods': 3,
            }),
            'enabled': True,
            'max_positions': 4,  # Increased from 3
            'risk_per_trade': 0.25,  # Reduced risk per trade
        }
        
        # Momentum Breakout - Trend following
        strategies['momentum_breakout'] = {
            'instance': MomentumBreakoutStrategy({
                'momentum_period': 5,
                'breakout_threshold': 0.35,  # Slightly higher threshold
                'signal_cooldown': 6,  # Increased cooldown
            }),
            'enabled': True,
            'max_positions': 3,  # Increased from 2
            'risk_per_trade': 0.5,  # Reduced from 0.7%
        }
        
        # Mean Reversion - Counter-trend
        strategies['mean_reversion'] = {
            'instance': MeanReversionStrategy({
                'ma_period': 15,
                'std_multiplier': 1.3,  # Slightly higher threshold
                'rsi_oversold': 32,  # More restrictive
                'rsi_overbought': 68,  # More restrictive
                'signal_cooldown': 10,  # Increased cooldown
            }),
            'enabled': True,
            'max_positions': 2,  # Keep same
            'risk_per_trade': 0.4,  # Reduced from 0.6%
        }
        
        # HFT EMA Scalper - Ultra fast
        strategies['hft_ema'] = {
            'instance': HFTEMAScalper({
                'fast_ema': 3,
                'slow_ema': 7,
                'signal_cooldown': 2,  # Increased cooldown
                'min_atr_filter': 0.00002,  # Higher filter
            }),
            'enabled': True,
            'max_positions': 3,  # Reduced from 4
            'risk_per_trade': 0.15,  # Reduced risk
        }
        
        return strategies
    
    def start(self):
        """Start optimized multi-strategy trading bot."""
        print("🚀 Starting Optimized Multi-Strategy Trading Bot")
        print("=" * 70)
        
        # Connect to MT5
        if not self.mt5_connector.connect():
            print("❌ Failed to connect to MT5")
            return False
        
        # Verify setup
        if not self.verify_setup():
            print("❌ Setup verification failed") 
            return False
        
        print("✅ Optimized Multi-Strategy Bot initialized successfully")
        print(f"📊 Active Strategies: {len([s for s in self.strategies.values() if s['enabled']])}")
        
        # Display strategy info
        total_max_positions = 0
        for name, config in self.strategies.items():
            if config['enabled']:
                strategy = config['instance']
                total_max_positions += config['max_positions']
                print(f"  🎯 {strategy.name}: Max={config['max_positions']}, Risk={config['risk_per_trade']}%")
        
        print(f"📈 Total Maximum Positions: {total_max_positions}")
        print("=" * 70)
        
        self.running = True
        self.stats['start_time'] = datetime.now()
        
        return self.run_optimized_loop()
    
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
    
    def run_optimized_loop(self):
        """Main optimized multi-strategy trading loop."""
        print("🔄 Starting optimized multi-strategy loop...")
        
        symbol = 'XAUUSD'
        timeframe = 'M1'  # Use M1 for all strategies
        lookback_periods = 100  # Reduced for faster processing
        
        last_status_time = time.time()
        
        try:
            while self.running:
                loop_start = time.time()
                
                # Get market data once for all strategies
                data = self.mt5_connector.get_market_data(symbol, timeframe, lookback_periods)
                if data is None or len(data) < 30:
                    time.sleep(0.1)
                    continue
                
                # Process strategies in order of priority (fastest execution first)
                strategy_order = ['aggressive_scalp', 'hft_ema', 'momentum_breakout', 'mean_reversion', 'ema_crossover']
                
                for strategy_name in strategy_order:
                    if strategy_name not in self.strategies or not self.strategies[strategy_name]['enabled']:
                        continue
                    
                    config = self.strategies[strategy_name]
                    strategy_start = time.time()
                    
                    try:
                        # Check strategy-specific position limits
                        current_positions = self.get_strategy_positions(strategy_name)
                        if len(current_positions) >= config['max_positions']:
                            self.stats['strategy_stats'][strategy_name]['position_limit_blocks'] += 1
                            continue
                        
                        # Get signal from strategy
                        strategy = config['instance']
                        signal = strategy.get_signal(data)
                        
                        if signal:
                            self.stats['strategy_stats'][strategy_name]['signals'] += 1
                            self.stats['global_stats']['signals'] += 1
                            
                            print(f"🚦 {strategy.name}: {signal} signal at {data['close'].iloc[-1]:.2f}")
                            
                            # Execute trade with enhanced risk checking
                            if self.execute_optimized_trade(strategy_name, signal, data, symbol):
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
                
                # Status update every 45 seconds
                if time.time() - last_status_time >= 45:
                    self.print_optimized_status()
                    last_status_time = time.time()
                
                # Optimized sleep timing
                loop_time = time.time() - loop_start
                time.sleep(max(0.05, 0.15 - loop_time))  # Target ~6.5 Hz
                
        except KeyboardInterrupt:
            print("\n🛑 Optimized multi-strategy bot shutdown requested...")
        except Exception as e:
            print(f"❌ Optimized multi-strategy loop error: {e}")
            self.logger.error(f"Optimized multi-strategy loop error: {e}")
        finally:
            self.stop()
    
    def execute_optimized_trade(self, strategy_name: str, signal: str, data, symbol: str) -> bool:
        """Execute trade with optimized risk management."""
        try:
            config = self.strategies[strategy_name]
            strategy = config['instance']
            
            # Enhanced risk check with strategy-specific limits
            if not self.risk_manager.check_trading_allowed(
                strategy_name=strategy_name, 
                max_strategy_positions=config['max_positions']
            ):
                self.stats['global_stats']['position_limit_blocks'] += 1
                return False
            
            # Get current price
            price_info = self.mt5_connector.get_current_price(symbol)
            if not price_info:
                return False
            
            entry_price = price_info['ask'] if signal == 'BUY' else price_info['bid']
            
            # Calculate stops
            stop_loss = strategy.get_stop_loss(data, signal, entry_price)
            take_profit = strategy.get_take_profit(data, signal, entry_price)
            
            # Use smaller position size for higher frequency
            volume = 0.01  # Keep small for testing
            
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
            self.logger.error(f"Error executing optimized {strategy_name} trade: {e}")
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
    
    def print_optimized_status(self):
        """Print comprehensive optimized status."""
        runtime = datetime.now() - self.stats['start_time']
        
        print(f"\n📊 OPTIMIZED MULTI-STRATEGY STATUS | Runtime: {runtime}")
        print(f"🔄 Total Loops: {self.stats['total_loops']}")
        print(f"🎯 Global Signals: {self.stats['global_stats']['signals']}")
        print(f"💰 Global Trades: {self.stats['global_stats']['trades']}")
        print(f"🚫 Position Limit Blocks: {self.stats['global_stats']['position_limit_blocks']}")
        
        # Success rate
        total_attempts = self.stats['global_stats']['trades'] + self.stats['global_stats']['failed_trades']
        success_rate = (self.stats['global_stats']['successful_trades'] / max(1, total_attempts) * 100)
        print(f"✅ Success Rate: {success_rate:.1f}%")
        
        # Account info
        account_info = self.mt5_connector.get_account_info()
        if account_info:
            print(f"💼 Balance: {account_info['balance']:.2f} | Equity: {account_info['equity']:.2f}")
        
        # Strategy breakdown with position limits
        print(f"\n📈 STRATEGY BREAKDOWN:")
        total_positions = 0
        for strategy_name, stats in self.stats['strategy_stats'].items():
            if self.strategies[strategy_name]['enabled']:
                positions = len(self.get_strategy_positions(strategy_name))
                max_pos = self.strategies[strategy_name]['max_positions']
                blocks = stats['position_limit_blocks']
                total_positions += positions
                print(f"  {strategy_name:18} | Sig: {stats['signals']:3d} | Trades: {stats['trades']:3d} | Pos: {positions}/{max_pos} | Blocks: {blocks}")
        
        print(f"📊 Total Active Positions: {total_positions}")
        
        # Signal rates
        total_signals = self.stats['global_stats']['signals']
        signal_rate = total_signals / runtime.total_seconds() * 60 if runtime.total_seconds() > 0 else 0
        print(f"📈 Signal Rate: {signal_rate:.1f}/min")
    
    def stop(self):
        """Stop optimized multi-strategy bot."""
        print("\n🛑 Stopping Optimized Multi-Strategy Bot...")
        self.running = False
        
        # Final statistics
        if self.stats['start_time']:
            runtime = datetime.now() - self.stats['start_time']
            
            print(f"\n📈 FINAL OPTIMIZED STATISTICS:")
            print(f"⏰ Total Runtime: {runtime}")
            print(f"🔄 Total Loops: {self.stats['total_loops']}")
            print(f"🎯 Total Signals: {self.stats['global_stats']['signals']}")
            print(f"💰 Total Trades: {self.stats['global_stats']['trades']}")
            print(f"✅ Successful Trades: {self.stats['global_stats']['successful_trades']}")
            print(f"❌ Failed Trades: {self.stats['global_stats']['failed_trades']}")
            print(f"🚫 Position Limit Blocks: {self.stats['global_stats']['position_limit_blocks']}")
            
            # Strategy performance
            print(f"\n📊 FINAL STRATEGY PERFORMANCE:")
            for strategy_name, stats in self.stats['strategy_stats'].items():
                if self.strategies[strategy_name]['enabled']:
                    efficiency = (stats['trades'] / max(1, stats['signals']) * 100)
                    print(f"  {strategy_name:20} | Signals: {stats['signals']:3d} | Trades: {stats['trades']:3d} | Efficiency: {efficiency:.1f}% | Blocks: {stats['position_limit_blocks']}")
        
        # Save performance data
        self.save_performance_data()
        
        # Disconnect
        self.mt5_connector.disconnect()
        print("✅ Optimized Multi-Strategy Bot stopped successfully")
    
    def save_performance_data(self):
        """Save optimized performance statistics to file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"optimized_multi_strategy_performance_{timestamp}.json"
            
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
            
            print(f"💾 Optimized performance data saved to {filename}")
            
        except Exception as e:
            self.logger.error(f"Error saving optimized performance data: {e}")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\n🚨 Received signal {signum}, shutting down optimized bot...")
        self.running = False

def main():
    """Main entry point for optimized multi-strategy bot."""
    print("🚀 OPTIMIZED MULTI-STRATEGY TRADING BOT")
    print("=" * 70)
    print("⚠️  WARNING: Ensure AutoTrading is ENABLED in MT5!")
    print("⚡ OPTIMIZED: Enhanced position limits and risk management!")
    print("📊 ENHANCED: Per-strategy position tracking and limits!")
    print("=" * 70)
    
    optimized_bot = OptimizedMultiStrategyBot()
    
    try:
        success = optimized_bot.start()
        if not success:
            print("❌ Failed to start optimized multi-strategy bot")
            sys.exit(1)
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
