import pytest
from tsrkit_types.bytearray import ByteArray
from tsrkit_types.bytes import Bytes


class TestByteArrayCreation:
    """Test ByteArray creation and basic operations."""

    @pytest.mark.parametrize("input_data,expected_bytes,expected_len", [
        (b"hello", b"hello", 5),
        ([104, 101, 108, 108, 111], b"hello", 5),
        ([], b"", 0),
        (b"", b"", 0),
    ])
    def test_creation(self, input_data, expected_bytes, expected_len):
        """Test creating ByteArray from various inputs."""
        data = ByteArray(input_data)
        assert len(data) == expected_len
        assert bytes(data) == expected_bytes

    def test_mutability(self):
        """Test ByteArray mutability operations."""
        data = ByteArray(b"hello")

        # Modify
        data[0] = ord('H')
        assert bytes(data) == b"Hello"

        # Append
        data.append(ord('!'))
        assert bytes(data) == b"Hello!"

        # Extend
        data.extend(b" World")
        assert bytes(data) == b"Hello! World"

    @pytest.mark.parametrize("data,index,expected", [
        (b"hello world", 0, ord('h')),
        (b"hello world", -1, ord('d')),
        (b"hello world", slice(0, 5), b"hello"),
        (b"hello world", slice(6, None), b"world"),
    ])
    def test_indexing_slicing(self, data, index, expected):
        """Test indexing and slicing operations."""
        ba = ByteArray(data)
        result = ba[index]

        if isinstance(index, slice):
            assert bytes(result) == expected
        else:
            assert result == expected


class TestByteArrayBitConversion:
    """Test bit conversion functionality."""

    @pytest.mark.parametrize("byte_val,order,expected_bits", [
        (0b10101010, "msb", [True, False, True, False, True, False, True, False]),
        (0b10101010, "lsb", [False, True, False, True, False, True, False, True]),
        (0xFF, "msb", [True] * 8),
        (0x00, "msb", [False] * 8),
    ])
    def test_to_bits(self, byte_val, order, expected_bits):
        """Test converting ByteArray to bits."""
        data = ByteArray([byte_val])
        bits = data.to_bits(order)
        assert bits == expected_bits

    @pytest.mark.parametrize("bits,order,expected_byte", [
        ([True, False, True, False, True, False, True, False], "msb", 0b10101010),
        ([True, False, True, False, True, False, True, False], "lsb", 0b01010101),
        ([True] * 8, "msb", 0xFF),
        ([False] * 8, "msb", 0x00),
    ])
    def test_from_bits(self, bits, order, expected_byte):
        """Test creating ByteArray from bits."""
        data = ByteArray.from_bits(bits, order)
        assert len(data) == 1
        assert data[0] == expected_byte

    @pytest.mark.parametrize("order", ["msb", "lsb"])
    def test_bits_roundtrip(self, order):
        """Test bits conversion roundtrip."""
        original = ByteArray(b"ABC")
        bits = original.to_bits(order)
        restored = ByteArray.from_bits(bits, order)
        assert bytes(restored) == bytes(original)

    def test_bits_invalid_order(self):
        """Test invalid bit order raises error."""
        data = ByteArray(b"test")

        with pytest.raises(ValueError, match="Unknown bit_order"):
            data.to_bits("invalid")

        with pytest.raises(ValueError, match="Unknown bit_order"):
            ByteArray.from_bits([True, False], "invalid")


class TestByteArrayJSON:
    """Test JSON serialization."""

    @pytest.mark.parametrize("input_data,expected_hex", [
        ([0xDE, 0xAD, 0xBE, 0xEF], "deadbeef"),
        ([], ""),
        ([0xFF], "ff"),
        ([0x00], "00"),
    ])
    def test_to_json(self, input_data, expected_hex):
        """Test converting ByteArray to JSON hex string."""
        data = ByteArray(input_data)
        json_str = data.to_json()
        assert json_str == expected_hex

    @pytest.mark.parametrize("hex_input,expected_bytes", [
        ("deadbeef", [0xDE, 0xAD, 0xBE, 0xEF]),
        ("0xdeadbeef", [0xDE, 0xAD, 0xBE, 0xEF]),
        ("", []),
        ("ff", [0xFF]),
    ])
    def test_from_json(self, hex_input, expected_bytes):
        """Test creating ByteArray from JSON hex string."""
        data = ByteArray.from_json(hex_input)
        assert list(data) == expected_bytes

    @pytest.mark.parametrize("hex_str", ["deadbeef", "DEADBEEF", "DeAdBeEf"])
    def test_json_case_insensitive(self, hex_str):
        """Test hex parsing is case insensitive."""
        data = ByteArray.from_json(hex_str)
        assert list(data) == [0xDE, 0xAD, 0xBE, 0xEF]

    def test_json_roundtrip(self):
        """Test JSON serialization roundtrip."""
        original = ByteArray(b"Hello, World!")
        json_str = original.to_json()
        restored = ByteArray.from_json(json_str)
        assert bytes(restored) == bytes(original)

    @pytest.mark.parametrize("invalid_hex", ["invalid_hex", "abcg", "xyz"])
    def test_invalid_hex_raises(self, invalid_hex):
        """Test invalid hex strings raise ValueError."""
        with pytest.raises(ValueError):
            ByteArray.from_json(invalid_hex)


class TestByteArraySerialization:
    """Test binary serialization."""

    @pytest.mark.parametrize("input_bytes", [
        b"test data",
        b"",
        b"a",
        b"hello world",
        bytes(range(256)),
        b"\x00\x01\x02\x03\xff\xfe\xfd",
    ])
    def test_encode_decode_roundtrip(self, input_bytes):
        """Test encoding and decoding roundtrip."""
        original = ByteArray(input_bytes)
        encoded = original.encode()
        decoded, bytes_read = ByteArray.decode_from(encoded)

        assert bytes(decoded) == input_bytes
        assert bytes_read == len(encoded)

    def test_encode_size(self):
        """Test encode_size calculation."""
        data = ByteArray(b"hello")
        size = data.encode_size()
        encoded = data.encode()
        assert size == len(encoded)

    def test_encode_into_buffer(self):
        """Test encoding into buffer at offset."""
        data = ByteArray(b"test")
        buffer = bytearray(20)
        bytes_written = data.encode_into(buffer, offset=5)

        assert bytes_written > 0
        assert buffer[0:5] == bytearray([0] * 5)

    def test_decode_from_offset(self):
        """Test decoding from buffer at offset."""
        data1 = ByteArray(b"first")
        data2 = ByteArray(b"second")

        buffer = bytearray(100)
        offset1 = data1.encode_into(buffer, 0)
        data2.encode_into(buffer, offset1)

        decoded1, bytes_read1 = ByteArray.decode_from(buffer, 0)
        decoded2, bytes_read2 = ByteArray.decode_from(buffer, bytes_read1)

        assert bytes(decoded1) == b"first"
        assert bytes(decoded2) == b"second"


class TestByteArrayEdgeCases:
    """Test edge cases and special scenarios."""

    def test_large_data(self):
        """Test with large ByteArray."""
        large_data = ByteArray(b"x" * 10000)
        assert len(large_data) == 10000

        encoded = large_data.encode()
        decoded, _ = ByteArray.decode_from(encoded)
        assert len(decoded) == 10000

    def test_binary_data_with_nulls(self):
        """Test binary data including null bytes."""
        binary_data = ByteArray(bytes(range(256)))

        # JSON roundtrip
        json_str = binary_data.to_json()
        restored = ByteArray.from_json(json_str)
        assert bytes(restored) == bytes(binary_data)

        # Binary roundtrip
        encoded = binary_data.encode()
        decoded, _ = ByteArray.decode_from(encoded)
        assert bytes(decoded) == bytes(binary_data)

    def test_buffer_edge_cases(self):
        """Test behavior with edge case buffers."""
        # Empty ByteArray properly encoded (length=0)
        result, bytes_read = ByteArray.decode_from(b"\x00")
        assert len(result) == 0
        assert bytes_read == 1

        # Truly empty buffer should fail (truncated/malformed)
        with pytest.raises(ValueError):
            ByteArray.decode_from(b"")

    def test_modification_operations(self):
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

    def test_concatenation(self):
        """Test concatenation operations."""
        ba1 = ByteArray(b"hello")
        ba2 = ByteArray(b"world")

        # += operator
        ba1 += ba2
        assert bytes(ba1) == b"helloworld"

        # + operator
        ba3 = ByteArray(b"foo")
        ba4 = ba3 + b"bar"
        assert bytes(ba4) == b"foobar"
        assert bytes(ba3) == b"foo"


class TestByteArrayIntegration:
    """Test integration with other types."""

    def test_with_bytes_conversion(self):
        """Test conversion between ByteArray and Bytes."""
        ba = ByteArray(b"hello")
        b = Bytes(bytes(ba))
        assert bytes(b) == b"hello"

        b = Bytes(b"world")
        ba = ByteArray(b)
        assert bytes(ba) == b"world"

    @pytest.mark.parametrize("ba1_data,ba2_data,should_equal", [
        (b"test", b"test", True),
        (b"test", b"different", False),
    ])
    def test_equality(self, ba1_data, ba2_data, should_equal):
        """Test ByteArray equality comparisons."""
        ba1 = ByteArray(ba1_data)
        ba2 = ByteArray(ba2_data)

        assert (ba1 == ba2) == should_equal
        assert (ba1 == ba1_data) == True

    def test_iteration(self):
        """Test iteration over ByteArray."""
        data = ByteArray([65, 66, 67])
        result = list(data)
        assert result == [65, 66, 67]

        assert 65 in data
        assert 90 not in data

    def test_clear_and_pop(self):
        """Test clear and pop operations."""
        data = ByteArray(b"hello")

        last_byte = data.pop()
        assert last_byte == ord('o')
        assert bytes(data) == b"hell"

        data.clear()
        assert len(data) == 0

    def test_copy_operations(self):
        """Test copying ByteArray instances."""
        original = ByteArray(b"original")

        copy1 = ByteArray(original)
        copy1[0] = ord('O')
        assert bytes(copy1) == b"Original"
        assert bytes(original) == b"original"


class TestJAMCodecBlobEncoding:
    """JAM codec blob encoding: E(x ∈ Y) ≡ x (identity for fixed-length)."""

    @pytest.mark.parametrize("data", [
        b'',
        b'\x00',
        b'\xff',
        b'\x00\x01\x02\x03',
        bytes(range(256)),
    ])
    def test_bytearray_roundtrip(self, data):
        """ByteArray encode/decode preserves data."""
        ba = ByteArray(data)
        encoded = ba.encode()
        decoded, _ = ByteArray.decode_from(encoded)
        assert bytes(decoded) == data

    def test_all_byte_values(self):
        """Test all 256 possible byte values."""
        for val in range(256):
            ba = ByteArray([val])
            encoded = ba.encode()
            decoded, _ = ByteArray.decode_from(encoded)
            assert bytes(decoded) == bytes([val])

    @pytest.mark.parametrize("size", [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024])
    def test_power_of_two_sizes(self, size):
        """Test power-of-2 byte lengths."""
        data = bytes([i % 256 for i in range(size)])
        ba = ByteArray(data)
        decoded, _ = ByteArray.decode_from(ba.encode())
        assert bytes(decoded) == data
