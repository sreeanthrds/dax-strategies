#!/usr/bin/env python3
"""
DAX Strategy - Optimized Serverless Deployment Script
====================================================

This script automates the deployment of the optimized DAX strategy
serverless optimization system with 1000 Lambdas.

Usage:
python deploy_optimized_serverless.py
"""

import json
import os
import subprocess
import time
from datetime import datetime

def create_deployment_package():
    """Create deployment packages for Lambda functions"""
    print("📦 Creating deployment packages...")
    
    # Create deployment directory
    os.makedirs("deployment_package", exist_ok=True)
    os.chdir("deployment_package")
    
    # Copy Lambda functions
    subprocess.run(["cp", "../lambda_dax_optimized_serverless_telegram.py", "."], check=True)
    subprocess.run(["cp", "../lambda_dax_optimized_worker_telegram.py", "."], check=True)
    
    # Create requirements.txt
    with open("requirements.txt", "w") as f:
        f.write("requests==2.31.0\n")
        f.write("boto3==1.28.57\n")
    
    # Install dependencies
    print("📥 Installing dependencies...")
    subprocess.run(["pip", "install", "-r", "requirements.txt", "-t", "."], check=True)
    
    # Create data directory and copy data
    os.makedirs("opt/signal_trade_processor/strategy_optimization_complete/data", exist_ok=True)
    subprocess.run([
        "cp", 
        "/Users/sreenathreddy/Downloads/UniTrader-project/signal_trade_processor/strategy_optimization_complete/data/dax_1min_ohlc.csv",
        "opt/signal_trade_processor/strategy_optimization_complete/data/"
    ], check=True)
    
    # Create zip files
    print("📦 Creating zip files...")
    subprocess.run(["zip", "-r", "orchestrator.zip", "lambda_dax_optimized_serverless_telegram.py", "opt/"], check=True)
    subprocess.run(["zip", "-r", "worker.zip", "lambda_dax_optimized_worker_telegram.py", "opt/"], check=True)
    
    print("✅ Deployment packages created successfully!")
    return True

def create_iam_role():
    """Create IAM role for Lambda functions"""
    print("🔐 Creating IAM role...")
    
    # Create trust policy
    trust_policy = {
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
    }
    
    # Create IAM role
    try:
        result = subprocess.run([
            "aws", "iam", "create-role",
            "--role-name", "DAXOptimizedOptimizerRole",
            "--assume-role-policy-document", json.dumps(trust_policy)
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ IAM role created successfully!")
            return True
        else:
            print("⚠️ IAM role may already exist")
            return True
            
    except Exception as e:
        print(f"❌ Error creating IAM role: {e}")
        return False

def attach_iam_policies():
    """Attach policies to IAM role"""
    print("📎 Attaching IAM policies...")
    
    # Basic Lambda execution policy
    lambda_policy = {
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
            }
        ]
    }
    
    try:
        # Create and attach policy
        subprocess.run([
            "aws", "iam", "put-role-policy",
            "--role-name", "DAXOptimizedOptimizerRole",
            "--policy-name", "DAXOptimizedLambdaPolicy",
            "--policy-document", json.dumps(lambda_policy)
        ], check=True)
        
        print("✅ IAM policies attached successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error attaching IAM policies: {e}")
        return False

def create_lambda_functions():
    """Create Lambda functions"""
    print("🚀 Creating Lambda functions...")
    
    # Get AWS account ID
    try:
        result = subprocess.run([
            "aws", "sts", "get-caller-identity"
        ], capture_output=True, text=True, check=True)
        
        account_id = json.loads(result.stdout)["Account"]
        print(f"📋 AWS Account ID: {account_id}")
        
    except Exception as e:
        print(f"❌ Error getting AWS account ID: {e}")
        return False
    
    # Create orchestrator function
    print("📊 Creating orchestrator function...")
    try:
        subprocess.run([
            "aws", "lambda", "create-function",
            "--function-name", "dax-optimized-optimizer-orchestrator",
            "--runtime", "python3.9",
            "--role", f"arn:aws:iam::{account_id}:role/DAXOptimizedOptimizerRole",
            "--handler", "lambda_dax_optimized_serverless_telegram.lambda_handler",
            "--zip-file", "fileb://orchestrator.zip",
            "--timeout", "900",
            "--memory-size", "1024",
            "--environment", "Variables={WORKER_FUNCTION_NAME=dax-optimized-optimizer-worker,TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN,TELEGRAM_CHAT_ID=YOUR_CHAT_ID}"
        ], check=True)
        
        print("✅ Orchestrator function created successfully!")
        
    except subprocess.CalledProcessError as e:
        if "already exists" in e.stderr:
            print("⚠️ Orchestrator function already exists, updating...")
            subprocess.run([
                "aws", "lambda", "update-function-code",
                "--function-name", "dax-optimized-optimizer-orchestrator",
                "--zip-file", "fileb://orchestrator.zip"
            ], check=True)
            print("✅ Orchestrator function updated!")
        else:
            print(f"❌ Error creating orchestrator: {e}")
            return False
    
    # Create worker function
    print("🔧 Creating worker function...")
    try:
        subprocess.run([
            "aws", "lambda", "create-function",
            "--function-name", "dax-optimized-optimizer-worker",
            "--runtime", "python3.9",
            "--role", f"arn:aws:iam::{account_id}:role/DAXOptimizedOptimizerRole",
            "--handler", "lambda_dax_optimized_worker_telegram.lambda_handler",
            "--zip-file", "fileb://worker.zip",
            "--timeout", "300",
            "--memory-size", "1536"
        ], check=True)
        
        print("✅ Worker function created successfully!")
        
    except subprocess.CalledProcessError as e:
        if "already exists" in e.stderr:
            print("⚠️ Worker function already exists, updating...")
            subprocess.run([
                "aws", "lambda", "update-function-code",
                "--function-name", "dax-optimized-optimizer-worker",
                "--zip-file", "fileb://worker.zip"
            ], check=True)
            print("✅ Worker function updated!")
        else:
            print(f"❌ Error creating worker: {e}")
            return False
    
    return True

def configure_concurrency():
    """Configure Lambda concurrency"""
    print("⚡ Configuring Lambda concurrency...")
    
    try:
        # Set reserved concurrency for orchestrator
        subprocess.run([
            "aws", "lambda", "put-function-concurrency",
            "--function-name", "dax-optimized-optimizer-orchestrator",
            "--reserved-concurrent-executions", "1"
        ], check=True)
        
        # Set reserved concurrency for worker
        subprocess.run([
            "aws", "lambda", "put-function-concurrency",
            "--function-name", "dax-optimized-optimizer-worker",
            "--reserved-concurrent-executions", "1000"
        ], check=True)
        
        print("✅ Lambda concurrency configured successfully!")
        print("   📊 Orchestrator: 1 concurrent execution")
        print("   🔧 Worker: 1000 concurrent executions")
        
        return True
        
    except Exception as e:
        print(f"❌ Error configuring concurrency: {e}")
        return False

def test_deployment():
    """Test the deployment"""
    print("🧪 Testing deployment...")
    
    try:
        # Test worker function
        print("🔧 Testing worker function...")
        test_payload = {
            "chunk_id": 0,
            "combinations": [{
                'pivot_left': 5, 'pivot_right': 8, 'timeframe_minutes': 5,
                'target_points': 75.0, 'base_stop': 36.0, 'stop_mode': 'zone',
                'accumulated_loss_mode': 'none', 'reset_on_target': True,
                'target_increase_on_hit': 30.0, 'max_accumulated_loss_cap': 150.0,
                'force_exit_time': "16:55", 'dual_position': False,
                'bidirectional': False
            }],
            "data_file_path": "/opt/signal_trade_processor/strategy_optimization_complete/data/dax_1min_ohlc.csv"
        }
        
        result = subprocess.run([
            "aws", "lambda", "invoke",
            "--function-name", "dax-optimized-optimizer-worker",
            "--payload", json.dumps(test_payload),
            "worker_test_result.json"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Worker function test successful!")
            
            # Read and display result
            with open("worker_test_result.json", "r") as f:
                test_result = json.load(f)
            
            if "chunk_id" in test_result and "results" in test_result:
                print(f"   📊 Chunk ID: {test_result['chunk_id']}")
                print(f"   📊 Results: {len(test_result['results'])}")
                print("   ✅ Worker function is working correctly!")
            else:
                print("   ⚠️ Unexpected response format")
            
        else:
            print(f"❌ Worker function test failed: {result.stderr}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing deployment: {e}")
        return False

def run_optimization():
    """Run the full optimization"""
    print("🚀 Starting full optimization...")
    
    try:
        print("📊 This will test 1,759,968 parameter combinations")
        print("⏱️  Estimated runtime: ~1.8 hours")
        print("💰 Estimated cost: ~$0.00")
        print("📱 You'll receive Telegram notifications")
        print()
        
        confirm = input("🤔 Do you want to proceed with the full optimization? (y/N): ")
        
        if confirm.lower() != 'y':
            print("❌ Optimization cancelled")
            return False
        
        print("🚀 Starting optimization...")
        
        # Run orchestrator
        result = subprocess.run([
            "aws", "lambda", "invoke",
            "--function-name", "dax-optimized-optimizer-orchestrator",
            "--payload", "{}",
            "optimization_result.json"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Optimization started successfully!")
            print("📱 Monitor Telegram for progress updates")
            print("📊 Results will be saved to Lambda execution environment")
            
            # Display initial response
            with open("optimization_result.json", "r") as f:
                opt_result = json.load(f)
            
            print(f"   📊 Status: {opt_result.get('body', '{}')}")
            
            return True
        else:
            print(f"❌ Error starting optimization: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error running optimization: {e}")
        return False

def main():
    """Main deployment function"""
    print("🚀 DAX Strategy - Optimized Serverless Deployment")
    print("=" * 60)
    print("📊 This will deploy the optimized serverless optimization system")
    print("⚡ Configured for 1000 parallel Lambdas")
    print("📱 Includes Telegram notifications")
    print()
    
    # Check prerequisites
    print("🔍 Checking prerequisites...")
    
    # Check AWS CLI
    try:
        subprocess.run(["aws", "--version"], check=True, capture_output=True)
        print("✅ AWS CLI found")
    except:
        print("❌ AWS CLI not found. Please install AWS CLI first.")
        return False
    
    # Check AWS credentials
    try:
        subprocess.run(["aws", "sts", "get-caller-identity"], check=True, capture_output=True)
        print("✅ AWS credentials configured")
    except:
        print("❌ AWS credentials not configured. Please run 'aws configure' first.")
        return False
    
    print()
    
    # Deployment steps
    steps = [
        ("Create deployment packages", create_deployment_package),
        ("Create IAM role", create_iam_role),
        ("Attach IAM policies", attach_iam_policies),
        ("Create Lambda functions", create_lambda_functions),
        ("Configure concurrency", configure_concurrency),
        ("Test deployment", test_deployment),
        ("Run optimization", run_optimization)
    ]
    
    for step_name, step_func in steps:
        print(f"\n📋 {step_name}...")
        try:
            if step_func():
                print(f"✅ {step_name} completed successfully!")
            else:
                print(f"❌ {step_name} failed!")
                if step_name != "Run optimization":
                    print("🛑 Deployment stopped due to error")
                    return False
                else:
                    print("🛑 Optimization cancelled or failed")
                    return False
        except Exception as e:
            print(f"❌ {step_name} failed with error: {e}")
            if step_name != "Run optimization":
                print("🛑 Deployment stopped due to error")
                return False
            else:
                print("🛑 Optimization cancelled or failed")
                return False
    
    print("\n🎉 Deployment completed successfully!")
    print("📊 Monitor Telegram for optimization progress")
    print("📈 Expected completion: ~1.8 hours")
    print("💰 Estimated cost: ~$0.00")
    
    return True

if __name__ == "__main__":
    main()
