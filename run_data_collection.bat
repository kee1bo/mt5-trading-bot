@echo off
title Data Collection Bot
echo.
echo ===============================================
echo      DATA COLLECTION BOT LAUNCHER
echo ===============================================
echo.
echo Starting data collection for ML training...
echo This will collect comprehensive market data
echo.
pause

cd /d "c:\Users\nsaiv\OneDrive\Desktop\ANMS-20250818T172818Z-1-001\trading-bot\mt5-trading-bot"

REM Activate virtual environment
call trading_bot_env\Scripts\activate.bat

REM Run data collection bot
python data_collection_bot.py

echo.
echo Data Collection Bot has stopped.
pause
