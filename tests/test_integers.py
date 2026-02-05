import pytest
from dataclasses import dataclass
from tsrkit_types.integers import Uint


class TestIntegerTypes:
    """Test integer type creation and basic operations."""

    @pytest.mark.parametrize("bit_size,value,expected_bytes", [
        (8, 28, 1),
        (8, 100, 1),
        (8, 255, 1),
        (16, 8080, 2),
        (16, 65535, 2),
        (32, 123456789, 4),
        (32, 4294967295, 4),
        (64, 1703001234567, 8),
        (64, 18446744073709551615, 8),
    ])
    def test_fixed_size_integers(self, bit_size, value, expected_bytes):
        """Test fixed-size integer types with various bit sizes."""
        IntType = Uint[bit_size]
        num = IntType(value)

        assert num == value
        assert num.byte_size == expected_bytes

        # Test encoding
        encoded = num.encode()
        assert len(encoded) == expected_bytes

        # Test decoding
        decoded, bytes_read = IntType.decode_from(encoded)
        assert decoded == num
        assert bytes_read == expected_bytes

    @pytest.mark.parametrize("value,max_bytes", [
        (10, 1),
        (127, 1),
        (128, 2),
        (255, 2),
        (256, 2),
        (1000, 2),
        (1000000, 3),
        (2**32, 5),
    ])
    def test_variable_size_integers(self, value, max_bytes):
        """Test variable-size general integers."""
        num = Uint(value)
        assert num == value

        encoded = num.encode()
        assert len(encoded) <= max_bytes

        decoded, _ = Uint.decode_from(encoded)
        assert decoded == num


class TestIntegerArithmetic:
    """Test arithmetic operations that preserve types."""

    @pytest.mark.parametrize("op,a_val,b_val,expected", [
        (lambda a, b: a + b, 100, 50, 150),
        (lambda a, b: a - b, 100, 50, 50),
        (lambda a, b: a - b, 100, 80, 20),
        (lambda a, b: a * b, 100, 2, 200),
        (lambda a, b: a // b, 100, 3, 33),
        (lambda a, b: a & b, 100, 0xFF, 100),
        (lambda a, b: a | b, 100, 0x0F, 111),
        (lambda a, b: a ^ b, 100, 0xAA, 206),
    ])
    def test_arithmetic_operations(self, op, a_val, b_val, expected):
        """Test arithmetic operations preserve U8 type."""
        a = Uint[8](a_val)
        b = Uint[8](b_val)
        result = op(a, b)

        assert isinstance(result, Uint[8])
        assert result == expected


class TestIntegerComparison:
    """Test integer comparison operations."""

    @pytest.mark.parametrize("a_val,b_val,expected_eq,expected_lt,expected_gt", [
        (100, 100, True, False, False),
        (100, 200, False, True, False),
        (200, 100, False, False, True),
    ])
    def test_comparison_with_same_type(self, a_val, b_val, expected_eq, expected_lt, expected_gt):
        """Test comparisons between same integer types."""
        a = Uint[16](a_val)
        b = Uint[16](b_val)

        assert (a == b) == expected_eq
        assert (a < b) == expected_lt
        assert (a > b) == expected_gt
        assert (a <= b) == (expected_eq or expected_lt)
        assert (a >= b) == (expected_eq or expected_gt)

    @pytest.mark.parametrize("uint_val,int_val,op,expected", [
        (100, 80, "gt", True),
        (100, 120, "lt", True),
        (100, 100, "ge", True),
        (100, 100, "le", True),
        (100, 101, "ne", True),
        (100, 100, "eq", True),
    ])
    def test_comparison_with_int(self, uint_val, int_val, op, expected):
        """Test comparisons with regular Python ints."""
        a = Uint[8](uint_val)

        if op == "gt":
            assert (a > int_val) == expected
        elif op == "lt":
            assert (a < int_val) == expected
        elif op == "ge":
            assert (a >= int_val) == expected
        elif op == "le":
            assert (a <= int_val) == expected
        elif op == "ne":
            assert (a != int_val) == expected
        elif op == "eq":
            assert (a == int_val) == expected

    def test_min_max_functions(self):
        """Test min/max with Uint values."""
        assert min(Uint[8](100), Uint[8](80)) == Uint[8](80)
        assert max(Uint[8](100), Uint[8](80)) == Uint[8](100)

    def test_different_sizes_equal_values(self):
        """Test that different sizes with same value are equal."""
        assert Uint[8](10) == Uint[16](10)
        # But types are different
        assert type(Uint[8](10)) != type(Uint[16](10))


class TestIntegerEncoding:
    """Test encoding and decoding operations."""

    @pytest.mark.parametrize("bit_size,value", [
        (8, 100),
        (16, 12345),
        (32, 12345),
        (64, 12345),
    ])
    def test_encode_decode_roundtrip(self, bit_size, value):
        """Test encoding/decoding roundtrip for fixed sizes."""
        IntType = Uint[bit_size]
        original = IntType(value)
        encoded = original.encode()
        decoded = IntType.decode(encoded)

        assert decoded == original

    def test_variable_encoding_efficiency(self):
        """Test that variable-size integers encode efficiently."""
        small = Uint(10)
        medium = Uint(1000)
        large = Uint(1000000)

        small_enc = small.encode()
        medium_enc = medium.encode()
        large_enc = large.encode()

        # Smaller values use fewer bytes
        assert len(small_enc) <= len(medium_enc) <= len(large_enc)

        # All roundtrip correctly
        assert Uint.decode(small_enc) == small
        assert Uint.decode(medium_enc) == medium
        assert Uint.decode(large_enc) == large


class TestIntegerJSON:
    """Test JSON serialization."""

    @pytest.mark.parametrize("int_type,value", [
        (Uint[8], 255),
        (Uint[16], 65535),
        (Uint[32], 12345),
        (Uint, 1000000),
    ])
    def test_json_roundtrip(self, int_type, value):
        """Test JSON serialization roundtrip."""
        original = int_type(value)
        json_data = original.to_json()
        restored = int_type.from_json(str(json_data))

        assert restored == original
        assert isinstance(restored, int_type)


class TestIntegerValidation:
    """Test range validation for integers."""

    @pytest.mark.parametrize("bit_size,invalid_value", [
        (8, 256),
        (8, -1),
        (16, 70000),
        (16, -5),
    ])
    def test_out_of_range_raises(self, bit_size, invalid_value):
        """Test that out-of-range values raise ValueError."""
        with pytest.raises(ValueError):
            Uint[bit_size](invalid_value)

    def test_variable_negative_raises(self):
        """Test that negative values raise for variable Uint."""
        with pytest.raises(ValueError):
            Uint(-5)


class TestIntegerBits:
    """Test bit conversion operations."""

    def test_to_bits_and_from_bits(self):
        """Test converting integers to/from bits."""
        a = Uint[8](160)
        bits = a.to_bits()
        restored = Uint[8].from_bits(bits)
        assert a == restored


class TestIntegerInstance:
    """Test instance checks and type behavior."""

    def test_instance_checks(self):
        """Test isinstance behavior."""
        class U8(Uint[8]): ...

        assert isinstance(U8(10), U8)
        assert isinstance(Uint[8](10), int)
        assert not isinstance(Uint[8](10), Uint[16])

    def test_static_type_hints(self):
        """Test usage with dataclasses and type hints."""
        @dataclass
        class DataStore:
            a: Uint[8]
            b: Uint[16]

        # These should work
        DataStore(a=Uint[8](19), b=Uint[16](288))
        # Type checker would flag these but they'll run
        DataStore(a=19, b=288)
        DataStore(a=Uint[16](19), b=Uint[32](288))


class TestIntegerCustomSizes:
    """Test custom integer bit sizes."""

    @pytest.mark.parametrize("bit_size,max_value", [
        (24, 2**24 - 1),  # 16777215
        (128, 2**128 - 1),
    ])
    def test_custom_sizes(self, bit_size, max_value):
        """Test custom bit sizes work correctly."""
        IntType = Uint[bit_size]
        value = IntType(max_value)

        assert value == max_value

        # Test roundtrip
        encoded = value.encode()
        decoded = IntType.decode(encoded)
        assert decoded == value


class TestIntegerRepr:
    """Test string representation."""

    def test_repr_format(self):
        """Test that repr shows type and value."""
        a = Uint[8](100)
        b = Uint[8](80)

        assert str(a - b) == 'U8(20)'


class TestJAMCodecCompliance:
    """JAM codec edge cases: boundaries, LE encoding, variable-length ranges."""

    @pytest.mark.parametrize("value,expected_bytes", [
        (0, b'\x00'),
        (1, b'\x01'),
        (255, b'\xff'),
        (256, b'\x00\x01'),  # LE: low byte first
        (0x1234, b'\x34\x12'),
        (0x12345678, b'\x78\x56\x34\x12'),
    ])
    def test_little_endian_encoding(self, value, expected_bytes):
        """Verify little-endian byte order per JAM spec."""
        bit_size = len(expected_bytes) * 8
        num = Uint[bit_size](value)
        assert num.encode() == expected_bytes

    @pytest.mark.parametrize("boundary", [
        2**7 - 1, 2**7,      # 127/128: 1-byte to 2-byte boundary
        2**14 - 1, 2**14,    # 2-byte to 3-byte
        2**21 - 1, 2**21,    # 3-byte to 4-byte
        2**28 - 1, 2**28,    # 4-byte to 5-byte
        2**35 - 1, 2**35,    # 5-byte to 6-byte
        2**56 - 1, 2**56,    # Before/after [255] prefix
    ])
    def test_variable_length_boundaries(self, boundary):
        """Test variable-length encoding at critical boundaries."""
        num = Uint(boundary)
        encoded = num.encode()
        decoded, _ = Uint.decode_from(encoded)
        assert decoded == num
        # Verify encoding is compact
        assert len(encoded) <= 9

    @pytest.mark.parametrize("IntType,max_val", [
        (Uint[8], 0xff),
        (Uint[16], 0xffff),
        (Uint[32], 0xffffffff),
        (Uint[64], 0xffffffffffffffff),
    ])
    def test_max_values_encode_correctly(self, IntType, max_val):
        """Test maximum values for each size."""
        num = IntType(max_val)
        decoded = IntType.decode(num.encode())
        assert decoded == num
        assert decoded == max_val

    def test_zero_special_case(self):
        """Variable Uint(0) encodes as single zero byte."""
        assert Uint(0).encode() == b'\x00'

    @pytest.mark.parametrize("power", range(64))
    def test_powers_of_two(self, power):
        """Test all powers of 2 from 2^0 to 2^63."""
        value = 2 ** power
        num = Uint(value)
        assert Uint.decode(num.encode()) == num
