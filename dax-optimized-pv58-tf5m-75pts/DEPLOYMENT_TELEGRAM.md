# DAX Strategy Serverless Optimization with Telegram Notifications

## 📋 Overview
Serverless AWS Lambda solution for comprehensive DAX strategy optimization testing ALL 8,100 parameter combinations in parallel with real-time Telegram notifications.

## 🎯 Parameter Combinations
- **Pivot Combinations:** 36 (6 left × 6 right - ALL combinations including left >= right)
- **Timeframes:** 5 options (5, 10, 15, 30, 60 minutes)
- **Targets:** 5 options (75, 100, 125, 150, 200 points)
- **Stop Modes:** 3 options (zone, distance, both)
- **Accumulated Loss Modes:** 3 options (none, fixed, to_target_increase)
- **TOTAL:** 8,100 combinations

## 📱 Telegram Setup

### 1. Create Telegram Bot
1. Open Telegram and search for **@BotFather**
2. Send `/newbot` command
3. Follow instructions to create your bot
4. Save the **Bot Token** (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Get Your Chat ID
1. Search for **@userinfobot** in Telegram
2. Send any message to get your **Chat ID**
3. Save the Chat ID (looks like: `123456789`)

### 3. Test Your Bot
```bash
# Test message
curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/sendMessage" \
  -H "Content-Type: application/json" \
  -d '{"chat_id": "<YOUR_CHAT_ID>", "text": "🚀 DAX Optimizer Bot is ready!"}'
```

## ⚡ Architecture
- **Main Lambda:** `lambda_dax_serverless_telegram.py` (Orchestrator)
- **Worker Lambda:** `lambda_dax_worker_telegram.py` (Parallel processing)
- **Parallel Workers:** 100 Lambda functions
- **Tests per Worker:** ~81 combinations
- **Estimated Time:** 2-3 minutes
- **Estimated Cost:** ~$0.50

## 🚀 Deployment Steps

### 1. Create Lambda Functions

#### Main Function (dax-optimizer-main)
```bash
aws lambda create-function \
  --function-name dax-optimizer-main \
  --runtime python3.9 \
  --role arn:aws:iam::ACCOUNT:role/lambda-execution-role \
  --handler lambda_dax_serverless_telegram.lambda_handler \
  --zip-file fileb://dax-optimizer-main.zip \
  --timeout 900 \
  --memory-size 2048 \
  --environment Variables={
    WORKER_FUNCTION_NAME=dax-optimizer-worker,
    TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN,
    TELEGRAM_CHAT_ID=YOUR_CHAT_ID
  }
```

#### Worker Function (dax-optimizer-worker)
```bash
aws lambda create-function \
  --function-name dax-optimizer-worker \
  --runtime python3.9 \
  --role arn:aws:iam::ACCOUNT:role/lambda-execution-role \
  --handler lambda_dax_worker_telegram.lambda_handler \
  --zip-file fileb://dax-optimizer-worker.zip \
  --timeout 900 \
  --memory-size 1024 \
  --environment Variables={
    TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN,
    TELEGRAM_CHAT_ID=YOUR_CHAT_ID
  }
```

### 2. Package Dependencies
```bash
# Create deployment packages
mkdir package
pip install pandas boto3 requests -t ./package
cp lambda_dax_serverless_telegram.py ./package/
cp lambda_dax_worker_telegram.py ./package/
cp dax_strategy_rebuilt.py ./package/

# Main package
cd package
zip -r ../dax-optimizer-main.zip .
cd ..

# Worker package (same as main)
cp dax-optimizer-main.zip dax-optimizer-worker.zip
```

### 3. Data Setup
```bash
# Upload data to S3
aws s3 cp signal_trade_processor/strategy_optimization_complete/data/dax_1min_ohlc.csv s3://your-bucket/dax-data/
```

### 4. IAM Role Permissions
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "s3:GetObject"
      ],
      "Resource": "*"
    }
  ]
}
```

### 5. Update Lambda Functions (if needed)
```bash
# Update main function
aws lambda update-function-code \
  --function-name dax-optimizer-main \
  --zip-file fileb://dax-optimizer-main.zip

# Update worker function
aws lambda update-function-code \
  --function-name dax-optimizer-worker \
  --zip-file fileb://dax-optimizer-worker.zip
```

## 📱 Telegram Notifications You'll Receive

### 1. Start Notification
```
🚀 DAX Serverless Optimization Started

📊 Testing ALL 8,100 parameter combinations
⚡ Using 100 parallel Lambda workers
⏱️ Estimated time: 2-3 minutes
```

### 2. Progress Updates
```
⏳ Progress: 25/100 workers completed (25.0%)
📈 Results so far: 2,025 successful tests
```

### 3. Worker Completions
```
✅ Worker 12 completed

📊 Results: 81/81 successful
🏆 Best in chunk: Pv 5/10 TF 15m T 125
📈 Score: 2741.3 | P&L: +8966.85 | Win Rate: 47.9%
```

### 4. Final Results
```
✅ DAX Optimization Completed!

🏆 BEST CONFIGURATION:
🎯 Pivot: 5/10
⏰ Timeframe: 15m
🎯 Target: 125 pts
🛡️ Stop Mode: both
💸 Loss Mode: to_target_increase

📊 PERFORMANCE:
💰 Total P&L: +8966.85 points
📈 Score: 2741.3
🎯 Win Rate: 47.9%
📊 Trades: 730
⚡ Sharpe: 0.185

🏅 TOP 3 RESULTS:
1. Pv 5/10 TF 15m T 125 - Score: 2741.3
2. Pv 5/10 TF 30m T 150 - Score: 1555.6
3. Pv 5/10 TF 30m T 125 - Score: 1495.4

📊 SUMMARY:
🔢 Total Tests: 8100/8100
⏱️ Execution Time: 145.2s
🚀 Workers Used: 100
```

## 🚀 Execute the Optimization

### Option 1: AWS Console
1. Go to AWS Lambda console
2. Select `dax-optimizer-main` function
3. Click "Test" tab
4. Create test event with empty `{}`
5. Click "Test" button

### Option 2: AWS CLI
```bash
aws lambda invoke \
  --function-name dax-optimizer-main \
  --payload '{}' \
  response.json

# View results
cat response.json
```

### Option 3: Python SDK
```python
import boto3
import json

lambda_client = boto3.client('lambda')
response = lambda_client.invoke(
    FunctionName='dax-optimizer-main',
    Payload=json.dumps({})
)

result = json.loads(response['Payload'].read())
print(result)
```

## 📊 Expected Results
- **Top 10 configurations** ranked by composite score
- **Best configuration** with full performance metrics
- **Complete analysis** of all 8,100 combinations
- **Real-time progress updates** via Telegram
- **Significant improvement** over current +8,966.85 points

## 🔧 Troubleshooting

### Common Issues
1. **Telegram Bot Not Responding**
   - Check bot token is correct
   - Verify chat ID is correct
   - Ensure bot is started (send `/start` to your bot)

2. **Lambda Timeout**
   - Increase timeout to 900 seconds
   - Check memory allocation (2048 MB for main, 1024 MB for worker)

3. **Data Loading Issues**
   - Verify S3 bucket permissions
   - Check data file path in Lambda
   - Ensure data is uploaded to correct S3 location

4. **Worker Failures**
   - Check CloudWatch logs for worker function
   - Verify environment variables are set
   - Ensure worker function exists and is accessible

## ✅ Success Indicators
- ✅ Telegram start message received
- ✅ Progress updates every 10-25 workers
- ✅ Worker completion messages
- ✅ Final results with top 10 configurations
- ✅ Best configuration outperforms +8,966.85 points

## 🎯 Current Best Performance
- **Configuration:** Pv 5/10 TF 15m T 125 SM both AL to_target_increase
- **Performance:** +8,966.85 points
- **Expected Improvement:** Higher score with comprehensive testing

## ⚡ Performance Benefits
- **Speed:** 100x faster than local execution
- **Cost:** Minimal (~$0.50)
- **Scalability:** Automatic parallel processing
- **Reliability:** Serverless architecture
- **Monitoring:** Real-time Telegram notifications

## 🎉 Ready for Deployment!
1. Set up Telegram bot and get credentials
2. Package both Lambda functions with dependencies
3. Create IAM role with required permissions
4. Deploy Lambda functions with environment variables
5. Upload data to S3
6. Execute main Lambda function
7. Monitor progress via Telegram
8. Receive comprehensive results in 2-3 minutes
