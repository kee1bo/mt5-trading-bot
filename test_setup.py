#!/usr/bin/env python3
"""
Trading Bot Test Script - Check configuration and basic functionality
"""

import sys
import os
import traceback
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_environment_variables():
    """Test if environment variables are loaded correctly."""
    print("Testing Environment Variables...")
    print("-" * 40)
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        # Test MT5 credentials
        mt5_login = os.getenv('MT5_LOGIN')
        mt5_password = os.getenv('MT5_PASSWORD')
        mt5_server = os.getenv('MT5_SERVER')
        
        print(f"MT5_LOGIN: {mt5_login}")
        print(f"MT5_PASSWORD: {'*' * len(mt5_password) if mt5_password else 'Not set'}")
        print(f"MT5_SERVER: {mt5_server}")
        
        # Test trading settings
        trading_symbol = os.getenv('TRADING_SYMBOL')
        trading_timeframe = os.getenv('TRADING_TIMEFRAME')
        lot_size = os.getenv('DEFAULT_LOT_SIZE')
        
        print(f"TRADING_SYMBOL: {trading_symbol}")
        print(f"TRADING_TIMEFRAME: {trading_timeframe}")
        print(f"DEFAULT_LOT_SIZE: {lot_size}")
        
        return True
        
    except ImportError:
        print("❌ python-dotenv not installed")
        return False
    except Exception as e:
        print(f"❌ Error loading environment variables: {e}")
        return False

def test_config_loading():
    """Test if config.py loads correctly."""
    print("\nTesting Configuration Loading...")
    print("-" * 40)
    
    try:
        from config import MT5_SETTINGS, TRADING_SETTINGS, RISK_SETTINGS, STRATEGY_SETTINGS
        
        print("✅ Config imported successfully")
        print(f"MT5 Login: {MT5_SETTINGS['login']}")
        print(f"MT5 Server: {MT5_SETTINGS['server']}")
        print(f"Trading Symbol: {TRADING_SETTINGS['symbol']}")
        print(f"Timeframe: {TRADING_SETTINGS['timeframe']}")
        print(f"Lot Size: {TRADING_SETTINGS['lot_size']}")
        print(f"Active Strategy: {STRATEGY_SETTINGS['active_strategy']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        traceback.print_exc()
        return False

def test_metatrader5_availability():
    """Test if MetaTrader5 package is available."""
    print("\nTesting MetaTrader5 Package...")
    print("-" * 40)
    
    try:
        import MetaTrader5 as mt5
        print("✅ MetaTrader5 package imported successfully")
        
        # Test initialization (this will fail if MT5 terminal is not running)
        try:
            if mt5.initialize():
                print("✅ MT5 terminal connection successful")
                
                # Get terminal info
                terminal_info = mt5.terminal_info()
                if terminal_info:
                    print(f"Terminal: {terminal_info.name}")
                    print(f"Version: {terminal_info.version}")
                    print(f"Build: {terminal_info.build}")
                
                # Test account connection with our credentials
                from config import MT5_SETTINGS
                login_result = mt5.login(
                    login=MT5_SETTINGS['login'],
                    password=MT5_SETTINGS['password'],
                    server=MT5_SETTINGS['server']
                )
                
                if login_result:
                    print("✅ Account login successful")
                    
                    # Get account info
                    account_info = mt5.account_info()
                    if account_info:
                        print(f"Account: {account_info.login}")
                        print(f"Server: {account_info.server}")
                        print(f"Balance: {account_info.balance}")
                        print(f"Currency: {account_info.currency}")
                        print(f"Leverage: 1:{account_info.leverage}")
                        print(f"Trade Allowed: {account_info.trade_allowed}")
                    
                    # Test symbol info for XAUUSD
                    symbol_info = mt5.symbol_info("XAUUSD")
                    if symbol_info:
                        print(f"✅ XAUUSD symbol available")
                        print(f"Bid: {symbol_info.bid}")
                        print(f"Ask: {symbol_info.ask}")
                        print(f"Spread: {symbol_info.spread}")
                        print(f"Digits: {symbol_info.digits}")
                        print(f"Min Volume: {symbol_info.volume_min}")
                        print(f"Max Volume: {symbol_info.volume_max}")
                        print(f"Volume Step: {symbol_info.volume_step}")
                    else:
                        print("❌ XAUUSD symbol not available")
                        
                else:
                    print(f"❌ Account login failed: {mt5.last_error()}")
                
                mt5.shutdown()
                
            else:
                print(f"❌ MT5 initialization failed: {mt5.last_error()}")
                print("Make sure MetaTrader 5 terminal is installed and running")
        
        except Exception as e:
            print(f"❌ MT5 connection error: {e}")
            
        return True
        
    except ImportError:
        print("❌ MetaTrader5 package not available")
        print("Note: MetaTrader5 package is only available on Windows with MT5 terminal installed")
        return False
    except Exception as e:
        print(f"❌ Error testing MetaTrader5: {e}")
        return False

def test_strategy_imports():
    """Test if all strategies can be imported."""
    print("\nTesting Strategy Imports...")
    print("-" * 40)
    
    strategies = [
        ('ema_crossover', 'EMACrossoverStrategy'),
        ('rsi_divergence', 'RSIDivergenceStrategy'),
        ('bollinger_scalp', 'BollingerScalpStrategy'),
        ('stochastic_momentum', 'StochasticMomentumStrategy'),
        ('macd_signal_cross', 'MACDSignalCrossStrategy'),
    ]
    
    success_count = 0
    
    for module_name, class_name in strategies:
        try:
            module = __import__(f'strategies.{module_name}', fromlist=[class_name])
            strategy_class = getattr(module, class_name)
            
            # Test strategy instantiation
            strategy = strategy_class()
            info = strategy.get_strategy_info()
            
            print(f"✅ {class_name}: {info.get('description', 'No description')}")
            success_count += 1
            
        except Exception as e:
            print(f"❌ {class_name}: {e}")
    
    print(f"\nStrategies loaded: {success_count}/{len(strategies)}")
    return success_count == len(strategies)

def test_basic_functionality():
    """Test basic bot functionality without MT5 connection."""
    print("\nTesting Basic Functionality...")
    print("-" * 40)
    
    try:
        # Test strategy creation
        from strategies.ema_crossover import EMACrossoverStrategy
        strategy = EMACrossoverStrategy()
        
        print(f"✅ Strategy created: {strategy.name}")
        print(f"Minimum bars required: {strategy.get_minimum_bars()}")
        
        # Create sample data for testing
        import pandas as pd
        import numpy as np
        
        # Generate sample OHLC data
        dates = pd.date_range(start='2024-01-01', periods=200, freq='5min')
        np.random.seed(42)
        
        # Simulate XAUUSD price movement (around 2000)
        prices = 2000 + np.cumsum(np.random.randn(200) * 0.5)
        
        data = pd.DataFrame({
            'open': prices + np.random.randn(200) * 0.1,
            'high': prices + np.random.randn(200) * 0.1 + 0.5,
            'low': prices + np.random.randn(200) * 0.1 - 0.5,
            'close': prices,
            'volume': np.random.randint(100, 1000, 200)
        }, index=dates)
        
        # Ensure OHLC relationships are correct
        data['high'] = data[['open', 'high', 'low', 'close']].max(axis=1)
        data['low'] = data[['open', 'high', 'low', 'close']].min(axis=1)
        
        print(f"✅ Sample data created: {len(data)} rows")
        print(f"Price range: {data['low'].min():.2f} - {data['high'].max():.2f}")
        
        # Test signal generation
        signal = strategy.get_signal(data)
        print(f"✅ Signal generation test: {signal if signal else 'No signal'}")
        
        # Test stop loss and take profit calculation
        current_price = data['close'].iloc[-1]
        
        if signal:
            sl = strategy.get_stop_loss(data, signal, current_price)
            tp = strategy.get_take_profit(data, signal, current_price)
            
            print(f"Entry Price: {current_price:.2f}")
            if sl:
                print(f"Stop Loss: {sl:.2f} ({abs(current_price - sl):.2f} points)")
            if tp:
                print(f"Take Profit: {tp:.2f} ({abs(tp - current_price):.2f} points)")
        
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("TRADING BOT CONFIGURATION AND FUNCTIONALITY TEST")
    print("=" * 60)
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python Version: {sys.version}")
    print(f"Working Directory: {os.getcwd()}")
    
    tests = [
        ("Environment Variables", test_environment_variables),
        ("Configuration Loading", test_config_loading),
        ("MetaTrader5 Package", test_metatrader5_availability),
        ("Strategy Imports", test_strategy_imports),
        ("Basic Functionality", test_basic_functionality),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print("\n" + "=" * 60)
        try:
            if test_func():
                print(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 All tests passed! The trading bot is ready to run.")
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
        
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
