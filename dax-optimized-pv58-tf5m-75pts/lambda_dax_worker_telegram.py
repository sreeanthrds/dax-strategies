#!/usr/bin/env python3
"""
Worker Lambda for DAX Strategy Optimization with Telegram Notifications
Processes chunks of combinations in parallel with real-time updates
"""

import json
import sys
import os
import requests
from datetime import datetime, time as dt_time
from typing import Dict, List
import pandas as pd

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

def lambda_handler(event, context):
    """Worker Lambda handler with Telegram notifications"""
    
    chunk_id = event.get('chunk_id', 'unknown')
    combinations_chunk = event.get('combinations', [])
    
    print(f"🔄 Worker {chunk_id}: Processing {len(combinations_chunk)} combinations")
    
    try:
        # Load data once per worker
        data_file = "/opt/signal_trade_processor/strategy_optimization_complete/data/dax_1min_ohlc.csv"
        data = load_dax_1min_data(data_file)
        
        if not data:
            error_msg = f"❌ Worker {chunk_id}: Failed to load data"
            send_telegram_message(error_msg)
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Failed to load data'})
            }
        
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
                
                # Progress indicator for large chunks
                if len(combinations_chunk) > 20 and (i + 1) % 20 == 0:
                    progress = ((i + 1) / len(combinations_chunk)) * 100
                    print(f"  Worker {chunk_id}: {i + 1}/{len(combinations_chunk)} completed ({progress:.1f}%)")
                    
            except Exception as e:
                print(f"  Worker {chunk_id}: Error in combination {i}: {e}")
                continue
        
        # Send completion notification for this worker
        if best_config and results:
            completion_msg = f"✅ Worker {chunk_id} completed\\n\\n📊 Results: {len(results)}/{len(combinations_chunk)} successful\\n"
            completion_msg += f"🏆 Best in chunk: Pv {best_config['pivot_left']}/{best_config['pivot_right']} TF {best_config['timeframe_minutes']}m T {best_config['target_points']}\\n"
            completion_msg += f"📈 Score: {best_score:.1f} | P&L: +{best_metrics['total_pnl']:.2f} | Win Rate: {best_metrics['win_rate']:.1f}%"
            send_telegram_message(completion_msg)
        
        print(f"✅ Worker {chunk_id}: Completed {len(results)} successful tests")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'worker_results': results,
                'processed_count': len(combinations_chunk),
                'successful_count': len(results),
                'chunk_id': chunk_id,
                'best_score': best_score,
                'best_config': best_config
            })
        }
        
    except Exception as e:
        error_msg = f"❌ Worker {chunk_id} failed: {str(e)}"
        send_telegram_message(error_msg)
        print(f"❌ Worker {chunk_id} failed: {e}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e), 'chunk_id': chunk_id})
        }
