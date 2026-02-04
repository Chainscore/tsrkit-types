# Benchmarks

This document records the latest benchmark run and the Python/stdlib baselines used for comparison.
All timings are **seconds for 20,000 runs** on the local machine; results are not directly comparable across hardware or Python versions.

## How To Run

```bash
PYTHONPATH=. python3.12 benchmarks/bench_types.py
```

Raw data is written to:
- `benchmarks/out/bench_results.json`
- `benchmarks/out/bench_profiles.json`

## Latest Results (Local)

**Run date:** 2026-02-04  
**Python:** 3.12.11  
**Runs:** 20,000

### TSRKit Types (selected)

| Case | init_s | encode_s | decode_s | json_encode_s | json_decode_s |
| --- | --- | --- | --- | --- | --- |
| Uint | 0.008567 | 0.004479 | 0.014276 | 0.002534 | 0.008913 |
| U16 | 0.008530 | 0.004632 | 0.014242 | 0.002791 | 0.009892 |
| Bytes(var,64B) | 0.004458 | 0.010630 | 0.008252 | 0.003609 | 0.010214 |
| ByteArray | 0.003199 | 0.006915 | 0.006440 | 0.003522 | 0.009588 |
| Bits(var,64b) | 0.011615 | 0.011080 | 0.016224 | 0.007608 | 0.024439 |
| TypedArray[U16,10] | 0.014253 | 0.006967 | 0.017195 | 0.003189 | 0.152636 |
| Dictionary[String,U16] | 0.023382 | 0.061991 | 0.149705 | 0.068052 | 0.179980 |

### Python/Stdlib Baselines (selected)

| Case | init_s | encode_s | decode_s |
| --- | --- | --- | --- |
| PyInt(varint) | 0.002778 | 0.006405 | 0.007207 |
| PyU16(to_bytes) | 0.004112 | 0.003861 | 0.006797 |
| PyBytes(var,64B) | 0.003516 | 0.005396 | 0.005538 |
| PyByteArray(var,64B) | 0.003091 | 0.006694 | 0.006594 |
| PyBits(var,64b) | 0.006438 | 0.088161 | 0.150918 |
| PyArray('H',10) | 0.006611 | 0.008616 | 0.006599 |
| PyDict[str,U16] | 0.003587 | 0.095823 | 0.077303 |

## Notes On Baselines

- `PyInt(varint)`: pure-Python varint encoder/decoder (same scheme as `Uint`).
- `PyU16(to_bytes)`: `int.to_bytes` / `int.from_bytes` for fixed-width integers.
- `PyBytes(var,64B)` / `PyByteArray(var,64B)`: length-prefixed bytes (varint length).
- `PyBits(var,64b)`: list[bool] packed/unpacked to bytes in Python.
- `PyArray('H',10)`: stdlib `array('H')` with `.tobytes()` / `.frombytes()`.
- `PyDict[str,U16]`: sorted key encode; keys length-prefixed; values fixed 2-byte little-endian.
