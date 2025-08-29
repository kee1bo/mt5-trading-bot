@echo off
title Master Trading Bot Launcher
color 0A
echo.
echo ================================================================
echo                   MASTER TRADING BOT LAUNCHER
echo ================================================================
echo.
echo Choose your trading configuration:
echo.
echo 1. Multi-Strategy Bot Only
echo 2. Data Collection Bot Only  
echo 3. HFT Bot Only
echo 4. Multi-Strategy + Data Collection (Recommended)
echo 5. HFT + Data Collection
echo 6. All Bots (Multi-Strategy + HFT + Data Collection)
echo 7. Exit
echo.
set /p choice="Enter your choice (1-7): "

if "%choice%"=="1" goto multi_only
if "%choice%"=="2" goto data_only
if "%choice%"=="3" goto hft_only
if "%choice%"=="4" goto multi_data
if "%choice%"=="5" goto hft_data
if "%choice%"=="6" goto all_bots
if "%choice%"=="7" goto exit
goto invalid

:multi_only
echo.
echo Starting Multi-Strategy Bot...
start "Multi-Strategy Bot" cmd /k "run_multi_strategy.bat"
goto end

:data_only
echo.
echo Starting Data Collection Bot...
start "Data Collection Bot" cmd /k "run_data_collection.bat"
goto end

:hft_only
echo.
echo Starting HFT Bot...
start "HFT Bot" cmd /k "run_hft_bot.bat"
goto end

:multi_data
echo.
echo Starting Multi-Strategy Bot + Data Collection...
echo Opening two terminal windows...
start "Multi-Strategy Bot" cmd /k "run_multi_strategy.bat"
timeout /t 2 /nobreak >nul
start "Data Collection Bot" cmd /k "run_data_collection.bat"
goto end

:hft_data
echo.
echo Starting HFT Bot + Data Collection...
echo Opening two terminal windows...
start "HFT Bot" cmd /k "run_hft_bot.bat"
timeout /t 2 /nobreak >nul
start "Data Collection Bot" cmd /k "run_data_collection.bat"
goto end

:all_bots
echo.
echo Starting ALL Bots...
echo Opening three terminal windows...
echo WARNING: This will use significant system resources!
pause
start "Multi-Strategy Bot" cmd /k "run_multi_strategy.bat"
timeout /t 2 /nobreak >nul
start "HFT Bot" cmd /k "run_hft_bot.bat"
timeout /t 2 /nobreak >nul
start "Data Collection Bot" cmd /k "run_data_collection.bat"
goto end

:invalid
echo Invalid choice. Please try again.
timeout /t 2 /nobreak >nul
goto start

:end
echo.
echo ================================================================
echo                     BOTS LAUNCHED SUCCESSFULLY
echo ================================================================
echo.
echo Bot Status:
if "%choice%"=="1" echo - Multi-Strategy Bot: RUNNING
if "%choice%"=="2" echo - Data Collection Bot: RUNNING
if "%choice%"=="3" echo - HFT Bot: RUNNING
if "%choice%"=="4" (
    echo - Multi-Strategy Bot: RUNNING
    echo - Data Collection Bot: RUNNING
)
if "%choice%"=="5" (
    echo - HFT Bot: RUNNING
    echo - Data Collection Bot: RUNNING
)
if "%choice%"=="6" (
    echo - Multi-Strategy Bot: RUNNING
    echo - HFT Bot: RUNNING
    echo - Data Collection Bot: RUNNING
)
echo.
echo IMPORTANT REMINDERS:
echo - Ensure AutoTrading is ENABLED in MT5
echo - Monitor all terminal windows for activity
echo - Check log files for detailed information
echo - Use Ctrl+C in each terminal to stop bots safely
echo.
echo Log Files:
echo - multi_strategy_bot.log
echo - trading_bot.log (HFT)
echo - data_collection_bot.log
echo.
echo Data Files:
echo - Performance data: multi_strategy_performance_*.json
echo - Collected data: collected_data\xauusd_data_collection_*.csv
echo.
pause

:exit
echo Goodbye!
timeout /t 2 /nobreak >nul
