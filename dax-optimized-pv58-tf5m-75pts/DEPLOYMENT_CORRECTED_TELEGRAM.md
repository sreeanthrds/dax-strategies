# 🚀 DAX Strategy - Serverless Optimization Deployment Guide
# ========================================================
# Corrected Version with Telegram Notifications

## 📋 Overview

This guide shows how to deploy the serverless DAX strategy optimization with:
- **Corrected entry timing** (no look-ahead bias)
- **Telegram notifications** for real-time updates
- **8,100+ parameter combinations**
- **Parallel processing** with Lambda workers
- **Comprehensive results** with performance metrics

## 🔧 Prerequisites

### **AWS Requirements:**
- AWS account with Lambda and IAM permissions
- Python 3.9+ environment
- AWS CLI configured
- Telegram bot token and chat ID

### **Data Requirements:**
- DAX 1-minute OHLC CSV file
- File path: `/opt/signal_trade_processor/strategy_optimization_complete/data/dax_1min_ohlc.csv`

### **Telegram Setup:**
1. Create bot with @BotFather on Telegram
2. Get bot token
3. Get your chat ID (send `/start` to @userinfobot)
4. Save both for configuration

## 📦 Lambda Functions

### **1. Orchestrator Function**
**File:** `lambda_dax_corrected_serverless_telegram.py`

**Purpose:**
- Generates all parameter combinations
- Splits into chunks for parallel processing
- Invokes worker functions
- Sends Telegram notifications
- Aggregates and ranks results

### **2. Worker Function**
**File:** `lambda_dax_corrected_worker_telegram.py`

**Purpose:**
- Processes 50 parameter combinations per invocation
- Runs corrected DAX strategy (no look-ahead bias)
- Calculates performance metrics
- Returns results to orchestrator

## 🛠️ Deployment Steps

### **Step 1: Create IAM Role**

```bash
# Create IAM policy
aws iam create-policy \
  --policy-name DAXCorrectedOptimizerPolicy \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunction",
                "lambda:GetFunction",
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject"
            ],
            "Resource": "arn:aws:s3:::dax-strategy-data/*"
        }
    ]
}'

# Create IAM role
aws iam create-role \
  --role-name DAXCorrectedOptimizerRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}'

# Attach policy to role
aws iam attach-role-policy \
  --role-name DAXCorrectedOptimizerRole \
  --policy-arn arn:aws:iam::ACCOUNT_ID:policy/DAXCorrectedOptimizerPolicy
```

### **Step 2: Package Dependencies**

```bash
# Create deployment package directory
mkdir lambda_corrected_deployment
cd lambda_corrected_deployment

# Copy Lambda functions
cp /path/to/lambda_dax_corrected_serverless_telegram.py .
cp /path/to/lambda_dax_corrected_worker_telegram.py .

# Create requirements.txt
cat > requirements.txt << EOF
requests==2.31.0
boto3==1.28.57
EOF

# Install dependencies
pip install -r requirements.txt -t .

# Create zip files
zip -r orchestrator.zip lambda_dax_corrected_serverless_telegram.py
zip -r worker.zip lambda_dax_corrected_worker_telegram.py
```

### **Step 3: Deploy Orchestrator Lambda**

```bash
# Create orchestrator function
aws lambda create-function \
  --function-name dax-corrected-optimizer-orchestrator \
  --runtime python3.9 \
  --role arn:aws:iam::ACCOUNT_ID:role/DAXCorrectedOptimizerRole \
  --handler lambda_dax_corrected_serverless_telegram.lambda_handler \
  --zip-file fileb://orchestrator.zip \
  --timeout 900 \
  --memory-size 512 \
  --environment Variables='{
    "WORKER_FUNCTION_NAME": "dax-corrected-optimizer-worker",
    "TELEGRAM_BOT_TOKEN": "YOUR_BOT_TOKEN",
    "TELEGRAM_CHAT_ID": "YOUR_CHAT_ID"
  }'

# Update function configuration
aws lambda update-function-configuration \
  --function-name dax-corrected-optimizer-orchestrator \
  --timeout 900 \
  --memory-size 1024
```

### **Step 4: Deploy Worker Lambda**

```bash
# Create worker function
aws lambda create-function \
  --function-name dax-corrected-optimizer-worker \
  --runtime python3.9 \
  --role arn:aws:iam::ACCOUNT_ID:role/DAXCorrectedOptimizerRole \
  --handler lambda_dax_corrected_worker_telegram.lambda_handler \
  --zip-file fileb://worker.zip \
  --timeout 300 \
  --memory-size 1024

# Update function configuration
aws lambda update-function-configuration \
  --function-name dax-corrected-optimizer-worker \
  --timeout 300 \
  --memory-size 1536
```

### **Step 5: Upload Data to Lambda Environment**

```bash
# Create Lambda layer with data (or use S3)
# Option 1: Include data in Lambda package
mkdir -p opt/signal_trade_processor/strategy_optimization_complete/data
cp /path/to/dax_1min_ohlc.csv opt/signal_trade_processor/strategy_optimization_complete/data/

# Update Lambda functions with data
zip -r orchestrator_with_data.zip lambda_dax_corrected_serverless_telegram.py opt/
zip -r worker_with_data.zip lambda_dax_corrected_worker_telegram.py opt/

aws lambda update-function-code \
  --function-name dax-corrected-optimizer-orchestrator \
  --zip-file fileb://orchestrator_with_data.zip

aws lambda update-function-code \
  --function-name dax-corrected-optimizer-worker \
  --zip-file fileb://worker_with_data.zip
```

## 🚀 Execution

### **Step 1: Test Worker Function**

```bash
# Test worker with single combination
aws lambda invoke \
  --function-name dax-corrected-optimizer-worker \
  --payload '{
    "chunk_id": 0,
    "combinations": [{
      "pivot_left": 5,
      "pivot_right": 8,
      "timeframe_minutes": 5,
      "target_points": 75.0,
      "base_stop": 36.0,
      "accumulated_loss_mode": "none",
      "reset_on_target": true,
      "target_increase_on_hit": 30.0,
      "max_accumulated_loss_cap": 150.0,
      "force_exit_time": "16:55",
      "dual_position": false,
      "stop_mode": "zone"
    }],
    "data_file_path": "/opt/signal_trade_processor/strategy_optimization_complete/data/dax_1min_ohlc.csv"
  }' \
  response.json
```

### **Step 2: Run Full Optimization**

```bash
# Execute orchestrator
aws lambda invoke \
  --function-name dax-corrected-optimizer-orchestrator \
  --payload '{}' \
  optimization_result.json
```

### **Step 3: Monitor Progress**

**Telegram notifications will show:**
- Start notification
- Progress updates (every 10 chunks)
- Final results (top 5 combinations)
- Completion summary

**CloudWatch logs:**
```bash
# View orchestrator logs
aws logs tail /aws/lambda/dax-corrected-optimizer-orchestrator --follow

# View worker logs
aws logs tail /aws/lambda/dax-corrected-optimizer-worker --follow
```

## 📊 Expected Results

### **Parameter Combinations:**
- **Total combinations:** ~8,100+
- **Chunk size:** 50 combinations per worker
- **Total chunks:** ~162
- **Concurrent workers:** Up to 100
- **Estimated runtime:** 2-4 hours

### **Performance Metrics:**
Each result includes:
- Total P&L (points)
- Win rate (%)
- Profit factor
- Sharpe ratio
- Max drawdown
- Target hits vs stop losses
- Total trades

### **Telegram Notifications:**

**Start:**
```
🚀 DAX Corrected Strategy - Serverless Optimization Started
⏰ Time: 2024-01-XX XX:XX:XX
📊 Worker Function: dax-corrected-optimizer-worker
🔄 Generating parameter combinations...
```

**Progress:**
```
📊 Progress: 50/162 chunks completed (30.9%)
```

**Results:**
```
🏆 DAX Corrected Strategy - Optimization Results

#1 📊 Pv 5/8 TF 5m T 75 S 36 zone
💰 P&L: 4,012.1 pts | 📈 Win Rate: 41.7% | 🎯 PF: 1.12 | 📊 Trades: 1,589

#2 📊 Pv 4/9 TF 10m T 90 S 40 both
💰 P&L: 3,856.4 pts | 📈 Win Rate: 43.2% | 🎯 PF: 1.18 | 📊 Trades: 1,445
```

**Completion:**
```
✅ DAX Corrected Strategy - Optimization Completed
📊 Total Combinations: 8,100
📦 Total Chunks: 162
🏆 Valid Results: 6,234
💾 Results File: /tmp/dax_corrected_optimization_results_202401XX_XXXXXX.json
```

## 🔧 Configuration

### **Environment Variables:**

**Orchestrator:**
```bash
WORKER_FUNCTION_NAME=dax-corrected-optimizer-worker
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN
TELEGRAM_CHAT_ID=YOUR_CHAT_ID
```

**Worker:**
```bash
# No environment variables needed
# Data file path is passed in payload
```

### **Lambda Settings:**

**Orchestrator:**
- **Timeout:** 900 seconds (15 minutes)
- **Memory:** 1024 MB
- **Storage:** 512 MB (for data)

**Worker:**
- **Timeout:** 300 seconds (5 minutes)
- **Memory:** 1536 MB (for processing)
- **Storage:** 512 MB (for data)

## 🛠️ Troubleshooting

### **Common Issues:**

#### **1. Telegram Notifications Not Working**
```bash
# Check bot token and chat ID
curl -X POST "https://api.telegram.org/botYOUR_BOT_TOKEN/getMe"

# Test message sending
curl -X POST "https://api.telegram.org/botYOUR_BOT_TOKEN/sendMessage" \
  -d "chat_id=YOUR_CHAT_ID" \
  -d "text=Test message"
```

#### **2. Lambda Timeout**
```bash
# Increase timeout settings
aws lambda update-function-configuration \
  --function-name dax-corrected-optimizer-orchestrator \
  --timeout 1800  # 30 minutes
```

#### **3. Memory Issues**
```bash
# Increase memory size
aws lambda update-function-configuration \
  --function-name dax-corrected-optimizer-worker \
  --memory-size 2048  # 2GB
```

#### **4. Data File Not Found**
```bash
# Check file path in Lambda
aws lambda invoke \
  --function-name dax-corrected-optimizer-worker \
  --payload '{"data_file_path": "/opt/signal_trade_processor/strategy_optimization_complete/data/dax_1min_ohlc.csv"}' \
  test.json

# Check logs for file path errors
aws logs tail /aws/lambda/dax-corrected-optimizer-worker --follow
```

### **Performance Optimization:**

#### **1. Reduce Chunk Size**
```python
# In orchestrator, change:
CHUNK_SIZE = 25  # Reduce from 50
```

#### **2. Increase Concurrency**
```python
# In orchestrator, change:
MAX_CONCURRENT = 150  # Increase from 100
```

#### **3. Optimize Data Loading**
```python
# Cache data in worker initialization
# Add data loading to Lambda init
```

## 📁 Files Created

1. **`lambda_dax_corrected_serverless_telegram.py`** - Orchestrator
2. **`lambda_dax_corrected_worker_telegram.py`** - Worker
3. **`DEPLOYMENT_CORRECTED_TELEGRAM.md`** - This guide

## 🎯 Expected Outcomes

### **Performance Results:**
- **Realistic P&L:** 3,000-5,000 points (corrected from 20,000+)
- **Win Rate:** 40-45%
- **Profit Factor:** 1.1-1.3
- **Drawdown:** 800-1,500 points

### **Top Parameter Combinations:**
The optimization will identify the best parameters for the corrected strategy, likely:
- **Pivot:** 5/8 or similar
- **Timeframe:** 5-15 minutes
- **Target:** 60-90 points
- **Stop:** 30-45 points
- **Stop Mode:** zone or both

## 🚀 Next Steps

1. **Deploy both Lambda functions**
2. **Test with single combination**
3. **Run full optimization**
4. **Monitor Telegram notifications**
5. **Analyze top results**
6. **Implement best parameters in live trading**

---

**🎯 This serverless optimization will test 8,100+ parameter combinations for the corrected DAX strategy and send real-time results to your Telegram!**
