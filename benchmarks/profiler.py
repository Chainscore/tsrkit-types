import argparse
import cProfile
import pstats
from typing import Callable, Any

from tsrkit_types import (
    U8, U16, U32, U64, Uint,
    Bytes, Bytes32, ByteArray,
    Bits, String, Dictionary,
    TypedVector, Option,
)


def profile_operation(name: str, fn: Callable, runs: int):
    """Profile a specific operation with detailed breakdown."""
    print(f"\n{'='*70}")
    print(f"{name} ({runs} runs)")
    print('='*70)

    profiler = cProfile.Profile()
    profiler.enable()
    for _ in range(runs):
        fn()
    profiler.disable()

    stats = pstats.Stats(profiler)
    stats.strip_dirs()
    stats.sort_stats('cumulative')

    print("\nTop functions by cumulative time:")
    stats.print_stats(20)

    print("\nTop functions by total time:")
    stats.sort_stats('tottime')
    stats.print_stats(20)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=10000)
    parser.add_argument("--type", choices=["int", "uint", "bytes", "bits", "seq", "dict", "option", "all"],
                        default="all", help="Which type to profile")
    args = parser.parse_args()

    # Profile integers
    if args.type in ["int", "all"]:
        u8 = U8(42)
        profile_operation("U8.encode()", lambda: u8.encode(), args.runs)

        u64 = U64(1234567890)
        profile_operation("U64.encode()", lambda: u64.encode(), args.runs)

        buf = u8.encode()
        profile_operation("U8.decode()", lambda: U8.decode(buf), args.runs)

    # Profile Uint
    if args.type in ["uint", "all"]:
        small = Uint(127)
        profile_operation("Uint(127).encode()", lambda: small.encode(), args.runs)

        medium = Uint(10000)
        profile_operation("Uint(10000).encode()", lambda: medium.encode(), args.runs)

        large = Uint(2**32)
        profile_operation("Uint(2^32).encode()", lambda: large.encode(), args.runs)

        buf = medium.encode()
        profile_operation("Uint(10000).decode()", lambda: Uint.decode(buf), args.runs)

    # Profile bytes
    if args.type in ["bytes", "all"]:
        b32 = Bytes32(b"x" * 32)
        profile_operation("Bytes32.encode()", lambda: b32.encode(), args.runs)

        bvar = Bytes(b"x" * 64)
        profile_operation("Bytes(64B).encode()", lambda: bvar.encode(), args.runs)

        buf = b32.encode()
        profile_operation("Bytes32.decode()", lambda: Bytes32.decode(buf), args.runs)

    # Profile bits
    if args.type in ["bits", "all"]:
        bits_cls = Bits[64, "msb"]
        bits = bits_cls([True, False] * 32)
        profile_operation("Bits[64,msb].encode()", lambda: bits.encode(), args.runs)

        buf = bits.encode()
        profile_operation("Bits[64,msb].decode()", lambda: bits_cls.decode(buf), args.runs)

    # Profile sequences
    if args.type in ["seq", "all"]:
        vec_cls = TypedVector[U16]
        vec = vec_cls([U16(i) for i in range(10)])
        profile_operation("TypedVector[U16](10).encode()", lambda: vec.encode(), args.runs // 10)

        buf = vec.encode()
        profile_operation("TypedVector[U16](10).decode()", lambda: vec_cls.decode(buf), args.runs // 10)

    # Profile dictionary
    if args.type in ["dict", "all"]:
        dict_cls = Dictionary[String, U16]
        d = dict_cls({String(f"k{i}"): U16(i) for i in range(10)})
        profile_operation("Dictionary[String,U16](10).encode()", lambda: d.encode(), args.runs // 10)

        buf = d.encode()
        profile_operation("Dictionary[String,U16](10).decode()", lambda: dict_cls.decode(buf), args.runs // 10)

    # Profile Option (checking for regression)
    if args.type in ["option", "all"]:
        opt_cls = Option[U16]
        opt_some = opt_cls(U16(12345))
        profile_operation("Option[U16](Some).encode()", lambda: opt_some.encode(), args.runs)

        opt_none = opt_cls()
        profile_operation("Option[U16](None).encode()", lambda: opt_none.encode(), args.runs)


if __name__ == "__main__":
    main()
