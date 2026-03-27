# DAX Strategy Serverless Optimization Deployment

## 📋 Overview
Serverless AWS Lambda solution for comprehensive DAX strategy optimization testing ALL 8,100 parameter combinations in parallel.

## 🎯 Parameter Combinations
- **Pivot Combinations:** 36 (6 left × 6 right - ALL combinations including left >= right)
- **Timeframes:** 5 options (5, 10, 15, 30, 60 minutes)
- **Targets:** 5 options (75, 100, 125, 150, 200 points)
- **Stop Modes:** 3 options (zone, distance, both)
- **Accumulated Loss Modes:** 3 options (none, fixed, to_target_increase)
- **TOTAL:** 8,100 combinations

## ⚡ Architecture
- **Main Lambda:** `lambda_dax_serverless_comprehensive.py` (Orchestrator)
- **Worker Lambda:** `lambda_dax_worker.py` (Parallel processing)
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
  --handler lambda_dax_serverless_comprehensive.lambda_handler \
  --zip-file fileb://dax-optimizer-main.zip \
  --timeout 900 \
  --memory-size 2048 \
  --environment Variables={WORKER_FUNCTION_NAME=dax-optimizer-worker}
```

#### Worker Function (dax-optimizer-worker)
```bash
aws lambda create-function \
  --function-name dax-optimizer-worker \
  --runtime python3.9 \
  --role arn:aws:iam::ACCOUNT:role/lambda-execution-role \
  --handler lambda_dax_worker.lambda_handler \
  --zip-file fileb://dax-optimizer-worker.zip \
  --timeout 900 \
  --memory-size 1024
```

### 2. Package Dependencies
```bash
# Create deployment packages
pip install pandas boto3 -t ./package
cp lambda_dax_serverless_comprehensive.py ./package/
cp lambda_dax_worker.py ./package/
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

## 📊 Expected Results
- **Top 10 configurations** ranked by composite score
- **Best configuration** with full performance metrics
- **Complete analysis** of all 8,100 combinations
- **Significant improvement** over current +8,966.85 points

## 🎯 Current Best Performance
- **Configuration:** Pv 5/10 TF 15m T 125 SM both AL to_target_increase
- **Performance:** +8,966.85 points
- **Expected Improvement:** Higher score with comprehensive testing

## ⚡ Performance Benefits
- **Speed:** 100x faster than local execution
- **Cost:** Minimal (~$0.50)
- **Scalability:** Automatic parallel processing
- **Reliability:** Serverless architecture

## 🔍 Output Format
```json
{
  "total_combinations_tested": 8100,
  "successful_tests": 8100,
  "parallel_workers_used": 100,
  "top_10_results": [...],
  "best_configuration": {
    "parameters": {...},
    "performance": {...}
  }
}
```

## ✅ Ready for Deployment
1. Package both Lambda functions
2. Create IAM role with required permissions
3. Deploy Lambda functions
4. Upload data to S3
5. Execute main Lambda function
6. Receive comprehensive results in 2-3 minutes
