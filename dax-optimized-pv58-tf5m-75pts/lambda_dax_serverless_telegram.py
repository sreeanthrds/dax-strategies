#!/usr/bin/env python3
"""
Serverless DAX Strategy Optimizer with Telegram Notifications
Uses AWS Lambda parallel processing with real-time Telegram updates
"""

import json
import sys
import os
import requests
from datetime import datetime, time as dt_time
from typing import Dict, List, Tuple
import pandas as pd
import boto3
from concurrent.futures import ThreadPoolExecutor
import math

# Add the path to the DAX strategy
sys.path.append('/opt')

from dax_strategy_rebuilt import DAXStrategyEngine, StrategyConfig

# Telegram configuration
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

def send_telegram_message(message: str):
    """Send message to Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials not configured")
        return
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown'
        }
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            print("Telegram message sent successfully")
        else:
            print(f"Failed to send Telegram message: {response.status_code}")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

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
        send_telegram_message(f"❌ Error loading data: {e}")
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

def split_combinations_for_parallel(combinations: List[Dict], num_workers: int = 100) -> List[List[Dict]]:
    """Split combinations into chunks for parallel processing"""
    chunk_size = math.ceil(len(combinations) / num_workers)
    chunks = []
    
    for i in range(0, len(combinations), chunk_size):
        chunk = combinations[i:i + chunk_size]
        chunks.append(chunk)
    
    return chunks

def lambda_handler(event, context):
    """AWS Lambda handler for parallel comprehensive optimization with Telegram notifications"""
    
    start_time = datetime.now()
    
    # Send start notification
    send_telegram_message("🚀 *DAX Serverless Optimization Started*\\n\\n📊 Testing ALL 8,100 parameter combinations\\n⚡ Using 100 parallel Lambda workers\\n⏱️ Estimated time: 2-3 minutes")
    
    print("=" * 80)
    print("🚀 DAX COMPREHENSIVE SERVERLESS OPTIMIZATION")
    print("=" * 80)
    
    # Check if this is the main orchestrator or a worker
    if event.get('worker_mode'):
        # Worker mode - process a chunk
        combinations_chunk = event.get('combinations', [])
        chunk_id = event.get('chunk_id', 'unknown')
        
        try:
            # Load data once per worker
            data_file = "/opt/signal_trade_processor/strategy_optimization_complete/data/dax_1min_ohlc.csv"
            data = load_dax_1min_data(data_file)
            
            if not data:
                return {
                    'statusCode': 500,
                    'body': json.dumps({'error': 'Failed to load data'})
                }
            
            results = []
            
            for params in combinations_chunk:
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
                except Exception as e:
                    print(f"Error in worker {chunk_id}: {e}")
                    continue
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'worker_results': results,
                    'processed_count': len(combinations_chunk),
                    'chunk_id': chunk_id
                })
            }
        except Exception as e:
            send_telegram_message(f"❌ Worker {chunk_id} failed: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': str(e)})
            }
    
    # Main orchestrator mode
    try:
        print("📊 Starting comprehensive optimization...")
        
        # Generate all combinations
        combinations = generate_all_combinations()
        total_combinations = len(combinations)
        
        print(f"🔢 Total Combinations: {total_combinations}")
        send_telegram_message(f"📊 Generated {total_combinations} parameter combinations\\n🎯 Including ALL 36 pivot combinations (left >= right)")
        
        # Split for parallel processing
        num_workers = min(100, total_combinations)
        chunks = split_combinations_for_parallel(combinations, num_workers)
        
        print(f"🔄 Splitting into {len(chunks)} chunks for parallel processing")
        send_telegram_message(f"🔄 Splitting into {len(chunks)} parallel chunks\\n⚡ Starting {num_workers} Lambda workers")
        
        # Initialize Lambda client
        lambda_client = boto3.client('lambda')
        worker_function_name = os.environ.get('WORKER_FUNCTION_NAME', 'dax-optimizer-worker')
        
        # Invoke workers in parallel
        all_results = []
        completed_workers = 0
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = []
            
            for i, chunk in enumerate(chunks):
                payload = {
                    'worker_mode': True,
                    'combinations': chunk,
                    'chunk_id': i
                }
                
                future = executor.submit(
                    lambda_client.invoke,
                    FunctionName=worker_function_name,
                    InvocationType='RequestResponse',
                    Payload=json.dumps(payload)
                )
                futures.append((future, i))
            
            # Collect results
            for future, chunk_id in futures:
                try:
                    response = future.result()
                    result = json.loads(response['Payload'].read())
                    worker_results = result.get('worker_results', [])
                    all_results.extend(worker_results)
                    completed_workers += 1
                    
                    # Progress update
                    progress = (completed_workers / len(chunks)) * 100
                    send_telegram_message(f"⏳ Progress: {completed_workers}/{len(chunks)} workers completed ({progress:.1f}%)\\n📈 Results so far: {len(all_results)} successful tests")
                    
                except Exception as e:
                    print(f"❌ Chunk {chunk_id + 1} failed: {e}")
                    send_telegram_message(f"❌ Worker {chunk_id + 1} failed: {e}")
        
        # Sort all results by score
        all_results.sort(key=lambda x: x['metrics']['score'], reverse=True)
        
        # Get top results
        top_results = all_results[:10]
        
        # Send completion notification with top results
        if top_results:
            best = top_results[0]
            best_config = best['config']
            best_metrics = best['performance'] = best['metrics']
            
            completion_message = f"✅ *DAX Optimization Completed!*\\n\\n🏆 **BEST CONFIGURATION:**\\n"
            completion_message += f"🎯 Pivot: {best_config['pivot_left']}/{best_config['pivot_right']}\\n"
            completion_message += f"⏰ Timeframe: {best_config['timeframe_minutes']}m\\n"
            completion_message += f"🎯 Target: {best_config['target_points']} pts\\n"
            completion_message += f"🛡️ Stop Mode: {best_config['stop_mode']}\\n"
            completion_message += f"💸 Loss Mode: {best_config['accumulated_loss_mode']}\\n\\n"
            completion_message += f"📊 **PERFORMANCE:**\\n"
            completion_message += f"💰 Total P&L: +{best_metrics['total_pnl']:.2f} points\\n"
            completion_message += f"📈 Score: {best_metrics['score']:.1f}\\n"
            completion_message += f"🎯 Win Rate: {best_metrics['win_rate']:.1f}%\\n"
            completion_message += f"📊 Trades: {best_metrics['total_trades']}\\n"
            completion_message += f"⚡ Sharpe: {best_metrics['sharpe_ratio']:.3f}\\n\\n"
            completion_message += f"🏅 **TOP 3 RESULTS:**\\n"
            
            for i, result in enumerate(top_results[:3], 1):
                config = result['config']
                metrics = result['metrics']
                completion_message += f"{i}. Pv {config['pivot_left']}/{config['pivot_right']} TF {config['timeframe_minutes']}m T {config['target_points']} - Score: {metrics['score']:.1f}\\n"
            
            completion_message += f"\\n📊 **SUMMARY:**\\n"
            completion_message += f"🔢 Total Tests: {len(all_results)}/{total_combinations}\\n"
            completion_message += f"⏱️ Execution Time: {(datetime.now() - start_time).total_seconds():.1f}s\\n"
            completion_message += f"🚀 Workers Used: {num_workers}\\n"
            
            send_telegram_message(completion_message)
        
        # Format response
        response = {
            'total_combinations_tested': total_combinations,
            'successful_tests': len(all_results),
            'parallel_workers_used': num_workers,
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
            response['top_10_results'].append(top_result)
        
        # Add best configuration
        if top_results:
            best = top_results[0]
            response['best_configuration'] = {
                'parameters': best['parameters'],
                'performance': best['performance']
            }
        
        print("=" * 80)
        print("✅ COMPREHENSIVE PARALLEL OPTIMIZATION COMPLETE")
        print("=" * 80)
        
        return {
            'statusCode': 200,
            'body': json.dumps(response, indent=2)
        }
        
    except Exception as e:
        error_message = f"❌ *DAX Optimization Failed!*\\n\\n🚨 Error: {str(e)}\\n⏱️ Execution Time: {(datetime.now() - start_time).total_seconds():.1f}s"
        send_telegram_message(error_message)
        print(f"❌ Error: {e}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

if __name__ == "__main__":
    # For local testing
    event = {}
    context = {}
    result = lambda_handler(event, context)
    print(json.dumps(result, indent=2))
