# MetaTrader 5 Trading Bot

A comprehensive trading bot for MetaTrader 5 with multiple strategies for scalping and intraday trading on XAUUSD (Gold).

## Features

- **5 Trading Strategies:**
  - EMA Crossover (Fast/Slow moving averages)
  - RSI Divergence (Momentum reversal detection)
  - Bollinger Squeeze (Volatility breakout)
  - Stochastic Momentum (Overbought/Oversold levels)
  - MACD Signal Cross (Trend confirmation)

- **Risk Management:**
  - Position sizing based on account balance
  - Stop loss and take profit levels
  - Maximum daily loss limits
  - Risk per trade percentage control

- **Modular Architecture:**
  - Separate strategy classes for easy extension
  - Centralized trade management
  - MT5 connection handling
  - Environment-based configuration

## Requirements

- **Python 3.8+**
- **MetaTrader 5 terminal** (Windows required - MT5 Python package only works on Windows)
- **Active MT5 demo/live account**

## Installation & Setup

### 1. Clone Repository
```bash
git clone <repository-url>
cd trade-bot
```

### 2. Create Virtual Environment
```bash
python -m venv trading_bot_env
# Windows:
trading_bot_env\Scripts\activate
# Linux/Mac:
source trading_bot_env/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the project root:
```env
MT5_LOGIN=your_account_number
MT5_PASSWORD=your_password
MT5_SERVER=your_broker_server
TRADING_SYMBOL=XAUUSD
```

### 5. Install & Configure MT5 Terminal
- Download MT5 from your broker or MetaQuotes
- Install and login with your credentials
- Enable algo trading in Tools → Options → Expert Advisors
- Make sure Python API is allowed

### 6. Run the Bot
```bash
python main.py
```

## Configuration

The bot uses environment variables for sensitive data and `config.py` for trading parameters:

### Environment Variables (.env)
- `MT5_LOGIN`: Your MT5 account number
- `MT5_PASSWORD`: Your MT5 password  
- `MT5_SERVER`: Your broker's server name
- `TRADING_SYMBOL`: Trading symbol (default: XAUUSD)

### Trading Parameters (config.py)
- Risk percentage per trade
- Position sizing settings
- Strategy-specific parameters
- Trading timeframes

## Strategies Overview

### 1. EMA Crossover
- Fast EMA (12) crosses above/below Slow EMA (26)
- Trend-following strategy
- Good for trending markets

### 2. RSI Divergence
- Detects price vs RSI divergences
- Mean reversion strategy
- Works in ranging markets

### 3. Bollinger Squeeze
- Identifies low volatility periods
- Trades breakouts from consolidation
- Catches explosive moves

### 4. Stochastic Momentum
- Uses Stochastic oscillator levels
- Overbought/oversold signals
- Good for range-bound trading

### 5. MACD Signal Cross
- MACD line crossing signal line
- Momentum confirmation
- Filters trend changes

## Risk Management

- **Position Size**: Calculated based on account balance and risk percentage
- **Stop Loss**: Automatic SL placement based on strategy signals
- **Take Profit**: Multiple TP levels for partial position closing
- **Daily Limits**: Maximum loss per day protection
- **Correlation**: Prevents opening correlated positions

## Testing

Run the test suite to verify everything works:
```bash
python test_setup.py      # Test MT5 connection
python test_strategies.py # Test strategy logic
```

## Important Notes

⚠️ **Windows Only**: The MetaTrader5 Python package only works on Windows with MT5 terminal installed.

⚠️ **Demo First**: Always test with demo account before using real money.

⚠️ **Risk Warning**: Trading involves substantial risk. Only trade with money you can afford to lose.

## Demo Account Details

The bot is pre-configured for testing with MetaQuotes demo server:
- **Server**: MetaQuotes-Demo
- **Symbol**: XAUUSD (Gold)
- **Account**: Demo account (configure your own credentials)

## Troubleshooting

### Common Issues:

1. **"MetaTrader5 module not found"**
   - Install MT5 terminal first
   - Ensure you're on Windows
   - Reinstall: `pip install MetaTrader5`

2. **"Failed to connect to MT5"**
   - Check MT5 terminal is running
   - Verify login credentials
   - Enable algo trading in MT5 settings

3. **"Invalid symbol XAUUSD"**
   - Check if symbol is available on your broker
   - Try different symbol name format (GOLD, XAU/USD, etc.)

## Project Structure

```
trade-bot/
├── main.py                 # Main execution file
├── config.py              # Configuration settings
├── mt5_connector.py       # MT5 API connection
├── trade_manager.py       # Trade execution logic
├── risk_manager.py        # Risk management
├── strategies/            # Trading strategies
│   ├── __init__.py
│   ├── base_strategy.py
│   ├── ema_crossover.py
│   ├── rsi_divergence.py
│   ├── bollinger_scalp.py
│   ├── stochastic_momentum.py
│   └── macd_signal_cross.py
├── requirements.txt       # Python dependencies
├── .env                  # Environment variables (create this)
└── README.md             # This file
```

## Getting Started on Windows

1. **Download and install MetaTrader 5** from MetaQuotes or your broker
2. **Clone this repository** to your Windows machine
3. **Create virtual environment** and install dependencies
4. **Setup `.env` file** with your MT5 credentials
5. **Run `python test_setup.py`** to verify MT5 connection
6. **Start trading** with `python main.py`

## License

This project is for educational purposes. Use at your own risk.
