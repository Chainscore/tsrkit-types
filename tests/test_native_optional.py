import pytest

_native = pytest.importorskip("tsrkit_types._native")

from tsrkit_types import Uint, U16, TypedArray


def test_native_uint_roundtrip():
    values = [0, 1, 127, 128, 255, 1000, 2**32]
    for value in values:
        encoded = _native.uint_encode(value, 0, False)
        assert encoded == Uint(value).encode()
        decoded, size = _native.uint_decode(encoded, 0, 0, False)
        assert decoded == value
        assert size == len(encoded)


def test_native_uint_fixed_roundtrip():
    value = 500
    encoded = _native.uint_encode(value, 2, False)
    assert encoded == U16(value).encode()
    decoded, size = _native.uint_decode(encoded, 0, 2, False)
    assert decoded == value
    assert size == 2


def test_native_bits_pack_unpack():
    bits = [True, False, True, False, True, False, True, False, True]
    packed = _native.pack_bits(bits, len(bits), "msb")
    unpacked = _native.unpack_bits(packed, len(bits), "msb")
    assert unpacked == bits


def test_native_fixed_array_roundtrip():
    arr_cls = TypedArray[U16, 4]
    values = [U16(1), U16(2), U16(3), U16(4)]
    encoded = _native.encode_fixed_array(values, U16.byte_size)
    assert encoded == arr_cls(values).encode()

    items, size = _native.decode_fixed_array(encoded, 0, 4, U16.byte_size, U16)
    assert size == 4 * U16.byte_size
    assert [int(x) for x in items] == [1, 2, 3, 4]
    assert all(isinstance(x, U16) for x in items)
