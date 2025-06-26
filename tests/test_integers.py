import pytest
from tsrkit_types.integers import Uint, Int, U8, U16, U32, U64, I8, I16, I32, I64


def test_fixed_size_integers():
    """Test fixed-size integer types and their usage."""
    # Pre-defined integer types
    age = Uint[8](25)        # 8-bit: 0-255
    port = Uint[16](8080)    # 16-bit: 0-65535
    user_id = Uint[32](123456789)  # 32-bit
    timestamp = Uint[64](1703001234567)  # 64-bit
    
    assert age == 25
    assert port == 8080
    assert user_id == 123456789
    assert timestamp == 1703001234567
    
    # Custom bit sizes
    U24 = Uint[24]  # 24-bit integer (3 bytes)
    U128 = Uint[128]  # 128-bit integer (16 bytes)
    
    color_value = U24(0xFF00FF)  # 24-bit color value
    big_number = U128(12345678901234567890)
    
    assert color_value == 0xFF00FF
    assert big_number == 12345678901234567890


def test_signed_fixed_size_integers():
    """Test signed fixed-size integer types and their usage."""
    # Pre-defined signed integer types
    temperature = I8(-40)        # 8-bit: -128 to 127
    altitude = I16(-1000)        # 16-bit: -32768 to 32767
    balance = I32(-1000000)      # 32-bit: -2147483648 to 2147483647
    big_signed = I64(-9223372036854775808)  # 64-bit: min value
    
    assert temperature == -40
    assert altitude == -1000
    assert balance == -1000000
    assert big_signed == -9223372036854775808
    
    # Test positive values in signed types
    pos_temp = I8(100)
    pos_alt = I16(5000)
    pos_balance = I32(1000000)
    pos_big = I64(9223372036854775807)  # max value
    
    assert pos_temp == 100
    assert pos_alt == 5000
    assert pos_balance == 1000000
    assert pos_big == 9223372036854775807


def test_signed_integer_ranges():
    """Test signed integer range validation."""
    # Test valid boundary values
    assert I8(-128) == -128  # min
    assert I8(127) == 127    # max
    assert I16(-32768) == -32768  # min
    assert I16(32767) == 32767    # max
    assert I32(-2147483648) == -2147483648  # min
    assert I32(2147483647) == 2147483647    # max
    assert I64(-9223372036854775808) == -9223372036854775808  # min
    assert I64(9223372036854775807) == 9223372036854775807    # max
    
    # Test invalid values should raise ValueError
    with pytest.raises(ValueError):
        I8(-129)  # below minimum
    with pytest.raises(ValueError):
        I8(128)   # above maximum
        
    with pytest.raises(ValueError):
        I16(-32769)  # below minimum
    with pytest.raises(ValueError):
        I16(32768)   # above maximum
        
    with pytest.raises(ValueError):
        I32(-2147483649)  # below minimum
    with pytest.raises(ValueError):
        I32(2147483648)   # above maximum


def test_signed_encoding_decoding():
    """Test encoding and decoding of signed integers."""
    # Test various signed values
    test_cases = [
        (I8, [-128, -1, 0, 1, 127]),
        (I16, [-32768, -100, 0, 100, 32767]),
        (I32, [-2147483648, -1000000, 0, 1000000, 2147483647]),
        (I64, [-9223372036854775808, -1000000000, 0, 1000000000, 9223372036854775807])
    ]
    
    for int_type, values in test_cases:
        for value in values:
            original = int_type(value)
            encoded = original.encode()
            decoded, size = int_type.decode_from(encoded)
            
            assert decoded == original
            assert decoded == value
            assert size == int_type.byte_size
            
            # Test round-trip consistency
            re_encoded = decoded.encode()
            assert re_encoded == encoded


def test_twos_complement_conversion():
    """Test two's complement conversion for signed integers."""
    # Test specific two's complement cases
    test_cases = [
        (I8(-1), 0xFF),      # -1 should encode as 0xFF
        (I8(-128), 0x80),    # -128 should encode as 0x80
        (I8(127), 0x7F),     # 127 should encode as 0x7F
        (I16(-1), 0xFFFF),   # -1 should encode as 0xFFFF
        (I16(-32768), 0x8000), # -32768 should encode as 0x8000
        (I32(-1), 0xFFFFFFFF), # -1 should encode as 0xFFFFFFFF
    ]
    
    for signed_val, expected_unsigned in test_cases:
        unsigned_repr = signed_val.to_unsigned()
        assert unsigned_repr == expected_unsigned
        
        # Test encoding produces expected bytes
        encoded = signed_val.encode()
        if signed_val.byte_size == 1:
            assert encoded[0] == expected_unsigned
        elif signed_val.byte_size == 2:
            assert int.from_bytes(encoded, 'little') == expected_unsigned
        elif signed_val.byte_size == 4:
            assert int.from_bytes(encoded, 'little') == expected_unsigned


def test_signed_unsigned_mixed_operations():
    """Test operations between signed and unsigned integers."""
    # Test that types are preserved in operations
    signed_val = I16(-100)
    unsigned_val = U16(200)
    
    # Operations with same signed type should preserve type
    result1 = signed_val + I16(50)
    assert isinstance(result1, I16)
    assert result1 == -50
    
    # Test arithmetic edge cases
    max_i8 = I8(127)
    min_i8 = I8(-128)
    
    # These should work within range
    assert max_i8 + I8(-1) == 126
    assert min_i8 + I8(1) == -127


def test_variable_size_integers():
    """Test variable-size general integers."""
    # Variable-size integers (up to 2^64 - 1) - use explicit variable size
    VarUint = Int[(0, False)]  # Variable-size unsigned integer
    small = VarUint(10)        # Uses 1 byte
    medium = VarUint(1000)     # Uses 2 bytes  
    large = VarUint(1000000)   # Uses 3 bytes
    huge = VarUint(2**32)      # Uses 5 bytes
    
    numbers = [small, medium, large, huge]
    expected_values = [10, 1000, 1000000, 2**32]
    
    for num, expected in zip(numbers, expected_values):
        assert num == expected
        encoded = num.encode()
        assert len(encoded) > 0  # Should encode to some bytes


def test_variable_size_signed_integers():
    """Test variable-size signed integers."""
    # Test signed variable-size integers
    small_neg = Int[(0, True)](-10)      # General signed integer
    medium_neg = Int[(0, True)](-1000)   
    large_neg = Int[(0, True)](-1000000)
    huge_neg = Int[(0, True)](-2**32)
    
    # Test positive values in signed general integers
    small_pos = Int[(0, True)](10)
    medium_pos = Int[(0, True)](1000)
    large_pos = Int[(0, True)](1000000)
    huge_pos = Int[(0, True)](2**32)
    
    test_values = [small_neg, medium_neg, large_neg, huge_neg,
                   small_pos, medium_pos, large_pos, huge_pos]
    expected = [-10, -1000, -1000000, -2**32, 10, 1000, 1000000, 2**32]
    
    for val, expected_val in zip(test_values, expected):
        assert val == expected_val
        
        # Test encoding/decoding
        encoded = val.encode()
        decoded, size = type(val).decode_from(encoded)
        assert decoded == val
        assert size > 0


def test_encoding_decoding():
    """Test encoding and decoding operations."""
    # Fixed-size encoding
    value = Uint[16](12345)
    encoded = value.encode()
    decoded = Uint[16].decode(encoded)
    
    assert len(encoded) == 2  # U16 should be 2 bytes
    assert decoded == value
    
    # Variable-size encoding
    VarUint = Int[(0, False)]  # Variable-size unsigned integer
    var_value = VarUint(12345)
    var_encoded = var_value.encode()
    var_decoded, _ = VarUint.decode_from(var_encoded)
    
    assert var_decoded == var_value
    assert len(var_encoded) > 0


def test_arithmetic_operations():
    """Test arithmetic operations that preserve types."""
    a = Uint[8](100)
    b = Uint[8](50)
    
    # All operations preserve the U8 type
    assert isinstance(a + b, Uint[8])
    assert isinstance(a - b, Uint[8])
    assert isinstance(a * Uint[8](2), Uint[8])
    assert isinstance(a // Uint[8](3), Uint[8])
    assert isinstance(a & Uint[8](0xFF), Uint[8])
    assert isinstance(a | Uint[8](0x0F), Uint[8])
    assert isinstance(a ^ Uint[8](0xAA), Uint[8])
    
    # Test actual values
    assert a + b == 150
    assert a - b == 50
    assert a * Uint[8](2) == 200


def test_signed_arithmetic_operations():
    """Test arithmetic operations with signed integers."""
    a = I16(-100)
    b = I16(50)
    
    # All operations preserve the I16 type
    assert isinstance(a + b, I16)
    assert isinstance(a - b, I16)
    assert isinstance(a * I16(-2), I16)
    assert isinstance(a // I16(3), I16)
    
    # Test actual values
    assert a + b == -50
    assert a - b == -150
    assert a * I16(-2) == 200
    assert a // I16(3) == -34  # -100 // 3 = -33.33... -> -34 (floor division)


def test_json_serialization():
    """Test JSON serialization of integers."""
    VarUint = Int[(0, False)]  # Variable-size unsigned integer
    values = [Uint[8](255), Uint[16](65535), Uint[32](12345), VarUint(1000000)]
    
    for value in values:
        json_data = value.to_json()
        restored = type(value).from_json(str(json_data))
        
        assert restored == value
        assert isinstance(restored, type(value))


def test_signed_json_serialization():
    """Test JSON serialization of signed integers."""
    signed_values = [I8(-128), I16(-1000), I32(-1000000), I64(-9223372036854775808)]
    
    for value in signed_values:
        json_data = value.to_json()
        restored = type(value).from_json(str(json_data))
        
        assert restored == value
        assert isinstance(restored, type(value))
        assert restored == int(value)  # Should preserve the actual value


def test_range_validation():
    """Test range validation for fixed-size integers."""
    # Valid values
    valid_u8 = Uint[8](255)  # Maximum value for U8
    assert valid_u8 == 255
    
    # Invalid values should raise ValueError
    with pytest.raises(ValueError):
        Uint[8](256)  # exceeds maximum
    
    with pytest.raises(ValueError):
        Uint[8](-1)  # below minimum
    
    with pytest.raises(ValueError):
        Uint[16](70000)  # exceeds maximum
    
    with pytest.raises(ValueError):
        Uint(-5)  # negative value


def test_integer_types_comprehensive():
    """Comprehensive test of all integer type features."""
    # Test each predefined type
    types_and_values = [
        (Uint[8], 255, 1),
        (Uint[16], 65535, 2),
        (Uint[32], 4294967295, 4),
        (Uint[64], 18446744073709551615, 8),
    ]
    
    for int_type, max_val, expected_size in types_and_values:
        # Test maximum value
        max_instance = int_type(max_val)
        assert max_instance == max_val
        
        # Test encoding size
        encoded = max_instance.encode()
        assert len(encoded) == expected_size
        
        # Test round-trip
        decoded = int_type.decode(encoded)
        assert decoded == max_instance
        
        # Test JSON round-trip
        json_data = max_instance.to_json()
        json_restored = int_type.from_json(str(json_data))
        assert json_restored == max_instance


def test_signed_integer_types_comprehensive():
    """Comprehensive test of signed integer type features."""
    # Test each predefined signed type
    signed_types_and_values = [
        (I8, -128, 127, 1),
        (I16, -32768, 32767, 2),
        (I32, -2147483648, 2147483647, 4),
        (I64, -9223372036854775808, 9223372036854775807, 8),
    ]
    
    for int_type, min_val, max_val, expected_size in signed_types_and_values:
        # Test minimum and maximum values
        min_instance = int_type(min_val)
        max_instance = int_type(max_val)
        
        assert min_instance == min_val
        assert max_instance == max_val
        
        # Test encoding size
        min_encoded = min_instance.encode()
        max_encoded = max_instance.encode()
        
        assert len(min_encoded) == expected_size
        assert len(max_encoded) == expected_size
        
        # Test round-trip for both min and max
        min_decoded = int_type.decode(min_encoded)
        max_decoded = int_type.decode(max_encoded)
        
        assert min_decoded == min_instance
        assert max_decoded == max_instance
        
        # Test JSON round-trip
        min_json = min_instance.to_json()
        max_json = max_instance.to_json()
        
        min_json_restored = int_type.from_json(str(min_json))
        max_json_restored = int_type.from_json(str(max_json))
        
        assert min_json_restored == min_instance
        assert max_json_restored == max_instance


def test_custom_integer_sizes():
    """Test custom integer bit sizes."""
    # Test various custom sizes (must be multiples of 8)
    U16_custom = Uint[16]  # 16-bit (2 bytes)
    U24_custom = Uint[24]  # 24-bit (3 bytes) 
    U32_custom = Uint[32]  # 32-bit (4 bytes)
    
    # Test maximum values for each size
    val_16 = U16_custom(2**16 - 1)  # 65535
    val_24 = U24_custom(2**24 - 1)  # 16777215
    val_32 = U32_custom(2**32 - 1)  # 4294967295
    
    assert val_16 == 65535
    assert val_24 == 16777215
    assert val_32 == 4294967295
    
    # Test encoding/decoding
    for val in [val_16, val_24, val_32]:
        encoded = val.encode()
        decoded = type(val).decode(encoded)
        assert decoded == val


def test_custom_signed_integer_sizes():
    """Test custom signed integer bit sizes."""
    # Test standard byte-aligned sizes only (custom bit sizes need more work)
    I24 = Int[(24, True)]  # 24-bit signed (3 bytes)
    I40 = Int[(40, True)]  # 40-bit signed (5 bytes)
    
    # Test values within range  
    val_24_neg = I24(-8388608)  # minimum for 24-bit signed
    val_24_pos = I24(8388607)   # maximum for 24-bit signed
    val_40_neg = I40(-549755813888)  # minimum for 40-bit signed
    val_40_pos = I40(549755813887)   # maximum for 40-bit signed
    
    assert val_24_neg == -8388608
    assert val_24_pos == 8388607
    assert val_40_neg == -549755813888
    assert val_40_pos == 549755813887
    
    # Test encoding/decoding
    for val in [val_24_neg, val_24_pos, val_40_neg, val_40_pos]:
        encoded = val.encode()
        decoded, size = type(val).decode_from(encoded)
        assert decoded == val


def test_integer_comparison():
    """Test integer comparison operations."""
    a = Uint[16](100)
    b = Uint[16](200)
    c = Uint[16](100)
    
    assert a == c
    assert a != b
    assert a < b
    assert b > a
    assert a <= c
    assert a >= c


def test_signed_integer_comparison():
    """Test signed integer comparison operations."""
    a = I16(-100)
    b = I16(50)
    c = I16(-100)
    d = I16(-200)
    
    assert a == c
    assert a != b
    assert a < b    # -100 < 50
    assert b > a    # 50 > -100
    assert a > d    # -100 > -200
    assert d < a    # -200 < -100
    assert a <= c
    assert a >= c


def test_integer_encoding_efficiency():
    """Test that variable-size integers encode efficiently."""
    # Small values should use fewer bytes
    VarUint = Int[(0, False)]  # Variable-size unsigned integer
    small = VarUint(10)
    medium = VarUint(1000)
    large = VarUint(1000000)
    
    small_encoded = small.encode()
    medium_encoded = medium.encode()
    large_encoded = large.encode()
    
    # Smaller values should generally use fewer bytes
    assert len(small_encoded) <= len(medium_encoded)
    assert len(medium_encoded) <= len(large_encoded)
    
    # All should round-trip correctly
    small_decoded, _ = VarUint.decode_from(small_encoded)
    medium_decoded, _ = VarUint.decode_from(medium_encoded)
    large_decoded, _ = VarUint.decode_from(large_encoded)
    
    assert small_decoded == small
    assert medium_decoded == medium
    assert large_decoded == large


def test_signed_integer_encoding_efficiency():
    """Test that variable-size signed integers encode efficiently."""
    SignedInt = Int[(0, True)]  # General signed integer
    
    # Test both positive and negative values
    small_pos = SignedInt(10)
    small_neg = SignedInt(-10)
    medium_pos = SignedInt(1000)
    medium_neg = SignedInt(-1000)
    large_pos = SignedInt(1000000)
    large_neg = SignedInt(-1000000)
    
    values = [small_pos, small_neg, medium_pos, medium_neg, large_pos, large_neg]
    
    for val in values:
        encoded = val.encode()
        decoded, size = type(val).decode_from(encoded)
        assert decoded == val
        assert size > 0


def test_bit_operations():
    """Test bit manipulation operations for both signed and unsigned integers."""
    # Test unsigned bit operations
    u8_val = U8(0b10101010)  # 170
    bits_msb = u8_val.to_bits("msb")
    bits_lsb = u8_val.to_bits("lsb")
    
    expected_msb = [True, False, True, False, True, False, True, False]
    expected_lsb = [False, True, False, True, False, True, False, True]
    
    assert bits_msb == expected_msb
    assert bits_lsb == expected_lsb
    
    # Test reconstruction from bits
    reconstructed_msb = U8.from_bits(bits_msb, "msb")
    reconstructed_lsb = U8.from_bits(bits_lsb, "lsb")
    
    assert reconstructed_msb == u8_val
    assert reconstructed_lsb == u8_val
    
    # Test signed bit operations
    i8_val = I8(-86)  # 0b10101010 in two's complement
    signed_bits = i8_val.to_bits("msb")
    
    # For -86, the two's complement representation should be 0b10101010
    expected_signed_bits = [True, False, True, False, True, False, True, False]
    assert signed_bits == expected_signed_bits
    
    # Test reconstruction
    reconstructed_signed = I8.from_bits(signed_bits, "msb")
    assert reconstructed_signed == i8_val


def test_edge_case_zero():
    """Test that zero is handled correctly in both signed and unsigned types."""
    # Zero should work in all types
    unsigned_zero = U8(0)
    signed_zero = I8(0)
    
    assert unsigned_zero == 0
    assert signed_zero == 0
    
    # Encoding should be the same
    u_encoded = unsigned_zero.encode()
    s_encoded = signed_zero.encode()
    
    assert u_encoded == s_encoded == b'\x00'
    
    # Decoding should work correctly
    u_decoded = U8.decode(u_encoded)
    s_decoded = I8.decode(s_encoded)
    
    assert u_decoded == unsigned_zero
    assert s_decoded == signed_zero


def test_type_preservation():
    """Test that integer types are preserved through operations."""
    # Test that operations preserve the exact type
    u8_val = U8(100)
    i8_val = I8(-50)
    
    # Arithmetic operations should preserve type
    u8_result = u8_val + U8(50)
    i8_result = i8_val + I8(25)
    
    assert type(u8_result) == U8
    assert type(i8_result) == I8
    assert u8_result == 150
    assert i8_result == -25
    
    # Bitwise operations should preserve type
    u8_bitwise = u8_val & U8(0xFF)
    i8_bitwise = i8_val | I8(0x0F)
    
    assert type(u8_bitwise) == U8
    assert type(i8_bitwise) == I8 