import pytest
from tsrkit_types.bytearray import ByteArray
from tsrkit_types.bytes import Bytes


class TestByteArrayBasicFunctionality:
    """Test basic ByteArray functionality and creation."""
    
    def test_bytearray_creation_from_bytes(self):
        """Test creating ByteArray from bytes."""
        data = ByteArray(b"hello")
        assert len(data) == 5
        assert bytes(data) == b"hello"
    
    def test_bytearray_creation_from_list(self):
        """Test creating ByteArray from list of integers."""
        data = ByteArray([104, 101, 108, 108, 111])  # "hello" in ASCII (h=104, not 72=H)
        assert bytes(data) == b"hello"
    
    def test_bytearray_creation_empty(self):
        """Test creating empty ByteArray."""
        data = ByteArray()
        assert len(data) == 0
        assert bytes(data) == b""
    
    def test_bytearray_mutability(self):
        """Test that ByteArray is mutable unlike bytes."""
        data = ByteArray(b"hello")
        data[0] = ord('H')  # Change 'h' to 'H'
        assert bytes(data) == b"Hello"
        
        # Test append
        data.append(ord('!'))
        assert bytes(data) == b"Hello!"
        
        # Test extend
        data.extend(b" World")
        assert bytes(data) == b"Hello! World"
    
    def test_bytearray_indexing_and_slicing(self):
        """Test indexing and slicing operations."""
        data = ByteArray(b"hello world")
        assert data[0] == ord('h')
        assert data[-1] == ord('d')
        assert bytes(data[0:5]) == b"hello"
        assert bytes(data[6:]) == b"world"
    
    def test_bytearray_clear_and_pop(self):
        """Test clear and pop operations."""
        data = ByteArray(b"hello")
        
        # Test pop
        last_byte = data.pop()
        assert last_byte == ord('o')
        assert bytes(data) == b"hell"
        
        # Test clear
        data.clear()
        assert len(data) == 0
        assert bytes(data) == b""


class TestByteArrayBitConversion:
    """Test bit conversion functionality."""
    
    def test_bytearray_to_bits_msb(self):
        """Test converting ByteArray to bits with MSB order."""
        data = ByteArray([0b10101010])  # 170 in decimal
        bits = data.to_bits("msb")
        expected = [True, False, True, False, True, False, True, False]
        assert bits == expected
    
    def test_bytearray_to_bits_lsb(self):
        """Test converting ByteArray to bits with LSB order."""
        data = ByteArray([0b10101010])  # 170 in decimal
        bits = data.to_bits("lsb")
        expected = [False, True, False, True, False, True, False, True]
        assert bits == expected
    
    def test_bytearray_from_bits_msb(self):
        """Test creating ByteArray from bits with MSB order."""
        bits = [True, False, True, False, True, False, True, False]
        data = ByteArray.from_bits(bits, "msb")
        assert len(data) == 1
        assert data[0] == 0b10101010
    
    def test_bytearray_from_bits_lsb(self):
        """Test creating ByteArray from bits with LSB order."""
        bits = [True, False, True, False, True, False, True, False]
        data = ByteArray.from_bits(bits, "lsb")
        assert len(data) == 1
        assert data[0] == 0b01010101  # Different due to LSB interpretation
    
    def test_bytearray_bits_roundtrip(self):
        """Test bits conversion roundtrip."""
        original = ByteArray(b"ABC")
        bits_msb = original.to_bits("msb")
        restored_msb = ByteArray.from_bits(bits_msb, "msb")
        assert bytes(restored_msb) == bytes(original)
        
        bits_lsb = original.to_bits("lsb")
        restored_lsb = ByteArray.from_bits(bits_lsb, "lsb")
        assert bytes(restored_lsb) == bytes(original)
    
    def test_bytearray_bits_padding(self):
        """Test bits conversion with padding."""
        # 5 bits should be padded to 8 bits (1 byte)
        bits = [True, False, True, False, True]
        data = ByteArray.from_bits(bits)
        assert len(data) == 1
        
        # Convert back should include padding
        restored_bits = data.to_bits()
        assert len(restored_bits) == 8
        assert restored_bits[:5] == bits  # Original bits preserved
    
    def test_bytearray_bits_invalid_order(self):
        """Test invalid bit order raises error."""
        data = ByteArray(b"test")
        with pytest.raises(ValueError, match="Unknown bit_order"):
            data.to_bits("invalid")
        
        with pytest.raises(ValueError, match="Unknown bit_order"):
            ByteArray.from_bits([True, False], "invalid")


class TestByteArrayJSONSerialization:
    """Test JSON serialization and deserialization."""
    
    def test_bytearray_to_json(self):
        """Test converting ByteArray to JSON hex string."""
        data = ByteArray([0xDE, 0xAD, 0xBE, 0xEF])
        json_str = data.to_json()
        assert json_str == "deadbeef"
    
    def test_bytearray_from_json_simple(self):
        """Test creating ByteArray from JSON hex string."""
        data = ByteArray.from_json("deadbeef")
        assert len(data) == 4
        assert list(data) == [0xDE, 0xAD, 0xBE, 0xEF]
    
    def test_bytearray_from_json_with_0x_prefix(self):
        """Test creating ByteArray from JSON hex string with 0x prefix."""
        data = ByteArray.from_json("0xdeadbeef")
        assert len(data) == 4
        assert list(data) == [0xDE, 0xAD, 0xBE, 0xEF]
    
    def test_bytearray_from_json_empty(self):
        """Test creating ByteArray from empty hex string."""
        data = ByteArray.from_json("")
        assert len(data) == 0
        assert bytes(data) == b""
    
    def test_bytearray_json_roundtrip(self):
        """Test JSON serialization roundtrip."""
        original = ByteArray(b"Hello, World!")
        json_str = original.to_json()
        restored = ByteArray.from_json(json_str)
        assert bytes(restored) == bytes(original)
    
    def test_bytearray_json_case_insensitive(self):
        """Test that hex parsing is case insensitive."""
        data1 = ByteArray.from_json("deadbeef")
        data2 = ByteArray.from_json("DEADBEEF")
        data3 = ByteArray.from_json("DeAdBeEf")
        
        assert bytes(data1) == bytes(data2) == bytes(data3)


class TestByteArraySerialization:
    """Test binary serialization and deserialization."""
    
    def test_bytearray_encode_decode_simple(self):
        """Test basic encoding and decoding."""
        original = ByteArray(b"test data")
        encoded = original.encode()
        decoded, bytes_read = ByteArray.decode_from(encoded)
        
        assert bytes(decoded) == bytes(original)
        assert bytes_read == len(encoded)
    
    def test_bytearray_encode_size(self):
        """Test encode_size calculation."""
        data = ByteArray(b"hello")
        size = data.encode_size()
        encoded = data.encode()
        assert size == len(encoded)
    
    def test_bytearray_encode_into_buffer(self):
        """Test encoding directly into a buffer."""
        data = ByteArray(b"test")
        buffer = bytearray(20)  # Large enough buffer
        bytes_written = data.encode_into(buffer, offset=5)
        
        assert bytes_written > 0
        # Verify the buffer was modified at the correct offset
        assert buffer[0:5] == bytearray([0] * 5)  # Untouched
        # The actual data should be encoded starting at offset 5
    
    def test_bytearray_decode_from_offset(self):
        """Test decoding from buffer at specific offset."""
        data1 = ByteArray(b"first")
        data2 = ByteArray(b"second")
        
        # Encode both into a single buffer
        buffer = bytearray(100)
        offset1 = data1.encode_into(buffer, 0)
        offset2 = data2.encode_into(buffer, offset1)
        
        # Decode each separately
        decoded1, bytes_read1 = ByteArray.decode_from(buffer, 0)
        decoded2, bytes_read2 = ByteArray.decode_from(buffer, bytes_read1)
        
        assert bytes(decoded1) == b"first"
        assert bytes(decoded2) == b"second"
    
    def test_bytearray_encode_decode_empty(self):
        """Test encoding and decoding empty ByteArray."""
        empty = ByteArray()
        encoded = empty.encode()
        decoded, bytes_read = ByteArray.decode_from(encoded)
        
        assert len(decoded) == 0
        assert bytes_read == len(encoded)
    
    def test_bytearray_roundtrip_serialization(self):
        """Test complete serialization roundtrip with various data."""
        test_cases = [
            b"",
            b"a",
            b"hello world",
            bytes(range(256)),  # All possible byte values
            b"\x00\x01\x02\x03\xff\xfe\xfd",
        ]
        
        for original_bytes in test_cases:
            original = ByteArray(original_bytes)
            encoded = original.encode()
            decoded, _ = ByteArray.decode_from(encoded)
            assert bytes(decoded) == original_bytes


class TestByteArrayEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_bytearray_large_data(self):
        """Test with large ByteArray."""
        large_data = ByteArray(b"x" * 10000)
        assert len(large_data) == 10000
        
        # Test serialization still works
        encoded = large_data.encode()
        decoded, _ = ByteArray.decode_from(encoded)
        assert len(decoded) == 10000
        assert bytes(decoded) == bytes(large_data)
    
    def test_bytearray_binary_data(self):
        """Test with binary data including null bytes."""
        binary_data = ByteArray(bytes(range(256)))
        
        # Test JSON serialization preserves data
        json_str = binary_data.to_json()
        restored = ByteArray.from_json(json_str)
        assert bytes(restored) == bytes(binary_data)
        
        # Test binary serialization preserves data
        encoded = binary_data.encode()
        decoded, _ = ByteArray.decode_from(encoded)
        assert bytes(decoded) == bytes(binary_data)
    
    def test_bytearray_buffer_edge_cases(self):
        """Test behavior with edge case buffer data."""
        # Test with empty buffer - implementation handles gracefully
        result, bytes_read = ByteArray.decode_from(b"")
        assert len(result) == 0
        assert bytes_read == 1  # Reads length byte as 0
        
        # Test with single byte buffer
        result, bytes_read = ByteArray.decode_from(b"\x00")
        assert len(result) == 0
        assert bytes_read == 1
    
    def test_bytearray_invalid_hex_json(self):
        """Test invalid hex strings raise appropriate errors."""
        with pytest.raises(ValueError):
            ByteArray.from_json("invalid_hex")
        
        with pytest.raises(ValueError):
            ByteArray.from_json("abcg")  # 'g' is not a valid hex digit


class TestByteArrayIntegration:
    """Test integration with other types."""
    
    def test_bytearray_with_bytes_conversion(self):
        """Test conversion between ByteArray and Bytes."""
        # ByteArray to Bytes
        ba = ByteArray(b"hello")
        b = Bytes(bytes(ba))
        assert bytes(b) == b"hello"
        
        # Bytes to ByteArray
        b = Bytes(b"world")
        ba = ByteArray(b)
        assert bytes(ba) == b"world"
    
    def test_bytearray_equality(self):
        """Test ByteArray equality comparisons."""
        ba1 = ByteArray(b"test")
        ba2 = ByteArray(b"test")
        ba3 = ByteArray(b"different")
        
        assert ba1 == ba2
        assert ba1 != ba3
        assert ba1 == b"test"  # Should work with bytes
    
    def test_bytearray_string_representation(self):
        """Test string representation of ByteArray."""
        data = ByteArray(b"hello")
        repr_str = repr(data)
        str_repr = str(data)
        
        assert "ByteArray" in str_repr
        assert "hello" in str_repr.lower()  # hex representation
    
    def test_bytearray_iteration(self):
        """Test iteration over ByteArray."""
        data = ByteArray([65, 66, 67])  # ABC
        result = list(data)
        assert result == [65, 66, 67]
        
        # Test in operator
        assert 65 in data
        assert 90 not in data


class TestByteArrayPerformance:
    """Test performance-related aspects."""
    
    def test_bytearray_memory_efficiency(self):
        """Test that ByteArray doesn't use excessive memory."""
        # Create large ByteArray
        large_data = ByteArray(b"x" * 50000)
        
        # Should be able to encode/decode efficiently
        encoded = large_data.encode()
        decoded, _ = ByteArray.decode_from(encoded)
        
        assert len(decoded) == len(large_data)
        assert bytes(decoded) == bytes(large_data)
    
    def test_bytearray_encode_decode_speed(self):
        """Test that encode/decode operations complete reasonably quickly."""
        import time
        
        medium_data = ByteArray(b"a" * 1000)
        
        start_time = time.time()
        for _ in range(100):  # Repeat 100 times
            encoded = medium_data.encode()
            decoded, _ = ByteArray.decode_from(encoded)
        end_time = time.time()
        
        # Should complete in reasonable time
        assert end_time - start_time < 1.0


class TestByteArraySpecialCases:
    """Test special cases and boundary conditions."""
    
    def test_bytearray_modification_after_creation(self):
        """Test various modification operations."""
        data = ByteArray(b"hello")
        
        # Insert
        data.insert(5, ord(' '))
        data.insert(6, ord('w'))
        assert bytes(data) == b"hello w"
        
        # Remove
        data.remove(ord(' '))
        assert bytes(data) == b"hellow"
        
        # Reverse
        data.reverse()
        assert bytes(data) == b"wolleh"
    
    def test_bytearray_concatenation(self):
        """Test concatenation operations."""
        ba1 = ByteArray(b"hello")
        ba2 = ByteArray(b"world")
        
        # Test += operator
        ba1 += ba2
        assert bytes(ba1) == b"helloworld"
        
        # Test + operator (creates new ByteArray)
        ba3 = ByteArray(b"foo")
        ba4 = ba3 + b"bar"
        assert bytes(ba4) == b"foobar"
        assert bytes(ba3) == b"foo"  # Original unchanged
    
    def test_bytearray_single_byte(self):
        """Test single byte operations."""
        single = ByteArray([42])
        assert len(single) == 1
        assert single[0] == 42
        
        # JSON roundtrip
        json_str = single.to_json()
        restored = ByteArray.from_json(json_str)
        assert bytes(restored) == bytes(single)
        
        # Binary roundtrip
        encoded = single.encode()
        decoded, _ = ByteArray.decode_from(encoded)
        assert bytes(decoded) == bytes(single)
    
    def test_bytearray_copy_operations(self):
        """Test copying ByteArray instances."""
        original = ByteArray(b"original")
        
        # Shallow copy
        copy1 = ByteArray(original)
        copy1[0] = ord('O')
        assert bytes(copy1) == b"Original"
        assert bytes(original) == b"original"  # Original unchanged
        
        # Using copy method if available
        if hasattr(original, 'copy'):
            copy2 = original.copy()
            copy2[0] = ord('X')
            assert bytes(original) == b"original"  # Original still unchanged 