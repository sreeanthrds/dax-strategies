#!/usr/bin/env python3
"""
DAX Strategy — Bidirectional Zone Entries
==========================================

Modified to take entries in both directions at both support and resistance zones:

Resistance Zone:
- BUY if zone high + signal candle high breaks (current)
- SELL if zone low + signal candle low breaks (NEW)

Support Zone:
- SELL if zone low + signal candle low breaks (current)
- BUY if zone high + signal candle high breaks (NEW)

Key Features:
• Pivot-based Support/Resistance zone detection
• Two-step signal generation (TF candle → 1-min confirmation)
• Bidirectional entries at both zones
• Multiple stop modes (zone, distance, both)
• Accumulated loss management
• Trading hours: 9:00-15:30
• Force exit at configured time
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
# CONFIGURATION
# =============================================================================

class StrategyConfig:
    """All DAX strategy parameters in one place."""
    def __init__(self,
                 pivot_left=5,               # Optimized: 5 bars left
                 pivot_right=8,              # Optimized: 8 bars right  
                 timeframe_minutes=5,        # Optimized: 5 minute TF
                 target_points=75.0,         # Optimized: 75 point target
                 base_stop=36.0,             # Optimized: 36 point base stop
                 accumulated_loss_mode='none', # Optimized: none
                 reset_on_target=True,       # Reset losses on target hit
                 target_increase_on_hit=30.0, # Increase target by 30 on hit
                 max_accumulated_loss_cap=150.0,  # Cap for accumulated losses
                 force_exit_time="16:55",    # Force exit at last candle before 17:00
                 dual_position=False,         # Single position for DAX
                 stop_mode='zone'):           # Zone stops work best for DAX
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
# CORE STRATEGY CLASSES
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
        """Return current zones as dict"""
        zones = {}
        if self.res1:
            zones["res1_high"] = self.res1["high"]
            zones["res1_low"] = self.res1["low"]
            zones["res1_time"] = self.res1_time
        if self.sup1:
            zones["sup1_high"] = self.sup1["high"]
            zones["sup1_low"] = self.sup1["low"]
            zones["sup1_time"] = self.sup1_time
        return zones

    def _check_pivot(self):
        """Check for pivot points in current window"""
        if len(self.window) < self.left + self.right + 1:
            return None, None

        # Extract highs and lows
        highs = [candle["high"] for candle in self.window]
        lows = [candle["low"] for candle in self.window]
        
        mid = self.left
        
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
        Generate bidirectional signals at both zones:
        
        Resistance Zone:
        - BUY if zone high + signal candle high breaks
        - SELL if zone low + signal candle low breaks
        
        Support Zone:
        - SELL if zone low + signal candle low breaks
        - BUY if zone high + signal candle high breaks
        
        occupied_sides: set of sides that already have positions, e.g. {'BUY'}
        """
        signals = []
        
        # Check Resistance Zone (res1)
        res1_high = zones.get("res1_high")
        res1_low = zones.get("res1_low")
        res1_time = zones.get("res1_time")
        
        if res1_high and res1_low:
            zone = {"high": res1_high, "low": res1_low}
            
            # Check if candle touches the resistance zone
            if candle["low"] <= res1_high <= candle["high"]:
                
                # Generate BUY signal if zone high breaks
                if candle["high"] > res1_high and "BUY" not in occupied_sides:
                    signals.append({
                        "type": "BUY",
                        "zone_name": "res1",
                        "zone": zone,
                        "zone_time": res1_time,
                        "signal_candle": {
                            "timestamp": candle["timestamp"],
                            "open": candle["open"],
                            "high": candle["high"],
                            "low": candle["low"],
                            "close": candle["close"],
                        },
                        "break_level": "high",  # Indicates which level broke
                    })
                
                # Generate SELL signal if zone low breaks
                if candle["low"] < res1_low and "SELL" not in occupied_sides:
                    signals.append({
                        "type": "SELL",
                        "zone_name": "res1",
                        "zone": zone,
                        "zone_time": res1_time,
                        "signal_candle": {
                            "timestamp": candle["timestamp"],
                            "open": candle["open"],
                            "high": candle["high"],
                            "low": candle["low"],
                            "close": candle["close"],
                        },
                        "break_level": "low",  # Indicates which level broke
                    })
        
        # Check Support Zone (sup1)
        sup1_high = zones.get("sup1_high")
        sup1_low = zones.get("sup1_low")
        sup1_time = zones.get("sup1_time")
        
        if sup1_high and sup1_low:
            zone = {"high": sup1_high, "low": sup1_low}
            
            # Check if candle touches the support zone
            if candle["low"] <= sup1_high <= candle["high"]:
                
                # Generate BUY signal if zone high breaks
                if candle["high"] > sup1_high and "BUY" not in occupied_sides:
                    signals.append({
                        "type": "BUY",
                        "zone_name": "sup1",
                        "zone": zone,
                        "zone_time": sup1_time,
                        "signal_candle": {
                            "timestamp": candle["timestamp"],
                            "open": candle["open"],
                            "high": candle["high"],
                            "low": candle["low"],
                            "close": candle["close"],
                        },
                        "break_level": "high",  # Indicates which level broke
                    })
                
                # Generate SELL signal if zone low breaks
                if candle["low"] < sup1_low and "SELL" not in occupied_sides:
                    signals.append({
                        "type": "SELL",
                        "zone_name": "sup1",
                        "zone": zone,
                        "zone_time": sup1_time,
                        "signal_candle": {
                            "timestamp": candle["timestamp"],
                            "open": candle["open"],
                            "high": candle["high"],
                            "low": candle["low"],
                            "close": candle["close"],
                        },
                        "break_level": "low",  # Indicates which level broke
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
        """Open a new position using open price"""
        side = signal["type"]
        if not self.can_take_signal(side):
            return None

        sc = signal["signal_candle"]
        zone = signal["zone"]
        entry_price = entry_candle["open"]  # Use open price for entry

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
            "entry_time": entry_candle["timestamp"],
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
                if candle_1m["close"] <= (pos["entry_price"] - pos["stop_distance"]):
                    return ("STOP_LOSS", candle_1m["close"])  # Use close for exit
            else:
                if candle_1m["close"] >= (pos["entry_price"] + pos["stop_distance"]):
                    return ("STOP_LOSS", candle_1m["close"])  # Use close for exit

        return None

    def close_position(self, side, exit_type, exit_price, exit_time):
        """Close position and handle accumulated losses"""
        pos = self.positions.get(side)
        if pos is None:
            return None

        # Calculate P&L
        if side == "BUY":
            pnl = exit_price - pos["entry_price"]
        else:
            pnl = pos["entry_price"] - exit_price

        # Handle accumulated losses
        if self.config.accumulated_loss_mode == 'fixed':
            if pnl < 0:
                self.accumulated_losses += abs(pnl)
                if self.accumulated_losses > self.config.max_accumulated_loss_cap:
                    self.accumulated_losses = self.config.max_accumulated_loss_cap
        elif self.config.accumulated_loss_mode == 'to_target_increase':
            if pnl < 0:
                self.accumulated_losses += abs(pnl)
                if self.accumulated_losses > self.config.max_accumulated_loss_cap:
                    self.accumulated_losses = self.config.max_accumulated_loss_cap

        # Handle target hit
        if exit_type == "TARGET" and self.config.reset_on_target:
            self.accumulated_losses = 0.0
            self.current_target_points = self.config.target_points
        elif exit_type == "TARGET" and self.config.target_increase_on_hit > 0:
            self.current_target_points += self.config.target_increase_on_hit

        trade = {
            "type": side,
            "zone_name": pos["zone_name"],
            "signal_time": pos["signal_time"],
            "entry_time": pos["entry_time"],
            "entry_price": pos["entry_price"],
            "target_price": pos["target_price"],
            "exit_time": exit_time,
            "exit_price": exit_price,
            "exit_type": exit_type,
            "pnl": pnl,
        }

        # Remove position
        del self.positions[side]
        return trade

    def reset_accumulated_losses(self):
        """Reset accumulated losses"""
        self.accumulated_losses = 0.0
        self.current_target_points = self.config.target_points


class DAXStrategyEngine:
    """Main DAX strategy engine with bidirectional zone entries"""
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.zone_engine = SRZoneEngine(config.pivot_left, config.pivot_right)
        self.signal_detector = SignalDetector()
        self.position_manager = PositionManager(config)
        self.trades = []
        self.current_candle_1m = None
        self.tf_candle_builder = None

    def run(self, data):
        """Run strategy on 1-minute data"""
        self.trades = []
        self.position_manager.reset_accumulated_losses()
        
        # Initialize TF candle builder
        self.tf_candle_builder = None
        
        for candle_1m in data:
            self.current_candle_1m = candle_1m
            
            # Build TF candles
            tf_candle = self._build_tf_candle(candle_1m)
            if tf_candle is None:
                continue
            
            # Update zones
            zones = self.zone_engine.update(tf_candle)
            
            # Check for new signals
            signal = self.signal_detector.check_signal(
                tf_candle, zones, self.position_manager.occupied_sides
            )
            
            # Check entry conditions
            if signal and self.signal_detector.check_entry_condition(candle_1m):
                if self.position_manager.can_take_signal(signal["type"]):
                    pos = self.position_manager.open_position(signal, candle_1m)
                    if pos:
                        self.signal_detector.consume_signal()
            
            # Check exits for all open positions
            for side in list(self.position_manager.occupied_sides):
                exit_result = self.position_manager.check_exit(candle_1m, side)
                if exit_result:
                    exit_type, exit_price = exit_result
                    trade = self.position_manager.close_position(
                        side, exit_type, exit_price, candle_1m["timestamp"]
                    )
                    if trade:
                        self.trades.append(trade)
            
            # Force exit check
            if self._should_force_exit(candle_1m):
                self._force_exit_all(candle_1m)
        
        return self.trades

    def _build_tf_candle(self, candle_1m):
        """Build TF candle from 1-minute candles"""
        timestamp_str = candle_1m["timestamp"]
        timestamp = datetime.fromisoformat(timestamp_str)
        
        # Round timestamp to TF boundary
        tf_minutes = self.config.timeframe_minutes
        minute = timestamp.minute
        tf_minute = (minute // tf_minutes) * tf_minutes
        
        tf_timestamp = timestamp.replace(minute=tf_minute, second=0, microsecond=0)
        
        # Initialize new TF candle if needed
        if (self.tf_candle_builder is None or 
            tf_timestamp.isoformat() != self.tf_candle_builder["timestamp"]):
            
            # Save previous TF candle if exists
            prev_tf_candle = self.tf_candle_builder
            
            # Start new TF candle
            self.tf_candle_builder = {
                "timestamp": tf_timestamp.isoformat(),
                "open": candle_1m["open"],
                "high": candle_1m["high"],
                "low": candle_1m["low"],
                "close": candle_1m["close"],
            }
            
            return prev_tf_candle
        
        # Update existing TF candle
        self.tf_candle_builder["high"] = max(self.tf_candle_builder["high"], candle_1m["high"])
        self.tf_candle_builder["low"] = min(self.tf_candle_builder["low"], candle_1m["low"])
        self.tf_candle_builder["close"] = candle_1m["close"]
        
        return None

    def _should_force_exit(self, candle_1m):
        """Check if we should force exit all positions"""
        if self.config.exit_cutoff is None:
            return False
        
        candle_time = datetime.fromisoformat(candle_1m["timestamp"]).time()
        return candle_time >= self.config.exit_cutoff

    def _force_exit_all(self, candle_1m):
        """Force exit all open positions"""
        for side in list(self.position_manager.occupied_sides):
            trade = self.position_manager.close_position(
                side, "FORCE_EXIT", candle_1m["close"], candle_1m["timestamp"]
            )
            if trade:
                self.trades.append(trade)
        self.signal_detector.clear()


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def load_dax_1min_data(file_path):
    """Load DAX 1-minute OHLC data"""
    data = []
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append({
                'timestamp': row['timestamp'],
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': 0
            })
    return data

def save_trades_to_csv(trades, filename):
    """Save trades to CSV file"""
    if not trades:
        return
    
    fieldnames = [
        'trade_id', 'type', 'zone_name', 'signal_time', 'entry_time', 'entry_price',
        'target_price', 'exit_time', 'exit_price', 'exit_type', 'pnl'
    ]
    
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for i, trade in enumerate(trades, 1):
            row = {
                'trade_id': i,
                'type': trade['type'],
                'zone_name': trade['zone_name'],
                'signal_time': trade['signal_time'],
                'entry_time': trade['entry_time'],
                'entry_price': trade['entry_price'],
                'target_price': trade['target_price'],
                'exit_time': trade['exit_time'],
                'exit_price': trade['exit_price'],
                'exit_type': trade['exit_type'],
                'pnl': trade['pnl']
            }
            writer.writerow(row)


# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    # Example usage
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
    
    # Load data and run strategy
    data = load_dax_1min_data("dax_1min_ohlc.csv")
    engine = DAXStrategyEngine(config)
    trades = engine.run(data)
    
    print(f"Generated {len(trades)} trades")
    save_trades_to_csv(trades, "dax_bidirectional_trades.csv")
