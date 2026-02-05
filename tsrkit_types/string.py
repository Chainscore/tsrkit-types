from typing import Union, Tuple

from tsrkit_types.integers import Uint
from tsrkit_types.itf.codable import Codable


class String(str, Codable):
    """
    UTF-8 encoded string type that implements the Codable interface.

    Examples:
        >>> s = String("Hello")
        >>> str(s)
        'Hello'
        >>> len(s)
        5
        >>> s.encode()
        b'\\x05Hello'  # Length prefix followed by UTF-8 bytes

    Note:
        String length is measured in UTF-16 code units, which means some Unicode
        characters (like emojis) may count as 2 units. This matches Python's
        string length behavior.
    """

    # ---------------------------------------------------------------------------- #
    #                                 Serialization                                #
    # ---------------------------------------------------------------------------- #
    def encode(self) -> bytes:
        utf8_bytes = str(self).encode("utf-8")
        buffer = bytearray(Uint(len(utf8_bytes)).encode_size() + len(utf8_bytes))
        offset = Uint(len(utf8_bytes)).encode_into(buffer, 0)
        buffer[offset:offset + len(utf8_bytes)] = utf8_bytes
        return buffer
    
    def encode_size(self) -> int:
        utf8_bytes = str(self).encode("utf-8")
        return Uint(len(utf8_bytes)).encode_size() + len(utf8_bytes)
    
    def encode_into(self, buffer: bytearray, offset: int = 0) -> int:
        current_offset = offset
        utf8_bytes = str(self).encode("utf-8")
        current_offset += Uint(len(utf8_bytes)).encode_into(buffer, current_offset)
        buffer[current_offset:current_offset + len(utf8_bytes)] = utf8_bytes
        return current_offset + len(utf8_bytes) - offset
    
    @classmethod
    def decode_from(cls, buffer: Union[bytes, bytearray, memoryview], offset: int = 0) -> Tuple["String", int]:
        from tsrkit_types.constants import MAX_STRING_BYTES

        current_offset = offset
        byte_len, size = Uint.decode_from(buffer, current_offset)
        current_offset += size

        # Security: Prevent DoS via unbounded allocation
        if byte_len > MAX_STRING_BYTES:
            raise ValueError(
                f"String byte length {byte_len} exceeds maximum {MAX_STRING_BYTES}"
            )

        # Security: Verify buffer has enough bytes
        if len(buffer) - current_offset < byte_len:
            raise ValueError(
                f"Insufficient buffer: expected {byte_len} UTF-8 bytes at offset {current_offset}, "
                f"have {len(buffer) - current_offset} bytes"
            )

        utf8_bytes = buffer[current_offset:current_offset + byte_len]

        # Security: Handle invalid UTF-8 with clear error message
        try:
            decoded_string = utf8_bytes.decode("utf-8")
        except UnicodeDecodeError as e:
            raise ValueError(
                f"Invalid UTF-8 data at offset {current_offset}: {e}"
            ) from e

        return cls(decoded_string), current_offset + byte_len - offset
    
    @classmethod
    def decode(cls, buffer: Union[bytes, bytearray, memoryview], offset: int = 0) -> Tuple["String", int]:
        value, bytes_read = cls.decode_from(buffer, offset)
        return value
    
    # ---------------------------------------------------------------------------- #
    #                                  JSON Serde                                  #
    # ---------------------------------------------------------------------------- #
    def to_json(self) -> str:
        return self
    
    @classmethod
    def from_json(cls, data: str) -> "String":
        return cls(data)
