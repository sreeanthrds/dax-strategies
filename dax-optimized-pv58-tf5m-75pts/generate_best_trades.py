#!/usr/bin/env python3
"""
Generate Detailed Trades for Best DAX Configuration
Creates comprehensive trade analysis for the optimal strategy
"""

import json
import sys
import os
from datetime import datetime, time as dt_time
from typing import Dict, List
import pandas as pd

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

def analyze_trades_detailed(trades: List[Dict]) -> Dict:
    """Analyze trades with detailed breakdowns"""
    if not trades:
        return {}
    
    # Monthly analysis
    monthly_stats = {}
    for trade in trades:
        entry_date = trade['entry_time'][:7]  # YYYY-MM
        if entry_date not in monthly_stats:
            monthly_stats[entry_date] = {
                'trades': 0,
                'pnl': 0,
                'wins': 0,
                'losses': 0,
                'target_hits': 0,
                'stop_hits': 0,
                'force_exits': 0
            }
        
        monthly_stats[entry_date]['trades'] += 1
        monthly_stats[entry_date]['pnl'] += trade['pnl']
        
        if trade['pnl'] > 0:
            monthly_stats[entry_date]['wins'] += 1
        else:
            monthly_stats[entry_date]['losses'] += 1
        
        if trade['exit_type'] == 'TARGET':
            monthly_stats[entry_date]['target_hits'] += 1
        elif trade['exit_type'] == 'STOP_LOSS':
            monthly_stats[entry_date]['stop_hits'] += 1
        elif trade['exit_type'] == 'FORCE_EXIT':
            monthly_stats[entry_date]['force_exits'] += 1
    
    # Calculate monthly win rates
    for month in monthly_stats:
        stats = monthly_stats[month]
        stats['win_rate'] = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
    
    # Daily analysis
    daily_stats = {}
    for trade in trades:
        entry_date = trade['entry_time'][:10]  # YYYY-MM-DD
        if entry_date not in daily_stats:
            daily_stats[entry_date] = {
                'trades': 0,
                'pnl': 0,
                'wins': 0,
                'losses': 0
            }
        
        daily_stats[entry_date]['trades'] += 1
        daily_stats[entry_date]['pnl'] += trade['pnl']
        
        if trade['pnl'] > 0:
            daily_stats[entry_date]['wins'] += 1
        else:
            daily_stats[entry_date]['losses'] += 1
    
    # Calculate daily win rates
    for day in daily_stats:
        stats = daily_stats[day]
        stats['win_rate'] = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
    
    # Hourly analysis
    hourly_stats = {}
    for trade in trades:
        entry_hour = trade['entry_time'][11:16]  # HH:MM
        hour_key = entry_hour[:2] + ":00"  # Round to hour
        if hour_key not in hourly_stats:
            hourly_stats[hour_key] = {
                'trades': 0,
                'pnl': 0,
                'wins': 0,
                'losses': 0
            }
        
        hourly_stats[hour_key]['trades'] += 1
        hourly_stats[hour_key]['pnl'] += trade['pnl']
        
        if trade['pnl'] > 0:
            hourly_stats[hour_key]['wins'] += 1
        else:
            hourly_stats[hour_key]['losses'] += 1
    
    # Calculate hourly win rates
    for hour in hourly_stats:
        stats = hourly_stats[hour]
        stats['win_rate'] = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
    
    return {
        'monthly_stats': monthly_stats,
        'daily_stats': daily_stats,
        'hourly_stats': hourly_stats
    }

def main():
    """Generate detailed trades for best configuration"""
    
    print("=" * 80)
    print("📊 GENERATING DETAILED TRADES - BEST DAX CONFIGURATION")
    print("=" * 80)
    
    # Load data
    data_file = "/Users/sreenathreddy/Downloads/UniTrader-project/signal_trade_processor/strategy_optimization_complete/data/dax_1min_ohlc.csv"
    data = load_dax_1min_data(data_file)
    
    if not data:
        print("❌ Failed to load data")
        return
    
    # Best configuration from comprehensive optimization
    config = StrategyConfig(
        pivot_left=5,
        pivot_right=8,
        timeframe_minutes=5,
        target_points=75,
        base_stop=36.0,
        stop_mode='zone',
        accumulated_loss_mode='none',
        reset_on_target=True,
        target_increase_on_hit=30.0,
        max_accumulated_loss_cap=150,
        force_exit_time="16:55",
        dual_position=False
    )
    
    print(f"\n🎯 Running Best Configuration:")
    print(f"  Pivot: {config.pivot_left}/{config.pivot_right}")
    print(f"  Timeframe: {config.timeframe_minutes} minutes")
    print(f"  Target: {config.target_points} points")
    print(f"  Stop Mode: {config.stop_mode}")
    print(f"  Accumulated Loss Mode: {config.accumulated_loss_mode}")
    
    # Run strategy
    engine = DAXStrategyEngine(config)
    trades = engine.run(data)
    
    print(f"\n📈 Strategy Results:")
    print(f"  Total Trades: {len(trades)}")
    
    if trades:
        # Calculate metrics
        metrics = calculate_performance_metrics(trades)
        
        print(f"  Total P&L: +{metrics['total_pnl']:.2f} points")
        print(f"  Win Rate: {metrics['win_rate']:.1f}%")
        print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.3f}")
        print(f"  Max Drawdown: {metrics['max_drawdown']:.2f} points")
        print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
        print(f"  Composite Score: {metrics['score']:.1f}")
        
        # Detailed analysis
        detailed_analysis = analyze_trades_detailed(trades)
        
        # Prepare trades for CSV
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
        
        # Save detailed trades to CSV
        df_trades = pd.DataFrame(trades_data)
        trades_csv_file = "/Users/sreenathreddy/Downloads/UniTrader-project/dax_best_detailed_trades_19825_points.csv"
        df_trades.to_csv(trades_csv_file, index=False)
        
        print(f"\n💾 Detailed Trades Saved:")
        print(f"  File: {trades_csv_file}")
        print(f"  Trades: {len(trades)}")
        
        # Save comprehensive analysis
        comprehensive_results = {
            'configuration': {
                'pivot_left': config.pivot_left,
                'pivot_right': config.pivot_right,
                'timeframe_minutes': config.timeframe_minutes,
                'target_points': config.target_points,
                'base_stop': config.base_stop,
                'stop_mode': config.stop_mode,
                'accumulated_loss_mode': config.accumulated_loss_mode,
                'reset_on_target': config.reset_on_target,
                'target_increase_on_hit': config.target_increase_on_hit,
                'max_accumulated_loss_cap': config.max_accumulated_loss_cap,
                'force_exit_time': config.force_exit_time,
                'dual_position': config.dual_position
            },
            'performance_metrics': metrics,
            'detailed_analysis': detailed_analysis,
            'total_trades': len(trades),
            'generation_time': datetime.now().isoformat()
        }
        
        analysis_file = "/Users/sreenathreddy/Downloads/UniTrader-project/dax_best_comprehensive_analysis.json"
        with open(analysis_file, 'w') as f:
            json.dump(comprehensive_results, f, indent=2)
        
        print(f"  Analysis: {analysis_file}")
        
        # Display sample trades
        print(f"\n📋 Sample Trades (First 10):")
        for i, trade in enumerate(trades[:10], 1):
            direction = "BUY" if trade['signal_type'] == 'BUY' else "SELL"
            pnl_sign = "+" if trade['pnl'] >= 0 else ""
            print(f"  {i:2d}. {direction} @ {trade['entry_price']:8.1f} → {trade['exit_price']:8.1f} ({pnl_sign}{trade['pnl']:6.1f}) [{trade['exit_type']:12}] {trade['hold_duration']:3.0f}m | {trade['entry_time']}")
        
        # Display monthly performance
        print(f"\n📅 Monthly Performance:")
        monthly_stats = detailed_analysis['monthly_stats']
        for month in sorted(monthly_stats.keys()):
            stats = monthly_stats[month]
            pnl_sign = "+" if stats['pnl'] >= 0 else ""
            print(f"  {month}: {stats['trades']:3d} trades, {pnl_sign}{stats['pnl']:7.1f} pts, {stats['win_rate']:5.1f}% win rate")
        
        # Display hourly performance
        print(f"\n🕐 Hourly Performance (Top 10 by trades):")
        hourly_stats = detailed_analysis['hourly_stats']
        sorted_hours = sorted(hourly_stats.items(), key=lambda x: x[1]['trades'], reverse=True)
        for hour, stats in sorted_hours[:10]:
            pnl_sign = "+" if stats['pnl'] >= 0 else ""
            print(f"  {hour}: {stats['trades']:3d} trades, {pnl_sign}{stats['pnl']:7.1f} pts, {stats['win_rate']:5.1f}% win rate")
        
        print(f"\n" + "=" * 80)
        print(f"✅ DETAILED TRADES GENERATION COMPLETE")
        print(f"📁 Files Created:")
        print(f"  • {trades_csv_file}")
        print(f"  • {analysis_file}")
        print("=" * 80)
        
    else:
        print("❌ No trades generated")

if __name__ == "__main__":
    main()
