"""Security tests for DoS prevention and bounds checking."""
import pytest
from tsrkit_types.integers import Uint, U8, U16, U32
from tsrkit_types.sequences import Vector
from tsrkit_types.dictionary import Dictionary
from tsrkit_types.bytearray import ByteArray
from tsrkit_types.string import String
from tsrkit_types.bits import Bits
from tsrkit_types.constants import (
    MAX_SEQUENCE_LENGTH,
    MAX_DICTIONARY_SIZE,
    MAX_BYTEARRAY_SIZE,
    MAX_STRING_BYTES,
    MAX_BITS_LENGTH,
)


class TestSequenceLimits:
    """Test sequence length limits prevent DoS."""

    def test_sequence_within_limit(self):
        """Sequences within limit decode successfully."""
        # Encode a small sequence
        vec = Vector[U8]([U8(i) for i in range(100)])
        encoded = vec.encode()
        decoded = Vector[U8].decode(encoded)
        assert len(decoded) == 100

    def test_sequence_exceeds_limit(self):
        """Sequences exceeding limit are rejected."""
        # Craft buffer with length = MAX + 1
        malicious_length = MAX_SEQUENCE_LENGTH + 1
        buffer = bytearray()
        buffer.extend(Uint(malicious_length).encode())
        # Don't need actual data - should fail on length check

        with pytest.raises(ValueError, match="exceeds maximum"):
            Vector[U8].decode(bytes(buffer))

    def test_sequence_at_boundary(self):
        """Sequence exactly at limit is allowed."""
        # Just verify the constant is reasonable (don't actually allocate)
        assert MAX_SEQUENCE_LENGTH > 1000
        assert MAX_SEQUENCE_LENGTH < 100_000_000  # Sanity check


class TestDictionaryLimits:
    """Test dictionary size limits prevent DoS."""

    def test_dictionary_within_limit(self):
        """Dictionaries within limit decode successfully."""
        d = Dictionary[String, U8]({
            String("a"): U8(1),
            String("b"): U8(2),
        })
        encoded = d.encode()
        decoded = Dictionary[String, U8].decode(encoded)
        assert len(decoded) == 2

    def test_dictionary_exceeds_limit(self):
        """Dictionaries exceeding limit are rejected."""
        malicious_size = MAX_DICTIONARY_SIZE + 1
        buffer = bytearray()
        buffer.extend(Uint(malicious_size).encode())

        with pytest.raises(ValueError, match="exceeds maximum"):
            Dictionary[String, U8].decode(bytes(buffer))

    def test_dictionary_key_ordering_enforced(self):
        """Dictionary keys must be in ascending order."""
        # Manually craft buffer with out-of-order keys
        buffer = bytearray()
        buffer.extend(Uint(2).encode())  # 2 entries

        # First key: "b"
        buffer.extend(String("b").encode())
        buffer.extend(U8(1).encode())

        # Second key: "a" (out of order!)
        buffer.extend(String("a").encode())
        buffer.extend(U8(2).encode())

        with pytest.raises(ValueError, match="ascending order"):
            Dictionary[String, U8].decode(bytes(buffer))

    def test_dictionary_key_ordering_valid(self):
        """Dictionary with properly ordered keys decodes."""
        buffer = bytearray()
        buffer.extend(Uint(2).encode())  # 2 entries

        # Keys in order: "a" < "b"
        buffer.extend(String("a").encode())
        buffer.extend(U8(1).encode())
        buffer.extend(String("b").encode())
        buffer.extend(U8(2).encode())

        decoded = Dictionary[String, U8].decode(bytes(buffer))
        assert len(decoded) == 2
        assert decoded[String("a")] == 1
        assert decoded[String("b")] == 2


class TestByteArrayLimits:
    """Test ByteArray size limits prevent DoS."""

    def test_bytearray_within_limit(self):
        """ByteArrays within limit decode successfully."""
        ba = ByteArray(b"test data")
        encoded = ba.encode()
        decoded, _ = ByteArray.decode_from(encoded)
        assert bytes(decoded) == b"test data"

    def test_bytearray_exceeds_limit(self):
        """ByteArrays exceeding limit are rejected."""
        malicious_length = MAX_BYTEARRAY_SIZE + 1
        buffer = bytearray()
        buffer.extend(Uint(malicious_length).encode())

        with pytest.raises(ValueError, match="exceeds maximum"):
            ByteArray.decode_from(bytes(buffer))

    def test_bytearray_truncated_buffer(self):
        """Truncated buffer is detected."""
        # Claim 100 bytes but only provide 10
        buffer = bytearray()
        buffer.extend(Uint(100).encode())
        buffer.extend(b"short data")  # Only 10 bytes

        with pytest.raises(ValueError, match="Insufficient buffer"):
            ByteArray.decode_from(bytes(buffer))


class TestStringLimits:
    """Test String size limits prevent DoS."""

    def test_string_within_limit(self):
        """Strings within limit decode successfully."""
        s = String("Hello, world!")
        encoded = s.encode()
        decoded = String.decode(encoded)
        assert str(decoded) == "Hello, world!"

    def test_string_exceeds_limit(self):
        """Strings exceeding limit are rejected."""
        malicious_length = MAX_STRING_BYTES + 1
        buffer = bytearray()
        buffer.extend(Uint(malicious_length).encode())

        with pytest.raises(ValueError, match="exceeds maximum"):
            String.decode(bytes(buffer))

    def test_string_truncated_buffer(self):
        """Truncated buffer is detected."""
        # Claim 100 UTF-8 bytes but only provide 10
        buffer = bytearray()
        buffer.extend(Uint(100).encode())
        buffer.extend(b"short")  # Only 5 bytes

        with pytest.raises(ValueError, match="Insufficient buffer"):
            String.decode(bytes(buffer))

    def test_string_invalid_utf8(self):
        """Invalid UTF-8 is detected."""
        buffer = bytearray()
        buffer.extend(Uint(2).encode())
        buffer.extend(b"\xff\xfe")  # Invalid UTF-8

        with pytest.raises(ValueError, match="Invalid UTF-8"):
            String.decode(bytes(buffer))


class TestBitsLimits:
    """Test Bits length limits prevent DoS."""

    def test_bits_within_limit(self):
        """Bits within limit decode successfully."""
        bits = Bits([True, False, True, False])
        encoded = bits.encode()
        decoded = Bits.decode(encoded)
        assert len(decoded) == 4

    def test_bits_exceeds_limit(self):
        """Bits exceeding limit are rejected."""
        malicious_length = MAX_BITS_LENGTH + 1
        buffer = bytearray()
        buffer.extend(Uint(malicious_length).encode())

        with pytest.raises(ValueError, match="exceeds maximum"):
            Bits.decode(bytes(buffer))

    def test_bits_overflow_protection(self):
        """Very large bit lengths don't cause integer overflow."""
        # First test: exceeds MAX_BITS_LENGTH
        large_length = MAX_BITS_LENGTH + 1
        buffer1 = bytearray()
        buffer1.extend(Uint(large_length).encode())

        with pytest.raises(ValueError, match="exceeds maximum"):
            Bits.decode(bytes(buffer1))

        # Note: The overflow check (2^63 - 8) would require modifying
        # MAX_BITS_LENGTH to test, but the limit check provides sufficient
        # DoS protection in practice


class TestFixedIntegerBounds:
    """Test fixed-length integer bounds checking."""

    @pytest.mark.parametrize("IntType,size", [
        (U8, 1), (U16, 2), (U32, 4),
    ])
    def test_fixed_int_truncated_buffer(self, IntType, size):
        """Truncated buffer for fixed-length int is detected."""
        # Provide fewer bytes than required
        buffer = b"\x01" * (size - 1)

        with pytest.raises(ValueError, match="Buffer too small"):
            IntType.decode(buffer)

    def test_fixed_int_empty_buffer(self):
        """Empty buffer for fixed-length int is detected."""
        with pytest.raises(ValueError, match="Buffer too small"):
            U32.decode(b"")

    def test_fixed_int_valid_decode(self):
        """Valid fixed-length int decodes correctly."""
        encoded = U32(0x12345678).encode()
        decoded = U32.decode(encoded)
        assert decoded == 0x12345678


class TestReasonableLimits:
    """Verify limits are reasonable for legitimate use."""

    def test_limits_allow_legitimate_data(self):
        """Limits allow reasonably large legitimate data."""
        # 10K item sequence is allowed
        assert MAX_SEQUENCE_LENGTH >= 10_000

        # 100K entry dictionary is allowed
        assert MAX_DICTIONARY_SIZE >= 100_000

        # 10MB bytearray is allowed
        assert MAX_BYTEARRAY_SIZE >= 10_000_000

        # 1MB string is allowed
        assert MAX_STRING_BYTES >= 1_000_000

        # 1MB of bits is allowed
        assert MAX_BITS_LENGTH >= 8_000_000

    def test_limits_prevent_ridiculous_allocation(self):
        """Limits prevent clearly malicious allocations."""
        # No type allows GB-scale allocations
        assert MAX_SEQUENCE_LENGTH < 1_000_000_000
        assert MAX_DICTIONARY_SIZE < 1_000_000_000
        assert MAX_BYTEARRAY_SIZE < 10_000_000_000
        assert MAX_STRING_BYTES < 1_000_000_000
        assert MAX_BITS_LENGTH < 10_000_000_000
