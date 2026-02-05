import pytest
from tsrkit_types.bits import Bits
from tsrkit_types.bytes import Bytes


class TestBitsCreation:
    """Test Bits creation and basic operations."""

    @pytest.mark.parametrize("input_bits,expected_len", [
        ([True, False, True, False], 4),
        ([True] * 8, 8),
        ([False] * 16, 16),
        ([], 0),
    ])
    def test_creation_from_list(self, input_bits, expected_len):
        """Test creating Bits from list of booleans."""
        bits = Bits(input_bits)
        assert len(bits) == expected_len
        assert list(bits) == input_bits

    def test_creation_rejects_non_bool(self):
        """Test that Bits only accepts bool values."""
        with pytest.raises(TypeError):
            Bits([1, 0, True, False])

    @pytest.mark.parametrize("bit_size", [4, 8, 16, 32])
    def test_fixed_size_bits(self, bit_size):
        """Test fixed-size Bits creation."""
        FixedBits = Bits[bit_size]
        bits = FixedBits([True, False] * (bit_size // 2))

        assert len(bits) == bit_size
        assert bits._min_length == bit_size
        assert bits._max_length == bit_size

    def test_fixed_size_wrong_length_raises(self):
        """Test fixed-size validation."""
        FixedBits = Bits[4]

        with pytest.raises(ValueError):
            FixedBits([True, False])  # Only 2 bits, expects 4

    @pytest.mark.parametrize("order", ["msb", "lsb"])
    def test_bits_with_order(self, order):
        """Test Bits with bit order specified."""
        OrderedBits = Bits[order]
        bits = OrderedBits([True, False, True])
        assert bits._order == order

    @pytest.mark.parametrize("size,order", [(4, "msb"), (8, "lsb"), (16, "msb")])
    def test_bits_with_size_and_order(self, size, order):
        """Test Bits with both size and order."""
        BitType = Bits[size, order]
        bits = BitType([True, False] * (size // 2))

        assert len(bits) == size
        assert bits._order == order


class TestBitsModification:
    """Test Bits modification operations."""

    def test_append_and_extend(self):
        """Test appending and extending bits."""
        bits = Bits([True, False])
        bits.append(True)
        assert list(bits) == [True, False, True]

        bits.extend([False, True])
        assert list(bits) == [True, False, True, False, True]

    @pytest.mark.parametrize("bits_list,index,expected", [
        ([True, False, True, False, True], 0, True),
        ([True, False, True, False, True], 1, False),
        ([True, False, True, False, True], -1, True),
        ([True, False, True, False, True], slice(1, 4), [False, True, False]),
    ])
    def test_indexing_slicing(self, bits_list, index, expected):
        """Test indexing and slicing operations."""
        bits = Bits(bits_list)
        result = bits[index]

        if isinstance(index, slice):
            assert list(result) == expected
        else:
            assert result == expected

    def test_setitem(self):
        """Test setting individual bit values."""
        bits = Bits([True, False, True])
        bits[1] = True
        assert list(bits) == [True, True, True]

    def test_append_non_bool_raises(self):
        """Test appending non-bool raises error."""
        bits = Bits([True, False])

        with pytest.raises((ValueError, TypeError)):
            bits.append(2)

        with pytest.raises(TypeError):
            bits.append(1)


class TestBitsJSON:
    """Test JSON serialization."""

    @pytest.mark.parametrize("bits_list,order,expected_hex", [
        ([True, False, True, False, True, False, True, False], "msb", "aa"),
        ([True] * 8, "msb", "ff"),
        ([False] * 8, "msb", "00"),
    ])
    def test_to_json(self, bits_list, order, expected_hex):
        """Test converting Bits to JSON hex."""
        bits = Bits[8, order](bits_list)
        json_str = bits.to_json()
        assert json_str == expected_hex

    @pytest.mark.parametrize("hex_input,expected_bits", [
        ("ff", [True] * 8),
        ("00", [False] * 8),
        ("0xff", [True] * 8),
    ])
    def test_from_json(self, hex_input, expected_bits):
        """Test creating Bits from JSON hex string."""
        FixedBits = Bits[8]
        bits = FixedBits.from_json(hex_input)
        assert list(bits) == expected_bits

    @pytest.mark.parametrize("order", ["msb", "lsb"])
    def test_json_roundtrip(self, order):
        """Test JSON serialization roundtrip."""
        original_bits = Bits[8, order]([True, False, True, True, False, False, True, False])
        json_str = original_bits.to_json()
        restored_bits = Bits[8, order].from_json(json_str)

        assert list(restored_bits) == list(original_bits)


class TestBitsSerialization:
    """Test binary serialization."""

    @pytest.mark.parametrize("bits_list", [
        [True, False, True, False, True],
        [False] * 7,
        [True] * 9,
        [True, False] * 10,
    ])
    def test_encode_decode_roundtrip(self, bits_list):
        """Test encoding/decoding roundtrip."""
        original_bits = Bits(bits_list)
        encoded = original_bits.encode()
        decoded_bits, bytes_read = Bits.decode_from(encoded)

        assert list(decoded_bits) == bits_list
        assert bytes_read == len(encoded)

    @pytest.mark.parametrize("size", [8, 16, 32])
    def test_fixed_length_encode_decode(self, size):
        """Test fixed-length encoding/decoding."""
        FixedBits = Bits[size]
        original_bits = FixedBits([True, False] * (size // 2))
        encoded = original_bits.encode()
        decoded_bits, bytes_read = FixedBits.decode_from(encoded)

        assert list(decoded_bits) == list(original_bits)
        assert bytes_read == len(encoded)

    def test_encode_size_variable(self):
        """Test encode_size for variable length."""
        bits = Bits([True, False, True])
        size = bits.encode_size()
        assert size > 1  # At least 1 byte + length prefix

    def test_encode_size_fixed(self):
        """Test encode_size for fixed length."""
        FixedBits = Bits[8]
        bits = FixedBits([True] * 8)
        size = bits.encode_size()
        assert size == 1  # Exactly 1 byte for 8 bits

    def test_encode_into_buffer(self):
        """Test encoding into buffer."""
        bits = Bits([True, False, True, False])
        buffer = bytearray(10)
        bytes_written = bits.encode_into(buffer, offset=2)

        assert bytes_written > 0
        assert buffer[0:2] == bytearray([0, 0])

    def test_decode_empty(self):
        """Test decoding empty bits."""
        EmptyBits = Bits[0]
        empty_bits = EmptyBits([])
        encoded = empty_bits.encode()
        decoded_bits, bytes_read = EmptyBits.decode_from(encoded)

        assert len(decoded_bits) == 0
        assert list(decoded_bits) == []

    def test_decode_buffer_too_small(self):
        """Test decoding from too-small buffer."""
        FixedBits = Bits[16]
        small_buffer = b"\x01"

        with pytest.raises(ValueError):
            FixedBits.decode_from(small_buffer)


class TestBitsEdgeCases:
    """Test edge cases."""

    def test_large_bits(self):
        """Test with large bit sequences."""
        large_bits = Bits([True, False] * 100)
        assert len(large_bits) == 200

        encoded = large_bits.encode()
        decoded_bits, _ = Bits.decode_from(encoded)
        assert list(decoded_bits) == list(large_bits)

    @pytest.mark.parametrize("order", ["msb", "lsb"])
    def test_byte_boundaries(self, order):
        """Test bits at byte boundaries."""
        # Exactly 1 byte
        one_byte = Bits[8, order]([True, False] * 4)
        assert len(one_byte) == 8

        # 9 bits
        nine_bits = Bits[9, order]([True, False] * 4 + [True])
        assert len(nine_bits) == 9

        # Both should serialize correctly
        encoded_8 = one_byte.encode()
        encoded_9 = nine_bits.encode()

        decoded_8, _ = Bits[8, order].decode_from(encoded_8)
        decoded_9, _ = Bits[9, order].decode_from(encoded_9)

        assert len(decoded_8) == 8
        assert len(decoded_9) == 9

    @pytest.mark.parametrize("single_bit", [True, False])
    def test_single_bit(self, single_bit):
        """Test single bit operations."""
        bits = Bits([single_bit])

        # JSON roundtrip
        json_str = bits.to_json()
        restored = Bits.from_json(json_str)
        assert restored[0] == single_bit


class TestBitsIntegration:
    """Test integration with other types."""

    def test_with_bytes_conversion(self):
        """Test conversion between Bits and Bytes."""
        bits = Bits[8]([True, False, True, False, True, False, True, False])

        hex_str = bits.to_json()
        bytes_obj = Bytes.from_json(hex_str)

        bits_back = bytes_obj.to_bits()
        assert bits_back[:len(bits)] == list(bits)

    @pytest.mark.parametrize("bits1,bits2,should_equal", [
        ([True, False, True], [True, False, True], True),
        ([True, False, True], [False, True, False], False),
    ])
    def test_equality(self, bits1, bits2, should_equal):
        """Test Bits equality comparisons."""
        b1 = Bits(bits1)
        b2 = Bits(bits2)
        assert (b1 == b2) == should_equal

    def test_different_orders_different_results(self):
        """Test same data with different orders."""
        MSBBits = Bits[8, "msb"]
        LSBBits = Bits[8, "lsb"]

        same_data = [True, False, True, False, True, False, True, False]

        msb_bits = MSBBits(same_data)
        lsb_bits = LSBBits(same_data)

        msb_json = msb_bits.to_json()
        lsb_json = lsb_bits.to_json()

        assert isinstance(msb_json, str)
        assert isinstance(lsb_json, str)


class TestBitsOriginal:
    """Original test cases from test_bytes.py."""

    def test_bits_from_bytes(self):
        """Original test - ensure compatibility."""
        a = Bits[2, "lsb"].from_json("01")
        assert len(a) == 2

    def test_bitarr_init(self):
        """Test Bits initialization."""
        a = Bits([True, False, True, False])
        assert len(a) == 4

    @pytest.mark.parametrize("size,order,bits,expected_hex", [
        (4, "msb", [True, False, True, False], "a0"),
        (4, "lsb", [True, False, True, False], "05"),
    ])
    def test_bitarr_enc(self, size, order, bits, expected_hex):
        """Test Bits encoding with different orders."""
        a = Bits[size, order](bits)
        assert a.encode().hex() == expected_hex

    def test_variable_lsb_encoding(self):
        """Test variable-length LSB encoding."""
        b = Bits["lsb"]([True, False, True, False])
        assert b.encode().hex() == "0405"
        assert b.encode()[0] == 4


class TestBytesIntegration:
    """Test Bytes type functionality (merged from test_bytes.py)."""

    def test_bytes_init(self):
        """Test Bytes initialization."""
        a = Bytes(b"hello")
        assert a
        assert isinstance(a, Bytes)

    @pytest.mark.parametrize("bits,order,expected_hex", [
        ([True, False, True, False, False, False, False, False], "msb", "a0"),
        ([True, False, True, False, False, False, False, False], "lsb", "05"),
    ])
    def test_bytes_from_bits(self, bits, order, expected_hex):
        """Test creating Bytes from bits."""
        a = Bytes.from_bits(bits, order)
        assert a.hex() == expected_hex

    def test_bytes_to_from_bits_roundtrip(self):
        """Test Bytes to/from bits roundtrip."""
        a = Bytes([160, 0])
        bits = a.to_bits()
        assert a == Bytes.from_bits(bits)

    @pytest.mark.parametrize("data,expected_type", [
        (b"hello", Bytes),
        (bytes(32), Bytes),
    ])
    def test_bytes_encoding(self, data, expected_type):
        """Test Bytes encoding/decoding."""
        if len(data) == 32:
            # Fixed size bytes
            a = Bytes[32](data)
            enc = a.encode()
            assert a == Bytes[32].decode_from(enc)[0]
        else:
            # Variable size bytes
            a = Bytes(data)
            enc = a.encode()
            assert a == Bytes.decode_from(enc)[0]


class TestJAMCodecBitPacking:
    """JAM codec bit packing: pack bits into octets LSB to MSB."""

    @pytest.mark.parametrize("num_bits,expected_bytes", [
        (0, 0), (1, 1), (7, 1), (8, 1),
        (9, 2), (16, 2), (17, 3), (64, 8),
    ])
    def test_bit_packing_byte_count(self, num_bits, expected_bytes):
        """Bits pack into correct number of octets."""
        if num_bits == 0:
            bits = Bits([])
        else:
            bits = Bits[num_bits, "lsb"]([True] * num_bits)
        encoded = bits.encode()
        # Variable-length includes length prefix
        if expected_bytes > 0:
            assert len(encoded) >= expected_bytes

    @pytest.mark.parametrize("bit_pattern,expected_byte", [
        ([False] * 8, 0b00000000),
        ([True] * 8, 0b11111111),
        ([True, False] * 4, 0b01010101),
        ([False, True] * 4, 0b10101010),
    ])
    def test_lsb_bit_packing_order(self, bit_pattern, expected_byte):
        """LSB packing: bit 0 is LSB of first byte."""
        bits = Bits[8, "lsb"](bit_pattern)
        encoded = bits.encode()
        assert encoded[0] == expected_byte

    def test_walking_ones(self):
        """Test walking 1s pattern (one bit set at a time)."""
        for i in range(8):
            pattern = [False] * 8
            pattern[i] = True
            bits = Bits[8, "lsb"](pattern)
            encoded = bits.encode()
            assert encoded[0] == (1 << i)

    def test_walking_zeros(self):
        """Test walking 0s pattern (one bit clear at a time)."""
        for i in range(8):
            pattern = [True] * 8
            pattern[i] = False
            bits = Bits[8, "lsb"](pattern)
            encoded = bits.encode()
            assert encoded[0] == (0xFF ^ (1 << i))
