# DAX Strategy Optimized - Complete Trading System

## 📊 Overview
This repository contains the complete DAX trading strategy optimization system that achieved **+19,825.35 points** over 2 years through comprehensive parameter testing of 8,100 combinations.

## 🏆 Best Configuration Results
- **Pivot:** 5/8
- **Timeframe:** 5 minutes
- **Target:** 75 points
- **Stop Mode:** zone
- **Accumulated Loss Mode:** none
- **Total P&L:** +19,825.35 points
- **Total Trades:** 1,663
- **Win Rate:** 47.6%
- **Sharpe Ratio:** 0.224
- **Profit Factor:** 1.73

## 📁 Repository Structure

### 🎯 Core Strategy Files
- **`dax_strategy_rebuilt.py`** - Main DAX strategy engine with pivot detection and signal generation
- **`generate_best_trades.py`** - Script to generate detailed trades for the best configuration
- **`run_comprehensive_optimization.py`** - Local comprehensive optimization script

### 📊 Results & Analysis
- **`dax_best_detailed_trades_19825_points.csv`** - Complete 1,663 trades with full details
- **`dax_best_comprehensive_analysis.json`** - Detailed performance analysis and statistics
- **`comprehensive_dax_results.json`** - Top 10 configurations from 8,100 tested combinations
- **`New-best-results.pdf`** - Performance report and analysis

### 🚀 Serverless Deployment
- **`lambda_dax_serverless_telegram.py`** - Main AWS Lambda orchestrator with Telegram notifications
- **`lambda_dax_worker_telegram.py`** - Worker Lambda for parallel processing
- **`DEPLOYMENT_TELEGRAM.md`** - Complete deployment guide with Telegram setup

### 📈 Additional Tools
- **`save_detailed_trades.py`** - Utility to save trades to CSV format
- **`lambda_dax_comprehensive.py`** - Alternative Lambda implementation
- **`lambda_dax_worker.py`** - Alternative worker implementation
- **`DEPLOYMENT_SERVERLESS.md`** - Serverless deployment guide

## 🎯 Strategy Performance

### 📅 Monthly Performance Highlights
- **Best Month:** April 2025 (+2,706.1 points, 72.0% win rate)
- **Strong Months:** March 2025 (+1,865.2 points, 59.6% win rate)
- **Consistent Performance:** 24 out of 24 months profitable
- **Average Monthly:** +826.1 points

### 🕐 Hourly Performance
- **Most Active:** 09:00 (305 trades, +3,909.5 points)
- **Best Win Rate:** 16:00 (70.5% win rate, +2,059.0 points)
- **High Volume:** 15:00 (245 trades, +3,669.2 points)

### 📊 Trade Analysis
- **Target Hits:** 529 trades (31.8%)
- **Stop Losses:** 802 trades (48.2%)
- **Force Exits:** 332 trades (20.0%)
- **Average Win:** 75.0 points (target achieved)
- **Risk Management:** Zone-based stops working effectively

## 🚀 Quick Start

### 1. Run Best Configuration
```bash
python generate_best_trades.py
```

### 2. Comprehensive Optimization
```bash
python run_comprehensive_optimization.py
```

### 3. Deploy to AWS Lambda
```bash
# Follow DEPLOYMENT_TELEGRAM.md for complete setup
```

## 📊 Optimization Results

### 🏆 Top 3 Configurations
1. **Pv 5/8 TF 5m T 75 SM zone AL none** - Score: 6,014.9
2. **Pv 5/8 TF 5m T 75 SM both AL none** - Score: 5,898.6
3. **Pv 3/8 TF 5m T 75 SM both AL none** - Score: 5,682.9

### 📈 Performance Improvement
- **Previous Best:** +8,966.85 points
- **NEW BEST:** +19,825.35 points
- **🚀 IMPROVEMENT:** +10,858.50 points (+121% increase!)

## 🛡️ Security & Risk Management

### 📊 Risk Metrics
- **Max Drawdown:** 463.95 points
- **Sharpe Ratio:** 0.224
- **Profit Factor:** 1.73
- **Stop Mode:** Zone-based stops
- **Force Exit:** 16:55 daily

### 🎯 Trading Hours
- **Trading Window:** 09:00-16:30 CET
- **Force Exit:** 16:55
- **Weekends:** Excluded
- **Holidays:** Automatically excluded

## 📱 Telegram Notifications (Optional)
Real-time monitoring with Telegram bot notifications:
- Start/stop notifications
- Progress updates during optimization
- Error alerts
- Final results delivery

## 🔧 Dependencies
- Python 3.9+
- pandas
- boto3 (for AWS deployment)
- requests (for Telegram notifications)

## 📈 Data Requirements
- **Data Source:** DAX 1-minute OHLC data
- **Format:** CSV with timestamp, open, high, low, close columns
- **Period:** 2+ years recommended for robust testing

## 🎯 Key Features
- **Pivot-based support/resistance detection**
- **Two-step signal generation**
- **Zone-based stop management**
- **Accumulated loss handling**
- **Force exit protection**
- **Comprehensive optimization**
- **Serverless deployment ready**

## 📊 Performance Validation
- ✅ All 8,100 parameter combinations tested
- ✅ Real DAX market data (2 years)
- ✅ Proper trading hours filtering
- ✅ Weekend/holiday exclusion
- ✅ Risk management validation

## 🎉 Achievement
This strategy represents a **121% improvement** over the previous best configuration, achieved through systematic comprehensive optimization of all parameter combinations.

## 📞 Support
For questions or support, refer to the deployment guides and analysis files included in this repository.

---

**⚠️ Risk Warning:** This is a backtested strategy. Past performance does not guarantee future results. Always validate with paper trading before live deployment.
