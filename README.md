# DAX Strategies Repository

## 📊 Strategies Overview

This repository contains multiple DAX trading strategies with comprehensive optimization and backtesting results.

## 🎯 Current Strategies

### 🚀 DAX Optimized - Pv 5/8 TF 5m T 75pts
**Folder:** `dax-optimized-pv58-tf5m-75pts/`

#### 🏆 Performance Results:
- **Total P&L:** +19,825.35 points
- **Total Trades:** 1,663 trades over 2 years
- **Win Rate:** 47.6%
- **Sharpe Ratio:** 0.224
- **Profit Factor:** 1.73
- **Max Drawdown:** 463.95 points

#### 📋 Best Configuration:
- **Pivot:** 5/8
- **Timeframe:** 5 minutes
- **Target:** 75 points
- **Stop Mode:** zone
- **Accumulated Loss Mode:** none

#### 📁 Strategy Contents:
- **Core Engine:** `dax_strategy_rebuilt.py`
- **Optimization:** `run_comprehensive_optimization.py`
- **Trade Generation:** `generate_best_trades.py`
- **Detailed Trades:** `dax_best_detailed_trades_19825_points.csv`
- **Analysis:** `dax_best_comprehensive_analysis.json`
- **Results:** `comprehensive_dax_results.json`
- **Performance Report:** `New-best-results.pdf`
- **Serverless Deployment:** AWS Lambda functions
- **Documentation:** Complete README and security guides

#### 🛡️ Security Features:
- Risk management with zone-based stops
- Trading hours filtering (09:00-16:30 CET)
- Force exit protection (16:55 daily)
- Weekend/holiday exclusion
- Maximum loss caps (150 points)

#### 🚀 Deployment:
- AWS Lambda serverless architecture
- Telegram notifications for real-time monitoring
- Production-ready security measures

## 📈 Performance Comparison

| Strategy | P&L (points) | Trades | Win Rate | Sharpe | Profit Factor |
|----------|---------------|--------|----------|--------|--------------|
| Pv 5/8 TF 5m T 75pts | +19,825.35 | 1,663 | 47.6% | 0.224 | 1.73 |

## 🔧 Usage

### Run Best Strategy:
```bash
cd dax-optimized-pv58-tf5m-75pts/
python generate_best_trades.py
```

### Comprehensive Optimization:
```bash
cd dax-optimized-pv58-tf5m-75pts/
python run_comprehensive_optimization.py
```

### AWS Lambda Deployment:
```bash
cd dax-optimized-pv58-tf5m-75pts/
# Follow DEPLOYMENT_TELEGRAM.md
```

## 🛡️ Risk Management

All strategies include:
- ✅ Proper risk management
- ✅ Trading hours filtering
- ✅ Force exit protection
- ✅ Weekend/holiday exclusion
- ✅ Maximum loss caps
- ✅ Comprehensive backtesting

## 📊 Optimization Results

### 🎯 Pv 5/8 TF 5m T 75pts Strategy:
- **8,100 parameter combinations** tested
- **121% improvement** over previous best
- **24/24 months** profitable
- **Execution time:** 61.7 minutes

### 🏆 Top 3 Configurations:
1. Pv 5/8 TF 5m T 75 SM zone AL none - Score: 6,014.9
2. Pv 5/8 TF 5m T 75 SM both AL none - Score: 5,898.6
3. Pv 3/8 TF 5m T 75 SM both AL none - Score: 5,682.9

## 🚀 Future Strategies

This repository is structured to accommodate additional DAX strategies:
- Each strategy in its own folder
- Consistent naming convention: `dax-{name}-{config}`
- Standardized documentation and deployment
- Performance comparison across strategies

## 📞 Contributing

To add new strategies:
1. Create new folder following naming convention
2. Include core strategy engine
3. Add optimization results
4. Provide performance documentation
5. Ensure security measures are implemented

---

**⚠️ Risk Warning:** All strategies are backtested. Past performance does not guarantee future results. Always validate with paper trading before live deployment.
