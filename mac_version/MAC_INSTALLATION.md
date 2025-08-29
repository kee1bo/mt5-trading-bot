# MT5 Trading Bot - macOS Installation Guide

## Quick macOS Installation

### Automated Setup (Recommended)
1. **Download and extract the trading bot**
2. **Open Terminal and navigate to the project folder**
3. **Run the deployment script**:
   ```bash
   chmod +x mac_version/deploy_mac.sh
   ./mac_version/deploy_mac.sh
   ```
4. **Test the installation**:
   ```bash
   ./test_mac_setup.sh
   ```
5. **Start trading**:
   ```bash
   ./run_mac_bot.sh
   ```

### Manual Installation

#### Prerequisites
- **macOS 10.14+**
- **Python 3.8+** - Install from [python.org](https://www.python.org/downloads/)
- **Homebrew** (optional) - Install from [brew.sh](https://brew.sh/)

#### Step 1: Install Dependencies
```bash
# Install Python dependencies
pip3 install pandas numpy python-dotenv

# Optional: Install Wine for MT5 support
brew install --cask wine-stable
```

#### Step 2: Create Virtual Environment
```bash
python3 -m venv mac_trading_env
source mac_trading_env/bin/activate
pip install -r mac_version/requirements.txt
```

#### Step 3: Configure Environment
Create a `.env` file:
```env
# Trading Settings
SYMBOL=XAUUSD
VOLUME=0.01
SIMULATION_MODE=true

# Optional: Real MT5 connection
# MT5_LOGIN=your_account
# MT5_PASSWORD=your_password
# MT5_SERVER=your_server
```

#### Step 4: Run the Bot
```bash
cd mac_version
python mac_multi_strategy_bot.py
```

## MT5 Integration Options

### Option 1: Simulation Mode (Recommended for Testing)
- **No MT5 installation required**
- **Perfect for development and testing**
- **Realistic price simulation**
- **All features available except real trading**

### Option 2: Wine + MT5 (Advanced Users)
1. **Install Wine**:
   ```bash
   brew install --cask wine-stable
   ```

2. **Download MT5 installer** from your broker

3. **Install MT5 via Wine**:
   ```bash
   wine mt5setup.exe
   ```

4. **Configure account credentials** in `.env` file

5. **Enable AutoTrading** in MT5 terminal

## Features on macOS

### ✅ **Fully Supported**
- Multi-strategy trading system
- Real-time market data simulation
- Risk management and position limits
- Performance tracking and statistics
- All trading strategies (EMA, Momentum, etc.)
- Cross-platform compatibility

### 🔄 **Simulation Mode**
- Realistic XAUUSD price simulation
- Complete trading environment
- Strategy testing and optimization
- Performance metrics and logging
- No broker account required

### 🍷 **Wine Mode** (Optional)
- Real MT5 connectivity via Wine
- Live market data and trading
- Full broker integration
- Requires MT5 installation via Wine

## Troubleshooting

### Common Issues

#### Python Not Found
```bash
# Install Python 3
brew install python3
# or download from python.org
```

#### Dependencies Failed
```bash
# Update pip first
pip3 install --upgrade pip
# Then retry installation
pip3 install pandas numpy python-dotenv
```

#### Wine Installation Issues
```bash
# Ensure Xcode Command Line Tools are installed
xcode-select --install

# Reinstall Wine
brew uninstall --cask wine-stable
brew install --cask wine-stable
```

#### Permission Denied
```bash
# Make scripts executable
chmod +x deploy_mac.sh
chmod +x run_mac_bot.sh
chmod +x test_mac_setup.sh
```

### Wine + MT5 Specific Issues

#### MT5 Not Found
- Check installation path: `~/.wine/drive_c/Program Files/MetaTrader 5/`
- Verify Wine prefix: `winecfg`
- Try alternative installation directory

#### Connection Failed
- Ensure MT5 is running in Wine
- Check account credentials in `.env`
- Verify broker server name
- Enable algo trading in MT5 settings

#### Performance Issues
- Reduce wine graphics settings
- Close unnecessary applications
- Use simulation mode for testing

## Performance Optimization

### For Best Performance
1. **Use SSD storage** for faster file I/O
2. **Close unnecessary applications** to free memory
3. **Use latest macOS version** for best compatibility
4. **Consider simulation mode** for development/testing

### Memory Usage
- **Simulation mode**: ~50-100 MB RAM
- **Wine + MT5**: ~200-500 MB RAM
- **Multiple strategies**: +20-50 MB per strategy

## Development on macOS

### IDE Recommendations
- **PyCharm** - Full Python IDE
- **Visual Studio Code** - Lightweight with Python extension
- **Jupyter Lab** - Interactive development

### Debugging
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python mac_multi_strategy_bot.py

# Monitor log files
tail -f logs/mac_multi_strategy.log
```

### Testing
```bash
# Run unit tests
python -m pytest tests/

# Performance testing
python -m cProfile mac_multi_strategy_bot.py
```

## Security Notes

### Safe Practices
- **Never commit** `.env` files with real credentials
- **Use demo accounts** for testing
- **Verify broker legitimacy** before live trading
- **Keep software updated** for security patches

### File Permissions
```bash
# Secure credential files
chmod 600 .env
chmod 600 .env.local
```

## Support

### Documentation
- Check `NEW_README.md` for full documentation
- Review strategy files in `strategies/` folder
- Examine logs in `logs/` directory

### Community
- GitHub Issues for bug reports
- Discussions for feature requests
- Wiki for additional documentation

---

**🎉 Enjoy trading on macOS!**

*Remember: This software is for educational purposes. Always test thoroughly before live trading.*
