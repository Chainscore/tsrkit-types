#!/usr/bin/env python3
"""Compare two benchmark runs and show what got faster/slower."""

import json
import sys
from pathlib import Path


def load_results(path):
    """Load benchmark results from JSON file."""
    with open(path) as f:
        return json.load(f)


def compare(current_path, baseline_path):
    """Compare current results against baseline."""
    current = load_results(current_path)
    baseline = load_results(baseline_path)

    # Extract results
    curr_tests = current.get("results", {})
    base_tests = baseline.get("results", {})
    curr_ops = current.get("container_ops", {})
    base_ops = baseline.get("container_ops", {})

    regressions = []
    improvements = []

    # Compare test results
    for name, ops in curr_tests.items():
        if name not in base_tests:
            continue
        for op, curr_time in ops.items():
            if op not in base_tests[name]:
                continue
            base_time = base_tests[name][op]
            if base_time == 0:
                continue

            ratio = curr_time / base_time
            change = (ratio - 1) * 100

            if ratio >= 1.10:  # 10% slower
                regressions.append((f"{name}.{op}", base_time, curr_time, change))
            elif ratio <= 0.90:  # 10% faster
                improvements.append((f"{name}.{op}", base_time, curr_time, change))

    # Compare container ops
    for name, curr_time in curr_ops.items():
        if name not in base_ops:
            continue
        base_time = base_ops[name]
        if base_time == 0:
            continue

        ratio = curr_time / base_time
        change = (ratio - 1) * 100

        if ratio >= 1.10:
            regressions.append((f"ops.{name}", base_time, curr_time, change))
        elif ratio <= 0.90:
            improvements.append((f"ops.{name}", base_time, curr_time, change))

    # Print results
    print(f"\n{'='*70}")
    print(f"Benchmark Comparison")
    print(f"{'='*70}")
    print(f"Baseline: {baseline_path}")
    print(f"Current:  {current_path}")
    print(f"Runs:     {current.get('runs', 'N/A')}")
    print(f"{'='*70}\n")

    print(f"Summary: {len(improvements)} improvements, {len(regressions)} regressions\n")

    if regressions:
        regressions.sort(key=lambda x: x[3], reverse=True)  # Sort by % change
        print(f"⚠️  REGRESSIONS (slower):")
        print(f"{'-'*70}")
        for name, base, curr, change in regressions[:20]:  # Top 20
            print(f"  {name:40} {base:.4f}s → {curr:.4f}s  ({change:+6.1f}%)")
        if len(regressions) > 20:
            print(f"  ... and {len(regressions) - 20} more")
        print()

    if improvements:
        improvements.sort(key=lambda x: x[3])  # Sort by % change
        print(f"✅ IMPROVEMENTS (faster):")
        print(f"{'-'*70}")
        for name, base, curr, change in improvements[:20]:  # Top 20
            print(f"  {name:40} {base:.4f}s → {curr:.4f}s  ({change:+6.1f}%)")
        if len(improvements) > 20:
            print(f"  ... and {len(improvements) - 20} more")
        print()

    # Exit with error if major regressions (>20% slower)
    major = [r for r in regressions if r[3] >= 20]
    if major:
        print(f"❌ {len(major)} major regression(s) found (>20% slower)\n")
        return 1

    return 0


def main():
    if len(sys.argv) < 2:
        print("Usage: python compare.py <current.json> [baseline.json]")
        print("   If baseline.json not provided, uses benchmarks/out/bench_baseline.json")
        sys.exit(1)

    current_path = Path(sys.argv[1])
    baseline_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("benchmarks/out/bench_baseline.json")

    # Make paths absolute if not already
    if not current_path.is_absolute():
        current_path = Path.cwd() / current_path
    if not baseline_path.is_absolute():
        baseline_path = Path.cwd() / baseline_path

    if not Path(current_path).exists():
        print(f"Error: {current_path} not found")
        sys.exit(1)
    if not Path(baseline_path).exists():
        print(f"Error: {baseline_path} not found")
        sys.exit(1)

    return compare(str(current_path), str(baseline_path))


if __name__ == "__main__":
    sys.exit(main())
