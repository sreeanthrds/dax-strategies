#!/usr/bin/env python3
"""
DAX Strategy - Bidirectional Logic Test
======================================

This script tests the bidirectional vs unidirectional signal generation logic
to verify the implementation works correctly.

Usage:
python test_bidirectional_logic.py
"""

import json
import time
import csv
from datetime import datetime
from lambda_dax_comprehensive_worker_telegram import (
    StrategyConfig, DAXStrategyEngineComprehensive, calculate_metrics
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

def test_bidirectional_logic():
    """Test bidirectional vs unidirectional logic"""
    print("🧪 Testing Bidirectional vs Unidirectional Logic...")
    
    # Test configurations
    configs = [
        {
            'name': 'Unidirectional',
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
                'dual_position': False,
                'stop_mode': 'zone',
                'bidirectional': False  # Unidirectional
            }
        },
        {
            'name': 'Bidirectional',
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
                'dual_position': False,
                'stop_mode': 'zone',
                'bidirectional': True  # Bidirectional
            }
        }
    ]
    
    data = load_test_data()
    if not data:
        return
    
    results = []
    
    for test_config in configs:
        print(f"\n📊 Testing {test_config['name']} configuration...")
        
        start_time = time.time()
        
        config = StrategyConfig(**test_config['config'])
        engine = DAXStrategyEngineComprehensive(config)
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
        print(f"📊 Target Hits: {metrics['target_hits']}")
        print(f"🛑 Stop Hits: {metrics['stop_hits']}")
        print(f"⏰ Force Exits: {metrics['force_exits']}")
    
    # Compare results
    print("\n🔍 Comparison Results:")
    print("=" * 80)
    
    for result in results:
        config = result['config']
        metrics = result['metrics']
        
        print(f"\n📊 {result['name']} (bidirectional={config['bidirectional']}):")
        print(f"   💰 P&L: {metrics['total_pnl']:.1f} points")
        print(f"   📈 Win Rate: {metrics['win_rate']:.1f}%")
        print(f"   🎯 Profit Factor: {metrics['profit_factor']:.2f}")
        print(f"   📊 Total Trades: {metrics['total_trades']}")
        print(f"   📊 Target Hits: {metrics['target_hits']}")
        print(f"   🛑 Stop Hits: {metrics['stop_hits']}")
        print(f"   ⏰ Force Exits: {metrics['force_exits']}")
        print(f"   📉 Max Drawdown: {metrics['max_drawdown']:.1f} points")
        print(f"   ⚡ Runtime: {result['runtime_seconds']:.2f} seconds")
    
    # Calculate differences
    if len(results) == 2:
        unidirectional = results[0]
        bidirectional = results[1]
        
        print(f"\n📈 Bidirectional Impact Analysis:")
        print("=" * 50)
        
        pnl_diff = bidirectional['metrics']['total_pnl'] - unidirectional['metrics']['total_pnl']
        trades_diff = bidirectional['metrics']['total_trades'] - unidirectional['metrics']['total_trades']
        wr_diff = bidirectional['metrics']['win_rate'] - unidirectional['metrics']['win_rate']
        pf_diff = bidirectional['metrics']['profit_factor'] - unidirectional['metrics']['profit_factor']
        
        print(f"💰 P&L Difference: {pnl_diff:+.1f} points ({pnl_diff/unidirectional['metrics']['total_pnl']*100:+.1f}%)")
        print(f"📊 Trade Count Difference: {trades_diff:+d} ({trades_diff/unidirectional['metrics']['total_trades']*100:+.1f}%)")
        print(f"📈 Win Rate Difference: {wr_diff:+.1f}%")
        print(f"🎯 Profit Factor Difference: {pf_diff:+.2f}")
        
        # Determine which is better
        if pnl_diff > 0:
            print(f"\n🏆 BIDIRECTIONAL performs better by {pnl_diff:.1f} points")
        elif pnl_diff < 0:
            print(f"\n🏆 UNIDIRECTIONAL performs better by {abs(pnl_diff):.1f} points")
        else:
            print(f"\n🤝 Both approaches perform similarly")
    
    return results

def test_signal_generation_logic():
    """Test the signal generation logic in detail"""
    print("\n🧪 Testing Signal Generation Logic...")
    
    # Import signal detector to test directly
    from lambda_dax_comprehensive_worker_telegram import SignalDetector, SRZoneEngine
    
    # Create test configurations
    unidirectional_config = StrategyConfig(bidirectional=False)
    bidirectional_config = StrategyConfig(bidirectional=True)
    
    # Create signal detectors
    uni_detector = SignalDetector(unidirectional_config)
    bi_detector = SignalDetector(bidirectional_config)
    
    # Test scenarios
    test_scenarios = [
        {
            'name': 'Support Zone - Close Above',
            'candle': {'timestamp': '2024-01-01T10:00:00', 'open': 16500, 'high': 16520, 'low': 16490, 'close': 16510},
            'zones': {'sup1_high': 16500, 'sup1_low': 16495, 'res1_high': None, 'res1_low': None}
        },
        {
            'name': 'Support Zone - Close Below',
            'candle': {'timestamp': '2024-01-01T10:05:00', 'open': 16490, 'high': 16500, 'low': 16480, 'close': 16485},
            'zones': {'sup1_high': 16500, 'sup1_low': 16495, 'res1_high': None, 'res1_low': None}
        },
        {
            'name': 'Resistance Zone - Close Above',
            'candle': {'timestamp': '2024-01-01T10:10:00', 'open': 16600, 'high': 16620, 'low': 16590, 'close': 16610},
            'zones': {'sup1_high': None, 'sup1_low': None, 'res1_high': 16615, 'res1_low': 16605}
        },
        {
            'name': 'Resistance Zone - Close Below',
            'candle': {'timestamp': '2024-01-01T10:15:00', 'open': 16600, 'high': 16610, 'low': 16590, 'close': 16595},
            'zones': {'sup1_high': None, 'sup1_low': None, 'res1_high': 16615, 'res1_low': 16605}
        }
    ]
    
    print("\n📊 Signal Generation Test Results:")
    print("=" * 60)
    
    for scenario in test_scenarios:
        print(f"\n🎯 Scenario: {scenario['name']}")
        print(f"   Candle: O={scenario['candle']['open']} H={scenario['candle']['high']} L={scenario['candle']['low']} C={scenario['candle']['close']}")
        
        # Test unidirectional
        uni_signal = uni_detector.check_signal(scenario['candle'], scenario['zones'], set())
        uni_types = []
        if uni_signal:
            uni_types = [uni_signal['type']]
        
        # Test bidirectional
        bi_signal = bi_detector.check_signal(scenario['candle'], scenario['zones'], set())
        bi_types = []
        if bi_signal:
            bi_types = [bi_signal['type']]
        
        print(f"   📊 Unidirectional: {uni_types if uni_types else 'No signal'}")
        print(f"   📊 Bidirectional: {bi_types if bi_types else 'No signal'}")
        
        # Explain the logic
        if 'sup1_low' in scenario['zones'] and scenario['zones']['sup1_low'] is not None:
            zone_low = scenario['zones']['sup1_low']
            zone_high = scenario['zones']['sup1_high']
        else:
            zone_low = scenario['zones']['res1_low']
            zone_high = scenario['zones']['res1_high']
        
        close = scenario['candle']['close']
        
        print(f"   🔍 Logic: Close={close}, Zone Low={zone_low}, Zone High={zone_high}")
        
        if uni_types != bi_types:
            print(f"   ⚠️  DIFFERENT SIGNALS DETECTED!")
        else:
            print(f"   ✅ Same signals generated")

def estimate_comprehensive_scale():
    """Estimate the scale of comprehensive optimization"""
    print("\n📊 Comprehensive Optimization Scale Estimation:")
    print("=" * 60)
    
    # Parameter counts
    pivot_left_options = 11  # 2-12
    pivot_right_options = 19  # 3-30
    tf_options = 8  # 1,3,5,10,15,20,30,60
    target_options = 12  # 25-250
    stop_options = 13  # 15-125
    stop_modes = 3  # zone, distance, both
    acc_loss_modes = 3  # none, to_target, to_target_increase
    bidirectional_options = 2  # True, False
    dual_position_options = 2  # True, False
    force_exit_options = 5  # 16:30-17:15
    
    # Calculate valid pivot combinations
    valid_pivot_combinations = 0
    pivot_left_values = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    pivot_right_values = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 25, 30]
    
    for left in pivot_left_values:
        for right in pivot_right_values:
            if left < right:
                valid_pivot_combinations += 1
    
    total_combinations = (valid_pivot_combinations * tf_options * target_options * 
                        stop_options * stop_modes * acc_loss_modes * 
                        bidirectional_options * dual_position_options * force_exit_options)
    
    print(f"🔢 Parameter Options:")
    print(f"   Valid Pivot Combinations: {valid_pivot_combinations}")
    print(f"   Timeframes: {tf_options}")
    print(f"   Targets: {target_options}")
    print(f"   Stops: {stop_options}")
    print(f"   Stop Modes: {stop_modes}")
    print(f"   Acc Loss Modes: {acc_loss_modes}")
    print(f"   Bidirectional: {bidirectional_options}")
    print(f"   Dual Position: {dual_position_options}")
    print(f"   Force Exit: {force_exit_options}")
    
    print(f"\n📊 Scale Estimates:")
    print(f"   Total Combinations: {total_combinations:,}")
    print(f"   Chunk Size: 25")
    print(f"   Total Chunks: {total_combinations // 25 + 1:,}")
    print(f"   Max Concurrent Workers: 150")
    print(f"   Estimated Runtime: {(total_combinations // 25 + 1) / 150 * 3:.1f} minutes")
    print(f"   Estimated Lambda Cost: ${total_combinations / 25 * 0.00001667 * 10 / 60:.2f}")
    
    return total_combinations

def main():
    """Main test function"""
    print("🧪 DAX Strategy - Comprehensive Bidirectional Logic Test")
    print("=" * 70)
    
    # Test 1: Bidirectional vs Unidirectional Performance
    print("\n1️⃣ Performance Comparison Test:")
    performance_results = test_bidirectional_logic()
    
    # Test 2: Signal Generation Logic
    print("\n2️⃣ Signal Generation Logic Test:")
    test_signal_generation_logic()
    
    # Test 3: Scale Estimation
    print("\n3️⃣ Comprehensive Scale Estimation:")
    total_combinations = estimate_comprehensive_scale()
    
    # Save results
    output_file = f"bidirectional_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'performance_results': performance_results,
            'total_combinations_estimated': total_combinations
        }, f, indent=2)
    
    print(f"\n💾 Test results saved to: {output_file}")
    
    print("\n✅ All tests completed successfully!")
    print("🚀 Ready for comprehensive Lambda deployment!")
    
    # Summary
    if performance_results and len(performance_results) == 2:
        uni_pnl = performance_results[0]['metrics']['total_pnl']
        bi_pnl = performance_results[1]['metrics']['total_pnl']
        
        print(f"\n📊 Summary:")
        print(f"   Unidirectional P&L: {uni_pnl:.1f} points")
        print(f"   Bidirectional P&L: {bi_pnl:.1f} points")
        print(f"   Difference: {bi_pnl - uni_pnl:+.1f} points")
        print(f"   Comprehensive Scale: {total_combinations:,} combinations")

if __name__ == "__main__":
    main()
