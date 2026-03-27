#!/usr/bin/env python3
"""
Local Comprehensive DAX Strategy Optimizer
Simulates the serverless optimization locally with progress tracking
"""

import json
import sys
import os
from datetime import datetime, time as dt_time
from typing import Dict, List, Tuple
import pandas as pd
import concurrent.futures
import math

# Add the path to the DAX strategy
sys.path.append('/Users/sreenathreddy/Downloads/UniTrader-project')

from dax_strategy_rebuilt import DAXStrategyEngine, StrategyConfig

def load_dax_1min_data(file_path: str) -> List[Dict]:
    """Load DAX 1-minute OHLC data"""
    try:
        df = pd.read_csv(file_path)
        print(f"Loaded {len(df):,} 1-minute records")
        
        # Convert timestamp to datetime objects properly
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed')
        
        # Filter for trading hours (9:00-16:30) AND weekdays only
        df = df[
            (df['timestamp'].dt.time >= dt_time(9, 0)) & 
            (df['timestamp'].dt.time <= dt_time(16, 30))
        ]
        df = df[df['timestamp'].dt.dayofweek < 5]  # Weekdays only
        
        print(f"Filtered to {len(df):,} trading hours records")
        
        # Convert to list of dictionaries
        data = []
        for _, row in df.iterrows():
            data.append({
                'timestamp': row['timestamp'].isoformat(),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': 0
            })
        
        return data
        
    except Exception as e:
        print(f"Error loading data: {e}")
        return []

def calculate_performance_metrics(trades: List[Dict]) -> Dict:
    """Calculate comprehensive performance metrics"""
    if not trades:
        return {
            'total_trades': 0,
            'total_pnl': 0,
            'win_rate': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'profit_factor': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'max_win': 0,
            'max_loss': 0,
            'target_hits': 0,
            'stop_hits': 0,
            'force_exits': 0,
            'score': 0
        }
    
    # Basic metrics
    total_trades = len(trades)
    total_pnl = sum(trade['pnl'] for trade in trades)
    winning_trades = [t for t in trades if t['pnl'] > 0]
    losing_trades = [t for t in trades if t['pnl'] < 0]
    win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
    
    # P&L metrics
    avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
    avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0
    max_win = max(t['pnl'] for t in trades) if trades else 0
    max_loss = min(t['pnl'] for t in trades) if trades else 0
    
    # Exit types
    target_hits = len([t for t in trades if t.get('exit_type') == 'TARGET'])
    stop_hits = len([t for t in trades if t.get('exit_type') == 'STOP_LOSS'])
    force_exits = len([t for t in trades if t.get('exit_type') == 'FORCE_EXIT'])
    
    # Risk metrics
    profit_factor = abs(sum(t['pnl'] for t in winning_trades) / sum(t['pnl'] for t in losing_trades)) if losing_trades and sum(t['pnl'] for t in losing_trades) != 0 else 0
    
    # Calculate running P&L for drawdown
    running_pnl = []
    cumulative_pnl = 0
    for trade in trades:
        cumulative_pnl += trade['pnl']
        running_pnl.append(cumulative_pnl)
    
    # Max drawdown
    if running_pnl:
        peak = running_pnl[0]
        max_drawdown = 0
        for pnl in running_pnl:
            if pnl > peak:
                peak = pnl
            drawdown = peak - pnl
            if drawdown > max_drawdown:
                max_drawdown = drawdown
    else:
        max_drawdown = 0
    
    # Sharpe ratio (simplified)
    if trades:
        returns = [trade['pnl'] for trade in trades]
        avg_return = sum(returns) / len(returns)
        if len(returns) > 1:
            variance = sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
            std_dev = variance ** 0.5
            sharpe_ratio = avg_return / std_dev if std_dev > 0 else 0
        else:
            sharpe_ratio = 0
    else:
        sharpe_ratio = 0
    
    # Composite score (weighted)
    score = (
        total_pnl * 0.3 +                    # Total profit
        sharpe_ratio * 100 * 0.25 +           # Risk-adjusted returns
        win_rate * 10 * 0.2 +                 # Win rate
        profit_factor * 50 * 0.15 +           # Profit factor
        (max_drawdown * -0.1)                 # Penalty for drawdown
    )
    
    return {
        'total_trades': total_trades,
        'total_pnl': total_pnl,
        'win_rate': win_rate,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'profit_factor': profit_factor,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'max_win': max_win,
        'max_loss': max_loss,
        'target_hits': target_hits,
        'stop_hits': stop_hits,
        'force_exits': force_exits,
        'score': score
    }

def run_strategy_test(config: StrategyConfig, data: List[Dict]) -> Dict:
    """Run strategy test with given configuration"""
    try:
        engine = DAXStrategyEngine(config)
        trades = engine.run(data)
        metrics = calculate_performance_metrics(trades)
        return metrics
    except Exception as e:
        print(f"Error running strategy: {e}")
        return None

def generate_all_combinations():
    """Generate ALL parameter combinations (left >= right allowed)"""
    
    # ALL pivot combinations - no restrictions on left >= right
    pivot_left_options = [3, 5, 8, 10, 15, 20]
    pivot_right_options = [8, 10, 13, 15, 20, 25]
    
    # Generate ALL possible pivot combinations
    pivot_combinations = []
    for left in pivot_left_options:
        for right in pivot_right_options:
            pivot_combinations.append((left, right))
    
    timeframes = [5, 10, 15, 30, 60]
    targets = [75, 100, 125, 150, 200]
    stop_modes = ['zone', 'distance', 'both']
    accumulated_loss_modes = ['none', 'fixed', 'to_target_increase']
    
    combinations = []
    
    for pivot_left, pivot_right in pivot_combinations:
        for timeframe in timeframes:
            for target in targets:
                for stop_mode in stop_modes:
                    for acc_loss_mode in accumulated_loss_modes:
                        
                        config = {
                            'pivot_left': pivot_left,
                            'pivot_right': pivot_right,
                            'timeframe_minutes': timeframe,
                            'target_points': target,
                            'base_stop': target * 0.48,
                            'stop_mode': stop_mode,
                            'accumulated_loss_mode': acc_loss_mode,
                            'reset_on_target': True,
                            'target_increase_on_hit': target * 0.4,
                            'max_accumulated_loss_cap': target * 2,
                            'force_exit_time': "16:55",
                            'dual_position': False
                        }
                        
                        combinations.append(config)
    
    return combinations

def split_combinations_for_parallel(combinations: List[Dict], num_workers: int = 8) -> List[List[Dict]]:
    """Split combinations into chunks for parallel processing"""
    chunk_size = math.ceil(len(combinations) / num_workers)
    chunks = []
    
    for i in range(0, len(combinations), chunk_size):
        chunk = combinations[i:i + chunk_size]
        chunks.append(chunk)
    
    return chunks

def worker_function(combinations_chunk: List[Dict], worker_id: int, data: List[Dict]) -> List[Dict]:
    """Worker function for processing a chunk of combinations"""
    results = []
    best_score = 0
    best_config = None
    
    for i, params in enumerate(combinations_chunk):
        try:
            # Create configuration
            config = StrategyConfig(**params)
            
            # Run test
            metrics = run_strategy_test(config, data)
            
            if metrics:
                result = {
                    'config': params,
                    'metrics': metrics
                }
                results.append(result)
                
                # Track best result in this chunk
                if metrics['score'] > best_score:
                    best_score = metrics['score']
                    best_config = params
                    best_metrics = metrics
            
            # Progress indicator
            if (i + 1) % 10 == 0:
                progress = ((i + 1) / len(combinations_chunk)) * 100
                print(f"  Worker {worker_id}: {i + 1}/{len(combinations_chunk)} completed ({progress:.1f}%)")
                
        except Exception as e:
            print(f"  Worker {worker_id}: Error in combination {i}: {e}")
            continue
    
    print(f"✅ Worker {worker_id}: Completed {len(results)} successful tests")
    if best_config:
        print(f"  🏆 Best in chunk: Pv {best_config['pivot_left']}/{best_config['pivot_right']} TF {best_config['timeframe_minutes']}m T {best_config['target_points']} - Score: {best_score:.1f}")
    
    return results

def main():
    """Main optimization function"""
    
    start_time = datetime.now()
    
    print("=" * 80)
    print("🚀 DAX COMPREHENSIVE LOCAL OPTIMIZATION")
    print("=" * 80)
    
    # Load data
    data_file = "/Users/sreenathreddy/Downloads/UniTrader-project/signal_trade_processor/strategy_optimization_complete/data/dax_1min_ohlc.csv"
    data = load_dax_1min_data(data_file)
    
    if not data:
        print("❌ Failed to load data")
        return
    
    # Generate all combinations
    combinations = generate_all_combinations()
    total_combinations = len(combinations)
    
    print(f"\n📊 Optimization Setup:")
    print(f"  Total Combinations: {total_combinations}")
    print(f"  Pivot Combinations: 36 (6 left × 6 right - ALL combinations)")
    print(f"  Timeframes: 5 options")
    print(f"  Targets: 5 options")
    print(f"  Stop Modes: 3 options")
    print(f"  Accumulated Loss Modes: 3 options")
    
    # For faster testing, let's run a subset first
    print(f"\n⚡ Running with 8 parallel workers")
    print(f"  Estimated time: 10-15 minutes")
    
    # Split for parallel processing
    num_workers = 8
    chunks = split_combinations_for_parallel(combinations, num_workers)
    
    print(f"🔄 Splitting into {len(chunks)} chunks for parallel processing")
    
    # Run workers in parallel
    all_results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        # Submit all worker tasks
        future_to_worker = {
            executor.submit(worker_function, chunk, i, data): i 
            for i, chunk in enumerate(chunks)
        }
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_worker):
            worker_id = future_to_worker[future]
            try:
                worker_results = future.result()
                all_results.extend(worker_results)
                print(f"📈 Worker {worker_id} results collected: {len(worker_results)} successful tests")
            except Exception as e:
                print(f"❌ Worker {worker_id} failed: {e}")
    
    # Sort all results by score
    all_results.sort(key=lambda x: x['metrics']['score'], reverse=True)
    
    # Get top results
    top_results = all_results[:10]
    
    print("\n" + "=" * 80)
    print("✅ COMPREHENSIVE OPTIMIZATION COMPLETE")
    print("=" * 80)
    
    # Display results
    print(f"\n📊 Summary:")
    print(f"  Total Tests: {len(all_results)}/{total_combinations}")
    print(f"  Execution Time: {(datetime.now() - start_time).total_seconds():.1f} seconds")
    print(f"  Workers Used: {num_workers}")
    
    if top_results:
        print(f"\n🏆 Top 10 Results:")
        for i, result in enumerate(top_results, 1):
            config = result['config']
            metrics = result['metrics']
            
            print(f"\n{i}. Pv {config['pivot_left']}/{config['pivot_right']} TF {config['timeframe_minutes']}m T {config['target_points']} SM {config['stop_mode']} AL {config['accumulated_loss_mode']}")
            print(f"   Score: {metrics['score']:.1f} | P&L: {metrics['total_pnl']:+.2f} | Win Rate: {metrics['win_rate']:.1f}% | Sharpe: {metrics['sharpe_ratio']:.3f}")
            print(f"   Trades: {metrics['total_trades']} | Profit Factor: {metrics['profit_factor']:.2f} | Max DD: {metrics['max_drawdown']:.2f}")
        
        # Best configuration
        best = top_results[0]
        print(f"\n🎯 BEST CONFIGURATION:")
        print(f"  Pivot: {best['config']['pivot_left']}/{best['config']['pivot_right']}")
        print(f"  Timeframe: {best['config']['timeframe_minutes']} minutes")
        print(f"  Target: {best['config']['target_points']} points")
        print(f"  Stop Mode: {best['config']['stop_mode']}")
        print(f"  Accumulated Loss Mode: {best['config']['accumulated_loss_mode']}")
        
        print(f"\n📊 Performance:")
        print(f"  Total P&L: {best['metrics']['total_pnl']:+.2f} points")
        print(f"  Total Trades: {best['metrics']['total_trades']}")
        print(f"  Win Rate: {best['metrics']['win_rate']:.1f}%")
        print(f"  Sharpe Ratio: {best['metrics']['sharpe_ratio']:.3f}")
        print(f"  Max Drawdown: {best['metrics']['max_drawdown']:.2f} points")
        print(f"  Profit Factor: {best['metrics']['profit_factor']:.2f}")
        print(f"  Composite Score: {best['metrics']['score']:.1f}")
        
        # Save results
        results_data = {
            'total_combinations_tested': total_combinations,
            'successful_tests': len(all_results),
            'execution_time_seconds': (datetime.now() - start_time).total_seconds(),
            'top_10_results': []
        }
        
        for i, result in enumerate(top_results):
            config = result['config']
            metrics = result['metrics']
            
            top_result = {
                'rank': i + 1,
                'parameters': config,
                'performance': {
                    'score': round(metrics['score'], 2),
                    'total_pnl': round(metrics['total_pnl'], 2),
                    'total_trades': metrics['total_trades'],
                    'win_rate': round(metrics['win_rate'], 1),
                    'sharpe_ratio': round(metrics['sharpe_ratio'], 3),
                    'max_drawdown': round(metrics['max_drawdown'], 2),
                    'profit_factor': round(metrics['profit_factor'], 2),
                    'target_hits': metrics['target_hits'],
                    'stop_hits': metrics['stop_hits'],
                    'force_exits': metrics['force_exits']
                }
            }
            results_data['top_10_results'].append(top_result)
        
        # Save to file
        with open('/Users/sreenathreddy/Downloads/UniTrader-project/comprehensive_dax_results.json', 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"\n💾 Results saved to 'comprehensive_dax_results.json'")

if __name__ == "__main__":
    main()
