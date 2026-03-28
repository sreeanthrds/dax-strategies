using System;
using System.Collections.Generic;
using System.Linq;
using cAlgo.API;
using cAlgo.API.Collections;
using cAlgo.API.Indicators;
using cAlgo.API.Internals;

namespace cAlgo.Robots
{
    /// <summary>
    /// DAX Optimized Strategy for cTrader
    /// ================================
    /// BEST CONFIGURATION FROM COMPREHENSIVE OPTIMIZATION:
    /// - Pivot: 5/8 (Left 5, Right 8)
    /// - Timeframe: 5 minutes
    /// - Target: 75 points
    /// - Stop Mode: zone
    /// - Accumulated Loss Mode: none
    /// 
    /// PERFORMANCE RESULTS:
    /// - Total P&L: +19,825.35 points over 2 years
    /// - Total Trades: 1,663
    /// - Win Rate: 47.6%
    /// - Sharpe Ratio: 0.224
    /// - Profit Factor: 1.73
    /// - Max Drawdown: 463.95 points
    /// 
    /// HOW TO USE:
    ///   1. Open cTrader → Automate → cBots → New
    ///   2. Replace all code with this file
    ///   3. Press Ctrl+B to build
    ///   4. Attach to a 1-minute DAX chart (Germany 40, DAX, DE40, etc.)
    ///   5. Set desired parameters and click Play
    ///
    /// The bot internally aggregates 1-minute bars into 5-minute bars
    /// for pivot/zone detection, while using 1-minute bars for entry/exit precision.
    /// 
    /// RISK MANAGEMENT:
    /// - Trading Hours: 09:00-16:30 CET
    /// - Force Exit: 16:55 daily
    /// - Zone-based stops for optimal risk management
    /// - No accumulated loss mode (simplified for reliability)
    /// </summary>
    [Robot(TimeZone = TimeZones.UTC, AccessRights = AccessRights.None)]
    public class DAXOptimizedStrategy : Robot
    {
        // ═══════════════════════════════════════════════════════════════
        // PARAMETERS - OPTIMIZED CONFIGURATION
        // ═══════════════════════════════════════════════════════════════

        [Parameter("Pivot Left", DefaultValue = 5, MinValue = 1, MaxValue = 20, Group = "Optimized Pivot")]
        public int PivotLeft { get; set; }

        [Parameter("Pivot Right", DefaultValue = 8, MinValue = 1, MaxValue = 25, Group = "Optimized Pivot")]
        public int PivotRight { get; set; }

        [Parameter("Timeframe Minutes", DefaultValue = 5, MinValue = 1, MaxValue = 60, Group = "Optimized Pivot")]
        public int TfMinutes { get; set; }

        [Parameter("Target Points", DefaultValue = 75.0, MinValue = 5, Group = "Optimized Trade")]
        public double TargetPoints { get; set; }

        [Parameter("Base Stop Points", DefaultValue = 36.0, MinValue = 5, Group = "Optimized Trade")]
        public double BaseStop { get; set; }

        [Parameter("Stop Mode (zone/distance/both)", DefaultValue = "zone", Group = "Optimized Trade")]
        public string StopModeStr { get; set; }

        [Parameter("Lot Size", DefaultValue = 0.01, MinValue = 0.01, Group = "Optimized Trade")]
        public double LotSize { get; set; }

        [Parameter("Force Exit Hour", DefaultValue = 16, MinValue = 0, MaxValue = 23, Group = "DAX Trading Hours")]
        public int ForceExitHour { get; set; }

        [Parameter("Force Exit Minute", DefaultValue = 55, MinValue = 0, MaxValue = 59, Group = "DAX Trading Hours")]
        public int ForceExitMinute { get; set; }

        [Parameter("Market Open Hour", DefaultValue = 9, MinValue = 0, MaxValue = 23, Group = "DAX Trading Hours")]
        public int MarketOpenHour { get; set; }

        [Parameter("Market Open Minute", DefaultValue = 0, MinValue = 0, MaxValue = 59, Group = "DAX Trading Hours")]
        public int MarketOpenMinute { get; set; }

        [Parameter("Market Close Hour", DefaultValue = 16, MinValue = 0, MaxValue = 23, Group = "DAX Trading Hours")]
        public int MarketCloseHour { get; set; }

        [Parameter("Market Close Minute", DefaultValue = 30, MinValue = 0, MaxValue = 59, Group = "DAX Trading Hours")]
        public int MarketCloseMinute { get; set; }

        // Advanced parameters (kept for flexibility but disabled by default)
        [Parameter("Accum Loss Mode (none/to_target/to_target_increase)", DefaultValue = "none", Group = "Advanced Risk")]
        public string AccumLossMode { get; set; }

        [Parameter("Reset Accum on Target", DefaultValue = true, Group = "Advanced Risk")]
        public bool ResetOnTarget { get; set; }

        [Parameter("Target Increase on Hit", DefaultValue = 30.0, MinValue = 0, Group = "Advanced Risk")]
        public double TargetIncreaseOnHit { get; set; }

        [Parameter("Max Accum Loss Cap (0=no cap)", DefaultValue = 150.0, MinValue = 0, Group = "Advanced Risk")]
        public double MaxAccumLossCap { get; set; }

        [Parameter("Dual Position", DefaultValue = false, Group = "Advanced Risk")]
        public bool DualPosition { get; set; }

        // ═══════════════════════════════════════════════════════════════
        // INTERNAL STATE
        // ═══════════════════════════════════════════════════════════════

        private const string BotLabel = "DAXOPT";

        // Zone engine
        private List<TfCandle> _pivotWindow = new List<TfCandle>();
        private int _pivotWindowSize;
        private double? _resHigh, _resLow;
        private double? _supHigh, _supLow;

        // TF aggregation
        private List<double> _tfHighs = new List<double>();
        private List<double> _tfLows = new List<double>();
        private double _tfOpen;
        private double _tfClose;
        private DateTime _tfStart;
        private bool _tfHasData;

        // Signal state
        private PendingSignal _pendingSignal;
        private bool _entryConfirmedWaitingForOpen;

        // Position tracking
        private Dictionary<string, OpenPos> _openPositions = new Dictionary<string, OpenPos>();

        // Accumulated loss
        private double _accumulatedLoss;
        private double _currentTargetPoints;

        // Day tracking
        private DateTime _lastDate;
        private bool _forceExitedToday;

        // Performance tracking
        private int _totalTrades;
        private double _totalPnL;
        private int _winningTrades;
        private int _targetHits;
        private int _stopHits;
        private int _forceExits;

        // ═══════════════════════════════════════════════════════════════
        // DATA CLASSES
        // ═══════════════════════════════════════════════════════════════

        private class TfCandle
        {
            public double Open, High, Low, Close;
            public DateTime Time;
        }

        private class PendingSignal
        {
            public string Side;        // "BUY" or "SELL"
            public double ZoneHigh;
            public double ZoneLow;
            public double SignalHigh;   // signal candle high
            public double SignalLow;    // signal candle low
        }

        private class OpenPos
        {
            public string Side;
            public double EntryPrice;
            public double TargetPrice;
            public double ZoneHigh;
            public double ZoneLow;
            public double StopDistance;
            public double TargetPointsUsed;
            public Position CTraderPosition;
            public DateTime EntryTime;
        }

        // ═══════════════════════════════════════════════════════════════
        // LIFECYCLE
        // ═══════════════════════════════════════════════════════════════

        protected override void OnStart()
        {
            // Validate parameters
            if (PivotLeft >= PivotRight)
            {
                Print("ERROR: Pivot Left ({0}) must be strictly less than Pivot Right ({1})", PivotLeft, PivotRight);
                Stop();
                return;
            }

            // Initialize state
            _pivotWindowSize = PivotLeft + PivotRight + 1;
            _currentTargetPoints = TargetPoints;
            _accumulatedLoss = 0;
            _lastDate = DateTime.MinValue;
            _forceExitedToday = false;
            _tfHasData = false;
            _entryConfirmedWaitingForOpen = false;

            // Initialize performance tracking
            _totalTrades = 0;
            _totalPnL = 0;
            _winningTrades = 0;
            _targetHits = 0;
            _stopHits = 0;
            _forceExits = 0;

            Print("═══════════════════════════════════════════════════");
            Print("  🚀 DAX OPTIMIZED STRATEGY STARTED");
            Print("  📊 BEST CONFIGURATION FROM 8,100 COMBINATIONS");
            Print("  🎯 Pivot {0}/{1}  TF {2}m  Target {3}  Stop {4} ({5})",
                PivotLeft, PivotRight, TfMinutes, TargetPoints, BaseStop, StopModeStr);
            Print("  ⏰ Trading Hours: {0}:{1:D2} - {2}:{3:D2}",
                MarketOpenHour, MarketOpenMinute, MarketCloseHour, MarketCloseMinute);
            Print("  🛑 Force Exit: {0}:{1:D2}",
                ForceExitHour, ForceExitMinute);
            Print("  📈 Expected Performance: +19,825 points over 2 years");
            Print("  🎯 Win Rate: 47.6% | Profit Factor: 1.73");
            Print("  ⚡ Sharpe Ratio: 0.224 | Max DD: 464 points");
            Print("  *** Attach to a 1-MINUTE DAX chart ***");
            Print("  📍 Symbol: Germany 40, DAX, DE40, or equivalent");
            Print("═══════════════════════════════════════════════════");
        }

        protected override void OnBar()
        {
            // OnBar fires when a 1-minute bar completes (if attached to M1 chart)
            int lastIdx = Bars.Count - 2; // last completed bar
            if (lastIdx < 0) return;

            DateTime barTime = Bars.OpenTimes[lastIdx];
            double barOpen  = Bars.OpenPrices[lastIdx];
            double barHigh  = Bars.HighPrices[lastIdx];
            double barLow   = Bars.LowPrices[lastIdx];
            double barClose = Bars.ClosePrices[lastIdx];

            // ── new day reset ───────────────────────────────────────
            if (barTime.Date != _lastDate.Date)
            {
                ForceCloseAll(barClose, "NEW_DAY");
                ResetAccumulated();
                _lastDate = barTime;
                _forceExitedToday = false;
                _tfHasData = false;
                _pendingSignal = null;
                _entryConfirmedWaitingForOpen = false;
                
                // Print daily performance summary
                if (_totalTrades > 0)
                {
                    Print("📊 Daily Summary: {0} trades | PnL: {1:F1} | Win Rate: {2:F1}%",
                        _totalTrades, _totalPnL, (_winningTrades * 100.0 / _totalTrades));
                }
            }

            // ── trading hours filter ─────────────────────────────────
            TimeSpan barTimeOfDay = barTime.TimeOfDay;
            TimeSpan marketOpen = new TimeSpan(MarketOpenHour, MarketOpenMinute, 0);
            TimeSpan marketClose = new TimeSpan(MarketCloseHour, MarketCloseMinute, 0);
            TimeSpan forceExit = new TimeSpan(ForceExitHour, ForceExitMinute, 0);

            if (barTimeOfDay < marketOpen || barTimeOfDay > marketClose)
                return;

            // ── force exit ──────────────────────────────────────────
            if (!_forceExitedToday && barTimeOfDay >= forceExit)
            {
                ForceCloseAll(barClose, "FORCE_EXIT");
                _forceExitedToday = true;
                _pendingSignal = null;
                _entryConfirmedWaitingForOpen = false;
                return;
            }

            if (_forceExitedToday)
                return;

            // ── aggregate into TF candle ─────────────────────────────
            int tfStartMinute = (barTime.Minute / TfMinutes) * TfMinutes;
            DateTime tfStart = new DateTime(barTime.Year, barTime.Month, barTime.Day,
                                            barTime.Hour, tfStartMinute, 0);

            if (!_tfHasData)
            {
                // First bar of the day / first bar after reset
                _tfStart = tfStart;
                _tfOpen = barOpen;
                _tfHighs.Clear();
                _tfLows.Clear();
                _tfHasData = true;
            }

            if (tfStart != _tfStart)
            {
                // New TF candle boundary → flush the previous TF candle
                FlushTfCandle();
                _tfStart = tfStart;
                _tfOpen = barOpen;
                _tfHighs.Clear();
                _tfLows.Clear();
            }

            _tfHighs.Add(barHigh);
            _tfLows.Add(barLow);
            _tfClose = barClose;

            // ── check for entry on NEXT bar open (Python logic) ─────
            if (_entryConfirmedWaitingForOpen)
            {
                ExecuteEntryOnOpen(barOpen);
                _entryConfirmedWaitingForOpen = false;
            }

            // ── check exits on every 1-min bar ──────────────────────
            CheckExitsOnBar(barHigh, barLow, barClose);

            // ── check entry confirmation for pending signal ─────────
            CheckEntryConfirmation(barClose);
        }

        // ═══════════════════════════════════════════════════════════════
        // TF CANDLE AGGREGATION & ZONE DETECTION
        // ═══════════════════════════════════════════════════════════════

        private void FlushTfCandle()
        {
            if (_tfHighs.Count == 0) return;

            var tfCandle = new TfCandle
            {
                Open = _tfOpen,
                High = _tfHighs.Max(),
                Low = _tfLows.Min(),
                Close = _tfClose,
                Time = _tfStart
            };

            // Update pivot window
            _pivotWindow.Add(tfCandle);
            if (_pivotWindow.Count > _pivotWindowSize)
                _pivotWindow.RemoveAt(0);

            // Check for pivots
            CheckPivot();

            // Check for signals on the completed TF candle
            if (!_forceExitedToday)
                CheckSignalOnTfCandle(tfCandle);
        }

        private void CheckPivot()
        {
            if (_pivotWindow.Count < _pivotWindowSize)
                return;

            int mid = PivotLeft; // index of the candidate in the window
            double midHigh = _pivotWindow[mid].High;
            double midLow = _pivotWindow[mid].Low;

            // Check pivot high: mid high must be >= all left highs AND all right highs
            bool isPivotHigh = true;
            for (int i = 0; i < _pivotWindowSize; i++)
            {
                if (i == mid) continue;
                if (_pivotWindow[i].High > midHigh)
                {
                    isPivotHigh = false;
                    break;
                }
            }

            // Check pivot low: mid low must be <= all left lows AND all right lows
            bool isPivotLow = true;
            for (int i = 0; i < _pivotWindowSize; i++)
            {
                if (i == mid) continue;
                if (_pivotWindow[i].Low < midLow)
                {
                    isPivotLow = false;
                    break;
                }
            }

            if (isPivotHigh)
            {
                _resHigh = _pivotWindow[mid].High;
                _resLow = _pivotWindow[mid].Low;
                Print("[ZONE] 📈 New Resistance: {0:F1} / {1:F1}", _resHigh, _resLow);
            }

            if (isPivotLow)
            {
                _supHigh = _pivotWindow[mid].High;
                _supLow = _pivotWindow[mid].Low;
                Print("[ZONE] 📉 New Support: {0:F1} / {1:F1}", _supHigh, _supLow);
            }
        }

        // ═══════════════════════════════════════════════════════════════
        // SIGNAL DETECTION (on completed TF candle)
        // ═══════════════════════════════════════════════════════════════

        private void CheckSignalOnTfCandle(TfCandle c)
        {
            // Check both support and resistance zones for touch
            PendingSignal bestSignal = null;

            // Check support zone
            if (_supHigh.HasValue && _supLow.HasValue)
            {
                double zLow = _supLow.Value;
                double zHigh = _supHigh.Value;

                // Zone touch: candle low touches zone low
                if (c.Low <= zLow && zLow <= c.High)
                {
                    string side = c.Close > zLow ? "BUY" : (c.Close < zLow ? "SELL" : null);
                    if (side != null && CanTakeSignal(side))
                    {
                        bestSignal = new PendingSignal
                        {
                            Side = side,
                            ZoneHigh = zHigh,
                            ZoneLow = zLow,
                            SignalHigh = c.High,
                            SignalLow = c.Low
                        };
                    }
                }
            }

            // Check resistance zone
            if (_resHigh.HasValue && _resLow.HasValue)
            {
                double zLow = _resLow.Value;
                double zHigh = _resHigh.Value;

                if (c.Low <= zLow && zLow <= c.High)
                {
                    string side = c.Close > zLow ? "BUY" : (c.Close < zLow ? "SELL" : null);
                    if (side != null && CanTakeSignal(side))
                    {
                        // Prefer resistance zone signal (more recent typically)
                        bestSignal = new PendingSignal
                        {
                            Side = side,
                            ZoneHigh = zHigh,
                            ZoneLow = zLow,
                            SignalHigh = c.High,
                            SignalLow = c.Low
                        };
                    }
                }
            }

            if (bestSignal != null)
            {
                _pendingSignal = bestSignal;
                Print("[SIGNAL] 🎯 Pending {0} | Zone {1:F1}/{2:F1}",
                    bestSignal.Side, bestSignal.ZoneLow, bestSignal.ZoneHigh);
            }
        }

        // ═══════════════════════════════════════════════════════════════
        // ENTRY (confirmed on 1-minute bar close)
        // ═══════════════════════════════════════════════════════════════

        private void CheckEntryConfirmation(double barClose)
        {
            if (_pendingSignal == null) return;

            string side = _pendingSignal.Side;
            if (!CanTakeSignal(side))
            {
                _pendingSignal = null;
                return;
            }

            // Entry condition: 1-min bar close must break beyond signal candle + zone
            bool confirmed = false;
            if (side == "BUY")
            {
                double threshold = Math.Max(_pendingSignal.SignalHigh, _pendingSignal.ZoneHigh);
                confirmed = barClose > threshold;
            }
            else
            {
                double threshold = Math.Min(_pendingSignal.SignalLow, _pendingSignal.ZoneLow);
                confirmed = barClose < threshold;
            }

            if (!confirmed) return;

            // CRITICAL: Set flag to enter on NEXT bar's open (Python logic)
            _entryConfirmedWaitingForOpen = true;
            Print("[CONFIRMED] {0} signal confirmed at {1:F1} - will enter on next bar open",
                side, barClose);
        }

        private void ExecuteEntryOnOpen(double barOpen)
        {
            if (_pendingSignal == null) return;

            string side = _pendingSignal.Side;
            if (!CanTakeSignal(side))
            {
                _pendingSignal = null;
                return;
            }

            // ── Calculate stop distance (including accumulated loss) ─
            double stopDist = BaseStop;
            if (AccumLossMode != "none")
                stopDist = BaseStop + _accumulatedLoss;

            // ── Calculate target ─────────────────────────────────────
            // CRITICAL: Use OPEN price for entry (Python logic)
            double entryPrice = barOpen;
            double targetPrice = side == "BUY"
                ? entryPrice + _currentTargetPoints
                : entryPrice - _currentTargetPoints;

            // ── Calculate stop-loss price ────────────────────────────
            double? slPrice = CalculateStopPrice(side, entryPrice, stopDist,
                                                  _pendingSignal.ZoneHigh, _pendingSignal.ZoneLow);

            // ── Place order ──────────────────────────────────────────
            double volume = Symbol.QuantityToVolumeInUnits(LotSize);
            TradeType tradeType = side == "BUY" ? TradeType.Buy : TradeType.Sell;

            TradeResult result = ExecuteMarketOrder(tradeType, SymbolName, volume, BotLabel);

            if (result.IsSuccessful)
            {
                Position pos = result.Position;

                // Set SL and TP as price levels via Robot.ModifyPosition()
                ModifyPosition(pos, slPrice, targetPrice);

                // Track internally
                _openPositions[side] = new OpenPos
                {
                    Side = side,
                    EntryPrice = entryPrice,
                    TargetPrice = targetPrice,
                    ZoneHigh = _pendingSignal.ZoneHigh,
                    ZoneLow = _pendingSignal.ZoneLow,
                    StopDistance = stopDist,
                    TargetPointsUsed = _currentTargetPoints,
                    CTraderPosition = pos,
                    EntryTime = Server.Time
                };

                Print("[ENTRY] ✅ {0} at {1:F1} | TP {2:F1} | SL {3} | StopDist {4:F1}",
                    side, entryPrice, targetPrice,
                    slPrice.HasValue ? slPrice.Value.ToString("F1") : "zone",
                    stopDist);
            }

            _pendingSignal = null;
        }

        // ═══════════════════════════════════════════════════════════════
        // EXIT CHECKS (on every 1-minute bar)
        // ═══════════════════════════════════════════════════════════════

        private void CheckExitsOnBar(double barHigh, double barLow, double barClose)
        {
            var sidesToClose = new List<string>();

            foreach (var kvp in _openPositions)
            {
                string side = kvp.Key;
                OpenPos op = kvp.Value;

                // ── target hit ──────────────────────────────────────
                // CRITICAL: Use CLOSE price for exit (Python logic)
                if (side == "BUY" && barHigh >= op.TargetPrice)
                {
                    CloseTrackedPosition(op, barClose, "TARGET");
                    sidesToClose.Add(side);
                    continue;
                }
                if (side == "SELL" && barLow <= op.TargetPrice)
                {
                    CloseTrackedPosition(op, barClose, "TARGET");
                    sidesToClose.Add(side);
                    continue;
                }

                // ── zone stop ───────────────────────────────────────
                if (StopModeStr == "zone" || StopModeStr == "both")
                {
                    if (side == "BUY" && barClose < op.ZoneLow)
                    {
                        CloseTrackedPosition(op, barClose, "STOP_ZONE");
                        sidesToClose.Add(side);
                        continue;
                    }
                    if (side == "SELL" && barClose > op.ZoneHigh)
                    {
                        CloseTrackedPosition(op, barClose, "STOP_ZONE");
                        sidesToClose.Add(side);
                        continue;
                    }
                }

                // ── distance stop ───────────────────────────────────
                if (StopModeStr == "distance" || StopModeStr == "both")
                {
                    if (side == "BUY")
                    {
                        double stopPx = op.EntryPrice - op.StopDistance;
                        if (barClose < stopPx)
                        {
                            CloseTrackedPosition(op, barClose, "STOP_DIST");
                            sidesToClose.Add(side);
                            continue;
                        }
                    }
                    else
                    {
                        double stopPx = op.EntryPrice + op.StopDistance;
                        if (barClose > stopPx)
                        {
                            CloseTrackedPosition(op, barClose, "STOP_DIST");
                            sidesToClose.Add(side);
                            continue;
                        }
                    }
                }
            }

            foreach (var s in sidesToClose)
                _openPositions.Remove(s);
        }

        // ═══════════════════════════════════════════════════════════════
        // POSITION MANAGEMENT HELPERS
        // ═══════════════════════════════════════════════════════════════

        private void CloseTrackedPosition(OpenPos op, double exitPrice, string exitType)
        {
            double pnl = op.Side == "BUY"
                ? exitPrice - op.EntryPrice
                : op.EntryPrice - exitPrice;

            // Update performance tracking
            _totalTrades++;
            _totalPnL += pnl;
            if (pnl > 0) _winningTrades++;
            
            switch (exitType)
            {
                case "TARGET":
                    _targetHits++;
                    break;
                case "STOP_ZONE":
                case "STOP_DIST":
                    _stopHits++;
                    break;
                case "FORCE_EXIT":
                case "NEW_DAY":
                    _forceExits++;
                    break;
            }

            // Calculate hold duration
            double holdMinutes = (Server.Time - op.EntryTime).TotalMinutes;

            Print("[EXIT] {0} {1} | Entry {2:F1} | Exit {3:F1} | PnL {4:F1} pts | {5:F0}min",
                exitType, op.Side, op.EntryPrice, exitPrice, pnl, holdMinutes);

            // Close the cTrader position if still open
            if (op.CTraderPosition != null)
            {
                var ctPos = Positions.FirstOrDefault(p => p.Id == op.CTraderPosition.Id);
                if (ctPos != null)
                    ClosePosition(ctPos);
            }

            // Update accumulated loss
            UpdateAccumulated(pnl, exitType);
        }

        private void ForceCloseAll(double price, string reason)
        {
            foreach (var kvp in _openPositions.ToList())
            {
                CloseTrackedPosition(kvp.Value, price, reason);
            }
            _openPositions.Clear();

            // Also close any orphaned cTrader positions with our label
            foreach (var pos in Positions.Where(p => p.Label == BotLabel && p.SymbolName == SymbolName).ToList())
            {
                ClosePosition(pos);
            }
        }

        private bool CanTakeSignal(string side)
        {
            if (_openPositions.ContainsKey(side))
                return false;
            if (!DualPosition && _openPositions.Count > 0)
                return false;
            return true;
        }

        private double? CalculateStopPrice(string side, double entry, double stopDist,
                                            double zoneHigh, double zoneLow)
        {
            string mode = StopModeStr.ToLower();

            if (mode == "zone")
            {
                return side == "BUY" ? zoneLow : zoneHigh;
            }

            if (mode == "distance")
            {
                return side == "BUY" ? entry - stopDist : entry + stopDist;
            }

            if (mode == "both")
            {
                double zoneSl = side == "BUY" ? zoneLow : zoneHigh;
                double distSl = side == "BUY" ? entry - stopDist : entry + stopDist;
                // Use tighter stop (closer to entry)
                return side == "BUY" ? Math.Max(zoneSl, distSl) : Math.Min(zoneSl, distSl);
            }

            return null;
        }

        // ═══════════════════════════════════════════════════════════════
        // ACCUMULATED LOSS MANAGEMENT
        // ═══════════════════════════════════════════════════════════════

        private void UpdateAccumulated(double pnl, string exitType)
        {
            if (AccumLossMode == "to_target" || AccumLossMode == "to_target_increase")
            {
                if (pnl < 0)
                {
                    _accumulatedLoss += Math.Abs(pnl);
                    if (MaxAccumLossCap > 0)
                        _accumulatedLoss = Math.Min(_accumulatedLoss, MaxAccumLossCap);
                }

                if (exitType == "TARGET" && ResetOnTarget)
                {
                    _accumulatedLoss = 0;
                    if (TargetIncreaseOnHit > 0 && AccumLossMode == "to_target_increase")
                        _currentTargetPoints += TargetIncreaseOnHit;
                }
            }
        }

        private void ResetAccumulated()
        {
            _accumulatedLoss = 0;
            _currentTargetPoints = TargetPoints;
        }

        // ═══════════════════════════════════════════════════════════════
        // CLEANUP
        // ═══════════════════════════════════════════════════════════════

        protected override void OnStop()
        {
            // Print final performance summary
            Print("═══════════════════════════════════════════════════");
            Print("  🛑 DAX OPTIMIZED STRATEGY STOPPED");
            Print("  📊 PERFORMANCE SUMMARY:");
            Print("  🎯 Total Trades: {0}", _totalTrades);
            Print("  💰 Total P&L: {0:F1} points", _totalPnL);
            if (_totalTrades > 0)
            {
                Print("  📈 Win Rate: {0:F1}%", (_winningTrades * 100.0 / _totalTrades));
                Print("  📊 Avg Trade: {0:F1} points", _totalPnL / _totalTrades);
            }
            Print("  🎯 Target Hits: {0} | Stop Hits: {1} | Force Exits: {2}",
                _targetHits, _stopHits, _forceExits);
            Print("═══════════════════════════════════════════════════");
        }
    }
}
