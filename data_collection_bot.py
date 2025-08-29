#!/usr/bin/env python3
"""
Data Collection Bot - Runs parallel to trading for ML model training
"""

import time
import logging
import threading
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import os
import signal
import sys

from mt5_connector import MT5Connector

class DataCollectionBot:
    """
    Comprehensive data collection bot for ML model training.
    Collects real-time market data, technical indicators, and trading signals.
    """
    
    def __init__(self, collection_interval: float = 1.0):
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.mt5_connector = MT5Connector()
        self.collection_interval = collection_interval
        self.running = False
        
        # Data storage
        self.data_buffer = []
        self.max_buffer_size = 10000
        self.last_save_time = time.time()
        self.save_interval = 300  # Save every 5 minutes
        
        # File management
        self.base_filename = "xauusd_data_collection"
        self.data_directory = "collected_data"
        os.makedirs(self.data_directory, exist_ok=True)
        
        # Collection statistics
        self.stats = {
            'start_time': None,
            'total_collections': 0,
            'total_saves': 0,
            'last_collection_time': None,
            'collection_rate': 0,
            'data_points_collected': 0,
            'unique_indicators': 0,
        }
        
        # Signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def setup_logging(self):
        """Setup logging for data collection bot."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('data_collection_bot.log'),
                logging.StreamHandler()
            ]
        )
    
    def start(self):
        """Start data collection bot."""
        print("🚀 Starting Data Collection Bot")
        print("=" * 60)
        
        # Connect to MT5
        if not self.mt5_connector.connect():
            print("❌ Failed to connect to MT5")
            return False
        
        print("✅ Data Collection Bot initialized successfully")
        print(f"📊 Collection Interval: {self.collection_interval}s")
        print(f"💾 Data Directory: {self.data_directory}")
        print(f"📈 Auto-save Interval: {self.save_interval}s")
        print("=" * 60)
        
        self.running = True
        self.stats['start_time'] = datetime.now()
        
        return self.run_collection_loop()
    
    def run_collection_loop(self):
        """Main data collection loop."""
        print("🔄 Starting data collection loop...")
        
        symbol = 'XAUUSD'
        timeframes = ['M1', 'M5', 'M15']  # Collect multiple timeframes
        lookback_periods = 100
        
        last_status_time = time.time()
        
        try:
            while self.running:
                collection_start = time.time()
                
                # Collect data from all timeframes
                collected_data = self.collect_comprehensive_data(symbol, timeframes, lookback_periods)
                
                if collected_data:
                    self.data_buffer.append(collected_data)
                    self.stats['total_collections'] += 1
                    self.stats['data_points_collected'] += len(collected_data.get('indicators', {}))
                    self.stats['last_collection_time'] = datetime.now()
                    
                    # Calculate collection rate
                    if self.stats['start_time']:
                        runtime = (datetime.now() - self.stats['start_time']).total_seconds()
                        self.stats['collection_rate'] = self.stats['total_collections'] / runtime
                    
                    # Check if buffer needs saving
                    if (len(self.data_buffer) >= self.max_buffer_size or 
                        time.time() - self.last_save_time >= self.save_interval):
                        self.save_collected_data()
                
                # Status update every 60 seconds
                if time.time() - last_status_time >= 60:
                    self.print_collection_status()
                    last_status_time = time.time()
                
                # Sleep for collection interval
                collection_time = time.time() - collection_start
                sleep_time = max(0.1, self.collection_interval - collection_time)
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            print("\n🛑 Data collection shutdown requested...")
        except Exception as e:
            print(f"❌ Data collection loop error: {e}")
            self.logger.error(f"Data collection loop error: {e}")
        finally:
            self.stop()
    
    def collect_comprehensive_data(self, symbol: str, timeframes: List[str], lookback: int) -> Optional[Dict]:
        """Collect comprehensive market data for ML training."""
        try:
            collection_timestamp = datetime.now()
            collected_data = {
                'timestamp': collection_timestamp.isoformat(),
                'symbol': symbol,
                'timeframes': {},
                'current_price': {},
                'indicators': {},
                'market_state': {}
            }
            
            # Get current price info
            price_info = self.mt5_connector.get_current_price(symbol)
            if price_info:
                collected_data['current_price'] = {
                    'bid': price_info.get('bid', 0),
                    'ask': price_info.get('ask', 0),
                    'spread': price_info.get('ask', 0) - price_info.get('bid', 0),
                    'last': price_info.get('last', 0),
                    'volume': price_info.get('volume', 0)
                }
            
            # Collect data from each timeframe
            for timeframe in timeframes:
                try:
                    data = self.mt5_connector.get_market_data(symbol, timeframe, lookback)
                    if data is not None and len(data) >= 50:
                        
                        # Store basic OHLCV data
                        collected_data['timeframes'][timeframe] = {
                            'latest_close': float(data['close'].iloc[-1]),
                            'latest_volume': float(data['tick_volume'].iloc[-1]),
                            'latest_spread': float(data['spread'].iloc[-1]) if 'spread' in data.columns else 0,
                            'bars_collected': len(data)
                        }
                        
                        # Calculate comprehensive technical indicators
                        indicators = self.calculate_comprehensive_indicators(data, timeframe)
                        collected_data['indicators'][timeframe] = indicators
                        
                except Exception as e:
                    self.logger.error(f"Error collecting {timeframe} data: {e}")
                    continue
            
            # Market state analysis
            collected_data['market_state'] = self.analyze_market_state(collected_data)
            
            # Update unique indicators count
            total_indicators = sum(len(tf_indicators) for tf_indicators in collected_data['indicators'].values())
            self.stats['unique_indicators'] = max(self.stats['unique_indicators'], total_indicators)
            
            return collected_data
            
        except Exception as e:
            self.logger.error(f"Error in comprehensive data collection: {e}")
            return None
    
    def calculate_comprehensive_indicators(self, data: pd.DataFrame, timeframe: str) -> Dict:
        """Calculate comprehensive technical indicators for ML features."""
        try:
            indicators = {}
            
            # Price-based indicators
            close = data['close']
            high = data['high']
            low = data['low']
            volume = data['tick_volume']
            
            # Moving Averages
            for period in [5, 10, 20, 50]:
                indicators[f'sma_{period}'] = float(close.rolling(period).mean().iloc[-1])
                indicators[f'ema_{period}'] = float(close.ewm(span=period).mean().iloc[-1])
            
            # Price momentum
            for period in [1, 5, 10, 20]:
                if len(close) > period:
                    indicators[f'price_change_{period}'] = float(close.iloc[-1] - close.iloc[-1-period])
                    indicators[f'price_change_pct_{period}'] = float((close.iloc[-1] / close.iloc[-1-period] - 1) * 100)
            
            # Volatility indicators
            indicators['atr_14'] = float((high - low).rolling(14).mean().iloc[-1])
            indicators['volatility_20'] = float(close.rolling(20).std().iloc[-1])
            indicators['bollinger_upper'] = float(close.rolling(20).mean().iloc[-1] + 2 * close.rolling(20).std().iloc[-1])
            indicators['bollinger_lower'] = float(close.rolling(20).mean().iloc[-1] - 2 * close.rolling(20).std().iloc[-1])
            
            # RSI
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            indicators['rsi_14'] = float(100 - (100 / (1 + rs.iloc[-1])))
            
            # MACD
            ema12 = close.ewm(span=12).mean()
            ema26 = close.ewm(span=26).mean()
            macd_line = ema12 - ema26
            signal_line = macd_line.ewm(span=9).mean()
            indicators['macd'] = float(macd_line.iloc[-1])
            indicators['macd_signal'] = float(signal_line.iloc[-1])
            indicators['macd_histogram'] = float(macd_line.iloc[-1] - signal_line.iloc[-1])
            
            # Stochastic
            lowest_low = low.rolling(14).min()
            highest_high = high.rolling(14).max()
            k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
            indicators['stoch_k'] = float(k_percent.iloc[-1])
            indicators['stoch_d'] = float(k_percent.rolling(3).mean().iloc[-1])
            
            # Volume indicators
            indicators['volume_sma_20'] = float(volume.rolling(20).mean().iloc[-1])
            indicators['volume_ratio'] = float(volume.iloc[-1] / volume.rolling(20).mean().iloc[-1])
            
            # Price position indicators
            indicators['price_vs_sma20'] = float((close.iloc[-1] / close.rolling(20).mean().iloc[-1] - 1) * 100)
            indicators['price_vs_ema20'] = float((close.iloc[-1] / close.ewm(span=20).mean().iloc[-1] - 1) * 100)
            
            # Trend strength
            indicators['trend_strength_5'] = float(np.corrcoef(range(5), close.tail(5))[0, 1] if len(close) >= 5 else 0)
            indicators['trend_strength_20'] = float(np.corrcoef(range(20), close.tail(20))[0, 1] if len(close) >= 20 else 0)
            
            # Support/Resistance levels
            recent_highs = high.rolling(20).max()
            recent_lows = low.rolling(20).min()
            indicators['resistance_distance'] = float((recent_highs.iloc[-1] - close.iloc[-1]) / close.iloc[-1] * 100)
            indicators['support_distance'] = float((close.iloc[-1] - recent_lows.iloc[-1]) / close.iloc[-1] * 100)
            
            # Market structure
            indicators['higher_high'] = 1 if high.iloc[-1] > high.iloc[-2] else 0
            indicators['lower_low'] = 1 if low.iloc[-1] < low.iloc[-2] else 0
            indicators['inside_bar'] = 1 if high.iloc[-1] < high.iloc[-2] and low.iloc[-1] > low.iloc[-2] else 0
            
            # Time-based features
            now = datetime.now()
            indicators['hour'] = now.hour
            indicators['day_of_week'] = now.weekday()
            indicators['is_market_open'] = 1 if 0 <= now.hour <= 23 else 0  # Forex market
            
            # Clean up any NaN values
            for key, value in indicators.items():
                if pd.isna(value) or np.isnan(value) or np.isinf(value):
                    indicators[key] = 0.0
                else:
                    indicators[key] = float(value)
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"Error calculating indicators for {timeframe}: {e}")
            return {}
    
    def analyze_market_state(self, data: Dict) -> Dict:
        """Analyze overall market state for context."""
        try:
            market_state = {}
            
            # Overall trend analysis
            if 'M1' in data['indicators']:
                m1_indicators = data['indicators']['M1']
                
                # Trend classification
                trend_score = 0
                if 'price_vs_sma20' in m1_indicators:
                    trend_score += 1 if m1_indicators['price_vs_sma20'] > 0 else -1
                if 'macd' in m1_indicators:
                    trend_score += 1 if m1_indicators['macd'] > 0 else -1
                if 'rsi_14' in m1_indicators:
                    if m1_indicators['rsi_14'] > 60:
                        trend_score += 1
                    elif m1_indicators['rsi_14'] < 40:
                        trend_score -= 1
                
                market_state['trend_classification'] = (
                    'bullish' if trend_score > 0 else 
                    'bearish' if trend_score < 0 else 
                    'neutral'
                )
                market_state['trend_strength'] = abs(trend_score) / 3.0
                
                # Volatility state
                if 'volatility_20' in m1_indicators and 'atr_14' in m1_indicators:
                    vol_ratio = m1_indicators['volatility_20'] / max(m1_indicators['atr_14'], 0.001)
                    market_state['volatility_state'] = (
                        'high' if vol_ratio > 1.5 else
                        'low' if vol_ratio < 0.5 else
                        'normal'
                    )
                
                # Momentum state
                if 'price_change_pct_5' in m1_indicators:
                    momentum = abs(m1_indicators['price_change_pct_5'])
                    market_state['momentum_state'] = (
                        'strong' if momentum > 0.1 else
                        'weak' if momentum < 0.02 else
                        'moderate'
                    )
            
            # Multi-timeframe alignment
            timeframe_trends = []
            for tf in ['M1', 'M5', 'M15']:
                if tf in data['indicators'] and 'price_vs_sma20' in data['indicators'][tf]:
                    timeframe_trends.append(1 if data['indicators'][tf]['price_vs_sma20'] > 0 else -1)
            
            if timeframe_trends:
                alignment = sum(timeframe_trends) / len(timeframe_trends)
                market_state['timeframe_alignment'] = (
                    'aligned_bullish' if alignment > 0.6 else
                    'aligned_bearish' if alignment < -0.6 else
                    'mixed'
                )
            
            return market_state
            
        except Exception as e:
            self.logger.error(f"Error analyzing market state: {e}")
            return {}
    
    def save_collected_data(self):
        """Save collected data to files."""
        try:
            if not self.data_buffer:
                return
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save as JSON for detailed analysis
            json_filename = os.path.join(self.data_directory, f"{self.base_filename}_{timestamp}.json")
            with open(json_filename, 'w') as f:
                json.dump(self.data_buffer, f, indent=2, default=str)
            
            # Convert to DataFrame for ML processing
            flattened_data = []
            for entry in self.data_buffer:
                flat_entry = {
                    'timestamp': entry['timestamp'],
                    'symbol': entry['symbol'],
                    'bid': entry.get('current_price', {}).get('bid', 0),
                    'ask': entry.get('current_price', {}).get('ask', 0),
                    'spread': entry.get('current_price', {}).get('spread', 0)
                }
                
                # Flatten indicators for each timeframe
                for tf, indicators in entry.get('indicators', {}).items():
                    for indicator, value in indicators.items():
                        flat_entry[f"{tf}_{indicator}"] = value
                
                # Add market state
                for key, value in entry.get('market_state', {}).items():
                    flat_entry[f"market_{key}"] = value
                
                flattened_data.append(flat_entry)
            
            # Save as CSV for easy ML processing
            if flattened_data:
                df = pd.DataFrame(flattened_data)
                csv_filename = os.path.join(self.data_directory, f"{self.base_filename}_{timestamp}.csv")
                df.to_csv(csv_filename, index=False)
                
                print(f"💾 Saved {len(self.data_buffer)} data points to {csv_filename}")
                print(f"📊 CSV contains {len(df.columns)} features")
            
            # Clear buffer and update stats
            self.data_buffer.clear()
            self.last_save_time = time.time()
            self.stats['total_saves'] += 1
            
        except Exception as e:
            self.logger.error(f"Error saving collected data: {e}")
            print(f"❌ Error saving data: {e}")
    
    def print_collection_status(self):
        """Print data collection status."""
        if not self.stats['start_time']:
            return
        
        runtime = datetime.now() - self.stats['start_time']
        
        print(f"\n📊 DATA COLLECTION STATUS | Runtime: {runtime}")
        print(f"🔄 Collections: {self.stats['total_collections']}")
        print(f"📈 Collection Rate: {self.stats['collection_rate']:.2f}/sec")
        print(f"💾 Auto-saves: {self.stats['total_saves']}")
        print(f"📋 Buffer Size: {len(self.data_buffer)}")
        print(f"🎯 Data Points: {self.stats['data_points_collected']}")
        print(f"🧮 Unique Indicators: {self.stats['unique_indicators']}")
        
        if self.stats['last_collection_time']:
            time_since_last = datetime.now() - self.stats['last_collection_time']
            print(f"⏰ Last Collection: {time_since_last.total_seconds():.1f}s ago")
    
    def stop(self):
        """Stop data collection bot."""
        print("\n🛑 Stopping Data Collection Bot...")
        self.running = False
        
        # Save any remaining data
        if self.data_buffer:
            print("💾 Saving remaining data...")
            self.save_collected_data()
        
        # Final statistics
        if self.stats['start_time']:
            runtime = datetime.now() - self.stats['start_time']
            
            print(f"\n📈 FINAL COLLECTION STATISTICS:")
            print(f"⏰ Total Runtime: {runtime}")
            print(f"🔄 Total Collections: {self.stats['total_collections']}")
            print(f"📈 Average Rate: {self.stats['collection_rate']:.2f}/sec")
            print(f"💾 Total Saves: {self.stats['total_saves']}")
            print(f"🎯 Total Data Points: {self.stats['data_points_collected']}")
            print(f"🧮 Unique Indicators: {self.stats['unique_indicators']}")
        
        # Disconnect
        self.mt5_connector.disconnect()
        print("✅ Data Collection Bot stopped successfully")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\n🚨 Received signal {signum}, shutting down data collection...")
        self.running = False

def main():
    """Main entry point for data collection bot."""
    print("🚀 DATA COLLECTION BOT FOR ML TRAINING")
    print("=" * 60)
    print("📊 Collecting comprehensive XAUUSD market data")
    print("🧮 Technical indicators across multiple timeframes")
    print("💾 Auto-saving to CSV and JSON formats")
    print("=" * 60)
    
    # Get collection interval from user
    try:
        interval = input("Collection interval in seconds (default 1.0): ").strip()
        interval = float(interval) if interval else 1.0
    except ValueError:
        interval = 1.0
    
    data_bot = DataCollectionBot(collection_interval=interval)
    
    try:
        success = data_bot.start()
        if not success:
            print("❌ Failed to start data collection bot")
            sys.exit(1)
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
