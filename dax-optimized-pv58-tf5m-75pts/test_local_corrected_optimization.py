#!/usr/bin/env python3
"""
DAX Strategy - Local Test for Serverless Optimization
===================================================

This script tests the corrected strategy locally before deploying to Lambda.
It helps verify the logic and estimate performance.

Usage:
python test_local_corrected_optimization.py
"""

import json
import time
import csv
from datetime import datetime
from lambda_dax_corrected_worker_telegram import (
    StrategyConfig, DAXStrategyEngineCorrected, calculate_metrics
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

def test_single_combination():
    """Test a single parameter combination"""
    print("🧪 Testing single parameter combination...")
    
    config_dict = {
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
        'dual_position': False,
        'stop_mode': 'zone'
    }
    
    data = load_test_data()
    if not data:
        return None
    
    start_time = time.time()
    
    config = StrategyConfig(**config_dict)
    engine = DAXStrategyEngineCorrected(config)
    trades = engine.run(data)
    metrics = calculate_metrics(trades)
    
    end_time = time.time()
    runtime = end_time - start_time
    
    result = {
        'config': config_dict,
        'metrics': metrics,
        'trades_count': len(trades),
        'runtime_seconds': runtime,
        'error': None
    }
    
    print(f"✅ Single test completed in {runtime:.2f} seconds")
    print(f"📊 P&L: {metrics['total_pnl']:.1f} points")
    print(f"📈 Win Rate: {metrics['win_rate']:.1f}%")
    print(f"🎯 Trades: {metrics['total_trades']}")
    
    return result

def test_multiple_combinations():
    """Test multiple parameter combinations"""
    print("🧪 Testing multiple parameter combinations...")
    
    # Generate test combinations (smaller subset)
    test_combinations = [
        {
            'pivot_left': 5, 'pivot_right': 8, 'timeframe_minutes': 5,
            'target_points': 75.0, 'base_stop': 36.0, 'stop_mode': 'zone',
            'accumulated_loss_mode': 'none', 'reset_on_target': True,
            'target_increase_on_hit': 30.0, 'max_accumulated_loss_cap': 150.0,
            'force_exit_time': "16:55", 'dual_position': False
        },
        {
            'pivot_left': 4, 'pivot_right': 9, 'timeframe_minutes': 10,
            'target_points': 60.0, 'base_stop': 30.0, 'stop_mode': 'both',
            'accumulated_loss_mode': 'none', 'reset_on_target': True,
            'target_increase_on_hit': 25.0, 'max_accumulated_loss_cap': 120.0,
            'force_exit_time': "16:55", 'dual_position': False
        },
        {
            'pivot_left': 6, 'pivot_right': 10, 'timeframe_minutes': 15,
            'target_points': 90.0, 'base_stop': 45.0, 'stop_mode': 'distance',
            'accumulated_loss_mode': 'to_target', 'reset_on_target': True,
            'target_increase_on_hit': 35.0, 'max_accumulated_loss_cap': 180.0,
            'force_exit_time': "16:55", 'dual_position': False
        }
    ]
    
    data = load_test_data()
    if not data:
        return []
    
    results = []
    start_time = time.time()
    
    for i, config_dict in enumerate(test_combinations):
        print(f"📊 Testing combination {i+1}/{len(test_combinations)}")
        
        try:
            config = StrategyConfig(**config_dict)
            engine = DAXStrategyEngineCorrected(config)
            trades = engine.run(data)
            metrics = calculate_metrics(trades)
            
            result = {
                'config': config_dict,
                'metrics': metrics,
                'trades_count': len(trades),
                'error': None
            }
            results.append(result)
            
            print(f"   P&L: {metrics['total_pnl']:.1f} | Win Rate: {metrics['win_rate']:.1f}%")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append({
                'config': config_dict,
                'metrics': None,
                'trades_count': 0,
                'error': str(e)
            })
    
    end_time = time.time()
    total_runtime = end_time - start_time
    
    print(f"✅ Multiple tests completed in {total_runtime:.2f} seconds")
    print(f"📊 Average runtime per combination: {total_runtime/len(test_combinations):.2f} seconds")
    
    # Sort by P&L
    valid_results = [r for r in results if r['metrics'] and not r['error']]
    sorted_results = sorted(valid_results, key=lambda x: x['metrics']['total_pnl'], reverse=True)
    
    print("\n🏆 Top Results:")
    for i, result in enumerate(sorted_results[:3], 1):
        config = result['config']
        metrics = result['metrics']
        print(f"#{i} Pv {config['pivot_left']}/{config['pivot_right']} TF {config['timeframe_minutes']}m "
              f"T {config['target_points']} S {config['base_stop']} {config['stop_mode']}")
        print(f"   P&L: {metrics['total_pnl']:.1f} | Win Rate: {metrics['win_rate']:.1f}% | "
              f"PF: {metrics['profit_factor']:.2f}")
    
    return results

def estimate_lambda_performance():
    """Estimate Lambda performance and costs"""
    print("📊 Estimating Lambda performance...")
    
    single_result = test_single_combination()
    if not single_result:
        return
    
    runtime_per_combo = single_result['runtime_seconds']
    
    # Estimate for full optimization
    total_combinations = 8100  # Approximate
    chunk_size = 50
    total_chunks = (total_combinations + chunk_size - 1) // chunk_size
    
    estimated_worker_runtime = runtime_per_combo * chunk_size
    estimated_total_runtime = estimated_worker_runtime * total_chunks / 100  # 100 concurrent workers
    
    print(f"\n📊 Performance Estimates:")
    print(f"🔢 Total combinations: {total_combinations}")
    print(f"📦 Chunk size: {chunk_size}")
    print(f"📦 Total chunks: {total_chunks}")
    print(f"⚡ Runtime per combination: {runtime_per_combo:.2f} seconds")
    print(f"⚡ Worker runtime per chunk: {estimated_worker_runtime:.2f} seconds")
    print(f"⚡ Estimated total runtime: {estimated_total_runtime/60:.1f} minutes")
    print(f"💰 Estimated Lambda cost: ${estimated_total_runtime/3600 * 0.00001667 * 1536/1024:.2f}")
    
    # Telegram message estimate
    print(f"\n📱 Telegram Notifications:")
    print(f"   Start notification: 1")
    print(f"   Progress updates: {total_chunks//10}")
    print(f"   Results summary: 1")
    print(f"   Completion notification: 1")
    print(f"   Total messages: {2 + total_chunks//10}")

def main():
    """Main test function"""
    print("🧪 DAX Strategy - Local Test for Corrected Optimization")
    print("=" * 60)
    
    # Test single combination
    print("\n1️⃣ Single Combination Test:")
    single_result = test_single_combination()
    
    if single_result:
        print("\n2️⃣ Multiple Combinations Test:")
        multiple_results = test_multiple_combinations()
        
        print("\n3️⃣ Performance Estimation:")
        estimate_lambda_performance()
        
        # Save test results
        output_file = f"local_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'single_test': single_result,
                'multiple_tests': multiple_results
            }, f, indent=2)
        
        print(f"\n💾 Test results saved to: {output_file}")
        
        print("\n✅ All tests completed successfully!")
        print("🚀 Ready for Lambda deployment!")
        
    else:
        print("\n❌ Single test failed. Please check data and configuration.")

if __name__ == "__main__":
    main()
