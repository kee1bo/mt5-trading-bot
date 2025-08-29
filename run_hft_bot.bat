@echo off
title HFT Trading Bot
echo.
echo ===============================================
echo     HIGH-FREQUENCY TRADING BOT LAUNCHER
echo ===============================================
echo.
echo Starting HFT bot (19.8 Hz frequency)...
echo WARNING: Ensure AutoTrading is ENABLED in MT5!
echo.
pause

cd /d "c:\Users\nsaiv\OneDrive\Desktop\ANMS-20250818T172818Z-1-001\trading-bot\mt5-trading-bot"

REM Activate virtual environment
call trading_bot_env\Scripts\activate.bat

REM Run HFT bot
python hft_main.py

echo.
echo HFT Bot has stopped.
pause
