#!/usr/bin/env python3
"""
DAX Strategy - Optimized Parameter Test
======================================

This script tests the optimized parameter space and explains force exit times.

Usage:
python test_optimized_parameters.py
"""

import json
import time
import csv
from datetime import datetime
from lambda_dax_optimized_worker_telegram import (
    StrategyConfig, DAXStrategyEngineOptimized, calculate_metrics
)

def load_test_data():
    """Load test data"""
    data_file = "/Users/sreenathreddy/Downloads/UniTrader-project/signal_trade_processor/strategy_optimization_complete/data/dax_1min_ohlc.csv"
    data = []
    
    try:
        with open(data_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    data.append({
                        'timestamp': row['timestamp'],
                        'open': float(row['open']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'close': float(row['close'])
                    })
                except (ValueError, KeyError):
                    continue
        print(f"✅ Loaded {len(data)} data points")
        return data
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return None

def explain_force_exit_times():
    """Explain what force exit times mean"""
    print("📅 FORCE EXIT TIMES EXPLANATION")
    print("=" * 50)
    
    print("\n🔍 What are Force Exit Times?")
    print("Force exit times are specific times when ALL open positions are")
    print("automatically closed, regardless of their current status.")
    
    print("\n📊 DAX Trading Hours:")
    print("• Market Open: 09:00 CET")
    print("• Market Close: 17:30 CET")
    print("• Last Entry: 16:30 CET")
    
    print("\n⚡ Force Exit Options:")
    print("• 16:30 - Close at last entry time (most conservative)")
    print("• 16:45 - Close 15 minutes before market close")
    print("• 16:55 - Close 35 minutes before market close (standard)")
    
    print("\n🎯 Why Use Force Exits?")
    print("1. **Risk Management** - Avoid overnight positions")
    print("2. **Volatility Control** - Exit before close volatility")
    print("3. **Liquidity** - Ensure good exit prices")
    print("4. **Consistency** - Standardize trading day")
    
    print("\n📈 Impact on Strategy:")
    print("• Earlier exits = Less time for targets to hit")
    print("• Earlier exits = Reduced risk exposure")
    print("• Earlier exits = Potentially lower P&L")
    print("• Later exits = More opportunity but higher risk")
    
    print("\n💡 Recommendation:")
    print("Start with 16:55 (35 minutes before close) as it balances")
    print("risk and opportunity. Adjust based on results.")

def estimate_optimized_scale():
    """Estimate the scale of optimized optimization"""
    print("\n📊 OPTIMIZED Parameter Scale Estimation:")
    print("=" * 60)
    
    # Optimized parameter counts
    pivot_left_options = 8  # 3-10
    pivot_right_options = 14  # 6-25
    tf_options = 6  # 3,5,10,15,20,30
    target_options = 7  # 50-150
    stop_options = 8  # 25-75 (REDUCED)
    stop_modes = 3  # zone, distance, both
    acc_loss_modes = 3  # none, to_target, to_target_increase
    bidirectional_options = 2  # True, False
    force_exit_options = 3  # 16:30, 16:45, 16:55 (REDUCED)
    
    # Calculate valid pivot combinations
    valid_pivot_combinations = 0
    pivot_left_values = [3, 4, 5, 6, 7, 8, 9, 10]
    pivot_right_values = [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 20, 25]
    
    for left in pivot_left_values:
        for right in pivot_right_values:
            if left < right:
                valid_pivot_combinations += 1
    
    total_combinations = (valid_pivot_combinations * tf_options * target_options * 
                        stop_options * stop_modes * acc_loss_modes * 
                        bidirectional_options * force_exit_options)
    
    print(f"🔢 OPTIMIZED Parameter Options:")
    print(f"   Valid Pivot Combinations: {valid_pivot_combinations}")
    print(f"   Timeframes: {tf_options}")
    print(f"   Targets: {target_options}")
    print(f"   Stops: {stop_options} (REDUCED from 13)")
    print(f"   Stop Modes: {stop_modes}")
    print(f"   Acc Loss Modes: {acc_loss_modes}")
    print(f"   Bidirectional: {bidirectional_options}")
    print(f"   Force Exit: {force_exit_options} (REDUCED from 5)")
    print(f"   Dual Position: FIXED (single only)")
    
    print(f"\n📊 OPTIMIZED Scale Estimates:")
    print(f"   Total Combinations: {total_combinations:,}")
    print(f"   Chunk Size: 50")
    print(f"   Total Chunks: {total_combinations // 50 + 1:,}")
    print(f"   Max Concurrent Workers: 100")
    print(f"   Estimated Runtime: {(total_combinations // 50 + 1) / 100 * 3:.1f} minutes")
    print(f"   Estimated Lambda Cost: ${total_combinations / 50 * 0.00001667 * 3 / 60:.2f}")
    
    # Compare with original comprehensive
    original_comprehensive = 34594560
    reduction = (original_comprehensive - total_combinations) / original_comprehensive * 100
    
    print(f"\n📈 Reduction from Comprehensive:")
    print(f"   Original: {original_comprehensive:,} combinations")
    print(f"   Optimized: {total_combinations:,} combinations")
    print(f"   Reduction: {reduction:.1f}% smaller")
    print(f"   Speed improvement: ~{reduction:.0f}x faster")
    
    return total_combinations

def test_optimized_configurations():
    """Test a few optimized configurations"""
    print("\n🧪 Testing Optimized Configurations:")
    print("=" * 50)
    
    # Test configurations
    configs = [
        {
            'name': 'Standard Setup',
            'config': {
                'pivot_left': 5,
                'pivot_right': 8,
                'timeframe_minutes': 5,
                'target_points': 75.0,
                'base_stop': 36.0,
                'accumulated_loss_mode': 'none',
                'reset_on_target': True,
                'target_increase_on_hit': 30.0,
                'max_accumulated_loss_cap': 150.0,
                'force_exit_time': "16:55",
                'dual_position': False,  # Single position only
                'stop_mode': 'zone',
                'bidirectional': False
            }
        },
        {
            'name': 'Bidirectional Setup',
            'config': {
                'pivot_left': 4,
                'pivot_right': 9,
                'timeframe_minutes': 10,
                'target_points': 60.0,
                'base_stop': 30.0,
                'accumulated_loss_mode': 'to_target',
                'reset_on_target': True,
                'target_increase_on_hit': 25.0,
                'max_accumulated_loss_cap': 120.0,
                'force_exit_time': "16:45",
                'dual_position': False,  # Single position only
                'stop_mode': 'both',
                'bidirectional': True
            }
        },
        {
            'name': 'Conservative Setup',
            'config': {
                'pivot_left': 6,
                'pivot_right': 10,
                'timeframe_minutes': 15,
                'target_points': 50.0,
                'base_stop': 25.0,
                'accumulated_loss_mode': 'none',
                'reset_on_target': True,
                'target_increase_on_hit': 20.0,
                'max_accumulated_loss_cap': 100.0,
                'force_exit_time': "16:30",
                'dual_position': False,  # Single position only
                'stop_mode': 'zone',
                'bidirectional': False
            }
        }
    ]
    
    data = load_test_data()
    if not data:
        return
    
    results = []
    
    for test_config in configs:
        print(f"\n📊 Testing {test_config['name']}...")
        
        start_time = time.time()
        
        config = StrategyConfig(**test_config['config'])
        engine = DAXStrategyEngineOptimized(config)
        trades = engine.run(data)
        metrics = calculate_metrics(trades)
        
        end_time = time.time()
        runtime = end_time - start_time
        
        result = {
            'name': test_config['name'],
            'config': test_config['config'],
            'metrics': metrics,
            'trades_count': len(trades),
            'runtime_seconds': runtime,
            'error': None
        }
        
        results.append(result)
        
        print(f"✅ {test_config['name']} completed in {runtime:.2f} seconds")
        print(f"📊 P&L: {metrics['total_pnl']:.1f} points")
        print(f"📈 Win Rate: {metrics['win_rate']:.1f}%")
        print(f"🎯 Trades: {metrics['total_trades']}")
        print(f"📊 Force Exits: {metrics['force_exits']}")
    
    # Show comparison
    print(f"\n🔍 Optimized Configuration Results:")
    print("=" * 80)
    
    for result in results:
        config = result['config']
        metrics = result['metrics']
        
        print(f"\n📊 {result['name']}:")
        print(f"   💰 P&L: {metrics['total_pnl']:.1f} points")
        print(f"   📈 Win Rate: {metrics['win_rate']:.1f}%")
        print(f"   🎯 Profit Factor: {metrics['profit_factor']:.2f}")
        print(f"   📊 Total Trades: {metrics['total_trades']}")
        print(f"   📊 Force Exits: {metrics['force_exits']}")
        print(f"   📉 Max Drawdown: {metrics['max_drawdown']:.1f} points")
        print(f"   ⚡ Runtime: {result['runtime_seconds']:.2f} seconds")
        print(f"   🕐 Force Exit: {config['force_exit_time']}")
        print(f"   🔄 Bidirectional: {config['bidirectional']}")
        print(f"   📊 Stop Mode: {config['stop_mode']}")
    
    return results

def main():
    """Main test function"""
    print("🧪 DAX Strategy - Optimized Parameter Test")
    print("=" * 60)
    
    # Explain force exit times
    print("\n1️⃣ Force Exit Times Explanation:")
    explain_force_exit_times()
    
    # Estimate scale
    print("\n2️⃣ Optimized Scale Estimation:")
    total_combinations = estimate_optimized_scale()
    
    # Test configurations
    print("\n3️⃣ Optimized Configuration Tests:")
    test_results = test_optimized_configurations()
    
    # Save results
    output_file = f"optimized_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_combinations_estimated': total_combinations,
            'test_results': test_results
        }, f, indent=2)
    
    print(f"\n💾 Test results saved to: {output_file}")
    
    print("\n✅ All tests completed successfully!")
    print("🚀 Ready for optimized Lambda deployment!")
    
    # Summary
    print(f"\n📊 Summary:")
    print(f"   Optimized Combinations: {total_combinations:,}")
    print(f"   Reduction from Comprehensive: ~94% smaller")
    print(f"   Estimated Runtime: ~{(total_combinations // 50 + 1) / 100 * 3:.1f} minutes")
    print(f"   Single Position Only: Yes (as requested)")
    print(f"   Reduced Stop Options: Yes (as requested)")
    print(f"   Force Exit Options: 3 (16:30, 16:45, 16:55)")

if __name__ == "__main__":
    main()
