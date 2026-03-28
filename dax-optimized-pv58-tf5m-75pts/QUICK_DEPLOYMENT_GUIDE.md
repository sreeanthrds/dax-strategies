# 🚀 DAX Strategy - Optimized Serverless Deployment Guide
# ======================================================

## 📋 Quick Deployment Steps

### **🔧 Prerequisites:**
1. **AWS CLI installed and configured**
2. **Python 3.9+**
3. **Telegram bot token and chat ID**
4. **DAX data file in correct location**

### **⚡ Fast Deployment:**

#### **Step 1: Run Deployment Script**
```bash
cd /Users/sreenathreddy/Downloads/dax-strategies/dax-optimized-pv58-tf5m-75pts
python deploy_optimized_serverless.py
```

#### **Step 2: Configure Telegram Credentials**
After deployment, update environment variables:
```bash
aws lambda update-function-configuration \
  --function-name dax-optimized-optimizer-orchestrator \
  --environment Variables='{
    "WORKER_FUNCTION_NAME": "dax-optimized-optimizer-worker",
    "TELEGRAM_BOT_TOKEN": "YOUR_BOT_TOKEN",
    "TELEGRAM_CHAT_ID": "YOUR_CHAT_ID"
  }'
```

#### **Step 3: Run Optimization**
The deployment script will ask if you want to run the full optimization:
- **Total combinations:** 1,759,968
- **Estimated runtime:** ~1.8 hours
- **Estimated cost:** ~$0.00
- **Concurrency:** 1000 Lambdas

### **📱 Expected Telegram Notifications:**

#### **Start:**
```
🚀 DAX OPTIMIZED Strategy - Serverless Optimization Started
⏰ Time: 2024-01-XX XX:XX:XX
📊 Worker Function: dax-optimized-optimizer-worker
🔄 Generating OPTIMIZED parameter combinations...
```

#### **Progress:**
```
📊 Progress: 500/35200 chunks completed (1.4%)
```

#### **Results:**
```
🏆 DAX OPTIMIZED Strategy - Top Results

#1 📊 Pv 5/8 TF 5m T 75 S 36 Z U
💰 P&L: 4,034.2 pts | 📈 Win Rate: 41.8% | 🎯 PF: 1.12
```

#### **Completion:**
```
✅ DAX OPTIMIZED Strategy - Optimization Completed
📊 Total Combinations: 1,759,968
📦 Total Chunks: 35,200
🏆 Valid Results: 1,234,567
⏰ Completed: 2024-01-XX XX:XX:XX
```

### **🔧 Manual Deployment (if script fails):**

#### **1. Create IAM Role:**
```bash
aws iam create-role \
  --role-name DAXOptimizedOptimizerRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "lambda.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'
```

#### **2. Create Lambda Functions:**
```bash
# Create deployment package
mkdir deployment && cd deployment
cp ../lambda_dax_optimized_*.py .
echo "requests==2.31.0" > requirements.txt
pip install -r requirements.txt -t .
mkdir -p opt/signal_trade_processor/strategy_optimization_complete/data
cp /path/to/dax_1min_ohlc.csv opt/signal_trade_processor/strategy_optimization_complete/data/
zip -r orchestrator.zip lambda_dax_optimized_serverless_telegram.py opt/
zip -r worker.zip lambda_dax_optimized_worker_telegram.py opt/

# Create functions
aws lambda create-function \
  --function-name dax-optimized-optimizer-orchestrator \
  --runtime python3.9 \
  --role arn:aws:iam::ACCOUNT_ID:role/DAXOptimizedOptimizerRole \
  --handler lambda_dax_optimized_serverless_telegram.lambda_handler \
  --zip-file fileb://orchestrator.zip \
  --timeout 900 --memory-size 1024

aws lambda create-function \
  --function-name dax-optimized-optimizer-worker \
  --runtime python3.9 \
  --role arn:aws:iam::ACCOUNT_ID:role/DAXOptimizedOptimizerRole \
  --handler lambda_dax_optimized_worker_telegram.lambda_handler \
  --zip-file fileb://worker.zip \
  --timeout 300 --memory-size 1536
```

#### **3. Configure Concurrency:**
```bash
aws lambda put-function-concurrency \
  --function-name dax-optimized-optimizer-orchestrator \
  --reserved-concurrent-executions 1

aws lambda put-function-concurrency \
  --function-name dax-optimized-optimizer-worker \
  --reserved-concurrent-executions 1000
```

#### **4. Run Optimization:**
```bash
aws lambda invoke \
  --function-name dax-optimized-optimizer-orchestrator \
  --payload '{}' \
  result.json
```

### **📊 Monitoring:**

#### **CloudWatch Logs:**
```bash
# View orchestrator logs
aws logs tail /aws/lambda/dax-optimized-optimizer-orchestrator --follow

# View worker logs
aws logs tail /aws/lambda/dax-optimized-optimizer-worker --follow
```

#### **Lambda Metrics:**
- **Concurrency utilization**
- **Error rates**
- **Duration metrics**
- **Throttle counts**

### **🛠️ Troubleshooting:**

#### **Common Issues:**

**1. "Function already exists"**
```bash
# Update existing function
aws lambda update-function-code \
  --function-name dax-optimized-optimizer-orchestrator \
  --zip-file fileb://orchestrator.zip
```

**2. "Access denied"**
```bash
# Check IAM permissions
aws iam get-role-policy --role-name DAXOptimizedOptimizerRole --policy-name DAXOptimizedLambdaPolicy
```

**3. "Concurrency limit exceeded"**
```bash
# Request limit increase
aws service-quotas request-service-quota-increase \
  --service-code lambda \
  --quota-code L-B99A9384 \
  --desired-value 1000
```

**4. "Telegram not working"**
```bash
# Verify bot token
curl -X POST "https://api.telegram.org/botYOUR_BOT_TOKEN/getMe"

# Verify chat ID
curl -X POST "https://api.telegram.org/botYOUR_BOT_TOKEN/sendMessage" \
  -d "chat_id=YOUR_CHAT_ID" -d "text=Test message"
```

### **📈 Expected Results:**

#### **Performance Metrics:**
- **Total combinations tested:** 1,759,968
- **Valid results:** ~1.2M combinations
- **Top configurations:** Ranked by P&L, win rate, profit factor
- **Optimal parameters:** For unidirectional and bidirectional modes

#### **Result Format:**
```json
{
  "timestamp": "2024-01-XXTXX:XX:XX",
  "total_combinations": 1759968,
  "total_chunks": 35200,
  "ranked_results": [
    {
      "config": {
        "pivot_left": 5,
        "pivot_right": 8,
        "timeframe_minutes": 5,
        "target_points": 75,
        "base_stop": 36,
        "bidirectional": false
      },
      "metrics": {
        "total_pnl": 4034.2,
        "win_rate": 41.8,
        "profit_factor": 1.12,
        "total_trades": 1590
      }
    }
  ]
}
```

### **🎯 Next Steps:**

1. **Deploy the system** using the script
2. **Configure Telegram** notifications
3. **Run full optimization** (1.8 hours)
4. **Analyze top results** 
5. **Implement best parameters** in live trading

---

**🚀 Ready to deploy! Run the deployment script and you'll have a fully optimized serverless system running in minutes!**
