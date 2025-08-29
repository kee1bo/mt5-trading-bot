#!/usr/bin/env python3
"""
Speed test for the trading bot components to measure execution frequency.
"""

import time
import pandas as pd
import numpy as np
from datetime import datetime
import logging

from mt5_connector import MT5Connector
from strategies.ema_crossover import EMACrossoverStrategy
from config import TRADING_SETTINGS, STRATEGY_SETTINGS

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_data_retrieval_speed():
    """Test how fast we can retrieve market data."""
    logger.info("Testing data retrieval speed...")
    
    connector = MT5Connector()
    if not connector.connect():
        logger.error("Failed to connect to MT5")
        return
    
    symbol = TRADING_SETTINGS['symbol']
    timeframe = TRADING_SETTINGS['timeframe']
    lookback_periods = 50  # Smaller dataset for speed
    
    # Test multiple data retrievals
    times = []
    for i in range(10):
        start_time = time.time()
        data = connector.get_market_data(symbol, timeframe, lookback_periods)
        end_time = time.time()
        
        if data is not None:
            times.append(end_time - start_time)
            logger.info(f"Data retrieval {i+1}: {(end_time - start_time)*1000:.2f}ms, {len(data)} bars")
        else:
            logger.error(f"Failed to retrieve data on attempt {i+1}")
    
    if times:
        avg_time = sum(times) / len(times)
        logger.info(f"Average data retrieval time: {avg_time*1000:.2f}ms")
        logger.info(f"Potential frequency: {1/avg_time:.2f} times per second")
    
    connector.disconnect()

def test_strategy_speed():
    """Test how fast the strategy can generate signals."""
    logger.info("Testing strategy execution speed...")
    
    # Create sample data
    dates = pd.date_range(start='2025-01-01', periods=200, freq='5min')
    np_random = np.random.RandomState(42)  # For reproducible results
    
    # Generate realistic OHLC data
    base_price = 2000.0
    data = []
    current_price = base_price
    
    for i in range(200):
        # Random walk with some trend
        change = np_random.normal(0, 1.0)
        current_price += change
        
        high = current_price + abs(np_random.normal(0, 0.5))
        low = current_price - abs(np_random.normal(0, 0.5))
        close = current_price + np_random.normal(0, 0.2)
        
        data.append({
            'time': dates[i],
            'open': current_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': np_random.randint(100, 1000)
        })
        current_price = close
    
    df = pd.DataFrame(data)
    
    # Test strategy
    strategy = EMACrossoverStrategy(STRATEGY_SETTINGS.get('ema_crossover', {}))
    
    # Test multiple signal generations
    times = []
    signals_generated = 0
    
    for i in range(100):
        start_time = time.time()
        signal = strategy.get_signal(df)
        end_time = time.time()
        
        times.append(end_time - start_time)
        if signal:
            signals_generated += 1
            logger.info(f"Signal generated: {signal}")
    
    avg_time = sum(times) / len(times)
    logger.info(f"Average strategy execution time: {avg_time*1000:.2f}ms")
    logger.info(f"Potential frequency: {1/avg_time:.2f} times per second")
    logger.info(f"Signals generated in test: {signals_generated}/100")

def test_full_loop_speed():
    """Test the full trading loop speed."""
    logger.info("Testing full trading loop speed...")
    
    connector = MT5Connector()
    if not connector.connect():
        logger.error("Failed to connect to MT5")
        return
    
    strategy = EMACrossoverStrategy(STRATEGY_SETTINGS.get('ema_crossover', {}))
    symbol = TRADING_SETTINGS['symbol']
    timeframe = TRADING_SETTINGS['timeframe']
    lookback_periods = 50
    
    # Test full loop cycles
    times = []
    for i in range(20):
        start_time = time.time()
        
        # Get market data
        data = connector.get_market_data(symbol, timeframe, lookback_periods)
        
        if data is not None and len(data) >= strategy.get_minimum_bars():
            # Generate signal
            signal = strategy.get_signal(data)
            
            # Get current price (simulating what the bot does)
            price_info = connector.get_current_price(symbol)
            
            # Check positions
            positions = connector.get_positions(symbol)
            
        end_time = time.time()
        cycle_time = end_time - start_time
        times.append(cycle_time)
        
        logger.info(f"Full cycle {i+1}: {cycle_time*1000:.2f}ms")
        
        # Small delay to avoid hammering the server
        time.sleep(0.1)
    
    if times:
        avg_time = sum(times) / len(times)
        logger.info(f"Average full cycle time: {avg_time*1000:.2f}ms")
        logger.info(f"Potential frequency: {1/avg_time:.2f} cycles per second")
        
        # Calculate theoretical max frequency with current update_interval
        update_interval = STRATEGY_SETTINGS['update_interval']
        theoretical_freq = 1 / update_interval
        actual_max_freq = 1 / avg_time
        
        logger.info(f"Current update interval: {update_interval}s ({theoretical_freq} Hz)")
        logger.info(f"Actual max frequency: {actual_max_freq:.2f} Hz")
        
        if actual_max_freq > theoretical_freq:
            logger.info("✅ System can handle faster updates!")
            recommended_interval = avg_time * 1.5  # Add 50% safety margin
            logger.info(f"Recommended update interval: {recommended_interval:.3f}s")
        else:
            logger.warning("⚠️ Current update interval may be too fast!")
    
    connector.disconnect()

def analyze_current_config():
    """Analyze current configuration for HFT suitability."""
    logger.info("Analyzing current configuration...")
    
    update_interval = STRATEGY_SETTINGS['update_interval']
    symbol = TRADING_SETTINGS['symbol']
    timeframe = TRADING_SETTINGS['timeframe']
    
    logger.info(f"Current Settings:")
    logger.info(f"  Symbol: {symbol}")
    logger.info(f"  Timeframe: {timeframe}")
    logger.info(f"  Update Interval: {update_interval}s")
    logger.info(f"  Strategy: {STRATEGY_SETTINGS['active_strategy']}")
    
    # HFT recommendations
    logger.info("\nHFT Recommendations:")
    logger.info("  ✅ Timeframe: M1 or Tick data for true HFT")
    logger.info("  ✅ Update Interval: < 0.1s for HFT (currently: {}s)".format(update_interval))
    logger.info("  ✅ Strategy: Simple, fast-executing strategies")
    logger.info("  ✅ Symbol: High-volume, low-spread instruments")

if __name__ == "__main__":
    print("🚀 Trading Bot Speed Analysis")
    print("=" * 50)
    
    analyze_current_config()
    print()
    
    test_data_retrieval_speed()
    print()
    
    test_strategy_speed()
    print()
    
    test_full_loop_speed()
    print()
    
    print("Speed analysis complete!")
