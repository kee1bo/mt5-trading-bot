#!/usr/bin/env python3
"""
Strategy Testing and Validation Script

This script helps test and validate trading strategies without live trading.
It can be used for backtesting and strategy parameter optimization.
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategies.ema_crossover import EMACrossoverStrategy
from strategies.rsi_divergence import RSIDivergenceStrategy
from strategies.bollinger_scalp import BollingerScalpStrategy
from strategies.stochastic_momentum import StochasticMomentumStrategy
from strategies.macd_signal_cross import MACDSignalCrossStrategy

def generate_sample_data(periods=1000, symbol='EURUSD'):
    """Generate sample OHLCV data for testing."""
    
    # Set random seed for reproducible results
    np.random.seed(42)
    
    # Starting price
    start_price = 1.1000
    
    # Generate price movement
    returns = np.random.normal(0, 0.001, periods)  # Daily returns with volatility
    prices = [start_price]
    
    for i in range(periods - 1):
        new_price = prices[-1] * (1 + returns[i])
        prices.append(new_price)
    
    # Generate OHLC data
    data = []
    for i, close in enumerate(prices):
        # Generate realistic OHLC
        daily_range = abs(np.random.normal(0, 0.0005))  # Daily range
        
        high = close + (daily_range * np.random.uniform(0.3, 0.7))
        low = close - (daily_range * np.random.uniform(0.3, 0.7))
        
        # Ensure OHLC relationships are correct
        high = max(high, close)
        low = min(low, close)
        
        if i == 0:
            open_price = start_price
        else:
            open_price = prices[i-1] * (1 + np.random.normal(0, 0.0002))
        
        # Ensure open is within high-low range
        open_price = max(min(open_price, high), low)
        
        volume = np.random.randint(1000, 10000)
        
        data.append({
            'open': round(open_price, 5),
            'high': round(high, 5),
            'low': round(low, 5),
            'close': round(close, 5),
            'volume': volume
        })
    
    # Create DataFrame with datetime index
    df = pd.DataFrame(data)
    df.index = pd.date_range(start='2023-01-01', periods=periods, freq='5T')  # 5-minute intervals
    
    return df

def test_strategy(strategy, data, strategy_name):
    """Test a strategy on sample data."""
    
    print(f"\n{'='*60}")
    print(f"Testing Strategy: {strategy_name}")
    print(f"{'='*60}")
    
    # Get strategy info
    info = strategy.get_strategy_info()
    print(f"Strategy Type: {info.get('strategy_type', 'Unknown')}")
    print(f"Market Condition: {info.get('market_condition', 'Unknown')}")
    print(f"Risk Level: {info.get('risk_level', 'Unknown')}")
    print(f"Description: {info.get('description', 'No description')}")
    print(f"Minimum Bars Required: {strategy.get_minimum_bars()}")
    
    # Test signal generation
    signals_generated = 0
    buy_signals = 0
    sell_signals = 0
    
    # Test on sliding windows
    min_bars = strategy.get_minimum_bars()
    test_points = min(50, len(data) - min_bars)  # Test last 50 points or available
    
    print(f"\nTesting signal generation on {test_points} data points...")
    
    for i in range(test_points):
        window_end = len(data) - test_points + i + 1
        window_start = max(0, window_end - min_bars - 20)  # Extra data for better analysis
        
        test_data = data.iloc[window_start:window_end].copy()
        
        if len(test_data) < min_bars:
            continue
        
        try:
            signal = strategy.get_signal(test_data)
            
            if signal:
                signals_generated += 1
                
                if signal == 'BUY':
                    buy_signals += 1
                elif signal == 'SELL':
                    sell_signals += 1
                
                # Test stop loss and take profit calculation
                current_price = test_data['close'].iloc[-1]
                
                sl = strategy.get_stop_loss(test_data, signal, current_price)
                tp = strategy.get_take_profit(test_data, signal, current_price)
                
                print(f"Signal {signals_generated}: {signal} at {current_price:.5f}")
                if sl:
                    print(f"  Stop Loss: {sl:.5f} ({abs(current_price - sl)/current_price*100:.2f}% risk)")
                if tp:
                    print(f"  Take Profit: {tp:.5f} ({abs(tp - current_price)/current_price*100:.2f}% reward)")
                
                # Test exit signal
                position = {
                    'type': signal,
                    'ticket': i,
                    'price_open': current_price,
                    'sl': sl,
                    'tp': tp
                }
                
                should_exit = strategy.should_exit(test_data, position)
                if should_exit:
                    print(f"  Exit signal detected")
                
        except Exception as e:
            print(f"Error testing signal at point {i}: {e}")
    
    # Print results
    print(f"\n{'-'*40}")
    print("TESTING RESULTS:")
    print(f"{'-'*40}")
    print(f"Total Signals Generated: {signals_generated}")
    print(f"BUY Signals: {buy_signals}")
    print(f"SELL Signals: {sell_signals}")
    
    if signals_generated > 0:
        print(f"Signal Frequency: {signals_generated/test_points*100:.1f}% of test points")
        print(f"BUY/SELL Ratio: {buy_signals}:{sell_signals}")
    else:
        print("No signals generated - consider adjusting strategy parameters")
    
    return {
        'strategy_name': strategy_name,
        'total_signals': signals_generated,
        'buy_signals': buy_signals,
        'sell_signals': sell_signals,
        'signal_frequency': signals_generated/test_points if test_points > 0 else 0
    }

def main():
    """Main testing function."""
    
    # Setup logging
    logging.basicConfig(level=logging.WARNING)  # Reduce log noise during testing
    
    print("MetaTrader 5 Trading Bot - Strategy Testing")
    print("=" * 60)
    
    # Generate sample data
    print("Generating sample market data...")
    data = generate_sample_data(periods=500)  # 500 5-minute candles
    
    print(f"Generated {len(data)} data points")
    print(f"Date range: {data.index[0]} to {data.index[-1]}")
    print(f"Price range: {data['low'].min():.5f} to {data['high'].max():.5f}")
    
    # Initialize strategies with default parameters
    strategies = [
        (EMACrossoverStrategy(), "EMA Crossover"),
        (RSIDivergenceStrategy(), "RSI Divergence"),
        (BollingerScalpStrategy(), "Bollinger Squeeze"),
        (StochasticMomentumStrategy(), "Stochastic Momentum"),
        (MACDSignalCrossStrategy(), "MACD Signal Cross"),
    ]
    
    # Test all strategies
    results = []
    
    for strategy, name in strategies:
        try:
            result = test_strategy(strategy, data, name)
            results.append(result)
        except Exception as e:
            print(f"Error testing {name}: {e}")
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY OF ALL STRATEGIES")
    print(f"{'='*60}")
    
    for result in results:
        print(f"{result['strategy_name']:<25} | "
              f"Signals: {result['total_signals']:<3} | "
              f"Frequency: {result['signal_frequency']*100:>5.1f}% | "
              f"B/S: {result['buy_signals']}/{result['sell_signals']}")
    
    print(f"\n{'='*60}")
    print("Testing completed successfully!")
    print("Note: This is synthetic data testing only.")
    print("Always test with real historical data and demo accounts before live trading.")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
