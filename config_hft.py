# High-Frequency Trading Configuration
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# MetaTrader 5 Settings
MT5_SETTINGS = {
    'login': int(os.getenv('MT5_LOGIN', '5039643367')),
    'password': os.getenv('MT5_PASSWORD', 'W-Z8AySp'),
    'server': os.getenv('MT5_SERVER', 'MetaQuotes-Demo'),
    'path': os.getenv('MT5_PATH', ''),
    'timeout': 60000,
}

# High-Frequency Trading Settings
TRADING_SETTINGS = {
    'symbol': os.getenv('TRADING_SYMBOL', 'XAUUSD'),
    'timeframe': os.getenv('TRADING_TIMEFRAME', 'M1'),  # 1-minute for HFT
    'lot_size': float(os.getenv('DEFAULT_LOT_SIZE', '0.01')),
    'max_positions': 3,  # Reduced for HFT
    'slippage': 1,  # Tighter slippage for HFT
}

# Aggressive Risk Management for HFT
RISK_SETTINGS = {
    'risk_per_trade': 0.005,  # 0.5% per trade for higher frequency
    'max_daily_loss': 0.03,  # 3% daily loss limit
    'max_drawdown': 0.05,  # 5% max drawdown
    'stop_loss_pips': 2,  # Tight stops for HFT
    'take_profit_pips': 4,  # Quick profits
    'trailing_stop': True,
    'trailing_stop_distance': 1,  # Very tight trailing
}

# Optimized Strategy Settings for HFT
STRATEGY_SETTINGS = {
    'active_strategy': 'ema_crossover',
    'update_interval': 0.05,  # 50ms for true HFT
    'lookback_periods': 100,  # Reduced for speed
    
    # Ultra-fast EMA strategy
    'ema_crossover': {
        'ema_period': 3,  # Very fast EMA
        'confirmation_candles': 0,  # No confirmation for speed
        'atr_period': 10,  # Faster ATR
        'stop_loss_atr_multiplier': 1.0,  # Tighter stops
        'take_profit_atr_multiplier': 1.5,  # Quick profits
        'min_atr_filter': 0.00001,  # Very low filter for more signals
        'signal_cooldown': 0,  # No cooldown for HFT
    },
    
    # Alternative HFT strategies
    'scalp_momentum': {
        'rsi_period': 7,
        'rsi_oversold': 25,
        'rsi_overbought': 75,
        'momentum_threshold': 0.5,
    },
    
    'micro_breakout': {
        'bollinger_period': 10,
        'bollinger_std': 1.5,
        'volume_threshold': 1.2,
    }
}

# HFT-Optimized Logging
LOGGING_SETTINGS = {
    'log_level': 'WARNING',  # Reduced logging for speed
    'log_file': 'hft_trading_bot.log',
    'max_log_size': 5 * 1024 * 1024,  # 5 MB
    'backup_count': 3,
}

# 24/7 Trading for HFT
TIME_SETTINGS = {
    'trading_start_hour': 0,
    'trading_end_hour': 23,
    'trading_days': [0, 1, 2, 3, 4, 5, 6],  # All days for HFT
    'timezone': 'UTC',
}

# Performance optimizations
PERFORMANCE_SETTINGS = {
    'enable_backtesting': False,
    'save_trades_to_file': True,
    'trades_file': 'hft_trades.csv',
    'performance_metrics': True,
    'memory_optimization': True,
    'parallel_processing': False,  # Keep simple for MT5
}
