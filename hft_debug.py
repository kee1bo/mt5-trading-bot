#!/usr/bin/env python3
"""
High-Frequency Trading Bot with detailed monitoring and faster execution.
"""

import time
import pandas as pd
import numpy as np
from datetime import datetime
import logging

from mt5_connector import MT5Connector
from trade_manager import TradeManager  
from risk_manager import RiskManager
from strategies.ema_crossover import EMACrossoverStrategy
from config import TRADING_SETTINGS, STRATEGY_SETTINGS, RISK_SETTINGS

# Setup enhanced logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_current_market_state():
    """Debug current market conditions to understand why no trades are happening."""
    logger.info("🔍 DEBUGGING CURRENT MARKET STATE")
    logger.info("=" * 60)
    
    connector = MT5Connector()
    if not connector.connect():
        logger.error("Failed to connect to MT5")
        return
    
    symbol = TRADING_SETTINGS['symbol']
    timeframe = TRADING_SETTINGS['timeframe']
    
    # Get current market data
    data = connector.get_market_data(symbol, timeframe, 200)
    if data is None:
        logger.error("Failed to get market data")
        return
    
    logger.info(f"📊 Market Data Retrieved: {len(data)} bars")
    logger.info(f"📅 Data Range: {data.index[0]} to {data.index[-1]}")
    
    # Get current price
    price_info = connector.get_current_price(symbol)
    if price_info:
        logger.info(f"💰 Current Price: Bid={price_info['bid']}, Ask={price_info['ask']}, Spread={price_info['spread']}")
    
    # Initialize strategy and test signal generation
    strategy = EMACrossoverStrategy(STRATEGY_SETTINGS.get('ema_crossover', {}))
    
    logger.info(f"🎯 Strategy: {strategy.name}")
    logger.info(f"📈 Strategy Parameters: {strategy.parameters}")
    logger.info(f"📏 Minimum Bars Required: {strategy.get_minimum_bars()}")
    
    # Calculate EMA manually to see what's happening
    ema_period = strategy.parameters['ema_period']
    data['ema'] = data['close'].ewm(span=ema_period).mean()
    
    # Show last few bars
    logger.info("\n📋 LAST 5 MARKET BARS:")
    last_bars = data[['open', 'high', 'low', 'close', 'ema']].tail(5)
    for time_idx, row in last_bars.iterrows():
        logger.info(f"  {time_idx}: O={row['open']:.2f} H={row['high']:.2f} L={row['low']:.2f} C={row['close']:.2f} EMA={row['ema']:.2f}")
    
    # Check signal generation
    signal = strategy.get_signal(data)
    logger.info(f"🚦 Current Signal: {signal}")
    
    # Check conditions manually
    last_candle = data.iloc[-1]
    previous_candle = data.iloc[-2]
    
    logger.info(f"\n🔬 SIGNAL ANALYSIS:")
    logger.info(f"  Previous: Close={previous_candle['close']:.2f}, EMA={previous_candle['ema']:.2f}")
    logger.info(f"  Current:  Close={last_candle['close']:.2f}, EMA={last_candle['ema']:.2f}")
    logger.info(f"  Price vs EMA: {last_candle['close'] - last_candle['ema']:.4f}")
    
    # Check ATR
    atr_period = strategy.parameters['atr_period']
    data['tr'] = np.maximum(
        data['high'] - data['low'],
        np.maximum(
            abs(data['high'] - data['close'].shift(1)),
            abs(data['low'] - data['close'].shift(1))
        )
    )
    data['atr'] = data['tr'].rolling(window=atr_period).mean()
    
    current_atr = data['atr'].iloc[-1]
    min_atr_filter = strategy.parameters['min_atr_filter']
    
    logger.info(f"  ATR: {current_atr:.6f} (Min required: {min_atr_filter:.6f})")
    logger.info(f"  ATR Filter: {'✅ PASS' if current_atr >= min_atr_filter else '❌ FAIL'}")
    
    # Check positions
    positions = connector.get_positions(symbol)
    logger.info(f"\n📊 Current Positions: {len(positions) if positions else 0}")
    
    if positions:
        for pos in positions:
            logger.info(f"  Position: {pos.get('type', 'Unknown')} {pos.get('volume', 0)} lots")
    
    # Check account info
    account_info = connector.get_account_info()
    if account_info:
        logger.info(f"\n💼 Account Info:")
        logger.info(f"  Balance: {account_info['balance']}")
        logger.info(f"  Equity: {account_info['equity']}")
        logger.info(f"  Free Margin: {account_info.get('free_margin', 'N/A')}")
        logger.info(f"  Trade Allowed: {account_info.get('trade_allowed', 'N/A')}")
    
    # Check symbol info
    symbol_info = connector.get_symbol_info(symbol)
    if symbol_info:
        logger.info(f"\n🏷️  Symbol Info:")
        logger.info(f"  Symbol: {symbol}")
        logger.info(f"  Trade Allowed: {symbol_info.get('trade_allowed', 'N/A')}")
        logger.info(f"  Min Volume: {symbol_info.get('volume_min', 'N/A')}")
        logger.info(f"  Max Volume: {symbol_info.get('volume_max', 'N/A')}")
        logger.info(f"  Volume Step: {symbol_info.get('volume_step', 'N/A')}")
    
    connector.disconnect()

def run_hft_mode():
    """Run the trading bot in high-frequency mode with detailed monitoring."""
    logger.info("🚀 STARTING HIGH-FREQUENCY TRADING MODE")
    logger.info("=" * 60)
    
    connector = MT5Connector()
    trade_manager = TradeManager(connector)
    risk_manager = RiskManager(connector, trade_manager)
    strategy = EMACrossoverStrategy(STRATEGY_SETTINGS.get('ema_crossover', {}))
    
    if not connector.connect():
        logger.error("Failed to connect to MT5")
        return
    
    symbol = TRADING_SETTINGS['symbol']
    timeframe = TRADING_SETTINGS['timeframe']
    
    # HFT Configuration
    update_interval = 0.05  # 50ms for high frequency
    signal_count = 0
    trade_count = 0
    loop_count = 0
    start_time = datetime.now()
    last_status_time = start_time
    
    logger.info(f"⚡ HFT Mode Configuration:")
    logger.info(f"  Update Interval: {update_interval*1000:.1f}ms")
    logger.info(f"  Symbol: {symbol}")
    logger.info(f"  Timeframe: {timeframe}")
    logger.info(f"  Strategy: {strategy.name}")
    
    try:
        while True:
            loop_start = time.time()
            loop_count += 1
            
            # Get market data
            data = connector.get_market_data(symbol, timeframe, 100)
            if data is None or len(data) < strategy.get_minimum_bars():
                time.sleep(update_interval)
                continue
            
            # Check for signals
            signal = strategy.get_signal(data)
            
            if signal:
                signal_count += 1
                logger.info(f"🚦 SIGNAL #{signal_count}: {signal} at {data['close'].iloc[-1]:.2f}")
                
                # Get current price
                price_info = connector.get_current_price(symbol)
                if not price_info:
                    logger.warning("Failed to get current price")
                    continue
                
                entry_price = price_info['ask'] if signal == 'BUY' else price_info['bid']
                
                # Calculate stop loss and take profit
                stop_loss = strategy.get_stop_loss(data, signal, entry_price)
                take_profit = strategy.get_take_profit(data, signal, entry_price)
                
                # Check if trading is allowed
                if not risk_manager.check_trading_allowed():
                    logger.warning("Trading not allowed by risk manager")
                    continue
                
                # Calculate position size
                volume = TRADING_SETTINGS['lot_size']
                if stop_loss:
                    calculated_volume = risk_manager.calculate_position_size(symbol, entry_price, stop_loss)
                    if calculated_volume:
                        volume = calculated_volume
                
                # Validate trade
                validation = risk_manager.validate_trade(
                    symbol, signal, volume, entry_price, stop_loss, take_profit
                )
                
                if not validation['valid']:
                    logger.warning(f"Trade validation failed: {validation['errors']}")
                    continue
                
                # Execute trade
                logger.info(f"💰 EXECUTING TRADE: {signal} {volume} lots at {entry_price:.2f}")
                result = trade_manager.place_market_order(
                    symbol=symbol,
                    order_type=signal,
                    volume=volume,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    comment=f"HFT-{strategy.name}-{signal}"
                )
                
                if result:
                    trade_count += 1
                    logger.info(f"✅ TRADE EXECUTED #{trade_count}: {result}")
                else:
                    logger.error("❌ TRADE EXECUTION FAILED")
            
            # Status update every 10 seconds
            now = datetime.now()
            if (now - last_status_time).total_seconds() >= 10:
                runtime = now - start_time
                freq = loop_count / runtime.total_seconds()
                
                account_info = connector.get_account_info()
                positions = connector.get_positions(symbol)
                
                logger.info(f"\n📊 STATUS UPDATE - Runtime: {runtime}")
                logger.info(f"  Loop Frequency: {freq:.1f} Hz")
                logger.info(f"  Loops: {loop_count}, Signals: {signal_count}, Trades: {trade_count}")
                if account_info:
                    logger.info(f"  Balance: {account_info['balance']:.2f}")
                    logger.info(f"  Positions: {len(positions) if positions else 0}")
                
                last_status_time = now
            
            # Calculate actual loop time and adjust sleep
            loop_time = time.time() - loop_start
            sleep_time = max(0, update_interval - loop_time)
            
            if sleep_time > 0:
                time.sleep(sleep_time)
            elif loop_count % 100 == 0:  # Log occasionally if running too fast
                logger.debug(f"Loop time: {loop_time*1000:.2f}ms (target: {update_interval*1000:.1f}ms)")
                
    except KeyboardInterrupt:
        logger.info("Stopping HFT mode...")
        runtime = datetime.now() - start_time
        avg_freq = loop_count / runtime.total_seconds()
        
        logger.info(f"\n📈 FINAL STATISTICS:")
        logger.info(f"  Runtime: {runtime}")
        logger.info(f"  Total Loops: {loop_count}")
        logger.info(f"  Average Frequency: {avg_freq:.1f} Hz")
        logger.info(f"  Signals Generated: {signal_count}")
        logger.info(f"  Trades Executed: {trade_count}")
        logger.info(f"  Signal Rate: {signal_count/runtime.total_seconds()*60:.1f} signals/minute")
    
    finally:
        connector.disconnect()

if __name__ == "__main__":
    print("🔍 Trading Bot Analysis & HFT Mode")
    print("=" * 50)
    
    # First debug why no trades are happening
    debug_current_market_state()
    
    print("\n" + "="*50)
    input("Press Enter to start HFT mode or Ctrl+C to exit...")
    
    # Then run in HFT mode
    run_hft_mode()
