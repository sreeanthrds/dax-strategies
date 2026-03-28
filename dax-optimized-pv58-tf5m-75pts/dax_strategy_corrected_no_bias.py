#!/usr/bin/env python3
"""
DAX Strategy - CORRECTED VERSION (No Look-Ahead Bias)
====================================================

This version fixes the critical look-ahead bias issue in the original backtest.
The key fix:
- Entry happens at NEXT bar's OPEN price (not current bar's OPEN)
- Entry time is NEXT bar's timestamp (not current bar's timestamp)
- This eliminates look-ahead bias and matches real trading conditions

Original Issue:
- Signal confirmed at bar close
- Entry executed at same bar's OPEN price (look-ahead bias!)
- Entry time recorded as current bar timestamp

Corrected Logic:
- Signal confirmed at bar close
- Entry executed at NEXT bar's OPEN price
- Entry time recorded as next bar timestamp
"""

import json
import os
import csv
import io
from datetime import datetime, time as dt_time
from collections import deque
from typing import Optional, Dict, List, Any
import statistics
import math


# =============================================================================
# CONFIGURATION (Same as original optimized)
# =============================================================================

class StrategyConfig:
    """All DAX strategy parameters - using optimized values"""
    def __init__(self,
                 pivot_left=5,              # DAX optimized: 5 bars left
                 pivot_right=8,             # DAX optimized: 8 bars right  
                 timeframe_minutes=5,       # DAX optimized: 5 minute TF
                 target_points=75.0,        # DAX optimized: 75 point target
                 base_stop=36.0,            # DAX optimized: 36 point base stop
                 accumulated_loss_mode='none',  # Simplified for now
                 reset_on_target=True,       # Reset losses on target hit
                 target_increase_on_hit=30.0, # Increase target by 30 on hit
                 max_accumulated_loss_cap=150.0,  # Cap for accumulated loss
                 force_exit_time="16:55",    # Force exit at last candle before 17:00
                 dual_position=False,         # Single position for DAX
                 stop_mode='zone'):          # Zone stops work best for DAX
        self.pivot_left = pivot_left
        self.pivot_right = pivot_right
        self.timeframe_minutes = timeframe_minutes
        self.target_points = target_points
        self.base_stop = base_stop
        self.accumulated_loss_mode = accumulated_loss_mode
        self.reset_on_target = reset_on_target
        self.target_increase_on_hit = target_increase_on_hit
        self.max_accumulated_loss_cap = max_accumulated_loss_cap
        self.force_exit_time = force_exit_time
        self.dual_position = dual_position
        self.stop_mode = stop_mode

        self._force_exit_time = None
        if self.force_exit_time:
            h, m = map(int, self.force_exit_time.split(":"))
            self._force_exit_time = dt_time(h, m)

    @property
    def exit_cutoff(self):
        return self._force_exit_time


# =============================================================================
# CORE STRATEGY CLASSES (Same as original)
# =============================================================================

class SRZoneEngine:
    """Support/Resistance Zone Detection using Pivot Points"""
    def __init__(self, left=5, right=8):
        self.left = left
        self.right = right
        # CRITICAL: Window size must be left + right + 1
        self.window = deque(maxlen=left + right + 1)
        self.res1 = None
        self.sup1 = None
        self.res1_time = None
        self.sup1_time = None

    def update(self, candle):
        """Update zone engine with new TF candle"""
        self.window.append(candle)
        pivot_high, pivot_low = self._check_pivot()
        if pivot_high:
            self.res1 = {"high": pivot_high["high"], "low": pivot_high["low"]}
            self.res1_time = candle["timestamp"]
        if pivot_low:
            self.sup1 = {"high": pivot_low["high"], "low": pivot_low["low"]}
            self.sup1_time = candle["timestamp"]
        return self.get_zones()

    def get_zones(self):
        """Get current support/resistance zones"""
        return {
            "res1_high": self.res1["high"] if self.res1 else None,
            "res1_low":  self.res1["low"]  if self.res1 else None,
            "res1_time": self.res1_time,
            "sup1_high": self.sup1["high"] if self.sup1 else None,
            "sup1_low":  self.sup1["low"]  if self.sup1 else None,
            "sup1_time": self.sup1_time,
        }

    def _check_pivot(self):
        """Check for pivot high/low at middle of window"""
        if len(self.window) < self.window.maxlen:
            return None, None
        
        mid = self.left  # Middle element
        highs = [c["high"] for c in self.window]
        lows  = [c["low"]  for c in self.window]
        
        # Pivot high: highest in left AND right sides
        pivot_high = self.window[mid] if (
            highs[mid] == max(highs[:mid + 1]) and highs[mid] == max(highs[mid:])
        ) else None
        
        # Pivot low: lowest in left AND right sides  
        pivot_low = self.window[mid] if (
            lows[mid] == min(lows[:mid + 1]) and lows[mid] == min(lows[mid:])
        ) else None
        
        return pivot_high, pivot_low


class SignalDetector:
    """Two-step signal detection: TF candle signal → 1-min confirmation"""
    def __init__(self):
        self.pending_signal = None

    def check_signal(self, candle, zones, occupied_sides):
        """
        Generate signal if a zone is touched on TF candle.
        occupied_sides: set of sides that already have positions, e.g. {'BUY'}
        """
        signals = []
        for zone_name in ["sup1", "res1"]:
            zone_high = zones.get(f"{zone_name}_high")
            zone_low  = zones.get(f"{zone_name}_low")
            zone_time = zones.get(f"{zone_name}_time")
            if zone_high is None or zone_low is None:
                continue
            
            zone = {"high": zone_high, "low": zone_low}
            
            # Check if candle touches the zone
            if not (candle["low"] <= zone_low <= candle["high"]):
                continue
            
            # Determine signal type based on close position
            if candle["close"] > zone_low:
                sig_type = "BUY"
            elif candle["close"] < zone_low:
                sig_type = "SELL"
            else:
                continue
            
            # Skip if that side is occupied
            if sig_type in occupied_sides:
                continue
            
            signals.append({
                "type": sig_type,
                "zone_name": zone_name,
                "zone": zone,
                "zone_time": zone_time,
                "signal_candle": {
                    "timestamp": candle["timestamp"],
                    "open": candle["open"],
                    "high": candle["high"],
                    "low": candle["low"],
                    "close": candle["close"],
                },
            })
        
        if not signals:
            return None
        
        # Use most recent zone (by zone_time)
        signals.sort(key=lambda s: s["zone_time"] or datetime.min, reverse=True)
        self.pending_signal = signals[0]
        return signals[0]

    def check_entry_condition(self, candle_1m):
        """Check entry condition on 1-minute candle"""
        if not self.pending_signal:
            return False
        
        sig = self.pending_signal
        sc  = sig["signal_candle"]
        zone = sig["zone"]
        
        if sig["type"] == "BUY":
            # Buy if close exceeds max(signal_high, zone_high)
            threshold = max(sc["high"], zone["high"])
            return candle_1m["close"] > threshold
        else:
            # Sell if close below min(signal_low, zone_low)
            threshold = min(sc["low"], zone["low"])
            return candle_1m["close"] < threshold

    def consume_signal(self):
        """Consume the pending signal"""
        sig = self.pending_signal
        self.pending_signal = None
        return sig

    def clear(self):
        """Clear pending signal"""
        self.pending_signal = None


class PositionManager:
    """Position management with accumulated loss handling"""
    def __init__(self, config):
        self.config = config
        # positions keyed by side: {'BUY': {...}, 'SELL': {...}}
        self.positions = {}
        self.accumulated_losses = 0.0
        self.current_target_points = config.target_points
        self.reset_accumulated_losses()

    # ── queries ────────────────────────────────────────────────────
    @property
    def occupied_sides(self):
        return set(self.positions.keys())

    def has_any_position(self):
        return len(self.positions) > 0

    def can_take_signal(self, side):
        """Can we open a position on this side?"""
        if side in self.positions:
            return False
        if not self.config.dual_position and self.positions:
            return False  # single-position mode, something is open
        return True

    # ── open / close ───────────────────────────────────────────────
    def open_position(self, signal, entry_candle):
        """Open a new position - CORRECTED VERSION"""
        side = signal["type"]
        if not self.can_take_signal(side):
            return None

        sc = signal["signal_candle"]
        zone = signal["zone"]
        
        # CORRECTED: Use entry_candle's open price (next bar's open)
        entry_price = entry_candle["open"]
        entry_time = entry_candle["timestamp"]

        # Calculate stop distance based on accumulated losses
        if self.config.accumulated_loss_mode == 'none':
            current_stop_distance = self.config.base_stop
        else:
            current_stop_distance = self.config.base_stop + self.accumulated_losses

        pos = {
            "type": side,
            "zone_name": signal["zone_name"],
            "zone": zone,
            "signal_candle": sc,
            "signal_time": sc["timestamp"],
            "entry_time": entry_time,
            "entry_price": entry_price,
            "target_price": (entry_price + self.current_target_points if side == "BUY"
                             else entry_price - self.current_target_points),
            "zone_low": zone["low"],
            "zone_high": zone["high"],
            "stop_distance": current_stop_distance,
            "target_points": self.current_target_points,
        }
        self.positions[side] = pos
        return pos

    def check_exit(self, candle_1m, side):
        """Check exit conditions for a specific side's position"""
        pos = self.positions.get(side)
        if pos is None:
            return None

        # ── target hit ────────────────────────────────────────────
        if side == "BUY":
            if candle_1m["high"] >= pos["target_price"]:
                return ("TARGET", candle_1m["close"])  # Use close for exit
        else:
            if candle_1m["low"] <= pos["target_price"]:
                return ("TARGET", candle_1m["close"])  # Use close for exit

        # ── zone-based stop ───────────────────────────────────────
        if self.config.stop_mode in ('zone', 'both'):
            if side == "BUY":
                if candle_1m["close"] < pos["zone_low"]:
                    return ("STOP_LOSS", candle_1m["close"])  # Use close for exit
            else:
                if candle_1m["close"] > pos["zone_high"]:
                    return ("STOP_LOSS", candle_1m["close"])  # Use close for exit

        # ── distance-based stop ───────────────────────────────────
        if self.config.stop_mode in ('distance', 'both'):
            if side == "BUY":
                stop_price = pos["entry_price"] - pos["stop_distance"]
                if candle_1m["close"] < stop_price:
                    return ("STOP_LOSS", candle_1m["close"])  # Use close for exit
            else:
                stop_price = pos["entry_price"] + pos["stop_distance"]
                if candle_1m["close"] > stop_price:
                    return ("STOP_LOSS", candle_1m["close"])  # Use close for exit

        return None

    def force_exit(self, candle_1m, side):
        """Force exit position using close price"""
        return ("FORCE_EXIT", candle_1m["close"])  # Use close for exit

    def close_position(self, side):
        """Close position and return it"""
        return self.positions.pop(side, None)

    def update_result(self, pnl, exit_type):
        """Update accumulated losses based on trade result"""
        mode = self.config.accumulated_loss_mode
        if mode in ('to_target', 'to_target_increase'):
            if pnl < 0:
                self.accumulated_losses += abs(pnl)
                cap = self.config.max_accumulated_loss_cap
                if cap > 0:
                    self.accumulated_losses = min(self.accumulated_losses, cap)

            if exit_type == "TARGET" and self.config.reset_on_target:
                self.accumulated_losses = 0.0
                if (self.config.target_increase_on_hit > 0
                        and mode == 'to_target_increase'):
                    self.current_target_points += self.config.target_increase_on_hit

    def reset_accumulated_losses(self):
        """Reset accumulated losses"""
        self.accumulated_losses = 0.0
        self.current_target_points = self.config.target_points


class TradeRecorder:
    """Record and track all trades"""
    def __init__(self):
        self.trades = []
        self._next_id = 1

    def record(self, position, exit_time, exit_price, exit_type):
        """Record a completed trade"""
        entry_price = position["entry_price"]
        pnl = ((exit_price - entry_price) if position["type"] == "BUY"
               else (entry_price - exit_price))
        
        entry_ts = datetime.fromisoformat(position["entry_time"].replace('Z', '+00:00'))
        exit_ts  = datetime.fromisoformat(exit_time.replace('Z', '+00:00'))
        hold_min = (exit_ts - entry_ts).total_seconds() / 60.0
        
        trade = {
            "trade_id": self._next_id,
            "signal_type": position["type"],
            "zone_name": position["zone_name"],
            "entry_time": position["entry_time"],
            "entry_price": entry_price,
            "target_price": position["target_price"],
            "exit_time": exit_time,
            "exit_price": exit_price,
            "exit_type": exit_type,
            "pnl": pnl,
            "hold_duration": hold_min,
            "entry_date": entry_ts.date().isoformat(),
            "exit_date": exit_ts.date().isoformat(),
            "entry_hour": entry_ts.strftime("%H:%M"),
            "exit_hour": exit_ts.strftime("%H:%M"),
        }
        
        self.trades.append(trade)
        self._next_id += 1
        return trade


# =============================================================================
# CORRECTED STRATEGY ENGINE
# =============================================================================

class DAXStrategyEngineCorrected:
    """DAX strategy engine with corrected entry timing (no look-ahead bias)"""
    def __init__(self, config):
        self.config = config
        self.zone_engine = SRZoneEngine(config.pivot_left, config.pivot_right)
        self.signal_detector = SignalDetector()
        self.position_mgr = PositionManager(config)
        self.trade_recorder = TradeRecorder()
        self._tf_buffer = []
        self._tf_start = None
        self._current_date = None
        self._force_exited_today = False
        
        # CORRECTED: Track confirmed signals for next bar entry
        self._confirmed_signal = None

    def run(self, df_1min):
        """Run strategy on 1-minute data with corrected timing"""
        df_1min = sorted(df_1min, key=lambda x: x["timestamp"])
        
        for i, candle in enumerate(df_1min):
            self._process_candle(candle)
            
        self._flush_tf_candle()
        
        # Close any remaining positions at the end
        if self.position_mgr.has_any_position() and self._tf_buffer:
            last = self._tf_buffer[-1]
            for side in list(self.position_mgr.positions.keys()):
                self._do_exit(last, side, *self.position_mgr.force_exit(last, side))
        
        return self.trade_recorder.trades

    def _process_candle(self, candle):
        """Process each 1-minute candle with corrected entry logic"""
        ts = datetime.fromisoformat(candle["timestamp"].replace('Z', '+00:00'))
        candle_date = ts.date()
        tf_min = self.config.timeframe_minutes
        
        # ── Trading time filters ───────────────────────────────────────
        market_open = dt_time(9, 0)
        last_trade_cutoff = dt_time(16, 30)
        
        # Skip processing outside trading hours
        if ts.time() < market_open or ts.time() > last_trade_cutoff:
            return

        tf_start_minute = (ts.minute // tf_min) * tf_min
        tf_start = ts.replace(minute=tf_start_minute, second=0, microsecond=0)

        # ── new day ───────────────────────────────────────────────
        if candle_date != self._current_date:
            if self.position_mgr.has_any_position() and self._tf_buffer:
                for side in list(self.position_mgr.positions.keys()):
                    self._do_exit(self._tf_buffer[-1], side,
                                  *self.position_mgr.force_exit(self._tf_buffer[-1], side))
            self.position_mgr.reset_accumulated_losses()
            self._current_date = candle_date
            self._force_exited_today = False
            self._confirmed_signal = None  # Reset confirmed signal

        # ── TF boundary ───────────────────────────────────────────
        if self._tf_start is not None and tf_start != self._tf_start:
            self._flush_tf_candle()
            self._tf_buffer = []

        self._tf_start = tf_start
        self._tf_buffer.append(candle)

        # ── force-exit time ───────────────────────────────────────
        cutoff = self.config.exit_cutoff
        if cutoff and not self._force_exited_today:
            if ts.time() >= cutoff:
                if self.position_mgr.has_any_position():
                    for side in list(self.position_mgr.positions.keys()):
                        self._do_exit(candle, side,
                                      *self.position_mgr.force_exit(candle, side))
                self._force_exited_today = True
                self.signal_detector.clear()
                self._confirmed_signal = None
                return

        if self._force_exited_today:
            return

        # ── check exits for all open positions ────────────────────
        for side in list(self.position_mgr.positions.keys()):
            result = self.position_mgr.check_exit(candle, side)
            if result:
                self._do_exit(candle, side, *result)

        # ── CORRECTED: Entry execution logic ───────────────────────
        # Step 1: Check for confirmed signal on current candle
        if self._confirmed_signal:
            # Execute entry at current candle's OPEN price
            sig_side = self._confirmed_signal["type"]
            if self.position_mgr.can_take_signal(sig_side):
                position = self.position_mgr.open_position(self._confirmed_signal, candle)
                if position:
                    print(f"[ENTRY] {sig_side} at {position['entry_price']:.2f} on {candle['timestamp']}")
            self._confirmed_signal = None  # Clear after execution

        # Step 2: Check for new signal confirmation
        elif self.signal_detector.pending_signal:
            sig_side = self.signal_detector.pending_signal["type"]
            if self.position_mgr.can_take_signal(sig_side):
                if self.signal_detector.check_entry_condition(candle):
                    # Signal confirmed - set for entry on next candle
                    self._confirmed_signal = self.signal_detector.consume_signal()
                    print(f"[CONFIRMED] {sig_side} signal confirmed at {candle['timestamp']} - will enter on next bar")

    def _flush_tf_candle(self):
        """Flush TF candle and check for signals"""
        if not self._tf_buffer:
            return
        
        tf_candle = {
            "timestamp": self._tf_start.isoformat(),
            "open": self._tf_buffer[0]["open"],
            "high": max(c["high"] for c in self._tf_buffer),
            "low": min(c["low"] for c in self._tf_buffer),
            "close": self._tf_buffer[-1]["close"],
        }
        
        # Update zones and check for signals
        zones = self.zone_engine.update(tf_candle)
        if not self._force_exited_today:
            occupied = self.position_mgr.occupied_sides
            self.signal_detector.check_signal(tf_candle, zones, occupied)

    def _do_exit(self, candle, side, exit_type, exit_price):
        """Execute position exit"""
        position = self.position_mgr.close_position(side)
        if position is None:
            return None
        trade = self.trade_recorder.record(position, candle["timestamp"],
                                           exit_price, exit_type)
        self.position_mgr.update_result(trade["pnl"], exit_type)
        return trade


# =============================================================================
# PERFORMANCE METRICS
# =============================================================================

def calculate_metrics(trades):
    """Calculate comprehensive performance metrics"""
    if not trades:
        return {
            'total_trades': 0, 'total_pnl': 0, 'win_rate': 0, 'avg_win': 0,
            'avg_loss': 0, 'max_drawdown': 0, 'profit_factor': 0,
            'sharpe_ratio': 0, 'target_hits': 0, 'stop_hits': 0, 'force_exits': 0,
            'profit_dd_ratio': 0,
        }

    total_trades = len(trades)
    total_pnl = sum(t['pnl'] for t in trades)
    winning_trades = [t for t in trades if t['pnl'] > 0]
    losing_trades = [t for t in trades if t['pnl'] < 0]
    
    win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
    avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
    avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0
    
    # Target and stop hit counts
    target_hits = len([t for t in trades if t['exit_type'] == 'TARGET'])
    stop_hits = len([t for t in trades if t['exit_type'] == 'STOP_LOSS'])
    force_exits = len([t for t in trades if t['exit_type'] == 'FORCE_EXIT'])
    
    # Calculate maximum drawdown
    cumulative_pnl = []
    running_pnl = 0
    for trade in trades:
        running_pnl += trade['pnl']
        cumulative_pnl.append(running_pnl)
    
    max_drawdown = 0
    peak = cumulative_pnl[0] if cumulative_pnl else 0
    for pnl in cumulative_pnl:
        if pnl > peak:
            peak = pnl
        drawdown = peak - pnl
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    # Calculate profit factor
    gross_profit = sum(t['pnl'] for t in winning_trades)
    gross_loss = abs(sum(t['pnl'] for t in losing_trades))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
    
    # Calculate Sharpe ratio (simplified)
    returns = [t['pnl'] for t in trades]
    if len(returns) > 1:
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance)
        sharpe_ratio = avg_return / std_dev * math.sqrt(252) if std_dev > 0 else 0
    else:
        sharpe_ratio = 0
    
    profit_dd_ratio = total_pnl / max_drawdown if max_drawdown > 0 else 0

    return {
        'total_trades': total_trades,
        'total_pnl': total_pnl,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'max_drawdown': max_drawdown,
        'profit_factor': profit_factor,
        'sharpe_ratio': sharpe_ratio,
        'target_hits': target_hits,
        'stop_hits': stop_hits,
        'force_exits': force_exits,
        'profit_dd_ratio': profit_dd_ratio,
    }


# =============================================================================
# DATA LOADING
# =============================================================================

def load_dax_1min_data(file_path):
    """Load DAX 1-minute OHLC data"""
    data = []
    try:
        with open(file_path, 'r') as f:
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
                except (ValueError, KeyError) as e:
                    print(f"Skipping invalid row: {e}")
                    continue
        print(f"✅ Loaded {len(data)} 1-minute bars from {file_path}")
        return data
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
        return None
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return None


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def run_corrected_strategy_test():
    """Run corrected strategy test and compare with original"""
    print("=" * 80)
    print("🔧 DAX STRATEGY - CORRECTED VERSION (No Look-Ahead Bias)")
    print("=" * 80)
    
    # Load data
    data_file = "/Users/sreenathreddy/Downloads/UniTrader-project/signal_trade_processor/strategy_optimization_complete/data/dax_1min_ohlc.csv"
    data = load_dax_1min_data(data_file)
    
    if not data:
        print("❌ Failed to load data")
        return
    
    # Create optimized configuration
    config = StrategyConfig(
        pivot_left=5,
        pivot_right=8,
        timeframe_minutes=5,
        target_points=75.0,
        base_stop=36.0,
        accumulated_loss_mode='none',
        reset_on_target=True,
        target_increase_on_hit=30.0,
        max_accumulated_loss_cap=150.0,
        force_exit_time="16:55",
        dual_position=False,
        stop_mode='zone'
    )
    
    print(f"📊 Configuration: Pv {config.pivot_left}/{config.pivot_right} TF {config.timeframe_minutes}m Target {config.target_points} Stop {config.base_stop}")
    print(f"📈 Data range: {data[0]['timestamp']} to {data[-1]['timestamp']}")
    print()
    
    # Run corrected strategy
    print("🚀 Running corrected strategy...")
    engine = DAXStrategyEngineCorrected(config)
    corrected_trades = engine.run(data)
    
    # Calculate metrics
    corrected_metrics = calculate_metrics(corrected_trades)
    
    # Display results
    print("\n" + "=" * 80)
    print("📊 CORRECTED STRATEGY RESULTS (No Look-Ahead Bias)")
    print("=" * 80)
    print(f"🎯 Total Trades: {corrected_metrics['total_trades']}")
    print(f"💰 Total P&L: {corrected_metrics['total_pnl']:.2f} points")
    print(f"📈 Win Rate: {corrected_metrics['win_rate']:.1f}%")
    print(f"📊 Avg Win: {corrected_metrics['avg_win']:.2f} points")
    print(f"📉 Avg Loss: {corrected_metrics['avg_loss']:.2f} points")
    print(f"🎯 Profit Factor: {corrected_metrics['profit_factor']:.2f}")
    print(f"📈 Sharpe Ratio: {corrected_metrics['sharpe_ratio']:.3f}")
    print(f"📉 Max Drawdown: {corrected_metrics['max_drawdown']:.2f} points")
    print(f"🎯 Target Hits: {corrected_metrics['target_hits']}")
    print(f"🛑 Stop Hits: {corrected_metrics['stop_hits']}")
    print(f"⏰ Force Exits: {corrected_metrics['force_exits']}")
    print(f"📊 Profit/DD Ratio: {corrected_metrics['profit_dd_ratio']:.2f}")
    
    # Save corrected trades
    output_file = "/Users/sreenathreddy/Downloads/dax-strategies/dax-optimized-pv58-tf5m-75pts/dax_corrected_trades_no_bias.csv"
    
    if corrected_trades:
        with open(output_file, 'w', newline='') as f:
            fieldnames = corrected_trades[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(corrected_trades)
        print(f"\n✅ Corrected trades saved to: {output_file}")
    
    # Compare with original (if available)
    original_file = "/Users/sreenathreddy/Downloads/UniTrader-project/dax_strategy_optimized/dax_best_detailed_trades_19825_points.csv"
    if os.path.exists(original_file):
        print("\n" + "=" * 80)
        print("📊 COMPARISON WITH ORIGINAL BACKTEST")
        print("=" * 80)
        
        # Load original results
        original_trades = []
        with open(original_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                original_trades.append(row)
        
        original_metrics = calculate_metrics(original_trades)
        
        print(f"📊 ORIGINAL (with bias):")
        print(f"   Total P&L: {original_metrics['total_pnl']:.2f} points")
        print(f"   Win Rate: {original_metrics['win_rate']:.1f}%")
        print(f"   Profit Factor: {original_metrics['profit_factor']:.2f}")
        print(f"   Max Drawdown: {original_metrics['max_drawdown']:.2f} points")
        
        print(f"\n📊 CORRECTED (no bias):")
        print(f"   Total P&L: {corrected_metrics['total_pnl']:.2f} points")
        print(f"   Win Rate: {corrected_metrics['win_rate']:.1f}%")
        print(f"   Profit Factor: {corrected_metrics['profit_factor']:.2f}")
        print(f"   Max Drawdown: {corrected_metrics['max_drawdown']:.2f} points")
        
        # Calculate difference
        pnl_diff = corrected_metrics['total_pnl'] - original_metrics['total_pnl']
        pnl_pct = (pnl_diff / original_metrics['total_pnl']) * 100 if original_metrics['total_pnl'] != 0 else 0
        
        print(f"\n📈 IMPACT OF CORRECTION:")
        print(f"   P&L Difference: {pnl_diff:.2f} points ({pnl_pct:+.1f}%)")
        print(f"   Trade Count Diff: {corrected_metrics['total_trades'] - original_metrics['total_trades']}")
        print(f"   Win Rate Diff: {corrected_metrics['win_rate'] - original_metrics['win_rate']:+.1f}%")
    
    return corrected_trades, corrected_metrics


if __name__ == "__main__":
    trades, metrics = run_corrected_strategy_test()
