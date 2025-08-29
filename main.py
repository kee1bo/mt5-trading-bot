import logging
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import signal
import sys

from mt5_connector import MT5Connector
from trade_manager import TradeManager
from risk_manager import RiskManager
from config import (
    TRADING_SETTINGS, STRATEGY_SETTINGS, TIME_SETTINGS, 
    LOGGING_SETTINGS, PERFORMANCE_SETTINGS
)

# Import strategies
from strategies.ema_crossover import EMACrossoverStrategy
from strategies.rsi_divergence import RSIDivergenceStrategy
from strategies.bollinger_scalp import BollingerScalpStrategy
from strategies.stochastic_momentum import StochasticMomentumStrategy
from strategies.macd_signal_cross import MACDSignalCrossStrategy

class TradingBot:
    """Main trading bot orchestrator."""
    
    def __init__(self):
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.mt5_connector = MT5Connector()
        self.trade_manager = TradeManager(self.mt5_connector)
        self.risk_manager = RiskManager(self.mt5_connector, self.trade_manager)
        
        # Initialize strategy
        self.strategy = None
        self.load_strategy()
        
        # Bot state
        self.running = False
        self.last_signal_time = None
        self.performance_stats = {
            'trades_opened': 0,
            'trades_closed': 0,
            'total_profit': 0.0,
            'start_time': None,
        }
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=getattr(logging, LOGGING_SETTINGS['log_level']),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(LOGGING_SETTINGS['log_file']),
                logging.StreamHandler()
            ]
        )
    
    def load_strategy(self):
        """Load the active trading strategy."""
        strategy_name = STRATEGY_SETTINGS['active_strategy']
        strategy_params = STRATEGY_SETTINGS.get(strategy_name, {})
        
        strategy_map = {
            'ema_crossover': EMACrossoverStrategy,
            'rsi_divergence': RSIDivergenceStrategy,
            'bollinger_scalp': BollingerScalpStrategy,
            'stochastic_momentum': StochasticMomentumStrategy,
            'macd_signal_cross': MACDSignalCrossStrategy,
        }
        
        if strategy_name not in strategy_map:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        
        self.strategy = strategy_map[strategy_name](strategy_params)
        self.logger.info(f"Loaded strategy: {self.strategy.name}")
    
    def start(self):
        """Start the trading bot."""
        self.logger.info("Starting trading bot...")
        
        # Connect to MT5
        if not self.mt5_connector.connect():
            self.logger.error("Failed to connect to MT5")
            return False
        
        # Verify account and symbol info
        if not self.verify_setup():
            self.logger.error("Setup verification failed")
            return False
        
        self.running = True
        self.performance_stats['start_time'] = datetime.now()
        
        self.logger.info("Trading bot started successfully")
        self.run_main_loop()
        
        return True
    
    def stop(self):
        """Stop the trading bot."""
        self.logger.info("Stopping trading bot...")
        self.running = False
        
        # Disconnect from MT5
        self.mt5_connector.disconnect()
        
        # Print performance stats
        self.print_performance_stats()
        
        self.logger.info("Trading bot stopped")
    
    def verify_setup(self) -> bool:
        """Verify trading setup."""
        try:
            # Check account info
            account_info = self.mt5_connector.get_account_info()
            if not account_info:
                return False
            
            self.logger.info(f"Account: {account_info['login']}, "
                           f"Balance: {account_info['balance']} {account_info['currency']}")
            
            # Check symbol info
            symbol = TRADING_SETTINGS['symbol']
            symbol_info = self.mt5_connector.get_symbol_info(symbol)
            if not symbol_info:
                return False
            
            self.logger.info(f"Symbol: {symbol}, Spread: {symbol_info['spread']} points")
            
            # Check trading permissions
            if not account_info.get('trade_allowed', False):
                self.logger.error("Trading not allowed on this account")
                return False
            
            if not symbol_info.get('trade_allowed', False):
                self.logger.error(f"Trading not allowed for symbol: {symbol}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error verifying setup: {e}")
            return False
    
    def run_main_loop(self):
        """Main trading loop."""
        self.logger.info("Starting main trading loop...")
        
        update_interval = STRATEGY_SETTINGS['update_interval']
        
        while self.running:
            try:
                # Check if trading is allowed at this time
                if not self.is_trading_time():
                    time.sleep(60)  # Check again in 1 minute
                    continue
                
                # Get market data
                market_data = self.get_market_data()
                if market_data is None or len(market_data) < self.strategy.get_minimum_bars():
                    self.logger.warning("Insufficient market data")
                    time.sleep(update_interval)
                    continue
                
                # Update trailing stops
                self.risk_manager.update_trailing_stops()
                
                # Check for exit signals on existing positions
                self.check_exit_signals(market_data)
                
                # Check for new entry signals
                self.check_entry_signals(market_data)
                
                # Log current status periodically
                self.log_status()
                
                time.sleep(update_interval)
                
            except KeyboardInterrupt:
                self.logger.info("Received keyboard interrupt")
                break
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                time.sleep(update_interval)
        
        self.stop()
    
    def get_market_data(self) -> Optional[pd.DataFrame]:
        """Get market data for analysis."""
        try:
            symbol = TRADING_SETTINGS['symbol']
            timeframe = TRADING_SETTINGS['timeframe']
            lookback_periods = STRATEGY_SETTINGS['lookback_periods']
            
            data = self.mt5_connector.get_market_data(symbol, timeframe, lookback_periods)
            
            if data is None or len(data) == 0:
                self.logger.warning(f"No market data received for {symbol}")
                return None
            
            return data
            
        except Exception as e:
            self.logger.error(f"Error getting market data: {e}")
            return None
    
    def check_entry_signals(self, data: pd.DataFrame):
        """Check for new entry signals."""
        try:
            # Check if trading is allowed
            if not self.risk_manager.check_trading_allowed():
                return
            
            # Get signal from strategy
            signal = self.strategy.get_signal(data)
            if not signal:
                return
            
            self.logger.info(f"Signal detected: {signal}")
            
            # Get current price for entry
            symbol = TRADING_SETTINGS['symbol']
            price_info = self.mt5_connector.get_current_price(symbol)
            if not price_info:
                self.logger.error("Failed to get current price")
                return
            
            entry_price = price_info['ask'] if signal == 'BUY' else price_info['bid']
            
            # Calculate stop loss and take profit
            stop_loss = self.strategy.get_stop_loss(data, signal, entry_price)
            take_profit = self.strategy.get_take_profit(data, signal, entry_price)
            
            # Calculate position size
            if stop_loss:
                volume = self.risk_manager.calculate_position_size(symbol, entry_price, stop_loss)
            else:
                volume = TRADING_SETTINGS['lot_size']
            
            # Validate trade
            validation = self.risk_manager.validate_trade(
                symbol, signal, volume, entry_price, stop_loss, take_profit
            )
            
            if not validation['valid']:
                self.logger.warning(f"Trade validation failed: {validation['errors']}")
                return
            
            # Use adjusted volume if necessary
            volume = validation['adjusted_volume']
            
            # Execute trade
            result = self.trade_manager.place_market_order(
                symbol=symbol,
                order_type=signal,
                volume=volume,
                stop_loss=stop_loss,
                take_profit=take_profit,
                comment=f"{self.strategy.name} - {signal}"
            )
            
            if result:
                self.logger.info(f"Trade executed: {result}")
                self.performance_stats['trades_opened'] += 1
                self.strategy.update_signal_history(signal)
                self.last_signal_time = datetime.now()
                
                # Save trade to file if enabled
                if PERFORMANCE_SETTINGS['save_trades_to_file']:
                    self.save_trade_to_file(result)
            else:
                self.logger.error("Failed to execute trade")
                
        except Exception as e:
            self.logger.error(f"Error checking entry signals: {e}")
    
    def check_exit_signals(self, data: pd.DataFrame):
        """Check for exit signals on existing positions."""
        try:
            symbol = TRADING_SETTINGS['symbol']
            positions = self.mt5_connector.get_positions(symbol)
            
            if not positions:
                return
            
            for position in positions:
                should_exit = self.strategy.should_exit(data, position)
                
                if should_exit:
                    result = self.trade_manager.close_position(position['ticket'])
                    if result:
                        self.logger.info(f"Position closed: {result}")
                        self.performance_stats['trades_closed'] += 1
                        
        except Exception as e:
            self.logger.error(f"Error checking exit signals: {e}")
    
    def is_trading_time(self) -> bool:
        """Check if current time is within trading hours."""
        try:
            now = datetime.now()
            
            # Check trading days
            if now.weekday() not in TIME_SETTINGS['trading_days']:
                return False
            
            # Check trading hours
            start_hour = TIME_SETTINGS['trading_start_hour']
            end_hour = TIME_SETTINGS['trading_end_hour']
            
            current_hour = now.hour
            
            return start_hour <= current_hour <= end_hour
            
        except Exception as e:
            self.logger.error(f"Error checking trading time: {e}")
            return False
    
    def log_status(self):
        """Log current bot status."""
        try:
            # Log every 10 minutes
            if (self.last_signal_time is None or 
                (datetime.now() - self.last_signal_time).seconds > 600):
                
                account_info = self.mt5_connector.get_account_info()
                positions = self.mt5_connector.get_positions()
                risk_metrics = self.risk_manager.get_risk_metrics()
                
                if account_info:
                    self.logger.info(
                        f"Status - Balance: {account_info['balance']:.2f}, "
                        f"Equity: {account_info['equity']:.2f}, "
                        f"Positions: {len(positions or [])}, "
                        f"Free Margin: {account_info.get('free_margin', 0):.2f}"
                    )
                
        except Exception as e:
            self.logger.error(f"Error logging status: {e}")
    
    def save_trade_to_file(self, trade_result: Dict[str, Any]):
        """Save trade result to CSV file."""
        try:
            trades_file = PERFORMANCE_SETTINGS['trades_file']
            
            # Create DataFrame with trade data
            trade_data = {
                'timestamp': trade_result['time'],
                'symbol': trade_result['symbol'],
                'type': trade_result['type'],
                'volume': trade_result['volume'],
                'price': trade_result['price'],
                'sl': trade_result.get('sl', ''),
                'tp': trade_result.get('tp', ''),
                'strategy': self.strategy.name,
                'comment': trade_result.get('comment', ''),
            }
            
            df = pd.DataFrame([trade_data])
            
            # Append to file
            try:
                df.to_csv(trades_file, mode='a', header=False, index=False)
            except FileNotFoundError:
                df.to_csv(trades_file, mode='w', header=True, index=False)
                
        except Exception as e:
            self.logger.error(f"Error saving trade to file: {e}")
    
    def print_performance_stats(self):
        """Print performance statistics."""
        try:
            if self.performance_stats['start_time']:
                runtime = datetime.now() - self.performance_stats['start_time']
                
                self.logger.info("=== Performance Statistics ===")
                self.logger.info(f"Runtime: {runtime}")
                self.logger.info(f"Trades Opened: {self.performance_stats['trades_opened']}")
                self.logger.info(f"Trades Closed: {self.performance_stats['trades_closed']}")
                self.logger.info(f"Strategy Used: {self.strategy.name}")
                
                # Get final account info
                account_info = self.mt5_connector.get_account_info()
                if account_info:
                    self.logger.info(f"Final Balance: {account_info['balance']}")
                    self.logger.info(f"Final Equity: {account_info['equity']}")
                
        except Exception as e:
            self.logger.error(f"Error printing performance stats: {e}")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

def main():
    """Main entry point."""
    print("Starting MetaTrader 5 Trading Bot...")
    print("=" * 50)
    
    bot = TradingBot()
    
    try:
        success = bot.start()
        if not success:
            print("Failed to start trading bot")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
    except Exception as e:
        print(f"Fatal error: {e}")
        logging.getLogger(__name__).error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
