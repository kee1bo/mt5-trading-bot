#!/usr/bin/env python3
"""
Simple Data Collection Bot - Auto-starts with 1 second interval
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

class SimpleDataCollectionBot:
    """
    Simple data collection bot that auto-starts with sensible defaults.
    """
    
    def __init__(self):
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.mt5_connector = MT5Connector()
        self.collection_interval = 1.0  # Fixed 1 second interval
        self.running = False
        
        # Data storage
        self.data_buffer = []
        self.max_buffer_size = 100  # Smaller buffer for faster saves
        self.last_save_time = time.time()
        self.save_interval = 60  # Save every minute
        
        # File management
        self.base_filename = "xauusd_ml_data"
        self.data_directory = "ml_data"
        os.makedirs(self.data_directory, exist_ok=True)
        
        # Collection statistics
        self.stats = {
            'start_time': None,
            'total_collections': 0,
            'total_saves': 0,
            'data_points_collected': 0,
        }
        
        # Signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def setup_logging(self):
        """Setup logging for data collection bot."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('simple_data_collection.log'),
                logging.StreamHandler()
            ]
        )
    
    def start(self):
        """Start data collection bot."""
        print("🚀 Starting Simple Data Collection Bot")
        print("=" * 50)
        
        # Connect to MT5
        if not self.mt5_connector.connect():
            print("❌ Failed to connect to MT5")
            return False
        
        print("✅ Data Collection Bot connected to MT5")
        print(f"📊 Collection Interval: {self.collection_interval}s")
        print(f"💾 Data Directory: {self.data_directory}")
        print("=" * 50)
        
        self.running = True
        self.stats['start_time'] = datetime.now()
        
        return self.run_collection_loop()
    
    def run_collection_loop(self):
        """Main data collection loop."""
        print("🔄 Starting data collection...")
        
        symbol = 'XAUUSD'
        timeframe = 'M1'
        lookback_periods = 50
        
        last_status_time = time.time()
        
        try:
            while self.running:
                collection_start = time.time()
                
                # Collect basic market data
                data = self.mt5_connector.get_market_data(symbol, timeframe, lookback_periods)
                if data is not None and len(data) >= 20:
                    
                    # Create simple feature set
                    features = self.create_simple_features(data)
                    if features:
                        
                        # Add timestamp and price info
                        current_price = self.mt5_connector.get_current_price(symbol)
                        if current_price:
                            features.update({
                                'timestamp': datetime.now().isoformat(),
                                'bid': current_price.get('bid', 0),
                                'ask': current_price.get('ask', 0),
                                'spread': current_price.get('ask', 0) - current_price.get('bid', 0)
                            })
                        
                        self.data_buffer.append(features)
                        self.stats['total_collections'] += 1
                        self.stats['data_points_collected'] += len(features)
                        
                        # Check if buffer needs saving
                        if (len(self.data_buffer) >= self.max_buffer_size or 
                            time.time() - self.last_save_time >= self.save_interval):
                            self.save_data()
                
                # Status update every 30 seconds
                if time.time() - last_status_time >= 30:
                    self.print_status()
                    last_status_time = time.time()
                
                # Sleep for collection interval
                collection_time = time.time() - collection_start
                sleep_time = max(0.1, self.collection_interval - collection_time)
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            print("\n🛑 Data collection shutdown requested...")
        except Exception as e:
            print(f"❌ Data collection error: {e}")
            self.logger.error(f"Collection error: {e}")
        finally:
            self.stop()
    
    def create_simple_features(self, data: pd.DataFrame) -> Dict:
        """Create simple feature set for ML."""
        try:
            features = {}
            
            close = data['close']
            high = data['high']
            low = data['low']
            volume = data['tick_volume']
            
            # Current price features
            features['close_price'] = float(close.iloc[-1])
            features['high_price'] = float(high.iloc[-1])
            features['low_price'] = float(low.iloc[-1])
            features['volume'] = float(volume.iloc[-1])
            
            # Simple moving averages
            features['sma_5'] = float(close.rolling(5).mean().iloc[-1])
            features['sma_10'] = float(close.rolling(10).mean().iloc[-1])
            features['sma_20'] = float(close.rolling(20).mean().iloc[-1])
            
            # Price changes
            features['price_change_1'] = float(close.iloc[-1] - close.iloc[-2])
            features['price_change_5'] = float(close.iloc[-1] - close.iloc[-6])
            
            # Simple indicators
            features['rsi'] = self.calculate_rsi(close, 14)
            features['atr'] = float((high - low).rolling(14).mean().iloc[-1])
            
            # Volatility
            features['volatility'] = float(close.rolling(20).std().iloc[-1])
            
            # Price position
            features['price_vs_sma20'] = float((close.iloc[-1] / features['sma_20'] - 1) * 100)
            
            # Market time features
            now = datetime.now()
            features['hour'] = now.hour
            features['day_of_week'] = now.weekday()
            
            # Clean NaN values
            for key, value in features.items():
                if pd.isna(value) or np.isnan(value) or np.isinf(value):
                    features[key] = 0.0
            
            return features
            
        except Exception as e:
            self.logger.error(f"Error creating features: {e}")
            return {}
    
    def calculate_rsi(self, prices, period=14):
        """Calculate RSI indicator."""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return float(rsi.iloc[-1])
        except:
            return 50.0  # Default RSI value
    
    def save_data(self):
        """Save collected data to CSV."""
        try:
            if not self.data_buffer:
                return
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Convert to DataFrame
            df = pd.DataFrame(self.data_buffer)
            
            # Save as CSV
            csv_filename = os.path.join(self.data_directory, f"{self.base_filename}_{timestamp}.csv")
            df.to_csv(csv_filename, index=False)
            
            print(f"💾 Saved {len(self.data_buffer)} records to {csv_filename}")
            print(f"📊 Features: {len(df.columns)}")
            
            # Clear buffer and update stats
            self.data_buffer.clear()
            self.last_save_time = time.time()
            self.stats['total_saves'] += 1
            
        except Exception as e:
            self.logger.error(f"Error saving data: {e}")
    
    def print_status(self):
        """Print collection status."""
        if not self.stats['start_time']:
            return
        
        runtime = datetime.now() - self.stats['start_time']
        rate = self.stats['total_collections'] / runtime.total_seconds() if runtime.total_seconds() > 0 else 0
        
        print(f"\n📊 DATA COLLECTION STATUS | Runtime: {runtime}")
        print(f"🔄 Collections: {self.stats['total_collections']} | Rate: {rate:.2f}/sec")
        print(f"💾 Saves: {self.stats['total_saves']} | Buffer: {len(self.data_buffer)}")
        print(f"🎯 Data Points: {self.stats['data_points_collected']}")
    
    def stop(self):
        """Stop data collection bot."""
        print("\n🛑 Stopping Data Collection...")
        self.running = False
        
        # Save any remaining data
        if self.data_buffer:
            self.save_data()
        
        # Final statistics
        if self.stats['start_time']:
            runtime = datetime.now() - self.stats['start_time']
            print(f"\n📈 FINAL STATISTICS:")
            print(f"⏰ Runtime: {runtime}")
            print(f"🔄 Collections: {self.stats['total_collections']}")
            print(f"💾 Saves: {self.stats['total_saves']}")
            print(f"🎯 Data Points: {self.stats['data_points_collected']}")
        
        self.mt5_connector.disconnect()
        print("✅ Data Collection stopped")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print(f"\n🚨 Signal {signum} received, stopping...")
        self.running = False

def main():
    """Main entry point."""
    print("🚀 SIMPLE DATA COLLECTION BOT")
    print("📊 Auto-collecting XAUUSD data for ML training")
    print("=" * 50)
    
    bot = SimpleDataCollectionBot()
    
    try:
        success = bot.start()
        if not success:
            print("❌ Failed to start data collection")
            sys.exit(1)
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
