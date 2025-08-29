#!/usr/bin/env python3
"""
XAUUSD Data Collector for ML Model Training
Collects comprehensive market data with technical indicators for AI/ML training.
"""

import pandas as pd
import numpy as np
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
import json

from mt5_connector import MT5Connector
from config import TRADING_SETTINGS

class XAUUSDDataCollector:
    """Comprehensive data collector for XAUUSD with technical indicators."""
    
    def __init__(self, symbol: str = 'XAUUSD'):
        self.symbol = symbol
        self.connector = MT5Connector()
        self.logger = logging.getLogger(__name__)
        
        # Data storage
        self.data_dir = 'ml_training_data'
        self.ensure_data_directory()
        
        # Collection settings
        self.timeframes = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1']
        self.indicators_cache = {}
        
    def ensure_data_directory(self):
        """Create data directory structure."""
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(f"{self.data_dir}/raw", exist_ok=True)
        os.makedirs(f"{self.data_dir}/processed", exist_ok=True)
        os.makedirs(f"{self.data_dir}/features", exist_ok=True)
    
    def collect_real_time_data(self, duration_minutes: int = 60):
        """Collect real-time tick data for specified duration."""
        print(f"🔄 Starting real-time data collection for {duration_minutes} minutes...")
        
        if not self.connector.connect():
            print("❌ Failed to connect to MT5")
            return
        
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        tick_data = []
        bar_data = {tf: [] for tf in ['M1', 'M5']}  # Focus on short timeframes for real-time
        
        try:
            while datetime.now() < end_time:
                timestamp = datetime.now()
                
                # Get current tick
                tick = self.connector.get_current_price(self.symbol)
                if tick:
                    tick_data.append({
                        'timestamp': timestamp,
                        'bid': tick['bid'],
                        'ask': tick['ask'],
                        'spread': tick['spread'],
                        'volume': tick.get('volume', 0)
                    })
                
                # Get latest bars for M1 and M5
                for tf in ['M1', 'M5']:
                    bars = self.connector.get_market_data(self.symbol, tf, 2)
                    if bars is not None and len(bars) >= 1:
                        latest_bar = bars.iloc[-1]
                        bar_data[tf].append({
                            'timestamp': timestamp,
                            'timeframe': tf,
                            'open': latest_bar['open'],
                            'high': latest_bar['high'],
                            'low': latest_bar['low'],
                            'close': latest_bar['close'],
                            'volume': latest_bar['volume'],
                            'bar_time': bars.index[-1]
                        })
                
                # Sleep for next tick (collect every 100ms)
                time.sleep(0.1)
                
                # Progress update every minute
                if len(tick_data) % 600 == 0:  # Every 60 seconds (600 ticks)
                    elapsed = datetime.now() - start_time
                    remaining = end_time - datetime.now()
                    print(f"📊 Collected {len(tick_data)} ticks | Elapsed: {elapsed} | Remaining: {remaining}")
        
        except KeyboardInterrupt:
            print("🛑 Data collection stopped by user")
        
        # Save collected data
        self.save_real_time_data(tick_data, bar_data, start_time)
        self.connector.disconnect()
        
        print(f"✅ Data collection complete! Collected {len(tick_data)} ticks")
    
    def collect_historical_data(self, days_back: int = 30):
        """Collect comprehensive historical data for ML training."""
        print(f"📈 Collecting {days_back} days of historical data for {self.symbol}...")
        
        if not self.connector.connect():
            print("❌ Failed to connect to MT5")
            return
        
        historical_data = {}
        
        for timeframe in self.timeframes:
            print(f"🔄 Collecting {timeframe} data...")
            
            # Calculate required bars
            bars_per_day = {
                'M1': 1440, 'M5': 288, 'M15': 96, 'M30': 48,
                'H1': 24, 'H4': 6, 'D1': 1
            }
            total_bars = days_back * bars_per_day[timeframe]
            
            # Get data
            data = self.connector.get_market_data(self.symbol, timeframe, total_bars)
            if data is not None:
                # Add technical indicators
                data_with_indicators = self.add_technical_indicators(data, timeframe)
                historical_data[timeframe] = data_with_indicators
                print(f"✅ {timeframe}: {len(data_with_indicators)} bars collected")
            else:
                print(f"❌ Failed to collect {timeframe} data")
        
        # Save historical data
        self.save_historical_data(historical_data, days_back)
        self.connector.disconnect()
        
        print("✅ Historical data collection complete!")
        return historical_data
    
    def add_technical_indicators(self, data: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """Add comprehensive technical indicators for ML features."""
        df = data.copy()
        
        # Price-based indicators
        df['price_range'] = df['high'] - df['low']
        df['price_change'] = df['close'].pct_change()
        df['price_change_abs'] = df['price_change'].abs()
        
        # Moving Averages
        for period in [5, 10, 20, 50, 100, 200]:
            df[f'sma_{period}'] = df['close'].rolling(window=period).mean()
            df[f'ema_{period}'] = df['close'].ewm(span=period).mean()
            df[f'close_vs_sma_{period}'] = df['close'] / df[f'sma_{period}'] - 1
            df[f'close_vs_ema_{period}'] = df['close'] / df[f'ema_{period}'] - 1
        
        # RSI
        for period in [7, 14, 21]:
            df[f'rsi_{period}'] = self.calculate_rsi(df['close'], period)
        
        # MACD
        df['macd'], df['macd_signal'], df['macd_histogram'] = self.calculate_macd(df['close'])
        
        # Bollinger Bands
        for period in [10, 20, 50]:
            bb_upper, bb_middle, bb_lower = self.calculate_bollinger_bands(df['close'], period)
            df[f'bb_upper_{period}'] = bb_upper
            df[f'bb_middle_{period}'] = bb_middle
            df[f'bb_lower_{period}'] = bb_lower
            df[f'bb_position_{period}'] = (df['close'] - bb_lower) / (bb_upper - bb_lower)
            df[f'bb_width_{period}'] = (bb_upper - bb_lower) / bb_middle
        
        # ATR (Average True Range)
        for period in [7, 14, 21]:
            df[f'atr_{period}'] = self.calculate_atr(df, period)
        
        # Stochastic
        for period in [14, 21]:
            df[f'stoch_k_{period}'], df[f'stoch_d_{period}'] = self.calculate_stochastic(df, period)
        
        # Volume indicators (if available)
        if 'volume' in df.columns:
            df['volume_sma_10'] = df['volume'].rolling(window=10).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma_10']
        
        # Price patterns
        df['doji'] = self.detect_doji(df)
        df['hammer'] = self.detect_hammer(df)
        df['engulfing'] = self.detect_engulfing(df)
        
        # Support/Resistance levels
        df['resistance'] = df['high'].rolling(window=20).max()
        df['support'] = df['low'].rolling(window=20).min()
        df['distance_to_resistance'] = (df['resistance'] - df['close']) / df['close']
        df['distance_to_support'] = (df['close'] - df['support']) / df['close']
        
        # Volatility measures
        df['volatility_10'] = df['price_change'].rolling(window=10).std()
        df['volatility_20'] = df['price_change'].rolling(window=20).std()
        
        # Time-based features
        df['hour'] = df.index.hour
        df['day_of_week'] = df.index.dayofweek
        df['day_of_month'] = df.index.day
        df['month'] = df.index.month
        
        # Market session indicators
        df['london_session'] = ((df['hour'] >= 8) & (df['hour'] < 16)).astype(int)
        df['new_york_session'] = ((df['hour'] >= 13) & (df['hour'] < 21)).astype(int)
        df['asian_session'] = ((df['hour'] >= 0) & (df['hour'] < 8)).astype(int)
        
        # Trend indicators
        df['trend_5'] = np.where(df['close'] > df['sma_5'], 1, -1)
        df['trend_20'] = np.where(df['close'] > df['sma_20'], 1, -1)
        df['trend_50'] = np.where(df['close'] > df['sma_50'], 1, -1)
        
        # Future price targets (for supervised learning)
        for periods in [1, 3, 5, 10, 20]:
            df[f'future_return_{periods}'] = df['close'].shift(-periods) / df['close'] - 1
            df[f'future_high_{periods}'] = df['high'].rolling(window=periods).max().shift(-periods)
            df[f'future_low_{periods}'] = df['low'].rolling(window=periods).min().shift(-periods)
        
        # Target classifications
        df['target_direction'] = np.where(df['future_return_1'] > 0, 1, 0)  # 1 = up, 0 = down
        df['target_magnitude'] = pd.cut(df['future_return_1'], 
                                       bins=[-np.inf, -0.001, 0.001, np.inf], 
                                       labels=['down', 'sideways', 'up'])
        
        return df
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def calculate_macd(self, prices: pd.Series, fast=12, slow=26, signal=9):
        """Calculate MACD."""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        macd_signal = macd.ewm(span=signal).mean()
        macd_histogram = macd - macd_signal
        return macd, macd_signal, macd_histogram
    
    def calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: float = 2):
        """Calculate Bollinger Bands."""
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        return upper, sma, lower
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        return true_range.rolling(period).mean()
    
    def calculate_stochastic(self, df: pd.DataFrame, period: int = 14):
        """Calculate Stochastic Oscillator."""
        lowest_low = df['low'].rolling(window=period).min()
        highest_high = df['high'].rolling(window=period).max()
        k_percent = 100 * ((df['close'] - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=3).mean()
        return k_percent, d_percent
    
    def detect_doji(self, df: pd.DataFrame) -> pd.Series:
        """Detect Doji candlestick patterns."""
        body_size = abs(df['close'] - df['open'])
        total_range = df['high'] - df['low']
        return (body_size / total_range < 0.1).astype(int)
    
    def detect_hammer(self, df: pd.DataFrame) -> pd.Series:
        """Detect Hammer candlestick patterns."""
        body_size = abs(df['close'] - df['open'])
        lower_shadow = df[['close', 'open']].min(axis=1) - df['low']
        total_range = df['high'] - df['low']
        return ((lower_shadow > 2 * body_size) & (body_size / total_range > 0.1)).astype(int)
    
    def detect_engulfing(self, df: pd.DataFrame) -> pd.Series:
        """Detect Engulfing patterns."""
        prev_body = abs(df['close'].shift(1) - df['open'].shift(1))
        curr_body = abs(df['close'] - df['open'])
        engulfing = (curr_body > prev_body * 1.5).astype(int)
        return engulfing
    
    def save_real_time_data(self, tick_data: List, bar_data: Dict, start_time: datetime):
        """Save real-time collected data."""
        timestamp_str = start_time.strftime("%Y%m%d_%H%M%S")
        
        # Save tick data
        if tick_data:
            tick_df = pd.DataFrame(tick_data)
            tick_file = f"{self.data_dir}/raw/ticks_{self.symbol}_{timestamp_str}.csv"
            tick_df.to_csv(tick_file, index=False)
            print(f"💾 Saved {len(tick_data)} ticks to {tick_file}")
        
        # Save bar data
        for tf, data in bar_data.items():
            if data:
                bar_df = pd.DataFrame(data)
                bar_file = f"{self.data_dir}/raw/bars_{self.symbol}_{tf}_{timestamp_str}.csv"
                bar_df.to_csv(bar_file, index=False)
                print(f"💾 Saved {len(data)} {tf} bars to {bar_file}")
    
    def save_historical_data(self, historical_data: Dict, days_back: int):
        """Save historical data with indicators."""
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for timeframe, data in historical_data.items():
            # Save raw data
            raw_file = f"{self.data_dir}/raw/historical_{self.symbol}_{timeframe}_{days_back}days_{timestamp_str}.csv"
            data.to_csv(raw_file)
            
            # Save processed data (features only)
            feature_cols = [col for col in data.columns if not col.startswith('future_')]
            features_df = data[feature_cols].dropna()
            features_file = f"{self.data_dir}/features/features_{self.symbol}_{timeframe}_{days_back}days_{timestamp_str}.csv"
            features_df.to_csv(features_file)
            
            # Save targets
            target_cols = [col for col in data.columns if col.startswith('future_') or col.startswith('target_')]
            if target_cols:
                targets_df = data[target_cols].dropna()
                targets_file = f"{self.data_dir}/features/targets_{self.symbol}_{timeframe}_{days_back}days_{timestamp_str}.csv"
                targets_df.to_csv(targets_file)
            
            print(f"💾 Saved {timeframe} data: {len(data)} rows")
    
    def get_data_summary(self) -> Dict:
        """Get summary of collected data."""
        summary = {
            'data_directory': self.data_dir,
            'files': [],
            'total_size_mb': 0
        }
        
        for root, dirs, files in os.walk(self.data_dir):
            for file in files:
                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                summary['files'].append({
                    'name': file,
                    'path': file_path,
                    'size_mb': round(file_size, 2)
                })
                summary['total_size_mb'] += file_size
        
        summary['total_size_mb'] = round(summary['total_size_mb'], 2)
        summary['file_count'] = len(summary['files'])
        
        return summary

def main():
    """Main function for data collection."""
    collector = XAUUSDDataCollector()
    
    print("🔄 XAUUSD Data Collector for ML Training")
    print("=" * 50)
    
    choice = input("""
Choose collection type:
1. Real-time data collection (60 minutes)
2. Historical data collection (30 days)
3. Both real-time and historical
4. Data summary

Enter choice (1-4): """).strip()
    
    if choice == '1':
        duration = int(input("Enter duration in minutes (default 60): ") or 60)
        collector.collect_real_time_data(duration)
    
    elif choice == '2':
        days = int(input("Enter days back (default 30): ") or 30)
        collector.collect_historical_data(days)
    
    elif choice == '3':
        days = int(input("Enter days back for historical (default 30): ") or 30)
        duration = int(input("Enter minutes for real-time (default 60): ") or 60)
        
        collector.collect_historical_data(days)
        print("\n" + "="*50)
        collector.collect_real_time_data(duration)
    
    elif choice == '4':
        summary = collector.get_data_summary()
        print(f"\n📊 Data Summary:")
        print(f"Directory: {summary['data_directory']}")
        print(f"Files: {summary['file_count']}")
        print(f"Total Size: {summary['total_size_mb']} MB")
        
        for file_info in summary['files'][-10:]:  # Show last 10 files
            print(f"  {file_info['name']} - {file_info['size_mb']} MB")
    
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()
