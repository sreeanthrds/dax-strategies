#!/usr/bin/env python3
"""
DAX Strategy - OPTIMIZED Worker Lambda Function
===============================================

This worker processes a chunk of parameter combinations for the optimized
DAX strategy with REDUCED parameter combinations and single position only.

Key Features:
- Processes 50 parameter combinations per invocation
- Single position only (no dual position)
- Reduced stop options
- Optimized parameter space
- Corrected entry timing (no look-ahead bias)

Expected runtime: ~2-4 minutes per chunk (optimized)
"""

import json
import os
import sys
import math
from datetime import datetime, time as dt_time
from collections import deque
from typing import List, Dict, Any, Optional

# =============================================================================
# OPTIMIZED STRATEGY IMPLEMENTATION
# =============================================================================

class StrategyConfig:
    """Optimized strategy configuration with single position only"""
    def __init__(self, **kwargs):
        self.pivot_left = kwargs.get('pivot_left', 5)
        self.pivot_right = kwargs.get('pivot_right', 8)
        self.timeframe_minutes = kwargs.get('timeframe_minutes', 5)
        self.target_points = kwargs.get('target_points', 75.0)
        self.base_stop = kwargs.get('base_stop', 36.0)
        self.accumulated_loss_mode = kwargs.get('accumulated_loss_mode', 'none')
        self.reset_on_target = kwargs.get('reset_on_target', True)
        self.target_increase_on_hit = kwargs.get('target_increase_on_hit', 30.0)
        self.max_accumulated_loss_cap = kwargs.get('max_accumulated_loss_cap', 150.0)
        self.force_exit_time = kwargs.get('force_exit_time', "16:55")
        self.dual_position = False  # Always single position (optimized)
        self.stop_mode = kwargs.get('stop_mode', 'zone')
        self.bidirectional = kwargs.get('bidirectional', False)  # Keep bidirectional option
        
        self._force_exit_time = None
        if self.force_exit_time:
            h, m = map(int, self.force_exit_time.split(":"))
            self._force_exit_time = dt_time(h, m)

    @property
    def exit_cutoff(self):
        return self._force_exit_time


class SRZoneEngine:
    """Support/Resistance Zone Detection"""
    def __init__(self, left=5, right=8):
        self.left = left
        self.right = right
        self.window = deque(maxlen=left + right + 1)
        self.res1 = None
        self.sup1 = None
        self.res1_time = None
        self.sup1_time = None

    def update(self, candle):
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
        return {
            "res1_high": self.res1["high"] if self.res1 else None,
            "res1_low":  self.res1["low"]  if self.res1 else None,
            "res1_time": self.res1_time,
            "sup1_high": self.sup1["high"] if self.sup1 else None,
            "sup1_low":  self.sup1["low"]  if self.sup1 else None,
            "sup1_time": self.sup1_time,
        }

    def _check_pivot(self):
        if len(self.window) < self.window.maxlen:
            return None, None
        
        mid = self.left
        highs = [c["high"] for c in self.window]
        lows  = [c["low"]  for c in self.window]
        
        pivot_high = self.window[mid] if (
            highs[mid] == max(highs[:mid + 1]) and highs[mid] == max(highs[mid:])
        ) else None
        
        pivot_low = self.window[mid] if (
            lows[mid] == min(lows[:mid + 1]) and lows[mid] == min(lows[mid:])
        ) else None
        
        return pivot_high, pivot_low


class SignalDetector:
    """Optimized signal detection with bidirectional option"""
    def __init__(self, config):
        self.pending_signal = None
        self._confirmed_signal = None
        self.bidirectional = config.bidirectional

    def check_signal(self, candle, zones, occupied_sides):
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
            
            # Determine signal types based on bidirectional setting
            signal_types = self._determine_signal_types(candle, zone, zone_name)
            
            for sig_type in signal_types:
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

    def _determine_signal_types(self, candle, zone, zone_name):
        """Determine signal types based on bidirectional setting"""
        signal_types = []
        
        if self.bidirectional:
            # BIDIRECTIONAL: Generate both signals based on position relative to zone
            if candle["close"] > zone["low"]:
                signal_types.append("BUY")
            if candle["close"] < zone["high"]:
                signal_types.append("SELL")
        else:
            # UNIDIRECTIONAL: Original logic
            if candle["close"] > zone["low"]:
                signal_types.append("BUY")
            elif candle["close"] < zone["low"]:
                signal_types.append("SELL")
        
        return signal_types

    def check_entry_condition(self, candle_1m):
        if not self.pending_signal:
            return False
        
        sig = self.pending_signal
        sc  = sig["signal_candle"]
        zone = sig["zone"]
        
        if sig["type"] == "BUY":
            threshold = max(sc["high"], zone["high"])
            return candle_1m["close"] > threshold
        else:
            threshold = min(sc["low"], zone["low"])
            return candle_1m["close"] < threshold

    def consume_signal(self):
        sig = self.pending_signal
        self.pending_signal = None
        return sig

    def set_confirmed_signal(self, signal):
        """Set confirmed signal for next bar entry"""
        self._confirmed_signal = signal

    def get_confirmed_signal(self):
        """Get confirmed signal for next bar entry"""
        sig = self._confirmed_signal
        self._confirmed_signal = None
        return sig

    def clear(self):
        self.pending_signal = None
        self._confirmed_signal = None


class PositionManager:
    """Optimized position management with single position only"""
    def __init__(self, config):
        self.config = config
        self.positions = {}
        self.accumulated_losses = 0.0
        self.current_target_points = config.target_points
        self.reset_accumulated_losses()

    @property
    def occupied_sides(self):
        return set(self.positions.keys())

    def has_any_position(self):
        return len(self.positions) > 0

    def can_take_signal(self, side):
        if side in self.positions:
            return False
        # OPTIMIZED: Always single position (no dual position)
        if self.positions:  # If any position exists, can't take new signal
            return False
        return True

    def open_position(self, signal, entry_candle):
        """Open position with corrected entry logic"""
        side = signal["type"]
        if not self.can_take_signal(side):
            return None

        sc = signal["signal_candle"]
        zone = signal["zone"]
        
        # CORRECTED: Use entry_candle's open price (next bar's open)
        entry_price = entry_candle["open"]
        entry_time = entry_candle["timestamp"]

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
        pos = self.positions.get(side)
        if pos is None:
            return None

        if side == "BUY":
            if candle_1m["high"] >= pos["target_price"]:
                return ("TARGET", candle_1m["close"])
        else:
            if candle_1m["low"] <= pos["target_price"]:
                return ("TARGET", candle_1m["close"])

        if self.config.stop_mode in ('zone', 'both'):
            if side == "BUY":
                if candle_1m["close"] < pos["zone_low"]:
                    return ("STOP_LOSS", candle_1m["close"])
            else:
                if candle_1m["close"] > pos["zone_high"]:
                    return ("STOP_LOSS", candle_1m["close"])

        if self.config.stop_mode in ('distance', 'both'):
            if side == "BUY":
                stop_price = pos["entry_price"] - pos["stop_distance"]
                if candle_1m["close"] < stop_price:
                    return ("STOP_LOSS", candle_1m["close"])
            else:
                stop_price = pos["entry_price"] + pos["stop_distance"]
                if candle_1m["close"] > stop_price:
                    return ("STOP_LOSS", candle_1m["close"])

        return None

    def force_exit(self, candle_1m, side):
        return ("FORCE_EXIT", candle_1m["close"])

    def close_position(self, side):
        return self.positions.pop(side, None)

    def update_result(self, pnl, exit_type):
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
        self.accumulated_losses = 0.0
        self.current_target_points = self.config.target_points


class TradeRecorder:
    """Trade recording"""
    def __init__(self):
        self.trades = []
        self._next_id = 1

    def record(self, position, exit_time, exit_price, exit_type):
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
        }
        
        self.trades.append(trade)
        self._next_id += 1
        return trade


class DAXStrategyEngineOptimized:
    """Optimized DAX strategy engine with single position only"""
    def __init__(self, config):
        self.config = config
        self.zone_engine = SRZoneEngine(config.pivot_left, config.pivot_right)
        self.signal_detector = SignalDetector(config)
        self.position_mgr = PositionManager(config)
        self.trade_recorder = TradeRecorder()
        self._tf_buffer = []
        self._tf_start = None
        self._current_date = None
        self._force_exited_today = False

    def run(self, df_1min):
        """Run strategy with optimized options"""
        df_1min = sorted(df_1min, key=lambda x: x["timestamp"])
        
        for candle in df_1min:
            self._process_candle(candle)
            
        self._flush_tf_candle()
        
        # Close remaining positions
        if self.position_mgr.has_any_position() and self._tf_buffer:
            last = self._tf_buffer[-1]
            for side in list(self.position_mgr.positions.keys()):
                self._do_exit(last, side, *self.position_mgr.force_exit(last, side))
        
        return self.trade_recorder.trades

    def _process_candle(self, candle):
        ts = datetime.fromisoformat(candle["timestamp"].replace('Z', '+00:00'))
        candle_date = ts.date()
        tf_min = self.config.timeframe_minutes
        
        # Trading hours filter
        market_open = dt_time(9, 0)
        last_trade_cutoff = dt_time(16, 30)
        
        if ts.time() < market_open or ts.time() > last_trade_cutoff:
            return

        tf_start_minute = (ts.minute // tf_min) * tf_min
        tf_start = ts.replace(minute=tf_start_minute, second=0, microsecond=0)

        # New day reset
        if candle_date != self._current_date:
            if self.position_mgr.has_any_position() and self._tf_buffer:
                for side in list(self.position_mgr.positions.keys()):
                    self._do_exit(self._tf_buffer[-1], side,
                                  *self.position_mgr.force_exit(self._tf_buffer[-1], side))
            self.position_mgr.reset_accumulated_losses()
            self._current_date = candle_date
            self._force_exited_today = False

        # TF boundary
        if self._tf_start is not None and tf_start != self._tf_start:
            self._flush_tf_candle()
            self._tf_buffer = []

        self._tf_start = tf_start
        self._tf_buffer.append(candle)

        # Force exit
        cutoff = self.config.exit_cutoff
        if cutoff and not self._force_exited_today:
            if ts.time() >= cutoff:
                if self.position_mgr.has_any_position():
                    for side in list(self.position_mgr.positions.keys()):
                        self._do_exit(candle, side,
                                      *self.position_mgr.force_exit(candle, side))
                self._force_exited_today = True
                self.signal_detector.clear()
                return

        if self._force_exited_today:
            return

        # Check exits
        for side in list(self.position_mgr.positions.keys()):
            result = self.position_mgr.check_exit(candle, side)
            if result:
                self._do_exit(candle, side, *result)

        # CORRECTED ENTRY LOGIC
        # Step 1: Execute confirmed signal
        confirmed_signal = self.signal_detector.get_confirmed_signal()
        if confirmed_signal:
            sig_side = confirmed_signal["type"]
            if self.position_mgr.can_take_signal(sig_side):
                position = self.position_mgr.open_position(confirmed_signal, candle)

        # Step 2: Check for new signal confirmation
        elif self.signal_detector.pending_signal:
            sig_side = self.signal_detector.pending_signal["type"]
            if self.position_mgr.can_take_signal(sig_side):
                if self.signal_detector.check_entry_condition(candle):
                    # Set confirmed signal for next bar
                    confirmed_signal = self.signal_detector.consume_signal()
                    self.signal_detector.set_confirmed_signal(confirmed_signal)

    def _flush_tf_candle(self):
        if not self._tf_buffer:
            return
        
        tf_candle = {
            "timestamp": self._tf_start.isoformat(),
            "open": self._tf_buffer[0]["open"],
            "high": max(c["high"] for c in self._tf_buffer),
            "low": min(c["low"] for c in self._tf_buffer),
            "close": self._tf_buffer[-1]["close"],
        }
        
        zones = self.zone_engine.update(tf_candle)
        if not self._force_exited_today:
            occupied = self.position_mgr.occupied_sides
            self.signal_detector.check_signal(tf_candle, zones, occupied)

    def _do_exit(self, candle, side, exit_type, exit_price):
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
    """Calculate performance metrics"""
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
    
    # Calculate Sharpe ratio
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
                except (ValueError, KeyError):
                    continue
        return data
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return None


# =============================================================================
# MAIN WORKER FUNCTION
# =============================================================================

def run_strategy_test(config_dict, data):
    """Run strategy test with given optimized configuration"""
    try:
        config = StrategyConfig(**config_dict)
        engine = DAXStrategyEngineOptimized(config)
        trades = engine.run(data)
        metrics = calculate_metrics(trades)
        
        return {
            'config': config_dict,
            'metrics': metrics,
            'trades_count': len(trades),
            'error': None
        }
        
    except Exception as e:
        return {
            'config': config_dict,
            'metrics': None,
            'trades_count': 0,
            'error': str(e)
        }


def lambda_handler(event, context):
    """Main Lambda handler for optimized worker"""
    
    try:
        # Extract parameters
        chunk_id = event.get('chunk_id', 0)
        combinations = event.get('combinations', [])
        data_file_path = event.get('data_file_path')
        
        print(f"🔄 Processing chunk {chunk_id} with {len(combinations)} optimized combinations")
        
        # Load data
        data = load_dax_1min_data(data_file_path)
        if not data:
            return {
                'chunk_id': chunk_id,
                'error': 'Failed to load data',
                'results': []
            }
        
        print(f"📊 Loaded {len(data)} data points")
        
        # Process each combination
        results = []
        for i, config_dict in enumerate(combinations):
            try:
                result = run_strategy_test(config_dict, data)
                results.append(result)
                
                if (i + 1) % 10 == 0:
                    print(f"📈 Completed {i + 1}/{len(combinations)} combinations")
                    
            except Exception as e:
                print(f"❌ Error processing combination {i}: {e}")
                results.append({
                    'config': config_dict,
                    'metrics': None,
                    'trades_count': 0,
                    'error': str(e)
                })
        
        print(f"✅ Chunk {chunk_id} completed: {len(results)} results")
        
        return {
            'chunk_id': chunk_id,
            'results': results,
            'error': None
        }
        
    except Exception as e:
        print(f"❌ Worker failed: {e}")
        return {
            'chunk_id': event.get('chunk_id', 0),
            'error': str(e),
            'results': []
        }


if __name__ == "__main__":
    # For local testing
    import csv
    
    class MockContext:
        pass
    
    # Test with sample optimized configurations
    test_event = {
        'chunk_id': 0,
        'combinations': [
            {
                'pivot_left': 5, 'pivot_right': 8, 'timeframe_minutes': 5,
                'target_points': 75.0, 'base_stop': 36.0, 'stop_mode': 'zone',
                'accumulated_loss_mode': 'none', 'reset_on_target': True,
                'target_increase_on_hit': 30.0, 'max_accumulated_loss_cap': 150.0,
                'force_exit_time': "16:55", 'dual_position': False,
                'bidirectional': False
            },
            {
                'pivot_left': 4, 'pivot_right': 9, 'timeframe_minutes': 10,
                'target_points': 60.0, 'base_stop': 30.0, 'stop_mode': 'both',
                'accumulated_loss_mode': 'to_target', 'reset_on_target': True,
                'target_increase_on_hit': 25.0, 'max_accumulated_loss_cap': 120.0,
                'force_exit_time': "16:30", 'dual_position': False,
                'bidirectional': True
            }
        ],
        'data_file_path': "/Users/sreenathreddy/Downloads/UniTrader-project/signal_trade_processor/strategy_optimization_complete/data/dax_1min_ohlc.csv"
    }
    
    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2))
