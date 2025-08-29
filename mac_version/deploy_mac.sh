#!/bin/bash
# macOS Deployment Script for MT5 Trading Bot
# This script sets up the trading bot environment on macOS

echo "🍎 macOS MT5 Trading Bot Deployment Script"
echo "=========================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}❌ This script is designed for macOS only${NC}"
    exit 1
fi

echo -e "${BLUE}🖥️  Platform: macOS detected${NC}"

# Step 1: Check Python installation
echo -e "${BLUE}📋 Step 1: Checking Python installation...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}✅ Python 3 found: $PYTHON_VERSION${NC}"
else
    echo -e "${RED}❌ Python 3 not found${NC}"
    echo -e "${YELLOW}💡 Install Python 3 from: https://www.python.org/downloads/${NC}"
    exit 1
fi

# Step 2: Check pip installation
echo -e "${BLUE}📋 Step 2: Checking pip installation...${NC}"
if command -v pip3 &> /dev/null; then
    echo -e "${GREEN}✅ pip3 found${NC}"
else
    echo -e "${RED}❌ pip3 not found${NC}"
    echo -e "${YELLOW}💡 Install pip with: python3 -m ensurepip --upgrade${NC}"
    exit 1
fi

# Step 3: Check Homebrew (optional for Wine)
echo -e "${BLUE}📋 Step 3: Checking Homebrew (for Wine support)...${NC}"
if command -v brew &> /dev/null; then
    echo -e "${GREEN}✅ Homebrew found${NC}"
    HOMEBREW_AVAILABLE=true
else
    echo -e "${YELLOW}⚠️  Homebrew not found${NC}"
    echo -e "${YELLOW}💡 Install Homebrew from: https://brew.sh/${NC}"
    HOMEBREW_AVAILABLE=false
fi

# Step 4: Check/Install Wine (optional)
echo -e "${BLUE}📋 Step 4: Checking Wine installation...${NC}"
if command -v wine &> /dev/null; then
    echo -e "${GREEN}✅ Wine found${NC}"
    WINE_AVAILABLE=true
else
    echo -e "${YELLOW}⚠️  Wine not found${NC}"
    if [ "$HOMEBREW_AVAILABLE" = true ]; then
        read -p "🍷 Install Wine via Homebrew? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${BLUE}📦 Installing Wine...${NC}"
            brew install --cask wine-stable
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}✅ Wine installed successfully${NC}"
                WINE_AVAILABLE=true
            else
                echo -e "${RED}❌ Wine installation failed${NC}"
                WINE_AVAILABLE=false
            fi
        else
            WINE_AVAILABLE=false
        fi
    else
        WINE_AVAILABLE=false
    fi
fi

# Step 5: Create virtual environment
echo -e "${BLUE}📋 Step 5: Setting up Python virtual environment...${NC}"
if [ ! -d "mac_trading_env" ]; then
    echo -e "${BLUE}🔧 Creating virtual environment...${NC}"
    python3 -m venv mac_trading_env
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Virtual environment created${NC}"
    else
        echo -e "${RED}❌ Failed to create virtual environment${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  Virtual environment already exists${NC}"
fi

# Activate virtual environment
echo -e "${BLUE}🔧 Activating virtual environment...${NC}"
source mac_trading_env/bin/activate

# Step 6: Install dependencies
echo -e "${BLUE}📋 Step 6: Installing Python dependencies...${NC}"
if [ -f "mac_version/requirements.txt" ]; then
    pip install -r mac_version/requirements.txt
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Dependencies installed successfully${NC}"
    else
        echo -e "${RED}❌ Failed to install dependencies${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  requirements.txt not found, installing basic packages...${NC}"
    pip install pandas numpy python-dotenv
fi

# Step 7: Configuration
echo -e "${BLUE}📋 Step 7: Configuration setup...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${BLUE}📝 Creating environment configuration file...${NC}"
    cat > .env << EOF
# MT5 Account Settings (Optional - for real MT5 connection)
# MT5_LOGIN=your_account_number
# MT5_PASSWORD=your_password
# MT5_SERVER=your_broker_server

# Risk Management
MAX_TOTAL_POSITIONS=15
MAX_STRATEGY_POSITIONS=5
RISK_PER_TRADE=0.2

# Trading Settings
SYMBOL=XAUUSD
TIMEFRAME=M1
VOLUME=0.01

# macOS Specific Settings
SIMULATION_MODE=true
MAC_COMPATIBILITY=true
EOF
    echo -e "${GREEN}✅ Configuration file created: .env${NC}"
else
    echo -e "${YELLOW}⚠️  Configuration file already exists${NC}"
fi

# Step 8: Create launcher scripts
echo -e "${BLUE}📋 Step 8: Creating launcher scripts...${NC}"

# Create run script
cat > run_mac_bot.sh << 'EOF'
#!/bin/bash
# MT5 Trading Bot Launcher for macOS

echo "🚀 Starting MT5 Trading Bot on macOS..."

# Activate virtual environment
source mac_trading_env/bin/activate

# Check if we should use Wine or Simulation
if command -v wine &> /dev/null && [ -f ~/.wine/drive_c/Program\ Files/MetaTrader\ 5/terminal64.exe ]; then
    echo "🍷 Wine and MT5 detected - attempting Wine connection"
    export MT5_USE_WINE=true
else
    echo "🔄 Running in simulation mode"
    export MT5_USE_WINE=false
fi

# Run the bot
cd mac_version
python mac_multi_strategy_bot.py

echo "🛑 Trading bot stopped"
EOF

chmod +x run_mac_bot.sh

# Create test script
cat > test_mac_setup.sh << 'EOF'
#!/bin/bash
# Test macOS Setup

echo "🧪 Testing macOS MT5 Trading Bot Setup..."

# Activate virtual environment
source mac_trading_env/bin/activate

# Run basic tests
cd mac_version
python -c "
import sys
print(f'Python version: {sys.version}')

try:
    import pandas as pd
    print('✅ pandas imported successfully')
except ImportError as e:
    print(f'❌ pandas import failed: {e}')

try:
    import numpy as np
    print('✅ numpy imported successfully')
except ImportError as e:
    print(f'❌ numpy import failed: {e}')

try:
    from mac_mt5_connector import MacMT5Connector
    print('✅ MacMT5Connector imported successfully')
    
    # Test connector initialization
    connector = MacMT5Connector()
    print('✅ MacMT5Connector initialized successfully')
    
    # Test simulation connection
    if connector.connect():
        print('✅ Simulation connection successful')
        account_info = connector.get_account_info()
        if account_info:
            print(f'✅ Account info retrieved: {account_info[\"login\"]}')
        connector.disconnect()
    else:
        print('❌ Connection failed')
        
except Exception as e:
    print(f'❌ MacMT5Connector test failed: {e}')

print('🎉 Setup test completed!')
"
EOF

chmod +x test_mac_setup.sh

echo -e "${GREEN}✅ Launcher scripts created${NC}"

# Step 9: Final summary
echo -e "${BLUE}📋 Step 9: Deployment Summary${NC}"
echo "=========================================="
echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo ""
echo -e "${BLUE}🎯 What's Available:${NC}"
echo "• Python virtual environment: mac_trading_env/"
echo "• Configuration file: .env"
echo "• Mac-compatible trading bot: mac_version/"
echo "• Launcher script: ./run_mac_bot.sh"
echo "• Test script: ./test_mac_setup.sh"
echo ""

if [ "$WINE_AVAILABLE" = true ]; then
    echo -e "${BLUE}🍷 Wine Integration:${NC}"
    echo "• Wine is available for MT5 connectivity"
    echo "• To use real MT5: Install MT5 via Wine and configure .env"
else
    echo -e "${YELLOW}🔄 Simulation Mode:${NC}"
    echo "• Running in simulation mode (no Wine/MT5 required)"
    echo "• Perfect for testing and development"
fi

echo ""
echo -e "${BLUE}🚀 Quick Start:${NC}"
echo "1. Test setup: ./test_mac_setup.sh"
echo "2. Run trading bot: ./run_mac_bot.sh"
echo "3. Configure .env file for your preferences"
echo ""

echo -e "${BLUE}🔧 MT5 Setup (Optional):${NC}"
echo "1. Download MT5 installer"
echo "2. Install via Wine: wine mt5setup.exe"
echo "3. Configure account in .env file"
echo "4. Enable AutoTrading in MT5"
echo ""

echo -e "${GREEN}🎉 macOS MT5 Trading Bot is ready to use!${NC}"
echo -e "${YELLOW}⚠️  Disclaimer: Test thoroughly before live trading${NC}"
