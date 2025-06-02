import pytest
from tsrkit_types.integers import Uint


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


def test_variable_size_integers():
    """Test variable-size general integers."""
    # Variable-size integers (up to 2^64 - 1)
    small = Uint(10)        # Uses 1 byte
    medium = Uint(1000)     # Uses 2 bytes  
    large = Uint(1000000)   # Uses 3 bytes
    huge = Uint(2**32)      # Uses 5 bytes
    
    numbers = [small, medium, large, huge]
    expected_values = [10, 1000, 1000000, 2**32]
    
    for num, expected in zip(numbers, expected_values):
        assert num == expected
        encoded = num.encode()
        assert len(encoded) > 0  # Should encode to some bytes


def test_encoding_decoding():
    """Test encoding and decoding operations."""
    # Fixed-size encoding
    value = Uint[16](12345)
    encoded = value.encode()
    decoded = Uint[16].decode(encoded)
    
    assert len(encoded) == 2  # U16 should be 2 bytes
    assert decoded == value
    
    # Variable-size encoding
    var_value = Uint(12345)
    var_encoded = var_value.encode()
    var_decoded = Uint.decode(var_encoded)
    
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


def test_json_serialization():
    """Test JSON serialization of integers."""
    values = [Uint[8](255), Uint[16](65535), Uint[32](12345), Uint(1000000)]
    
    for value in values:
        json_data = value.to_json()
        restored = type(value).from_json(str(json_data))
        
        assert restored == value
        assert isinstance(restored, type(value))


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


def test_integer_encoding_efficiency():
    """Test that variable-size integers encode efficiently."""
    # Small values should use fewer bytes
    small = Uint(10)
    medium = Uint(1000)
    large = Uint(1000000)
    
    small_encoded = small.encode()
    medium_encoded = medium.encode()
    large_encoded = large.encode()
    
    # Smaller values should generally use fewer bytes
    assert len(small_encoded) <= len(medium_encoded)
    assert len(medium_encoded) <= len(large_encoded)
    
    # All should round-trip correctly
    assert Uint.decode(small_encoded) == small
    assert Uint.decode(medium_encoded) == medium
    assert Uint.decode(large_encoded) == large 