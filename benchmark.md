# Benchmarks

Compare performance between runs. All timings are **seconds for 20,000 runs**.

## Quick Start

```bash
make bench                # Run benchmarks
make bench-compare        # Compare with baseline
make bench-baseline       # Set current as baseline
```

Results: `benchmarks/out/bench_results.json` (14KB)

## Workflow

```bash
# 1. Set baseline
make bench
make bench-baseline

# 2. Make changes...

# 3. Compare
make bench
make bench-compare
```

## Custom runs

```bash
make bench ARGS="--runs 1000 --no-profile"
```

## What's Tested

**Types**: Integers, Bytes, Bits, Strings, Bool, Collections, Dictionary, Option, Choice, Enum, Structures

**Operations**: init, encode, decode, json_encode/decode, container ops (append/extend/pop/getitem)
