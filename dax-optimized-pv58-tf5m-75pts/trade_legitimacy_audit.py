#!/usr/bin/env python3
"""
Trade Legitimacy Audit for DAX Strategy
Analyzes trades for impossible or impractical scenarios
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys

def load_trades(file_path):
    """Load trades from CSV file"""
    df = pd.read_csv(file_path)
    df['entry_time'] = pd.to_datetime(df['entry_time'])
    df['exit_time'] = pd.to_datetime(df['exit_time'])
    return df

def audit_trade_legitimacy(df):
    """Comprehensive audit of trade legitimacy"""
    
    print("=" * 80)
    print("🔍 DAX TRADE LEGITIMACY AUDIT")
    print("=" * 80)
    
    issues = []
    warnings = []
    
    # 1. Check for negative hold durations
    negative_durations = df[df['hold_duration'] < 0]
    if len(negative_durations) > 0:
        issues.append(f"❌ {len(negative_durations)} trades with negative hold duration")
        print(f"❌ CRITICAL: {len(negative_durations)} trades have negative hold duration")
    
    # 2. Check for impossible price movements
    df['price_change'] = abs(df['exit_price'] - df['entry_price'])
    df['price_change_pct'] = (df['price_change'] / df['entry_price']) * 100
    
    # Check for extreme price movements (> 2% in single trade)
    extreme_moves = df[df['price_change_pct'] > 2.0]
    if len(extreme_moves) > 0:
        warnings.append(f"⚠️ {len(extreme_moves)} trades with extreme price movements (>2%)")
        print(f"⚠️ WARNING: {len(extreme_moves)} trades with extreme price movements (>2%)")
        
        # Show extreme examples
        worst_moves = extreme_moves.nlargest(5, 'price_change_pct')
        print("\n📊 Most Extreme Price Movements:")
        for _, trade in worst_moves.iterrows():
            print(f"  Trade {trade['trade_id']}: {trade['entry_price']:.1f} → {trade['exit_price']:.1f} ({trade['price_change_pct']:.2f}%)")
    
    # 3. Check for unrealistic short duration trades
    very_short = df[df['hold_duration'] < 2]  # Less than 2 minutes
    if len(very_short) > 0:
        warnings.append(f"⚠️ {len(very_short)} trades with very short duration (<2 min)")
        print(f"⚠️ WARNING: {len(very_short)} trades with very short duration (<2 minutes)")
    
    # 4. Check for trades with exact target hits (possible look-ahead bias)
    target_hits = df[df['exit_type'] == 'TARGET']
    exact_targets = target_hits[abs(target_hits['pnl'] - 75.0) < 0.1]  # Within 0.1 points of target
    if len(exact_targets) > 0:
        warnings.append(f"⚠️ {len(exact_targets)} trades hit exact target (possible look-ahead bias)")
        print(f"⚠️ WARNING: {len(exact_targets)} trades hit exact target (possible look-ahead bias)")
    
    # 5. Check for overlapping trades (same timestamp)
    overlapping = df.groupby('entry_time').size()
    overlaps = overlapping[overlapping > 1]
    if len(overlaps) > 0:
        warnings.append(f"⚠️ {len(overlaps)} instances of overlapping trades")
        print(f"⚠️ WARNING: {len(overlaps)} instances of overlapping trades")
    
    # 6. Check for trades outside market hours
    df['entry_hour'] = df['entry_time'].dt.hour
    df['exit_hour'] = df['exit_time'].dt.hour
    
    outside_hours = df[(df['entry_hour'] < 9) | (df['entry_hour'] > 16) | 
                     (df['exit_hour'] < 9) | (df['exit_hour'] > 16)]
    if len(outside_hours) > 0:
        issues.append(f"❌ {len(outside_hours)} trades outside market hours (9:00-16:30)")
        print(f"❌ CRITICAL: {len(outside_hours)} trades outside market hours")
    
    # 7. Check for weekend trades
    df['entry_weekday'] = df['entry_time'].dt.dayofweek
    df['exit_weekday'] = df['exit_time'].dt.dayofweek
    
    weekend_trades = df[(df['entry_weekday'] >= 5) | (df['exit_weekday'] >= 5)]
    if len(weekend_trades) > 0:
        issues.append(f"❌ {len(weekend_trades)} trades on weekends")
        print(f"❌ CRITICAL: {len(weekend_trades)} trades on weekends")
    
    # 8. Check for impossible P&L calculations
    df['calculated_pnl'] = np.where(df['signal_type'] == 'SELL', 
                                   df['entry_price'] - df['exit_price'],
                                   df['exit_price'] - df['entry_price'])
    
    pnl_mismatch = df[abs(df['calculated_pnl'] - df['pnl']) > 0.1]
    if len(pnl_mismatch) > 0:
        issues.append(f"❌ {len(pnl_mismatch)} trades with P&L calculation errors")
        print(f"❌ CRITICAL: {len(pnl_mismatch)} trades with P&L calculation errors")
    
    # 9. Check for consecutive losses (possible overfitting)
    df['is_loss'] = df['pnl'] < 0
    df['loss_streak'] = df['is_loss'].astype(int).groupby((~df['is_loss']).cumsum()).cumsum()
    
    max_loss_streak = df['loss_streak'].max()
    if max_loss_streak > 10:
        warnings.append(f"⚠️ Maximum loss streak: {max_loss_streak} consecutive losses")
        print(f"⚠️ WARNING: Maximum loss streak: {max_loss_streak} consecutive losses")
    
    # 10. Check for trades with zero P&L (possible data issues)
    zero_pnl = df[abs(df['pnl']) < 0.01]
    if len(zero_pnl) > 0:
        warnings.append(f"⚠️ {len(zero_pnl)} trades with zero P&L")
        print(f"⚠️ WARNING: {len(zero_pnl)} trades with zero P&L")
    
    return issues, warnings

def analyze_trade_patterns(df):
    """Analyze trade patterns for practicality"""
    
    print("\n" + "=" * 80)
    print("📊 TRADE PATTERN ANALYSIS")
    print("=" * 80)
    
    # Trade frequency analysis
    df['date'] = df['entry_time'].dt.date
    daily_trades = df.groupby('date').size()
    
    print(f"📈 Trade Frequency:")
    print(f"  Average trades per day: {daily_trades.mean():.1f}")
    print(f"  Max trades in a day: {daily_trades.max()}")
    print(f"  Min trades in a day: {daily_trades.min()}")
    
    # Check for unusually high frequency days
    high_freq_days = daily_trades[daily_trades > 15]
    if len(high_freq_days) > 0:
        print(f"⚠️ Days with unusually high trade frequency (>15 trades):")
        for date, count in high_freq_days.head(5).items():
            print(f"    {date}: {count} trades")
    
    # Hold duration analysis
    print(f"\n⏱️ Hold Duration Analysis:")
    print(f"  Average hold: {df['hold_duration'].mean():.1f} minutes")
    print(f"  Min hold: {df['hold_duration'].min():.1f} minutes")
    print(f"  Max hold: {df['hold_duration'].max():.1f} minutes")
    
    # Check for very long holds
    long_holds = df[df['hold_duration'] > 300]  # > 5 hours
    if len(long_holds) > 0:
        print(f"⚠️ Very long holds (>5 hours): {len(long_holds)} trades")
    
    # P&L distribution
    print(f"\n💰 P&L Distribution:")
    print(f"  Average P&L: {df['pnl'].mean():.2f} points")
    print(f"  Max win: {df['pnl'].max():.2f} points")
    print(f"  Max loss: {df['pnl'].min():.2f} points")
    print(f"  Standard deviation: {df['pnl'].std():.2f} points")
    
    # Exit type analysis
    exit_types = df['exit_type'].value_counts()
    print(f"\n🎯 Exit Type Distribution:")
    for exit_type, count in exit_types.items():
        percentage = (count / len(df)) * 100
        print(f"  {exit_type}: {count} ({percentage:.1f}%)")

def check_slippage_impact(df):
    """Analyze potential slippage impact"""
    
    print("\n" + "=" * 80)
    print("💰 SLIPPAGE IMPACT ANALYSIS")
    print("=" * 80)
    
    # Simulate slippage scenarios
    slippage_scenarios = [0.5, 1.0, 2.0]  # points
    
    for slippage in slippage_scenarios:
        # Apply slippage to all trades
        df_with_slippage = df.copy()
        df_with_slippage['slippage_pnl'] = np.where(df_with_slippage['pnl'] > 0,
                                                   df_with_slippage['pnl'] - slippage,
                                                   df_with_slippage['pnl'] - slippage)
        
        total_pnl_with_slippage = df_with_slippage['slippage_pnl'].sum()
        impact = (total_pnl_with_slippage / df['pnl'].sum() - 1) * 100
        
        print(f"  Slippage {slippage} points: {total_pnl_with_slippage:.2f} P&L ({impact:+.1f}% impact)")
    
    # Check trades with small P&L that would be wiped out by slippage
    small_profits = df[(df['pnl'] > 0) & (df['pnl'] < 2.0)]
    print(f"\n⚠️ Small profit trades (< 2 points): {len(small_profits)} trades")
    print(f"   These would be wiped out by 1-2 point slippage")

def main():
    """Main audit function"""
    
    # Load trades
    file_path = "/Users/sreenathreddy/Downloads/dax-strategies/dax-optimized-pv58-tf5m-75pts/dax_best_detailed_trades_19825_points.csv"
    df = load_trades(file_path)
    
    print(f"📊 Loaded {len(df)} trades for audit")
    print(f"📅 Date range: {df['entry_time'].min()} to {df['entry_time'].max()}")
    
    # Run legitimacy audit
    issues, warnings = audit_trade_legitimacy(df)
    
    # Analyze patterns
    analyze_trade_patterns(df)
    
    # Check slippage impact
    check_slippage_impact(df)
    
    # Summary
    print("\n" + "=" * 80)
    print("📋 AUDIT SUMMARY")
    print("=" * 80)
    
    if len(issues) == 0 and len(warnings) == 0:
        print("✅ PASSED: No critical issues found")
        print("✅ All trades appear legitimate for live trading")
    else:
        print(f"❌ CRITICAL ISSUES: {len(issues)}")
        for issue in issues:
            print(f"  {issue}")
        
        print(f"\n⚠️ WARNINGS: {len(warnings)}")
        for warning in warnings:
            print(f"  {warning}")
    
    # Overall assessment
    print(f"\n🎯 OVERALL ASSESSMENT:")
    if len(issues) == 0:
        print("✅ TRADES ARE LEGITIMATE")
        print("✅ Strategy appears suitable for live trading")
        print("✅ No evidence of look-ahead bias or impossible trades")
    else:
        print("❌ TRADES HAVE CRITICAL ISSUES")
        print("❌ Strategy needs review before live trading")
        print("❌ Evidence of unrealistic or impossible trades")
    
    print(f"\n📊 Key Metrics:")
    print(f"  Total trades: {len(df)}")
    print(f"  Total P&L: {df['pnl'].sum():.2f} points")
    print(f"  Win rate: {(df['pnl'] > 0).sum() / len(df) * 100:.1f}%")
    print(f"  Average trade: {df['pnl'].mean():.2f} points")

if __name__ == "__main__":
    main()
