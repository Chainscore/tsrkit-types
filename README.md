# TSRKit Types

[![PyPI](https://img.shields.io/pypi/v/tsrkit-types.svg)](https://pypi.org/project/tsrkit-types/)
[![Python](https://img.shields.io/pypi/pyversions/tsrkit-types.svg)](https://pypi.org/project/tsrkit-types/)
[![CI](https://github.com/Chainscore/tsrkit-types/actions/workflows/ci.yml/badge.svg)](https://github.com/Chainscore/tsrkit-types/actions/workflows/ci.yml)
[![Release](https://github.com/Chainscore/tsrkit-types/actions/workflows/release.yml/badge.svg)](https://github.com/Chainscore/tsrkit-types/actions/workflows/release.yml)
[![License](https://img.shields.io/github/license/Chainscore/tsrkit-types.svg)](https://github.com/Chainscore/tsrkit-types/blob/main/LICENSE)

A high‑performance, strongly‑typed Python serialization library with built‑in JSON support. TSRKit Types provides a concise type system for integers, bytes, strings, bits, sequences, dictionaries, enums, and structs with deterministic, validated encoding.

## Highlights

- Native C extension for performance‑critical encode/decode paths
- Deterministic binary encoding and JSON serialization
- Strong runtime validation with type‑safe containers
- Clean, small API designed for application‑level data modeling

## Installation

### Wheels (recommended)

```bash
pip install tsrkit-types
```

### Build from source

```bash
pip install .
```

The native extension is required. Wheels are provided for macOS and Linux.

## Quickstart

```python
from tsrkit_types import Uint, U16, String, Bytes, Bits, TypedVector, Dictionary, structure

# Integers
value = Uint(1000)
encoded = value.encode()
decoded = Uint.decode(encoded)

# Fixed-width integer
port = U16(8080)

# Strings and bytes
name = String("alice")
blob = Bytes(b"payload")

# Bits
flags = Bits([True, False, True, True])

# Typed container
VecU16 = TypedVector[U16]
ports = VecU16([U16(80), U16(443)])

# Dictionary with typed keys/values
Config = Dictionary[String, U16]
config = Config({String("port"): U16(8080)})

# Structs
@structure
class Person:
    name: String
    age: U16

p = Person(name=String("bob"), age=U16(42))

# Binary + JSON
binary = p.encode()
json_data = p.to_json()
```

## Type Overview

- **Integers**: `Uint`, `U8`, `U16`, `U32`, `U64`
- **Strings**: `String`
- **Bytes**: `Bytes`, `Bytes16`, `Bytes32`, `Bytes64`, `Bytes128`, `Bytes256`, `Bytes512`, `Bytes1024`, `ByteArray`
- **Bits**: `Bits`
- **Sequences**: `Seq`, `Vector`, `Array`, `TypedVector`, `TypedArray`, `BoundedVector`, `TypedBoundedVector`
- **Dictionary**: `Dictionary`
- **Enums**: `Enum`
- **Structs**: `structure`
- **Choice/Option**: `Choice`, `Option`

## Encoding Notes

- Fixed‑width integers are little‑endian.
- Variable‑length integers use a compact prefix encoding optimized for smaller values.
- Dictionaries encode in sorted key order for determinism.

## Benchmarks

See `benchmark.md` for current results and Python/stdlib baselines. Raw benchmark outputs are written to:

- `benchmarks/out/bench_results.json`
- `benchmarks/out/bench_profiles.json`

## Development

### Tests

```bash
uv run pytest
```

### Linting

```bash
uv run ruff check .
```
