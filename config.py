# Configuration settings for the trading bot
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# MetaTrader 5 Settings
MT5_SETTINGS = {
    'login': int(os.getenv('MT5_LOGIN', '5039643367')),  # Demo account number
    'password': os.getenv('MT5_PASSWORD', 'W-Z8AySp'),  # Demo password
    'server': os.getenv('MT5_SERVER', 'MetaQuotes-Demo'),  # Demo server
    'path': os.getenv('MT5_PATH', ''),  # Path to MT5 terminal (if needed)
    'timeout': 60000,  # Connection timeout in milliseconds
}

# Trading Settings
TRADING_SETTINGS = {
    'symbol': os.getenv('TRADING_SYMBOL', 'XAUUSD'),  # Gold trading symbol
    'timeframe': os.getenv('TRADING_TIMEFRAME', 'M5'),  # Timeframe for analysis (M1, M5, M15, etc.)
    'lot_size': float(os.getenv('DEFAULT_LOT_SIZE', '0.01')),  # Default lot size
    'max_positions': 5,  # Maximum concurrent positions
    'slippage': 3,  # Maximum slippage in points
}

# Risk Management Settings
RISK_SETTINGS = {
    'risk_per_trade': 0.01,  # Risk 1% of account balance per trade
    'max_daily_loss': 0.05,  # Maximum 5% daily loss
    'max_drawdown': 0.10,  # Maximum 10% drawdown
    'stop_loss_pips': 5,  # Default stop loss in pips (adjusted for Gold)
    'take_profit_pips': 10,  # Default take profit in pips (adjusted for Gold)
    'trailing_stop': True,  # Enable trailing stop
    'trailing_stop_distance': 3,  # Trailing stop distance in pips (adjusted for Gold)
}

# Strategy Settings
STRATEGY_SETTINGS = {
    'active_strategy': 'ema_crossover',  # Default strategy
    'update_interval': 1,  # Update interval in seconds
    'lookback_periods': 200,  # Number of historical candles to fetch
    
    # Strategy-specific parameters
    'ema_crossover': {
        'ema_period': 5,
        'confirmation_candles': 1,
    },
    
    'rsi_divergence': {
        'rsi_period': 14,
        'lookback_candles': 10,
        'rsi_overbought': 70,
        'rsi_oversold': 30,
    },
    
    'bollinger_scalp': {
        'bb_period': 20,
        'bb_std': 2.0,
        'squeeze_threshold': 50,
    },
    
    'stochastic_momentum': {
        'k_period': 14,
        'd_period': 3,
        'smooth_k': 3,
        'overbought': 80,
        'oversold': 20,
    },
    
    'macd_signal_cross': {
        'fast_period': 12,
        'slow_period': 26,
        'signal_period': 9,
    }
}

# Logging Settings
LOGGING_SETTINGS = {
    'log_level': 'INFO',
    'log_file': 'trading_bot.log',
    'max_log_size': 10 * 1024 * 1024,  # 10 MB
    'backup_count': 5,
}

# Time Settings
TIME_SETTINGS = {
    'trading_start_hour': 0,  # Start trading at 00:00 UTC
    'trading_end_hour': 23,   # Stop trading at 23:00 UTC
    'trading_days': [0, 1, 2, 3, 4],  # Monday to Friday (0=Monday)
    'timezone': 'UTC',
}

# Performance Settings
PERFORMANCE_SETTINGS = {
    'enable_backtesting': False,
    'save_trades_to_file': True,
    'trades_file': 'trades.csv',
    'performance_metrics': True,
}
