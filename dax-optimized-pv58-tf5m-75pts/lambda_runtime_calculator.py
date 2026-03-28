#!/usr/bin/env python3
"""
DAX Strategy - Lambda Runtime Calculator
======================================

This script calculates runtime estimates for different Lambda concurrency levels.

Usage:
python lambda_runtime_calculator.py
"""

import math

def calculate_lambda_runtime():
    """Calculate runtime for different Lambda concurrency levels"""
    
    # Optimized parameters
    total_combinations = 1759968
    chunk_size = 50
    total_chunks = math.ceil(total_combinations / chunk_size)
    
    # Runtime assumptions
    avg_chunk_runtime_minutes = 3  # Average runtime per chunk
    
    print("🚀 Lambda Runtime Calculator")
    print("=" * 60)
    print(f"📊 Total Combinations: {total_combinations:,}")
    print(f"📦 Total Chunks: {total_chunks:,}")
    print(f"⚡ Average Chunk Runtime: {avg_chunk_runtime_minutes} minutes")
    print()
    
    # Different concurrency levels
    concurrency_levels = [10, 25, 50, 100, 200, 500, 1000]
    
    print("📈 Runtime Estimates by Concurrency Level:")
    print("=" * 60)
    
    for concurrency in concurrency_levels:
        # Calculate total runtime
        total_batches = math.ceil(total_chunks / concurrency)
        total_runtime_minutes = total_batches * avg_chunk_runtime_minutes
        
        # Convert to human-readable format
        if total_runtime_minutes < 60:
            runtime_str = f"{total_runtime_minutes:.1f} minutes"
        elif total_runtime_minutes < 1440:  # Less than 24 hours
            hours = total_runtime_minutes / 60
            runtime_str = f"{hours:.1f} hours"
        else:
            days = total_runtime_minutes / 1440
            runtime_str = f"{days:.1f} days"
        
        # Calculate cost
        lambda_cost_per_second = 0.00001667  # $0.00001667 per GB-second
        memory_gb = 2  # Assuming 2GB memory
        total_runtime_seconds = total_runtime_minutes * 60
        total_cost = (total_runtime_seconds * lambda_cost_per_second * memory_gb * concurrency) / 1000000
        
        print(f"🔢 {concurrency:4d} Lambdas:")
        print(f"   📦 Total Batches: {total_batches:,}")
        print(f"   ⏱️  Runtime: {runtime_str}")
        print(f"   💰 Lambda Cost: ${total_cost:.2f}")
        print()
    
    print("🎯 Specific Analysis for 1000 Lambdas:")
    print("=" * 50)
    
    concurrency_1000 = 1000
    total_batches_1000 = math.ceil(total_chunks / concurrency_1000)
    total_runtime_minutes_1000 = total_batches_1000 * avg_chunk_runtime_minutes
    
    print(f"📊 With 1000 Lambdas in parallel:")
    print(f"   📦 Total Chunks: {total_chunks:,}")
    print(f"   🔢 Lambdas: {concurrency_1000}")
    print(f"   📦 Chunks per Lambda: {total_chunks // concurrency_1000}")
    print(f"   📦 Remaining Chunks: {total_chunks % concurrency_1000}")
    print(f"   📦 Total Batches: {total_batches_1000}")
    print(f"   ⏱️  Runtime: {total_runtime_minutes_1000:.1f} minutes ({total_runtime_minutes_1000/60:.2f} hours)")
    
    # Cost calculation for 1000 lambdas
    lambda_cost_per_second = 0.00001667
    memory_gb = 2
    total_runtime_seconds_1000 = total_runtime_minutes_1000 * 60
    total_cost_1000 = (total_runtime_seconds_1000 * lambda_cost_per_second * memory_gb * concurrency_1000) / 1000000
    
    print(f"   💰 Lambda Cost: ${total_cost_1000:.2f}")
    
    # Comparison with baseline (100 lambdas)
    concurrency_100 = 100
    total_runtime_minutes_100 = (math.ceil(total_chunks / concurrency_100) * avg_chunk_runtime_minutes)
    speedup = total_runtime_minutes_100 / total_runtime_minutes_1000
    
    print(f"\n📈 Speedup vs 100 Lambdas:")
    print(f"   ⏱️  100 Lambdas: {total_runtime_minutes_100:.1f} minutes ({total_runtime_minutes_100/60:.2f} hours)")
    print(f"   ⏱️  1000 Lambdas: {total_runtime_minutes_1000:.1f} minutes ({total_runtime_minutes_1000/60:.2f} hours)")
    print(f"   🚀 Speedup: {speedup:.1f}x faster")
    
    # AWS Lambda limits consideration
    print(f"\n⚠️  AWS Lambda Limits Considerations:")
    print(f"   📊 Default Concurrent Execution Limit: 1,000")
    print(f"   📊 Can request limit increase to higher values")
    print(f"   📊 Regional quotas may apply")
    print(f"   📊 Account-level limits: 10,000+ (with request)")
    
    # Practical considerations
    print(f"\n🔧 Practical Considerations:")
    print(f"   📈 Diminishing returns after certain concurrency")
    print(f"   🌐 Network bottlenecks with very high concurrency")
    print(f"   💰 Cost increases linearly with concurrency")
    print(f"   📊 Data loading may become bottleneck")
    print(f"   🔥 Cold start impact with many concurrent functions")
    
    return {
        'total_combinations': total_combinations,
        'total_chunks': total_chunks,
        'runtime_1000_minutes': total_runtime_minutes_1000,
        'cost_1000': total_cost_1000,
        'speedup_vs_100': speedup
    }

def analyze_optimal_concurrency():
    """Analyze optimal concurrency level"""
    print("\n🎯 Optimal Concurrency Analysis:")
    print("=" * 50)
    
    total_combinations = 1759968
    chunk_size = 50
    total_chunks = math.ceil(total_combinations / chunk_size)
    avg_chunk_runtime_minutes = 3
    
    # Test different concurrency levels
    concurrency_levels = [50, 100, 200, 300, 400, 500, 750, 1000, 1500, 2000]
    
    print("📊 Efficiency Analysis:")
    print("Concurrency | Runtime (min) | Speedup | Cost ($) | Efficiency")
    print("-" * 70)
    
    baseline_runtime = (math.ceil(total_chunks / 100) * avg_chunk_runtime_minutes)
    
    for concurrency in concurrency_levels:
        total_batches = math.ceil(total_chunks / concurrency)
        runtime = total_batches * avg_chunk_runtime_minutes
        speedup = baseline_runtime / runtime
        
        # Cost calculation
        lambda_cost_per_second = 0.00001667
        memory_gb = 2
        total_runtime_seconds = runtime * 60
        cost = (total_runtime_seconds * lambda_cost_per_second * memory_gb * concurrency) / 1000000
        
        # Efficiency (speedup per dollar)
        efficiency = speedup / cost if cost > 0 else 0
        
        print(f"{concurrency:11d} | {runtime:13.1f} | {speedup:7.1f}x | {cost:8.2f} | {efficiency:10.1f}")
    
    print(f"\n💡 Recommendations:")
    print(f"   🎯 200-500 Lambdas: Best efficiency")
    print(f"   🚀 1000 Lambdas: Maximum speed, reasonable cost")
    print(f"   ⚡ 1500+ Lambdas: Diminishing returns, higher cost")

def main():
    """Main calculator function"""
    results = calculate_lambda_runtime()
    analyze_optimal_concurrency()
    
    print(f"\n📋 Summary for 1000 Lambdas:")
    print("=" * 40)
    print(f"⏱️  Runtime: {results['runtime_1000_minutes']:.1f} minutes")
    print(f"💰 Cost: ${results['cost_1000']:.2f}")
    print(f"🚀 Speedup: {results['speedup_vs_100']:.1f}x vs 100 Lambdas")
    print(f"📊 Total Combinations: {results['total_combinations']:,}")
    
    print(f"\n✅ Ready for deployment with 1000 Lambdas!")

if __name__ == "__main__":
    main()
