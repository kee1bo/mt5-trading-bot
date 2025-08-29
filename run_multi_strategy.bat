@echo off
title Multi-Strategy Trading Bot
echo.
echo ===============================================
echo    MULTI-STRATEGY TRADING BOT LAUNCHER
echo ===============================================
echo.
echo Starting multi-strategy trading bot...
echo WARNING: Ensure AutoTrading is ENABLED in MT5!
echo.
pause

cd /d "c:\Users\nsaiv\OneDrive\Desktop\ANMS-20250818T172818Z-1-001\trading-bot\mt5-trading-bot"

REM Activate virtual environment
call trading_bot_env\Scripts\activate.bat

REM Run multi-strategy bot
python multi_strategy_bot.py

echo.
echo Multi-Strategy Bot has stopped.
pause
