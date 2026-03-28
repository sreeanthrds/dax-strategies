#!/usr/bin/env python3
"""
DAX Strategy - Comprehensive Serverless Optimization (ALL COMBINATIONS)
=====================================================================

This Lambda function orchestrates COMPREHENSIVE parameter optimization for the
corrected DAX strategy with ALL possible parameter combinations.

Features:
- ALL parameter permutations and combinations
- Bidirectional trading option
- Massive parameter space (50,000+ combinations)
- Serverless parallel processing
- Telegram notifications
- Complete results aggregation

Expected Combinations: 50,000+ parameter combinations
"""

import json
import os
import math
import boto3
import requests
from datetime import datetime
from typing import List, Dict, Any

# =============================================================================
# CONFIGURATION
# =============================================================================

# Lambda Configuration
LAMBDA_CLIENT = boto3.client('lambda')
WORKER_FUNCTION_NAME = os.environ.get('WORKER_FUNCTION_NAME', 'dax-comprehensive-optimizer-worker')

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# Data Configuration
DATA_FILE_PATH = "/opt/signal_trade_processor/strategy_optimization_complete/data/dax_1min_ohlc.csv"

# Optimization Configuration
CHUNK_SIZE = 25  # Smaller chunks for more combinations
MAX_CONCURRENT = 150  # Higher concurrency for massive optimization
TIMEOUT_SECONDS = 600  # Longer timeout for comprehensive testing

# =============================================================================
# COMPREHENSIVE PARAMETER GENERATION
# =============================================================================

def generate_all_combinations():
    """Generate ALL possible parameter combinations for comprehensive testing"""
    combinations = []
    
    # Comprehensive pivot combinations
    pivot_left_options = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    pivot_right_options = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 25, 30]
    
    # Comprehensive timeframe options
    tf_options = [1, 3, 5, 10, 15, 20, 30, 60]  # Added 1min and 1hour
    
    # Comprehensive target options
    target_options = [25, 30, 40, 50, 60, 75, 90, 100, 125, 150, 200, 250]
    
    # Comprehensive stop options
    stop_options = [15, 20, 25, 30, 36, 40, 45, 50, 60, 75, 90, 100, 125]
    
    # Stop modes
    stop_modes = ['zone', 'distance', 'both']
    
    # Accumulated loss modes
    acc_loss_modes = ['none', 'to_target', 'to_target_increase']
    
    # NEW: Bidirectional options
    bidirectional_options = [True, False]
    
    # Dual position options
    dual_position_options = [True, False]
    
    # Force exit times
    force_exit_options = ["16:30", "16:45", "16:55", "17:00", "17:15"]
    
    print(f"🔢 Generating comprehensive parameter combinations...")
    print(f"📊 Pivot left: {len(pivot_left_options)} options")
    print(f"📊 Pivot right: {len(pivot_right_options)} options")
    print(f"📊 Timeframes: {len(tf_options)} options")
    print(f"📊 Targets: {len(target_options)} options")
    print(f"📊 Stops: {len(stop_options)} options")
    print(f"📊 Stop modes: {len(stop_modes)} options")
    print(f"📊 Acc loss modes: {len(acc_loss_modes)} options")
    print(f"📊 Bidirectional: {len(bidirectional_options)} options")
    print(f"📊 Dual position: {len(dual_position_options)} options")
    print(f"📊 Force exit: {len(force_exit_options)} options")
    
    # Generate all valid combinations
    total_generated = 0
    for pivot_left in pivot_left_options:
        for pivot_right in pivot_right_options:
            # Constraint: left must be < right
            if pivot_left >= pivot_right:
                continue
                
            for tf in tf_options:
                for target in target_options:
                    for stop in stop_options:
                        for stop_mode in stop_modes:
                            for acc_loss_mode in acc_loss_modes:
                                for bidirectional in bidirectional_options:
                                    for dual_position in dual_position_options:
                                        for force_exit_time in force_exit_options:
                                            
                                            # Calculate target increase
                                            target_increase = target * 0.4 if acc_loss_mode == 'to_target_increase' else 0
                                            
                                            config = {
                                                'pivot_left': pivot_left,
                                                'pivot_right': pivot_right,
                                                'timeframe_minutes': tf,
                                                'target_points': target,
                                                'base_stop': stop,
                                                'accumulated_loss_mode': acc_loss_mode,
                                                'reset_on_target': True,
                                                'target_increase_on_hit': target_increase,
                                                'max_accumulated_loss_cap': target * 2.5,
                                                'force_exit_time': force_exit_time,
                                                'dual_position': dual_position,
                                                'stop_mode': stop_mode,
                                                'bidirectional': bidirectional  # NEW PARAMETER
                                            }
                                            
                                            combinations.append(config)
                                            total_generated += 1
                                            
                                            # Progress reporting
                                            if total_generated % 10000 == 0:
                                                print(f"📈 Generated {total_generated} combinations...")
    
    print(f"✅ Total combinations generated: {len(combinations)}")
    return combinations

def split_into_chunks(combinations: List[Dict], chunk_size: int) -> List[List[Dict]]:
    """Split combinations into chunks for parallel processing"""
    chunks = []
    for i in range(0, len(combinations), chunk_size):
        chunk = combinations[i:i + chunk_size]
        chunks.append(chunk)
    return chunks

# =============================================================================
# TELEGRAM NOTIFICATIONS
# =============================================================================

def send_telegram_message(message: str) -> bool:
    """Send message to Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram credentials not configured")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown'
        }
        
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        print(f"✅ Telegram message sent: {message[:50]}...")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send Telegram message: {e}")
        return False

def format_results_summary(results: List[Dict]) -> str:
    """Format comprehensive optimization results for Telegram"""
    if not results:
        return "❌ No results to report"
    
    # Sort by total P&L
    sorted_results = sorted(results, key=lambda x: x.get('metrics', {}).get('total_pnl', 0), reverse=True)
    
    top_10 = sorted_results[:10]
    
    message = "🏆 **DAX COMPREHENSIVE Strategy - Top Results**\n\n"
    
    for i, result in enumerate(top_10, 1):
        config = result['config']
        metrics = result['metrics']
        
        # Format configuration compactly
        bidir = "B" if config.get('bidirectional', False) else "U"
        dual = "D" if config.get('dual_position', False) else "S"
        
        message += f"**#{i}** 📊 *Pv {config['pivot_left']}/{config['pivot_right']}* "
        message += f"*TF {config['timeframe_minutes']}m* "
        message += f"*T {config['target_points']}* "
        message += f"*S {config['base_stop']}* "
        message += f"*{config['stop_mode'][0].upper()}* "
        message += f"*{bidir}{dual}*\n"
        message += f"💰 *P&L*: `{metrics['total_pnl']:.1f}` pts | "
        message += f"📈 *WR*: `{metrics['win_rate']:.1f}%` | "
        message += f"🎯 *PF*: `{metrics['profit_factor']:.2f}` | "
        message += f"📊 *T*: `{metrics['total_trades']}`\n\n"
    
    # Summary statistics
    total_combinations = len(results)
    profitable = len([r for r in results if r['metrics']['total_pnl'] > 0])
    avg_pnl = sum(r['metrics']['total_pnl'] for r in results) / len(results)
    
    message += f"📋 **Summary**: {total_combinations} combos | "
    message += f"{profitable} profitable ({profitable/total_combinations*100:.1f}%) | "
    message += f"Avg P&L: {avg_pnl:.1f} pts"
    
    return message

# =============================================================================
# LAMBDA INVOCATION
# =============================================================================

def invoke_worker(chunk: List[Dict], chunk_id: int) -> Dict:
    """Invoke worker Lambda function"""
    try:
        payload = {
            'chunk_id': chunk_id,
            'combinations': chunk,
            'data_file_path': DATA_FILE_PATH
        }
        
        response = LAMBDA_CLIENT.invoke(
            FunctionName=WORKER_FUNCTION_NAME,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload),
            Timeout=TIMEOUT_SECONDS
        )
        
        result = json.loads(response['Payload'].read())
        
        if result.get('error'):
            print(f"❌ Worker {chunk_id} returned error: {result['error']}")
            return {'chunk_id': chunk_id, 'error': result['error'], 'results': []}
        
        print(f"✅ Worker {chunk_id} completed: {len(result.get('results', []))} results")
        return result
        
    except Exception as e:
        print(f"❌ Failed to invoke worker {chunk_id}: {e}")
        return {'chunk_id': chunk_id, 'error': str(e), 'results': []}

def invoke_workers_parallel(chunks: List[List[Dict]]) -> List[Dict]:
    """Invoke multiple workers in parallel"""
    import concurrent.futures
    
    all_results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as executor:
        # Submit all tasks
        future_to_chunk_id = {}
        for i, chunk in enumerate(chunks):
            future = executor.submit(invoke_worker, chunk, i)
            future_to_chunk_id[future] = i
        
        # Collect results as they complete
        completed = 0
        total = len(chunks)
        
        for future in concurrent.futures.as_completed(future_to_chunk_id):
            chunk_id = future_to_chunk_id[future]
            try:
                result = future.result()
                all_results.append(result)
                completed += 1
                
                # Send progress update (less frequent for massive optimization)
                if completed % 25 == 0 or completed == total:
                    progress = (completed / total) * 100
                    message = f"📊 **Progress**: {completed}/{total} chunks completed ({progress:.1f}%)"
                    send_telegram_message(message)
                
            except Exception as e:
                print(f"❌ Worker {chunk_id} failed: {e}")
                all_results.append({'chunk_id': chunk_id, 'error': str(e), 'results': []})
    
    return all_results

# =============================================================================
# RESULTS PROCESSING
# =============================================================================

def aggregate_results(worker_results: List[Dict]) -> List[Dict]:
    """Aggregate results from all workers"""
    all_combination_results = []
    
    for worker_result in worker_results:
        if 'error' in worker_result:
            print(f"⚠️ Skipping worker {worker_result['chunk_id']} due to error")
            continue
        
        chunk_results = worker_result.get('results', [])
        all_combination_results.extend(chunk_results)
    
    print(f"📊 Total results collected: {len(all_combination_results)}")
    return all_combination_results

def rank_and_filter_results(results: List[Dict]) -> List[Dict]:
    """Rank results by performance metrics"""
    # Filter out results with errors or insufficient trades
    valid_results = []
    
    for result in results:
        metrics = result.get('metrics', {})
        
        # Minimum requirements (more lenient for comprehensive testing)
        if (metrics.get('total_trades', 0) < 5 or 
            metrics.get('win_rate', 0) < 15 or
            metrics.get('profit_factor', 0) <= 0):
            continue
        
        valid_results.append(result)
    
    # Sort by composite score (P&L weighted)
    def composite_score(result):
        metrics = result['metrics']
        pnl = metrics.get('total_pnl', 0)
        win_rate = metrics.get('win_rate', 0)
        profit_factor = metrics.get('profit_factor', 0)
        trades = metrics.get('total_trades', 0)
        
        # Composite score: P&L * (1 + win_rate/100) * profit_factor * log(trades)
        score = pnl * (1 + win_rate/100) * profit_factor * math.log(max(trades, 5))
        return score
    
    ranked_results = sorted(valid_results, key=composite_score, reverse=True)
    return ranked_results

# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================

def lambda_handler(event, context):
    """Main Lambda handler for comprehensive optimization"""
    
    # Send start notification
    start_message = (
        "🚀 **DAX COMPREHENSIVE Strategy - Serverless Optimization Started**\n\n"
        f"⏰ *Time*: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"📊 *Worker Function*: `{WORKER_FUNCTION_NAME}`\n"
        f"📁 *Data File*: `{DATA_FILE_PATH}`\n"
        f"📏 *Chunk Size*: {CHUNK_SIZE}\n"
        f"⚡ *Max Concurrent*: {MAX_CONCURRENT}\n\n"
        "🔄 *Generating ALL parameter combinations...*"
    )
    send_telegram_message(start_message)
    
    try:
        # Step 1: Generate ALL parameter combinations
        print("📊 Generating comprehensive parameter combinations...")
        combinations = generate_all_combinations()
        total_combinations = len(combinations)
        
        message = (
            f"📊 **COMPREHENSIVE Parameter Combinations Generated**\n\n"
            f"🔢 *Total Combinations*: `{total_combinations:,}`\n"
            f"📏 *Chunk Size*: `{CHUNK_SIZE}`\n"
            f"📦 *Total Chunks*: `{math.ceil(total_combinations / CHUNK_SIZE):,}`\n\n"
            "🚀 *Starting massive parallel processing...*"
        )
        send_telegram_message(message)
        
        # Step 2: Split into chunks
        chunks = split_into_chunks(combinations, CHUNK_SIZE)
        total_chunks = len(chunks)
        
        print(f"📦 Split into {total_chunks:,} chunks")
        
        # Step 3: Invoke workers in parallel
        print("🚀 Starting massive parallel worker invocation...")
        worker_results = invoke_workers_parallel(chunks)
        
        # Step 4: Aggregate results
        print("📊 Aggregating results...")
        all_results = aggregate_results(worker_results)
        
        # Step 5: Rank and filter results
        print("🏆 Ranking and filtering results...")
        ranked_results = rank_and_filter_results(all_results)
        
        # Step 6: Send final results
        final_message = format_results_summary(ranked_results)
        send_telegram_message(final_message)
        
        # Save detailed results
        output_file = f"/tmp/dax_comprehensive_optimization_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_combinations': total_combinations,
                'total_chunks': total_chunks,
                'worker_results': worker_results,
                'ranked_results': ranked_results[:100]  # Top 100
            }, f, indent=2)
        
        print(f"💾 Results saved to: {output_file}")
        
        # Send completion notification
        completion_message = (
            f"✅ **DAX COMPREHENSIVE Strategy - Optimization Completed**\n\n"
            f"📊 *Total Combinations*: `{total_combinations:,}`\n"
            f"📦 *Total Chunks*: `{total_chunks:,}`\n"
            f"🏆 *Valid Results*: `{len(ranked_results):,}`\n"
            f"💾 *Results File*: `{output_file}`\n\n"
            f"⏰ *Completed*: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        send_telegram_message(completion_message)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'status': 'completed',
                'total_combinations': total_combinations,
                'total_chunks': total_chunks,
                'valid_results': len(ranked_results),
                'output_file': output_file
            })
        }
        
    except Exception as e:
        error_message = (
            f"❌ **DAX COMPREHENSIVE Strategy - Optimization Failed**\n\n"
            f"🔴 *Error*: `{str(e)}`\n"
            f"⏰ *Time*: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        send_telegram_message(error_message)
        
        print(f"❌ Optimization failed: {e}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'failed',
                'error': str(e)
            })
        }


if __name__ == "__main__":
    # For local testing
    class MockContext:
        pass
    
    result = lambda_handler({}, MockContext())
    print(json.dumps(result, indent=2))
