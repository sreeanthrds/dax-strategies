#!/usr/bin/env python3
"""
Lambda Optimizer for DAX Strategy - All Combinations
Ready for AWS Lambda deployment
"""

import json
import sys
import os
from datetime import datetime, time as dt_time
from typing import Dict, List, Tuple
import pandas as pd

# Add the path to the DAX strategy
sys.path.append('/opt')

from dax_strategy_rebuilt import DAXStrategyEngine, StrategyConfig

def load_dax_1min_data(file_path: str) -> List[Dict]:
    """Load DAX 1-minute OHLC data"""
    try:
        df = pd.read_csv(file_path)
        
        # Convert timestamp to datetime objects properly
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed')
        
        # Filter for trading hours (9:00-16:30) AND weekdays only
        df = df[
            (df['timestamp'].dt.time >= dt_time(9, 0)) & 
            (df['timestamp'].dt.time <= dt_time(16, 30))
        ]
        df = df[df['timestamp'].dt.dayofweek < 5]  # Weekdays only
        
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
    """Generate all parameter combinations to test"""
    
    # Comprehensive pivot ranges - test all left/right combinations
    pivot_left_options = [3, 5, 8, 10, 15, 20]
    pivot_right_options = [8, 10, 13, 15, 20, 25]
    
    # Generate all valid pivot combinations (left < right)
    pivot_combinations = []
    for left in pivot_left_options:
        for right in pivot_right_options:
            if left < right:
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
                            'base_stop': target * 0.48,  # 48% of target
                            'stop_mode': stop_mode,
                            'accumulated_loss_mode': acc_loss_mode,
                            'reset_on_target': True,
                            'target_increase_on_hit': target * 0.4,  # 40% increase
                            'max_accumulated_loss_cap': target * 2,
                            'force_exit_time': "16:55",
                            'dual_position': False
                        }
                        
                        combinations.append(config)
    
    return combinations

def lambda_handler(event, context):
    """AWS Lambda handler for comprehensive optimization"""
    
    print("=" * 80)
    print("🚀 DAX COMPREHENSIVE LAMBDA OPTIMIZATION")
    print("=" * 80)
    
    # Load data
    data_file = "/opt/signal_trade_processor/strategy_optimization_complete/data/dax_1min_ohlc.csv"
    data = load_dax_1min_data(data_file)
    
    if not data:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Failed to load data'})
        }
    
    # Generate all combinations
    combinations = generate_all_combinations()
    total_combinations = len(combinations)
    
    print(f"📊 Testing {total_combinations} parameter combinations...")
    
    results = []
    
    for i, params in enumerate(combinations):
        print(f"[{i+1}/{total_combinations}] Pv {params['pivot_left']}/{params['pivot_right']} TF {params['timeframe_minutes']}m T {params['target_points']} SM {params['stop_mode']} AL {params['accumulated_loss_mode']}")
        
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
            
            print(f"  ✅ Score: {metrics['score']:.1f} | P&L: {metrics['total_pnl']:+.1f} | Win Rate: {metrics['win_rate']:.1f}%")
        else:
            print(f"  ❌ Test failed")
    
    # Sort results by score
    results.sort(key=lambda x: x['metrics']['score'], reverse=True)
    
    # Get top results
    top_results = results[:10]
    
    # Format response
    response = {
        'total_combinations_tested': total_combinations,
        'successful_tests': len(results),
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
        response['top_10_results'].append(top_result)
    
    # Add best configuration
    if top_results:
        best = top_results[0]
        response['best_configuration'] = {
            'parameters': best['parameters'],
            'performance': best['performance']
        }
    
    print("=" * 80)
    print("✅ COMPREHENSIVE OPTIMIZATION COMPLETE")
    print("=" * 80)
    
    return {
        'statusCode': 200,
        'body': json.dumps(response, indent=2)
    }

if __name__ == "__main__":
    # For local testing
    event = {}
    context = {}
    result = lambda_handler(event, context)
    print(json.dumps(result, indent=2))
