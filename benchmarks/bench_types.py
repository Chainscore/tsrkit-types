#!/usr/bin/env python3
"""
Micro-benchmarks for tsrkit_types init/encode/decode + cProfile summaries.

Usage:
  python benchmarks/bench_types.py
  python benchmarks/bench_types.py --runs 20000 --profile-runs 2000 --op-runs 20000
"""

import argparse
import cProfile
import gc
import json
import os
import pstats
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Type
from array import array

from tsrkit_types import (
    Array,
    Bits,
    Bool,
    Bytes,
    Bytes16,
    Bytes32,
    Bytes64,
    Bytes128,
    Bytes256,
    Bytes512,
    Bytes1024,
    ByteArray,
    Choice,
    Dictionary,
    Enum,
    NullType,
    Option,
    Seq,
    String,
    TypedArray,
    TypedBoundedVector,
    TypedVector,
    U8,
    U16,
    U32,
    U64,
    Uint,
    Vector,
    BoundedVector,
    structure,
)


@dataclass
class Case:
    name: str
    ctor: Optional[Callable[..., Any]]
    init_args: List[Tuple[Tuple[Any, ...], Dict[str, Any]]]
    encode_values: List[Any]
    decode_fn: Optional[Callable[[bytes], Any]]
    decode_buffers: List[bytes]
    encode_fn: Optional[Callable[[Any], bytes]] = None
    json_decode: bool = True
    json_values: Optional[List[Any]] = None
    json_decode_fn: Optional[Callable[[Any], Any]] = None
    json_encode_fn: Optional[Callable[[Any], Any]] = None


def _make_bytes(length: int, seed: int) -> bytes:
    return bytes(((seed + i) & 0xFF) for i in range(length))


def _make_ascii(length: int, seed: int) -> str:
    base = "abcdefghijklmnopqrstuvwxyz0123456789"
    chars = [base[(seed + i) % len(base)] for i in range(length)]
    return "".join(chars)


def _encode_varint_u64_py(value: int) -> bytes:
    if value < 0:
        raise ValueError("Negative value not supported")
    if value < (1 << 7):
        return bytes((value,))
    if value < (1 << 56):
        length = (value.bit_length() - 1) // 7
        prefix_base = 256 - (1 << (8 - length))
        high = value >> (8 * length)
        prefix = prefix_base + high
        remaining = value & ((1 << (8 * length)) - 1)
        return bytes((prefix,)) + remaining.to_bytes(length, "little")
    if value < (1 << 64):
        return b"\xff" + value.to_bytes(8, "little")
    raise ValueError("Value too large for encoding")


def _decode_varint_u64_py(buf: bytes, offset: int = 0) -> Tuple[int, int]:
    tag = buf[offset]
    if tag < (1 << 7):
        return tag, 1
    if tag == 0xFF:
        if len(buf) - offset < 9:
            raise ValueError("Buffer too small to decode 64-bit integer")
        return int.from_bytes(buf[offset + 1 : offset + 9], "little"), 9
    length = 8 - ((tag ^ 0xFF).bit_length())
    if len(buf) - offset < length + 1:
        raise ValueError("Buffer too small to decode varint")
    alpha = tag + (1 << (8 - length)) - 256
    if length == 1:
        beta = buf[offset + 1]
    elif length == 2:
        beta = buf[offset + 1] | (buf[offset + 2] << 8)
    elif length == 3:
        beta = buf[offset + 1] | (buf[offset + 2] << 8) | (buf[offset + 3] << 16)
    elif length == 4:
        beta = (
            buf[offset + 1]
            | (buf[offset + 2] << 8)
            | (buf[offset + 3] << 16)
            | (buf[offset + 4] << 24)
        )
    else:
        beta = int.from_bytes(buf[offset + 1 : offset + 1 + length], "little")
    value = (alpha << (length * 8)) | beta
    return value, length + 1


def _encode_fixed_int_py(value: int, size: int) -> bytes:
    return int(value).to_bytes(size, "little")


def _decode_fixed_int_py(buf: bytes, size: int) -> int:
    return int.from_bytes(buf[:size], "little")


def _encode_bytes_var_py(data: bytes) -> bytes:
    return _encode_varint_u64_py(len(data)) + data


def _decode_bytes_var_py(buf: bytes) -> bytes:
    length, size = _decode_varint_u64_py(buf, 0)
    end = size + length
    if len(buf) < end:
        raise ValueError("Buffer too small to decode bytes")
    return buf[size:end]


def _encode_string_var_py(text: str) -> bytes:
    data = text.encode("utf-8")
    return _encode_varint_u64_py(len(data)) + data


def _decode_string_var_py(buf: bytes) -> str:
    length, size = _decode_varint_u64_py(buf, 0)
    end = size + length
    if len(buf) < end:
        raise ValueError("Buffer too small to decode string")
    return buf[size:end].decode("utf-8")


def _pack_bits_py(bits: List[bool], order: str = "msb") -> bytes:
    bit_len = len(bits)
    byte_count = (bit_len + 7) // 8
    out = bytearray(byte_count)
    idx = 0
    if order == "msb":
        for i in range(byte_count):
            val = 0
            for j in range(8):
                if idx < bit_len and bits[idx]:
                    val |= 1 << (7 - j)
                idx += 1
            out[i] = val
    else:
        for i in range(byte_count):
            val = 0
            for j in range(8):
                if idx < bit_len and bits[idx]:
                    val |= 1 << j
                idx += 1
            out[i] = val
    return bytes(out)


def _unpack_bits_py(data: bytes, bit_len: int, order: str = "msb") -> List[bool]:
    out: List[bool] = []
    for byte in data:
        if order == "msb":
            out.extend(bool((byte >> (7 - i)) & 1) for i in range(8))
        else:
            out.extend(bool((byte >> i) & 1) for i in range(8))
    return out[:bit_len]


def _encode_bits_var_py(bits: List[bool], order: str = "msb") -> bytes:
    packed = _pack_bits_py(bits, order=order)
    return _encode_varint_u64_py(len(bits)) + packed


def _decode_bits_var_py(buf: bytes, order: str = "msb") -> List[bool]:
    bit_len, size = _decode_varint_u64_py(buf, 0)
    byte_count = (bit_len + 7) // 8
    end = size + byte_count
    if len(buf) < end:
        raise ValueError("Buffer too small to decode bits")
    return _unpack_bits_py(buf[size:end], bit_len, order=order)


def _encode_bits_fixed_py(bits: List[bool], order: str = "msb") -> bytes:
    return _pack_bits_py(bits, order=order)


def _decode_bits_fixed_py(buf: bytes, bit_len: int, order: str = "msb") -> List[bool]:
    byte_count = (bit_len + 7) // 8
    if len(buf) < byte_count:
        raise ValueError("Buffer too small to decode bits")
    return _unpack_bits_py(buf[:byte_count], bit_len, order=order)


def _encode_u16_list_py(values: List[int]) -> bytes:
    return b"".join(_encode_fixed_int_py(v, 2) for v in values)


def _decode_u16_list_py(buf: bytes) -> List[int]:
    if len(buf) % 2:
        raise ValueError("Buffer length must be multiple of 2")
    return [int.from_bytes(buf[i : i + 2], "little") for i in range(0, len(buf), 2)]


def _encode_u16_array_py(values: List[int]) -> bytes:
    arr = array("H", values)
    return arr.tobytes()


def _decode_u16_array_py(buf: bytes) -> array:
    arr = array("H")
    arr.frombytes(buf)
    return arr


def _encode_dict_str_u16_py(data: Dict[str, int]) -> bytes:
    out = bytearray()
    out.extend(_encode_varint_u64_py(len(data)))
    for key in sorted(data):
        key_bytes = key.encode("utf-8")
        out.extend(_encode_varint_u64_py(len(key_bytes)))
        out.extend(key_bytes)
        out.extend(_encode_fixed_int_py(data[key], 2))
    return bytes(out)


def _decode_dict_str_u16_py(buf: bytes) -> Dict[str, int]:
    count, size = _decode_varint_u64_py(buf, 0)
    offset = size
    result: Dict[str, int] = {}
    for _ in range(count):
        key_len, inc = _decode_varint_u64_py(buf, offset)
        offset += inc
        key_bytes = buf[offset : offset + key_len]
        offset += key_len
        key = key_bytes.decode("utf-8")
        value = int.from_bytes(buf[offset : offset + 2], "little")
        offset += 2
        result[key] = value
    return result


def _timed_loop(runs: int, fn: Callable[[int], None]) -> float:
    gc.collect()
    gc.disable()
    try:
        start = time.perf_counter()
        for i in range(runs):
            fn(i)
        end = time.perf_counter()
    finally:
        gc.enable()
    return end - start


def _profile_loop(runs: int, fn: Callable[[int], None]) -> pstats.Stats:
    prof = cProfile.Profile()
    prof.enable()
    for i in range(runs):
        fn(i)
    prof.disable()
    stats = pstats.Stats(prof)
    stats.sort_stats("cumulative")
    return stats


def _stats_top(stats: pstats.Stats, limit: int = 8) -> List[Tuple[str, float, int]]:
    rows = []
    for func, stat in list(stats.stats.items()):
        cc, nc, tt, ct, callers = stat
        rows.append((func, ct, nc))
    rows.sort(key=lambda x: x[1], reverse=True)
    top = []
    for func, ct, nc in rows[:limit]:
        func_name = "%s:%d(%s)" % (func[0], func[1], func[2])
        top.append((func_name, ct, nc))
    return top


def _bench_container_ops(runs: int) -> Dict[str, float]:
    ops: Dict[str, float] = {}

    def run(name: str, factory: Callable[[], Any], op: Callable[[Any], None]) -> None:
        def _loop(_: int) -> None:
            obj = factory()
            op(obj)
        ops[name] = _timed_loop(runs, _loop)

    # Typed vector ops
    vec_cls = TypedVector[U16]
    run(
        "typed_vector_append",
        lambda: vec_cls([U16(1), U16(2), U16(3)]),
        lambda v: v.append(U16(4)),
    )
    run(
        "typed_vector_extend",
        lambda: vec_cls([U16(1), U16(2), U16(3)]),
        lambda v: v.extend([U16(4), U16(5)]),
    )
    run(
        "typed_vector_insert",
        lambda: vec_cls([U16(1), U16(2), U16(3)]),
        lambda v: v.insert(0, U16(9)),
    )
    run(
        "typed_vector_setitem",
        lambda: vec_cls([U16(1), U16(2), U16(3)]),
        lambda v: v.__setitem__(1, U16(9)),
    )
    run(
        "typed_vector_pop",
        lambda: vec_cls([U16(1), U16(2), U16(3)]),
        lambda v: v.pop(),
    )

    # Dictionary ops
    dict_cls = Dictionary[String, U16]
    run(
        "dictionary_setitem",
        lambda: dict_cls({String("a"): U16(1), String("b"): U16(2)}),
        lambda d: d.__setitem__(String("c"), U16(3)),
    )
    run(
        "dictionary_pop",
        lambda: dict_cls({String("a"): U16(1), String("b"): U16(2)}),
        lambda d: d.pop(String("a")),
    )

    # ByteArray ops
    run(
        "bytearray_append",
        lambda: ByteArray(b"abcd"),
        lambda b: b.append(0xEE),
    )
    run(
        "bytearray_extend",
        lambda: ByteArray(b"abcd"),
        lambda b: b.extend(b"efgh"),
    )

    # Bits ops
    run(
        "bits_append",
        lambda: Bits([True, False, True, False]),
        lambda b: b.append(True),
    )
    run(
        "bits_extend",
        lambda: Bits([True, False, True, False]),
        lambda b: b.extend([False, True]),
    )

    # Native Python container ops
    run(
        "py_list_append",
        lambda: [1, 2, 3],
        lambda v: v.append(4),
    )
    run(
        "py_list_extend",
        lambda: [1, 2, 3],
        lambda v: v.extend([4, 5]),
    )
    run(
        "py_list_insert",
        lambda: [1, 2, 3],
        lambda v: v.insert(0, 9),
    )
    run(
        "py_list_setitem",
        lambda: [1, 2, 3],
        lambda v: v.__setitem__(1, 9),
    )
    run(
        "py_list_pop",
        lambda: [1, 2, 3],
        lambda v: v.pop(),
    )
    run(
        "py_dict_setitem",
        lambda: {"a": 1, "b": 2},
        lambda d: d.__setitem__("c", 3),
    )
    run(
        "py_dict_pop",
        lambda: {"a": 1, "b": 2},
        lambda d: d.pop("a"),
    )
    run(
        "py_bytearray_append",
        lambda: bytearray(b"abcd"),
        lambda b: b.append(0xEE),
    )
    run(
        "py_bytearray_extend",
        lambda: bytearray(b"abcd"),
        lambda b: b.extend(b"efgh"),
    )
    run(
        "py_bits_list_append",
        lambda: [True, False, True, False],
        lambda b: b.append(True),
    )
    run(
        "py_bits_list_extend",
        lambda: [True, False, True, False],
        lambda b: b.extend([False, True]),
    )

    return ops


def _encode_buffers(values: Iterable[Any]) -> List[bytes]:
    return [v.encode() for v in values]


def _args_from_values(values: Iterable[Any]) -> List[Tuple[Tuple[Any, ...], Dict[str, Any]]]:
    return [((v,), {}) for v in values]


def _decode_via_decode(cls: Type[Any]) -> Callable[[bytes], Any]:
    def _fn(buf: bytes, _cls: Type[Any] = cls) -> Any:
        return _cls.decode(buf)
    return _fn


def _decode_via_decode_from(cls: Type[Any]) -> Callable[[bytes], Any]:
    def _fn(buf: bytes, _cls: Type[Any] = cls) -> Any:
        return _cls.decode_from(buf)[0]
    return _fn


def _build_cases() -> List[Case]:
    cases: List[Case] = []

    uint_vals = [1, 127, 128, 1000, 2**32]
    u8_vals = [1, 42, 255]
    u16_vals = [1, 12345, 65535]
    u32_vals = [1, 123456789, 2**32 - 1]
    u64_vals = [1, 1234567890123, 2**40]

    cases.append(
        Case(
            name="Uint",
            ctor=Uint,
            init_args=_args_from_values(uint_vals),
            encode_values=[Uint(v) for v in uint_vals],
            decode_fn=_decode_via_decode(Uint),
            decode_buffers=_encode_buffers([Uint(v) for v in uint_vals]),
        )
    )
    cases.append(
        Case(
            name="U8",
            ctor=U8,
            init_args=_args_from_values(u8_vals),
            encode_values=[U8(v) for v in u8_vals],
            decode_fn=_decode_via_decode(U8),
            decode_buffers=_encode_buffers([U8(v) for v in u8_vals]),
        )
    )
    cases.append(
        Case(
            name="U16",
            ctor=U16,
            init_args=_args_from_values(u16_vals),
            encode_values=[U16(v) for v in u16_vals],
            decode_fn=_decode_via_decode(U16),
            decode_buffers=_encode_buffers([U16(v) for v in u16_vals]),
        )
    )
    cases.append(
        Case(
            name="U32",
            ctor=U32,
            init_args=_args_from_values(u32_vals),
            encode_values=[U32(v) for v in u32_vals],
            decode_fn=_decode_via_decode(U32),
            decode_buffers=_encode_buffers([U32(v) for v in u32_vals]),
        )
    )
    cases.append(
        Case(
            name="U64",
            ctor=U64,
            init_args=_args_from_values(u64_vals),
            encode_values=[U64(v) for v in u64_vals],
            decode_fn=_decode_via_decode(U64),
            decode_buffers=_encode_buffers([U64(v) for v in u64_vals]),
        )
    )

    str_vals = [
        _make_ascii(5, 1),
        _make_ascii(16, 2),
        _make_ascii(64, 3),
    ]
    cases.append(
        Case(
            name="String",
            ctor=String,
            init_args=_args_from_values(str_vals),
            encode_values=[String(v) for v in str_vals],
            decode_fn=_decode_via_decode(String),
            decode_buffers=_encode_buffers([String(v) for v in str_vals]),
        )
    )

    bool_vals = [True, False]
    cases.append(
        Case(
            name="Bool",
            ctor=Bool,
            init_args=_args_from_values(bool_vals),
            encode_values=[Bool(v) for v in bool_vals],
            decode_fn=_decode_via_decode(Bool),
            decode_buffers=_encode_buffers([Bool(v) for v in bool_vals]),
        )
    )

    cases.append(
        Case(
            name="NullType",
            ctor=NullType,
            init_args=[((), {})],
            encode_values=[NullType()],
            decode_fn=_decode_via_decode(NullType),
            decode_buffers=[NullType().encode()],
        )
    )

    bytes_variants = [_make_bytes(64, i) for i in range(2048)]
    bytes_vals = [Bytes(b) for b in bytes_variants]
    cases.append(
        Case(
            name="Bytes(var,64B)",
            ctor=Bytes,
            init_args=_args_from_values(bytes_variants),
            encode_values=bytes_vals,
            decode_fn=_decode_via_decode_from(Bytes),
            decode_buffers=_encode_buffers(bytes_vals),
        )
    )

    fixed16_vals = [Bytes16(_make_bytes(16, i)) for i in range(512)]
    cases.append(
        Case(
            name="Bytes16",
            ctor=Bytes16,
            init_args=_args_from_values([_make_bytes(16, i) for i in range(512)]),
            encode_values=fixed16_vals,
            decode_fn=_decode_via_decode_from(Bytes16),
            decode_buffers=_encode_buffers(fixed16_vals),
        )
    )

    fixed32_vals = [Bytes32(_make_bytes(32, i)) for i in range(512)]
    cases.append(
        Case(
            name="Bytes32",
            ctor=Bytes32,
            init_args=_args_from_values([_make_bytes(32, i) for i in range(512)]),
            encode_values=fixed32_vals,
            decode_fn=_decode_via_decode_from(Bytes32),
            decode_buffers=_encode_buffers(fixed32_vals),
        )
    )

    fixed64_vals = [Bytes64(_make_bytes(64, i)) for i in range(512)]
    cases.append(
        Case(
            name="Bytes64",
            ctor=Bytes64,
            init_args=_args_from_values([_make_bytes(64, i) for i in range(512)]),
            encode_values=fixed64_vals,
            decode_fn=_decode_via_decode_from(Bytes64),
            decode_buffers=_encode_buffers(fixed64_vals),
        )
    )

    fixed128_vals = [Bytes128(_make_bytes(128, i)) for i in range(256)]
    cases.append(
        Case(
            name="Bytes128",
            ctor=Bytes128,
            init_args=_args_from_values([_make_bytes(128, i) for i in range(256)]),
            encode_values=fixed128_vals,
            decode_fn=_decode_via_decode_from(Bytes128),
            decode_buffers=_encode_buffers(fixed128_vals),
        )
    )

    fixed256_vals = [Bytes256(_make_bytes(256, i)) for i in range(128)]
    cases.append(
        Case(
            name="Bytes256",
            ctor=Bytes256,
            init_args=_args_from_values([_make_bytes(256, i) for i in range(128)]),
            encode_values=fixed256_vals,
            decode_fn=_decode_via_decode_from(Bytes256),
            decode_buffers=_encode_buffers(fixed256_vals),
        )
    )

    fixed512_vals = [Bytes512(_make_bytes(512, i)) for i in range(64)]
    cases.append(
        Case(
            name="Bytes512",
            ctor=Bytes512,
            init_args=_args_from_values([_make_bytes(512, i) for i in range(64)]),
            encode_values=fixed512_vals,
            decode_fn=_decode_via_decode_from(Bytes512),
            decode_buffers=_encode_buffers(fixed512_vals),
        )
    )

    fixed1024_vals = [Bytes1024(_make_bytes(1024, i)) for i in range(32)]
    cases.append(
        Case(
            name="Bytes1024",
            ctor=Bytes1024,
            init_args=_args_from_values([_make_bytes(1024, i) for i in range(32)]),
            encode_values=fixed1024_vals,
            decode_fn=_decode_via_decode_from(Bytes1024),
            decode_buffers=_encode_buffers(fixed1024_vals),
        )
    )

    ba_vals = [ByteArray(_make_bytes(64, i)) for i in range(512)]
    cases.append(
        Case(
            name="ByteArray",
            ctor=ByteArray,
            init_args=_args_from_values([_make_bytes(64, i) for i in range(512)]),
            encode_values=ba_vals,
            decode_fn=_decode_via_decode_from(ByteArray),
            decode_buffers=_encode_buffers(ba_vals),
        )
    )

    bits_list = [[bool((i + j) & 1) for j in range(64)] for i in range(128)]
    bits_vals = [Bits(b) for b in bits_list]
    cases.append(
        Case(
            name="Bits(var,64b)",
            ctor=Bits,
            init_args=_args_from_values(bits_list),
            encode_values=bits_vals,
            decode_fn=_decode_via_decode(Bits),
            decode_buffers=_encode_buffers(bits_vals),
        )
    )

    bits_fixed_cls = Bits[64, "msb"]
    bits_fixed_vals = [bits_fixed_cls(b) for b in bits_list]
    cases.append(
        Case(
            name="Bits[64,msb]",
            ctor=bits_fixed_cls,
            init_args=_args_from_values(bits_list),
            encode_values=bits_fixed_vals,
            decode_fn=_decode_via_decode(bits_fixed_cls),
            decode_buffers=_encode_buffers(bits_fixed_vals),
        )
    )

    # Sequence types
    u16_items = [U16(i) for i in range(10)]

    seq_cls = Seq[U16, 10]
    cases.append(
        Case(
            name="Seq[U16,N=10]",
            ctor=seq_cls,
            init_args=[((u16_items,), {})],
            encode_values=[seq_cls(u16_items)],
            decode_fn=_decode_via_decode(seq_cls),
            decode_buffers=_encode_buffers([seq_cls(u16_items)]),
        )
    )

    vec_cls = Vector[U16]
    cases.append(
        Case(
            name="Vector[U16]",
            ctor=vec_cls,
            init_args=[((u16_items,), {})],
            encode_values=[vec_cls(u16_items)],
            decode_fn=_decode_via_decode(vec_cls),
            decode_buffers=_encode_buffers([vec_cls(u16_items)]),
        )
    )

    arr_cls = Array[10]
    # Array does not enforce element types by default; set for decode benchmark.
    arr_cls._element_type = U16
    cases.append(
        Case(
            name="Array[10]",
            ctor=arr_cls,
            init_args=[((u16_items,), {})],
            encode_values=[arr_cls(u16_items)],
            decode_fn=_decode_via_decode(arr_cls),
            decode_buffers=_encode_buffers([arr_cls(u16_items)]),
        )
    )

    tvec_cls = TypedVector[U16]
    cases.append(
        Case(
            name="TypedVector[U16]",
            ctor=tvec_cls,
            init_args=[((u16_items,), {})],
            encode_values=[tvec_cls(u16_items)],
            decode_fn=_decode_via_decode(tvec_cls),
            decode_buffers=_encode_buffers([tvec_cls(u16_items)]),
        )
    )

    tarr_cls = TypedArray[U16, 10]
    cases.append(
        Case(
            name="TypedArray[U16,10]",
            ctor=tarr_cls,
            init_args=[((u16_items,), {})],
            encode_values=[tarr_cls(u16_items)],
            decode_fn=_decode_via_decode(tarr_cls),
            decode_buffers=_encode_buffers([tarr_cls(u16_items)]),
        )
    )

    bvec_cls = BoundedVector[0, 10]
    # BoundedVector lacks element type unless provided; set for decode benchmark.
    bvec_cls._element_type = U16
    cases.append(
        Case(
            name="BoundedVector[0,10]",
            ctor=bvec_cls,
            init_args=[((u16_items,), {})],
            encode_values=[bvec_cls(u16_items)],
            decode_fn=_decode_via_decode(bvec_cls),
            decode_buffers=_encode_buffers([bvec_cls(u16_items)]),
        )
    )

    tbvec_cls = TypedBoundedVector[U16, 0, 10]
    cases.append(
        Case(
            name="TypedBoundedVector[U16,0,10]",
            ctor=tbvec_cls,
            init_args=[((u16_items,), {})],
            encode_values=[tbvec_cls(u16_items)],
            decode_fn=_decode_via_decode(tbvec_cls),
            decode_buffers=_encode_buffers([tbvec_cls(u16_items)]),
        )
    )

    # Dictionary
    dict_cls = Dictionary[String, U16]
    dict_val = dict_cls({String(f"k{i}"): U16(i) for i in range(10)})
    cases.append(
        Case(
            name="Dictionary[String,U16]",
            ctor=dict_cls,
            init_args=[(({String(f'k{i}'): U16(i) for i in range(10)},), {})],
            encode_values=[dict_val],
            decode_fn=_decode_via_decode(dict_cls),
            decode_buffers=_encode_buffers([dict_val]),
        )
    )

    # Choice / Option
    choice_cls = Choice[U8, String]
    choice_vals = [U8(42), String("hello")]
    cases.append(
        Case(
            name="Choice[U8,String]",
            ctor=choice_cls,
            init_args=[((choice_vals[0],), {}), ((choice_vals[1],), {})],
            encode_values=[choice_cls(choice_vals[0]), choice_cls(choice_vals[1])],
            decode_fn=_decode_via_decode(choice_cls),
            decode_buffers=_encode_buffers([choice_cls(choice_vals[0]), choice_cls(choice_vals[1])]),
            json_decode=False,
        )
    )

    opt_cls = Option[U16]
    opt_val = U16(12345)
    cases.append(
        Case(
            name="Option[U16]",
            ctor=opt_cls,
            init_args=[((opt_val,), {}), ((), {})],
            encode_values=[opt_cls(opt_val), opt_cls()],
            decode_fn=_decode_via_decode(opt_cls),
            decode_buffers=_encode_buffers([opt_cls(opt_val), opt_cls()]),
        )
    )

    # Enum
    class Color(Enum):
        RED = 1
        GREEN = 2
        BLUE = 3

    cases.append(
        Case(
            name="Enum(Color)",
            ctor=Color,
            init_args=[((1,), {}), ((2,), {}), ((3,), {})],
            encode_values=[Color.RED, Color.GREEN, Color.BLUE],
            decode_fn=_decode_via_decode(Color),
            decode_buffers=_encode_buffers([Color.RED, Color.GREEN, Color.BLUE]),
        )
    )

    # Structure
    @structure
    class Person:
        name: String
        age: U8
        score: U16

    person_vals = [
        Person(name=String("alice"), age=U8(30), score=U16(900)),
        Person(name=String("bob"), age=U8(22), score=U16(450)),
    ]
    cases.append(
        Case(
            name="structure(Person)",
            ctor=Person,
            init_args=[
                ((String("alice"), U8(30), U16(900)), {}),
                ((String("bob"), U8(22), U16(450)), {}),
            ],
            encode_values=person_vals,
            decode_fn=_decode_via_decode(Person),
            decode_buffers=_encode_buffers(person_vals),
        )
    )

    # -------------------------------------------------------------------------- #
    # Native Python baselines (stdlib / CPython)
    # -------------------------------------------------------------------------- #
    cases.append(
        Case(
            name="PyInt(varint)",
            ctor=int,
            init_args=_args_from_values(uint_vals),
            encode_values=[int(v) for v in uint_vals],
            encode_fn=_encode_varint_u64_py,
            decode_fn=lambda b: _decode_varint_u64_py(b, 0)[0],
            decode_buffers=[_encode_varint_u64_py(v) for v in uint_vals],
        )
    )
    cases.append(
        Case(
            name="PyU8(to_bytes)",
            ctor=int,
            init_args=_args_from_values(u8_vals),
            encode_values=[int(v) for v in u8_vals],
            encode_fn=lambda v: _encode_fixed_int_py(v, 1),
            decode_fn=lambda b: _decode_fixed_int_py(b, 1),
            decode_buffers=[_encode_fixed_int_py(v, 1) for v in u8_vals],
        )
    )
    cases.append(
        Case(
            name="PyU16(to_bytes)",
            ctor=int,
            init_args=_args_from_values(u16_vals),
            encode_values=[int(v) for v in u16_vals],
            encode_fn=lambda v: _encode_fixed_int_py(v, 2),
            decode_fn=lambda b: _decode_fixed_int_py(b, 2),
            decode_buffers=[_encode_fixed_int_py(v, 2) for v in u16_vals],
        )
    )
    cases.append(
        Case(
            name="PyU32(to_bytes)",
            ctor=int,
            init_args=_args_from_values(u32_vals),
            encode_values=[int(v) for v in u32_vals],
            encode_fn=lambda v: _encode_fixed_int_py(v, 4),
            decode_fn=lambda b: _decode_fixed_int_py(b, 4),
            decode_buffers=[_encode_fixed_int_py(v, 4) for v in u32_vals],
        )
    )
    cases.append(
        Case(
            name="PyU64(to_bytes)",
            ctor=int,
            init_args=_args_from_values(u64_vals),
            encode_values=[int(v) for v in u64_vals],
            encode_fn=lambda v: _encode_fixed_int_py(v, 8),
            decode_fn=lambda b: _decode_fixed_int_py(b, 8),
            decode_buffers=[_encode_fixed_int_py(v, 8) for v in u64_vals],
        )
    )

    cases.append(
        Case(
            name="PyString(var)",
            ctor=str,
            init_args=_args_from_values(str_vals),
            encode_values=[str(v) for v in str_vals],
            encode_fn=_encode_string_var_py,
            decode_fn=_decode_string_var_py,
            decode_buffers=[_encode_string_var_py(v) for v in str_vals],
        )
    )

    py_bytes_vals = [_make_bytes(64, i) for i in range(2048)]
    cases.append(
        Case(
            name="PyBytes(var,64B)",
            ctor=bytes,
            init_args=_args_from_values(py_bytes_vals),
            encode_values=[bytes(v) for v in py_bytes_vals],
            encode_fn=_encode_bytes_var_py,
            decode_fn=_decode_bytes_var_py,
            decode_buffers=[_encode_bytes_var_py(v) for v in py_bytes_vals],
        )
    )
    cases.append(
        Case(
            name="PyBytes16",
            ctor=bytes,
            init_args=_args_from_values([_make_bytes(16, i) for i in range(512)]),
            encode_values=[_make_bytes(16, i) for i in range(512)],
            encode_fn=lambda v: bytes(v),
            decode_fn=lambda b: b[:16],
            decode_buffers=[_make_bytes(16, i) for i in range(512)],
        )
    )
    cases.append(
        Case(
            name="PyBytes32",
            ctor=bytes,
            init_args=_args_from_values([_make_bytes(32, i) for i in range(512)]),
            encode_values=[_make_bytes(32, i) for i in range(512)],
            encode_fn=lambda v: bytes(v),
            decode_fn=lambda b: b[:32],
            decode_buffers=[_make_bytes(32, i) for i in range(512)],
        )
    )
    cases.append(
        Case(
            name="PyBytes64",
            ctor=bytes,
            init_args=_args_from_values([_make_bytes(64, i) for i in range(512)]),
            encode_values=[_make_bytes(64, i) for i in range(512)],
            encode_fn=lambda v: bytes(v),
            decode_fn=lambda b: b[:64],
            decode_buffers=[_make_bytes(64, i) for i in range(512)],
        )
    )
    cases.append(
        Case(
            name="PyBytes128",
            ctor=bytes,
            init_args=_args_from_values([_make_bytes(128, i) for i in range(256)]),
            encode_values=[_make_bytes(128, i) for i in range(256)],
            encode_fn=lambda v: bytes(v),
            decode_fn=lambda b: b[:128],
            decode_buffers=[_make_bytes(128, i) for i in range(256)],
        )
    )
    cases.append(
        Case(
            name="PyBytes256",
            ctor=bytes,
            init_args=_args_from_values([_make_bytes(256, i) for i in range(128)]),
            encode_values=[_make_bytes(256, i) for i in range(128)],
            encode_fn=lambda v: bytes(v),
            decode_fn=lambda b: b[:256],
            decode_buffers=[_make_bytes(256, i) for i in range(128)],
        )
    )
    cases.append(
        Case(
            name="PyBytes512",
            ctor=bytes,
            init_args=_args_from_values([_make_bytes(512, i) for i in range(64)]),
            encode_values=[_make_bytes(512, i) for i in range(64)],
            encode_fn=lambda v: bytes(v),
            decode_fn=lambda b: b[:512],
            decode_buffers=[_make_bytes(512, i) for i in range(64)],
        )
    )
    cases.append(
        Case(
            name="PyBytes1024",
            ctor=bytes,
            init_args=_args_from_values([_make_bytes(1024, i) for i in range(32)]),
            encode_values=[_make_bytes(1024, i) for i in range(32)],
            encode_fn=lambda v: bytes(v),
            decode_fn=lambda b: b[:1024],
            decode_buffers=[_make_bytes(1024, i) for i in range(32)],
        )
    )

    py_ba_vals = [_make_bytes(64, i) for i in range(512)]
    cases.append(
        Case(
            name="PyByteArray(var,64B)",
            ctor=bytearray,
            init_args=_args_from_values(py_ba_vals),
            encode_values=[bytearray(v) for v in py_ba_vals],
            encode_fn=lambda v: _encode_bytes_var_py(bytes(v)),
            decode_fn=_decode_bytes_var_py,
            decode_buffers=[_encode_bytes_var_py(v) for v in py_ba_vals],
        )
    )

    py_bits_list = [[bool((i + j) & 1) for j in range(64)] for i in range(128)]
    cases.append(
        Case(
            name="PyBits(var,64b)",
            ctor=list,
            init_args=_args_from_values(py_bits_list),
            encode_values=[list(b) for b in py_bits_list],
            encode_fn=_encode_bits_var_py,
            decode_fn=lambda b: _decode_bits_var_py(b, "msb"),
            decode_buffers=[_encode_bits_var_py(b) for b in py_bits_list],
        )
    )
    cases.append(
        Case(
            name="PyBits[64,msb]",
            ctor=list,
            init_args=_args_from_values(py_bits_list),
            encode_values=[list(b) for b in py_bits_list],
            encode_fn=_encode_bits_fixed_py,
            decode_fn=lambda b: _decode_bits_fixed_py(b, 64, "msb"),
            decode_buffers=[_encode_bits_fixed_py(b) for b in py_bits_list],
        )
    )

    py_u16_list = [int(v) for v in range(10)]
    cases.append(
        Case(
            name="PyList[U16,N=10]",
            ctor=list,
            init_args=[((py_u16_list,), {})],
            encode_values=[list(py_u16_list)],
            encode_fn=_encode_u16_list_py,
            decode_fn=_decode_u16_list_py,
            decode_buffers=[_encode_u16_list_py(py_u16_list)],
        )
    )
    cases.append(
        Case(
            name="PyArray('H',10)",
            ctor=array,
            init_args=[(("H", py_u16_list), {})],
            encode_values=[py_u16_list],
            encode_fn=_encode_u16_array_py,
            decode_fn=_decode_u16_array_py,
            decode_buffers=[_encode_u16_array_py(py_u16_list)],
        )
    )

    py_dict_val = {f"k{i}": i for i in range(10)}
    cases.append(
        Case(
            name="PyDict[str,U16]",
            ctor=dict,
            init_args=[((py_dict_val,), {})],
            encode_values=[dict(py_dict_val)],
            encode_fn=_encode_dict_str_u16_py,
            decode_fn=_decode_dict_str_u16_py,
            decode_buffers=[_encode_dict_str_u16_py(py_dict_val)],
        )
    )

    return cases


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=20000)
    parser.add_argument("--profile-runs", type=int, default=2000)
    parser.add_argument("--op-runs", type=int, default=20000)
    parser.add_argument("--profile", action="store_true", default=True)
    parser.add_argument("--no-profile", action="store_false", dest="profile")
    parser.add_argument("--output-dir", default=os.path.join("benchmarks", "out"))
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    cases = _build_cases()
    results: Dict[str, Dict[str, float]] = {}
    profiles: Dict[str, Dict[str, List[Tuple[str, float, int]]]] = {}

    for case in cases:
        results[case.name] = {}

        if case.ctor and case.init_args:
            args_list = case.init_args
            n = len(args_list)

            def _init_loop(i: int) -> None:
                args_i, kwargs_i = args_list[i % n]
                case.ctor(*args_i, **kwargs_i)

            init_seconds = _timed_loop(args.runs, _init_loop)
            results[case.name]["init_s"] = init_seconds

            if args.profile:
                stats = _profile_loop(args.profile_runs, _init_loop)
                profiles.setdefault(case.name, {})["init"] = _stats_top(stats)

        if case.encode_values:
            vals = case.encode_values
            n = len(vals)
            encode_fn = case.encode_fn

            def _encode_loop(i: int) -> None:
                v = vals[i % n]
                if encode_fn is None:
                    v.encode()
                else:
                    encode_fn(v)

            encode_seconds = _timed_loop(args.runs, _encode_loop)
            results[case.name]["encode_s"] = encode_seconds

            if args.profile:
                stats = _profile_loop(args.profile_runs, _encode_loop)
                profiles.setdefault(case.name, {})["encode"] = _stats_top(stats)

        if case.decode_fn and case.decode_buffers:
            bufs = case.decode_buffers
            n = len(bufs)

            def _decode_loop(i: int) -> None:
                case.decode_fn(bufs[i % n])

            decode_seconds = _timed_loop(args.runs, _decode_loop)
            results[case.name]["decode_s"] = decode_seconds

            if args.profile:
                stats = _profile_loop(args.profile_runs, _decode_loop)
                profiles.setdefault(case.name, {})["decode"] = _stats_top(stats)

        if case.encode_values and case.ctor:
            vals = case.encode_values
            n = len(vals)
            if case.json_encode_fn is not None:
                json_vals = case.json_values or [case.json_encode_fn(v) for v in vals]

                def _json_encode_loop(i: int) -> None:
                    case.json_encode_fn(vals[i % n])
            elif hasattr(vals[0], "to_json"):
                json_vals = case.json_values or [v.to_json() for v in vals]

                def _json_encode_loop(i: int) -> None:
                    vals[i % n].to_json()
            else:
                json_vals = None
            if json_vals is not None:
                json_encode_seconds = _timed_loop(args.runs, _json_encode_loop)
                results[case.name]["json_encode_s"] = json_encode_seconds

                if args.profile:
                    stats = _profile_loop(args.profile_runs, _json_encode_loop)
                    profiles.setdefault(case.name, {})["json_encode"] = _stats_top(stats)

                json_decode_fn = case.json_decode_fn
                if json_decode_fn is None and case.json_decode and hasattr(case.ctor, "from_json"):
                    json_decode_fn = case.ctor.from_json

                if case.json_decode and json_decode_fn is not None:
                    def _json_decode_loop(i: int) -> None:
                        json_decode_fn(json_vals[i % n])

                    json_decode_seconds = _timed_loop(args.runs, _json_decode_loop)
                    results[case.name]["json_decode_s"] = json_decode_seconds

                    if args.profile:
                        stats = _profile_loop(args.profile_runs, _json_decode_loop)
                        profiles.setdefault(case.name, {})["json_decode"] = _stats_top(stats)

    container_ops = _bench_container_ops(args.op_runs)

    # Write results to disk
    results_path = os.path.join(args.output_dir, "bench_results.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "runs": args.runs,
                "profile_runs": args.profile_runs,
                "op_runs": args.op_runs,
                "results": results,
                "container_ops": container_ops,
            },
            f,
            indent=2,
            sort_keys=True,
        )

    if args.profile:
        profile_path = os.path.join(args.output_dir, "bench_profiles.json")
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "runs": args.profile_runs,
                    "profiles": profiles,
                },
                f,
                indent=2,
                sort_keys=True,
            )

    # Print a compact summary table to stdout
    print("Benchmark results (seconds for %d runs):" % args.runs)
    print("name, init_s, encode_s, decode_s, json_encode_s, json_decode_s")
    for name, vals in results.items():
        init_s = vals.get("init_s", 0.0)
        enc_s = vals.get("encode_s", 0.0)
        dec_s = vals.get("decode_s", 0.0)
        json_enc_s = vals.get("json_encode_s", 0.0)
        json_dec_s = vals.get("json_decode_s", 0.0)
        print("%s, %.6f, %.6f, %.6f, %.6f, %.6f" % (name, init_s, enc_s, dec_s, json_enc_s, json_dec_s))

    print("Container ops (seconds for %d runs):" % args.op_runs)
    for name, secs in container_ops.items():
        print("%s, %.6f" % (name, secs))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
