#!/usr/bin/env python3
"""
Test Bidirectional DAX Strategy
Runs the modified strategy with bidirectional zone entries
"""

import sys
import os
from datetime import datetime, time as dt_time
import pandas as pd

# Add the path to the DAX strategy
sys.path.append('/Users/sreenathreddy/Downloads/dax-strategies/dax-optimized-pv58-tf5m-75pts')

from dax_strategy_bidirectional import DAXStrategyEngine, StrategyConfig

def load_dax_1min_data(file_path: str):
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

def calculate_performance_metrics(trades):
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

def analyze_bidirectional_performance(trades):
    """Analyze performance by zone and direction"""
    
    # Analyze by zone type
    res1_trades = [t for t in trades if t['zone_name'] == 'res1']
    sup1_trades = [t for t in trades if t['zone_name'] == 'sup1']
    
    # Analyze by direction
    buy_trades = [t for t in trades if t['type'] == 'BUY']
    sell_trades = [t for t in trades if t['type'] == 'SELL']
    
    # Analyze by zone + direction combinations
    res1_buy = [t for t in trades if t['zone_name'] == 'res1' and t['type'] == 'BUY']
    res1_sell = [t for t in trades if t['zone_name'] == 'res1' and t['type'] == 'SELL']
    sup1_buy = [t for t in trades if t['zone_name'] == 'sup1' and t['type'] == 'BUY']
    sup1_sell = [t for t in trades if t['zone_name'] == 'sup1' and t['type'] == 'SELL']
    
    print("\n📊 Bidirectional Performance Analysis:")
    print("=" * 60)
    
    print(f"\n🎯 By Zone Type:")
    print(f"  Resistance Zone (res1): {len(res1_trades)} trades, P&L: {sum(t['pnl'] for t in res1_trades):+.2f}")
    print(f"  Support Zone (sup1): {len(sup1_trades)} trades, P&L: {sum(t['pnl'] for t in sup1_trades):+.2f}")
    
    print(f"\n📈 By Direction:")
    print(f"  BUY trades: {len(buy_trades)} trades, P&L: {sum(t['pnl'] for t in buy_trades):+.2f}")
    print(f"  SELL trades: {len(sell_trades)} trades, P&L: {sum(t['pnl'] for t in sell_trades):+.2f}")
    
    print(f"\n🎯 By Zone + Direction Combinations:")
    print(f"  Resistance + BUY: {len(res1_buy)} trades, P&L: {sum(t['pnl'] for t in res1_buy):+.2f}")
    print(f"  Resistance + SELL: {len(res1_sell)} trades, P&L: {sum(t['pnl'] for t in res1_sell):+.2f}")
    print(f"  Support + BUY: {len(sup1_buy)} trades, P&L: {sum(t['pnl'] for t in sup1_buy):+.2f}")
    print(f"  Support + SELL: {len(sup1_sell)} trades, P&L: {sum(t['pnl'] for t in sup1_sell):+.2f}")
    
    # Calculate win rates for each combination
    combinations = [
        ("Resistance + BUY", res1_buy),
        ("Resistance + SELL", res1_sell),
        ("Support + BUY", sup1_buy),
        ("Support + SELL", sup1_sell)
    ]
    
    print(f"\n📊 Win Rates by Combination:")
    for name, trades_list in combinations:
        if trades_list:
            wins = len([t for t in trades_list if t['pnl'] > 0])
            win_rate = wins / len(trades_list) * 100
            avg_pnl = sum(t['pnl'] for t in trades_list) / len(trades_list)
            print(f"  {name}: {win_rate:.1f}% win rate, avg P&L: {avg_pnl:+.2f}")

def main():
    """Main test function"""
    
    print("=" * 80)
    print("🔄 TESTING BIDIRECTIONAL DAX STRATEGY")
    print("=" * 80)
    
    # Load data
    data_file = "/Users/sreenathreddy/Downloads/UniTrader-project/signal_trade_processor/strategy_optimization_complete/data/dax_1min_ohlc.csv"
    data = load_dax_1min_data(data_file)
    
    if not data:
        print("❌ Failed to load data")
        return
    
    # Test bidirectional strategy with same optimal parameters
    config = StrategyConfig(
        pivot_left=5,
        pivot_right=8,
        timeframe_minutes=5,
        target_points=75.0,
        base_stop=36.0,
        stop_mode='zone',
        accumulated_loss_mode='none',
        reset_on_target=True,
        target_increase_on_hit=30.0,
        max_accumulated_loss_cap=150.0,
        force_exit_time="16:55",
        dual_position=False
    )
    
    print(f"\n🎯 Bidirectional Strategy Configuration:")
    print(f"  Pivot: {config.pivot_left}/{config.pivot_right}")
    print(f"  Timeframe: {config.timeframe_minutes} minutes")
    print(f"  Target: {config.target_points} points")
    print(f"  Stop Mode: {config.stop_mode}")
    print(f"  Accumulated Loss Mode: {config.accumulated_loss_mode}")
    
    print(f"\n🔄 Key Changes:")
    print(f"  ✅ Resistance Zone: BUY if high breaks, SELL if low breaks")
    print(f"  ✅ Support Zone: BUY if high breaks, SELL if low breaks")
    print(f"  ✅ Bidirectional entries at both zones")
    
    # Run bidirectional strategy
    engine = DAXStrategyEngine(config)
    trades = engine.run(data)
    
    print(f"\n📈 Bidirectional Strategy Results:")
    print(f"  Total Trades: {len(trades)}")
    
    if trades:
        # Calculate metrics
        metrics = calculate_performance_metrics(trades)
        
        print(f"  Total P&L: {metrics['total_pnl']:+.2f} points")
        print(f"  Win Rate: {metrics['win_rate']:.1f}%")
        print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.3f}")
        print(f"  Max Drawdown: {metrics['max_drawdown']:.2f} points")
        print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
        print(f"  Composite Score: {metrics['score']:.1f}")
        
        # Detailed analysis
        analyze_bidirectional_performance(trades)
        
        # Save results
        trades_data = []
        for i, trade in enumerate(trades, 1):
            trades_data.append({
                'trade_id': i,
                'signal_type': trade['type'],
                'zone_name': trade['zone_name'],
                'entry_time': trade['entry_time'],
                'entry_price': trade['entry_price'],
                'target_price': trade['target_price'],
                'exit_time': trade['exit_time'],
                'exit_price': trade['exit_price'],
                'exit_type': trade['exit_type'],
                'pnl': trade['pnl'],
                'hold_duration': (datetime.fromisoformat(trade['exit_time']) - datetime.fromisoformat(trade['entry_time'])).total_seconds() / 60
            })
        
        # Save to CSV
        df_trades = pd.DataFrame(trades_data)
        trades_csv_file = "/Users/sreenathreddy/Downloads/dax-strategies/dax-optimized-pv58-tf5m-75pts/dax_bidirectional_trades.csv"
        df_trades.to_csv(trades_csv_file, index=False)
        
        print(f"\n💾 Results saved to: {trades_csv_file}")
        
        # Show sample trades
        print(f"\n📋 Sample Trades (First 10):")
        for i, trade in enumerate(trades[:10], 1):
            direction = "BUY" if trade['type'] == 'BUY' else "SELL"
            zone = "Resistance" if trade['zone_name'] == 'res1' else "Support"
            pnl_sign = "+" if trade['pnl'] >= 0 else ""
            hold_duration = (datetime.fromisoformat(trade['exit_time']) - datetime.fromisoformat(trade['entry_time'])).total_seconds() / 60
            print(f"  {i:2d}. {direction} @ {zone} @ {trade['entry_price']:8.1f} → {trade['exit_price']:8.1f} ({pnl_sign}{trade['pnl']:6.1f}) [{trade['exit_type']:12}] {hold_duration:3.0f}m")
        
    else:
        print("❌ No trades generated")

if __name__ == "__main__":
    main()
