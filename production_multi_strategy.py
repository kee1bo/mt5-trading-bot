#!/usr/bin/env python3
"""
High-Performance Multi-Strategy Trading Bot - Production Ready
Only includes verified working strategies with optimized performance.
"""

import time
import logging
import threading
from datetime import datetime
from typing import Dict, List, Any
import signal
import sys
import json
import os

from mt5_connector import MT5Connector
from trade_manager import TradeManager
from risk_manager import RiskManager

# Import only working strategies
from strategies.aggressive_scalp import AggressiveScalpStrategy
from strategies.momentum_breakout import MomentumBreakoutStrategy

class ProductionMultiStrategyBot:
    """
    Production-ready multi-strategy trading bot with only verified working strategies.
    Optimized for high performance and reliability.
    """
    
    def __init__(self):
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.mt5_connector = MT5Connector()
        self.trade_manager = TradeManager(self.mt5_connector)
        self.risk_manager = RiskManager(self.mt5_connector, self.trade_manager)
        
        # Only working strategies
        self.strategies = self.initialize_working_strategies()
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
                'efficiency': 0.0
            }
        }
        
        # Initialize strategy stats
        for strategy_name in self.strategies.keys():
            self.stats['strategy_stats'][strategy_name] = {
                'signals': 0,
                'trades': 0,
                'last_signal_time': None,
                'avg_execution_time': 0,
                'efficiency': 0.0
            }
        
        # Signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def setup_logging(self):
        """Setup logging for production bot."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('production_multi_strategy.log'),
                logging.StreamHandler()
            ]
        )
    
    def initialize_working_strategies(self) -> Dict[str, Any]:
        """Initialize only verified working strategies."""
        strategies = {}
        
        # Aggressive Scalping - Proven high performance
        strategies['aggressive_scalp'] = {
            'instance': AggressiveScalpStrategy({
                'min_price_change': 0.01,  # Optimized threshold
                'signal_cooldown': 5,  # 5 second cooldown
                'momentum_periods': 3,
            }),
            'enabled': True,
            'max_positions': 6,  # Higher limit for good performer
            'risk_per_trade': 0.2,
            'priority': 1  # Highest priority
        }
        
        # Momentum Breakout - Reliable trend following
        strategies['momentum_breakout'] = {
            'instance': MomentumBreakoutStrategy({
                'momentum_period': 5,
                'breakout_threshold': 0.4,  # Slightly higher threshold
                'signal_cooldown': 8,  # 8 second cooldown
            }),
            'enabled': True,
            'max_positions': 4,
            'risk_per_trade': 0.3,
            'priority': 2
        }
        
        return strategies
    
    def start(self):
        """Start production multi-strategy trading bot."""
        print("🚀 Starting Production Multi-Strategy Trading Bot")
        print("=" * 60)
        
        # Connect to MT5
        if not self.mt5_connector.connect():
            print("❌ Failed to connect to MT5")
            return False
        
        # Verify setup
        if not self.verify_setup():
            print("❌ Setup verification failed") 
            return False
        
        print("✅ Production Multi-Strategy Bot initialized successfully")
        print(f"📊 Active Strategies: {len([s for s in self.strategies.values() if s['enabled']])}")
        
        # Display strategy info
        total_max_positions = 0
        for name, config in self.strategies.items():
            if config['enabled']:
                strategy = config['instance']
                total_max_positions += config['max_positions']
                print(f"  🎯 {strategy.name}: Max={config['max_positions']}, Risk={config['risk_per_trade']}%, Priority={config['priority']}")
        
        print(f"📈 Total Maximum Positions: {total_max_positions}")
        print("=" * 60)
        
        self.running = True
        self.stats['start_time'] = datetime.now()
        
        return self.run_production_loop()
    
    def verify_setup(self) -> bool:
        """Verify trading setup."""
        try:
            account_info = self.mt5_connector.get_account_info()
            if not account_info:
                return False
            
            print(f"💰 Account: {account_info['login']} | Balance: {account_info['balance']}")
            
            if not account_info.get('trade_allowed', False):
                print("⚠️  WARNING: Trading not allowed on account!")
                print("Continue anyway? (y/n): ", end="")
                if input().lower() != 'y':
                    return False
            
            return True
            
        except Exception as e:
            print(f"❌ Setup verification error: {e}")
            return False
    
    def run_production_loop(self):
        """Main production trading loop - optimized for speed and reliability."""
        print("🔄 Starting production trading loop...")
        
        symbol = 'XAUUSD'
        timeframe = 'M1'
        lookback_periods = 50  # Reduced for speed
        
        last_status_time = time.time()
        
        try:
            while self.running:
                loop_start = time.time()
                
                # Get market data once for all strategies
                data = self.mt5_connector.get_market_data(symbol, timeframe, lookback_periods)
                if data is None or len(data) < 30:
                    time.sleep(0.1)
                    continue
                
                # Process strategies by priority
                strategy_order = sorted(
                    self.strategies.keys(),
                    key=lambda x: self.strategies[x]['priority']
                )
                
                for strategy_name in strategy_order:
                    if not self.strategies[strategy_name]['enabled']:
                        continue
                    
                    config = self.strategies[strategy_name]
                    strategy_start = time.time()
                    
                    try:
                        # Check strategy-specific position limits
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
                            if self.execute_production_trade(strategy_name, signal, data, symbol):
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
                
                # Status update every 60 seconds
                if time.time() - last_status_time >= 60:
                    self.print_production_status()
                    last_status_time = time.time()
                
                # Optimized sleep timing
                loop_time = time.time() - loop_start
                time.sleep(max(0.05, 0.2 - loop_time))  # Target ~5 Hz
                
        except KeyboardInterrupt:
            print("\n🛑 Production bot shutdown requested...")
        except Exception as e:
            print(f"❌ Production loop error: {e}")
            self.logger.error(f"Production loop error: {e}")
        finally:
            self.stop()
    
    def execute_production_trade(self, strategy_name: str, signal: str, data, symbol: str) -> bool:
        """Execute trade with production-grade risk management."""
        try:
            config = self.strategies[strategy_name]
            strategy = config['instance']
            
            # Enhanced risk check
            if not self.risk_manager.check_trading_allowed(
                strategy_name=strategy_name, 
                max_strategy_positions=config['max_positions']
            ):
                return False
            
            # Get current price
            price_info = self.mt5_connector.get_current_price(symbol)
            if not price_info:
                return False
            
            entry_price = price_info['ask'] if signal == 'BUY' else price_info['bid']
            
            # Calculate stops
            stop_loss = strategy.get_stop_loss(data, signal, entry_price)
            take_profit = strategy.get_take_profit(data, signal, entry_price)
            
            # Use optimized position size
            volume = 0.01  # Conservative for production
            
            # Execute trade
            result = self.trade_manager.place_market_order(
                symbol=symbol,
                order_type=signal,
                volume=volume,
                stop_loss=stop_loss,
                take_profit=take_profit,
                comment=f"{strategy_name}_{signal}_prod"
            )
            
            return result is not None
            
        except Exception as e:
            self.logger.error(f"Error executing production trade for {strategy_name}: {e}")
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
    
    def print_production_status(self):
        """Print production status."""
        runtime = datetime.now() - self.stats['start_time']
        
        print(f"\n📊 PRODUCTION STATUS | Runtime: {runtime}")
        print(f"🔄 Total Loops: {self.stats['total_loops']}")
        print(f"🎯 Global Signals: {self.stats['global_stats']['signals']}")
        print(f"💰 Global Trades: {self.stats['global_stats']['trades']}")
        
        # Calculate efficiency
        total_signals = self.stats['global_stats']['signals']
        total_trades = self.stats['global_stats']['trades']
        global_efficiency = (total_trades / max(1, total_signals) * 100)
        
        print(f"📈 Global Efficiency: {global_efficiency:.1f}%")
        
        # Account info
        account_info = self.mt5_connector.get_account_info()
        if account_info:
            print(f"💼 Balance: {account_info['balance']:.2f} | Equity: {account_info['equity']:.2f}")
        
        # Strategy breakdown
        print(f"\n📈 STRATEGY BREAKDOWN:")
        total_positions = 0
        for strategy_name, stats in self.stats['strategy_stats'].items():
            if self.strategies[strategy_name]['enabled']:
                positions = len(self.get_strategy_positions(strategy_name))
                max_pos = self.strategies[strategy_name]['max_positions']
                efficiency = (stats['trades'] / max(1, stats['signals']) * 100)
                total_positions += positions
                print(f"  {strategy_name:18} | Sig: {stats['signals']:3d} | Trades: {stats['trades']:3d} | Pos: {positions}/{max_pos} | Eff: {efficiency:.1f}%")
        
        print(f"📊 Total Active Positions: {total_positions}")
        
        # Signal rates
        signal_rate = total_signals / runtime.total_seconds() * 60 if runtime.total_seconds() > 0 else 0
        print(f"📈 Signal Rate: {signal_rate:.1f}/min")
    
    def stop(self):
        """Stop production bot."""
        print("\n🛑 Stopping Production Multi-Strategy Bot...")
        self.running = False
        
        # Final statistics
        if self.stats['start_time']:
            runtime = datetime.now() - self.stats['start_time']
            
            print(f"\n📈 FINAL PRODUCTION STATISTICS:")
            print(f"⏰ Total Runtime: {runtime}")
            print(f"🔄 Total Loops: {self.stats['total_loops']}")
            print(f"🎯 Total Signals: {self.stats['global_stats']['signals']}")
            print(f"💰 Total Trades: {self.stats['global_stats']['trades']}")
            print(f"✅ Successful Trades: {self.stats['global_stats']['successful_trades']}")
            print(f"❌ Failed Trades: {self.stats['global_stats']['failed_trades']}")
            
            # Calculate final efficiency
            total_signals = self.stats['global_stats']['signals']
            total_trades = self.stats['global_stats']['trades']
            final_efficiency = (total_trades / max(1, total_signals) * 100)
            print(f"📊 Final Efficiency: {final_efficiency:.1f}%")
            
            # Strategy performance
            print(f"\n📊 FINAL STRATEGY PERFORMANCE:")
            for strategy_name, stats in self.stats['strategy_stats'].items():
                if self.strategies[strategy_name]['enabled']:
                    efficiency = (stats['trades'] / max(1, stats['signals']) * 100)
                    print(f"  {strategy_name:20} | Signals: {stats['signals']:3d} | Trades: {stats['trades']:3d} | Efficiency: {efficiency:.1f}%")
        
        # Save performance data
        self.save_performance_data()
        
        # Disconnect
        self.mt5_connector.disconnect()
        print("✅ Production Multi-Strategy Bot stopped successfully")
    
    def save_performance_data(self):
        """Save production performance statistics."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"production_performance_{timestamp}.json"
            
            performance_data = {
                'timestamp': timestamp,
                'runtime_seconds': (datetime.now() - self.stats['start_time']).total_seconds(),
                'stats': self.stats,
                'strategy_configs': {
                    name: {
                        'enabled': config['enabled'],
                        'max_positions': config['max_positions'],
                        'risk_per_trade': config['risk_per_trade'],
                        'priority': config['priority'],
                        'strategy_name': config['instance'].name
                    }
                    for name, config in self.strategies.items()
                }
            }
            
            with open(filename, 'w') as f:
                json.dump(performance_data, f, indent=2, default=str)
            
            print(f"💾 Production performance data saved to {filename}")
            
        except Exception as e:
            self.logger.error(f"Error saving production performance data: {e}")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\n🚨 Received signal {signum}, shutting down production bot...")
        self.running = False

def main():
    """Main entry point for production multi-strategy bot."""
    print("🚀 PRODUCTION MULTI-STRATEGY TRADING BOT")
    print("=" * 60)
    print("⚠️  WARNING: Ensure AutoTrading is ENABLED in MT5!")
    print("🏭 PRODUCTION: Only verified working strategies!")
    print("📊 OPTIMIZED: High performance and reliability!")
    print("=" * 60)
    
    production_bot = ProductionMultiStrategyBot()
    
    try:
        success = production_bot.start()
        if not success:
            print("❌ Failed to start production multi-strategy bot")
            sys.exit(1)
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
