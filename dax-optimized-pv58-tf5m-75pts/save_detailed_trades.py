#!/usr/bin/env python3
"""
Save Detailed Trades to CSV File
Exports all 730 trades with full details
"""

import pandas as pd
from datetime import datetime, time as dt_time
import sys
import os

# Add the path to the DAX strategy
sys.path.append('/Users/sreenathreddy/Downloads/UniTrader-project')

from dax_strategy_rebuilt import DAXStrategyEngine, StrategyConfig

def load_dax_1min_data(file_path):
    """Load DAX 1-minute OHLC data"""
    print(f"Loading DAX 1-minute data from {file_path}...")
    
    # Read the CSV file
    df = pd.read_csv(file_path)
    print(f"Loaded {len(df):,} 1-minute records")
    
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Filter for DAX trading hours (9:00-16:30) AND weekdays only
    df = df[(df['timestamp'].dt.hour >= 9) & (df['timestamp'].dt.hour < 17)]
    df = df[df['timestamp'].dt.dayofweek < 5]  # 0-4 = Monday-Friday
    print(f"Filtered to trading hours and weekdays: {len(df):,} records")
    
    # Convert to list of dictionaries for strategy engine
    data = []
    for _, row in df.iterrows():
        data.append({
            "timestamp": row['timestamp'].isoformat(),
            "open": float(row['open']),
            "high": float(row['high']),
            "low": float(row['low']),
            "close": float(row['close'])
        })
    
    return data

def save_trades_to_csv(trades, filename):
    """Save trades to CSV file with all details"""
    if not trades:
        print("❌ No trades to save")
        return
    
    # Prepare data for CSV
    trades_data = []
    for trade in trades:
        trades_data.append({
            'trade_id': trade['trade_id'],
            'signal_type': trade['signal_type'],
            'zone_name': trade['zone_name'],
            'entry_time': trade['entry_time'],
            'entry_price': trade['entry_price'],
            'target_price': trade['target_price'],
            'exit_time': trade['exit_time'],
            'exit_price': trade['exit_price'],
            'exit_type': trade['exit_type'],
            'pnl': trade['pnl'],
            'hold_duration': trade['hold_duration'],
            'entry_date': trade['entry_time'][:10],
            'exit_date': trade['exit_time'][:10],
            'entry_hour': trade['entry_time'][11:16],
            'exit_hour': trade['exit_time'][11:16]
        })
    
    # Create DataFrame and save
    df_trades = pd.DataFrame(trades_data)
    df_trades.to_csv(filename, index=False)
    
    print(f"✅ Saved {len(trades)} trades to {filename}")
    
    # Show summary
    print(f"\n📊 Trades File Summary:")
    print(f"  Total Trades: {len(trades)}")
    print(f"  BUY Trades: {len([t for t in trades if t['signal_type'] == 'BUY'])}")
    print(f"  SELL Trades: {len([t for t in trades if t['signal_type'] == 'SELL'])}")
    print(f"  Total P&L: {sum(t['pnl'] for t in trades):+.2f} points")
    print(f"  Winning Trades: {len([t for t in trades if t['pnl'] > 0])}")
    print(f"  Losing Trades: {len([t for t in trades if t['pnl'] < 0])}")
    
    return df_trades

def main():
    """Generate and save detailed trades"""
    print("=" * 80)
    print("💾 SAVING DETAILED DAX TRADES TO CSV")
    print("=" * 80)
    
    # Load data
    data_file = "/Users/sreenathreddy/Downloads/UniTrader-project/signal_trade_processor/strategy_optimization_complete/data/dax_1min_ohlc.csv"
    data = load_dax_1min_data(data_file)
    
    if not data:
        print("❌ No data loaded")
        return
    
    # Best configuration from optimization
    config = StrategyConfig(
        pivot_left=5,
        pivot_right=10,
        timeframe_minutes=15,
        target_points=125,
        base_stop=60.0,
        accumulated_loss_mode='to_target_increase',
        reset_on_target=True,
        target_increase_on_hit=50.0,
        max_accumulated_loss_cap=250,
        force_exit_time="16:55",
        dual_position=False,
        stop_mode='both'
    )
    
    print(f"\n🎯 Running Strategy with Best Configuration:")
    print(f"  Pivot: {config.pivot_left}/{config.pivot_right}")
    print(f"  Timeframe: {config.timeframe_minutes} minutes")
    print(f"  Target: {config.target_points} points")
    print(f"  Stop Mode: {config.stop_mode}")
    print(f"  Accumulated Loss Mode: {config.accumulated_loss_mode}")
    
    # Run strategy
    engine = DAXStrategyEngine(config)
    trades = engine.run(data)
    
    # Save trades to CSV
    output_file = "/Users/sreenathreddy/Downloads/UniTrader-project/dax_detailed_trades_8966_points.csv"
    df_trades = save_trades_to_csv(trades, output_file)
    
    # Show sample of saved data
    print(f"\n📋 Sample of Saved Trades (First 5):")
    print(df_trades.head().to_string())
    
    print(f"\n" + "=" * 80)
    print(f"✅ DETAILED TRADES SAVED SUCCESSFULLY")
    print(f"📁 File: {output_file}")
    print(f"📊 Trades: {len(trades)}")
    print(f"💰 Performance: +{sum(t['pnl'] for t in trades):.2f} points")
    print("=" * 80)

if __name__ == "__main__":
    main()
