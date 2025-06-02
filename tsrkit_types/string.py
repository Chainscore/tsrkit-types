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
        buffer = bytearray(self.encode_size())
        self.encode_into(buffer)
        return buffer
    
    def encode_size(self) -> int:
        utf8_bytes = str(self).encode('utf-8')
        return Uint(len(utf8_bytes)).encode_size() + len(utf8_bytes)
    
    def encode_into(self, buffer: bytearray, offset: int = 0) -> int:
        current_offset = offset
        utf8_bytes = str(self).encode('utf-8')
        current_offset += Uint(len(utf8_bytes)).encode_into(buffer, current_offset)
        buffer[current_offset:current_offset + len(utf8_bytes)] = utf8_bytes
        return current_offset + len(utf8_bytes) - offset
    
    @classmethod
    def decode_from(cls, buffer: Union[bytes, bytearray, memoryview], offset: int = 0) -> Tuple["String", int]:
        current_offset = offset
        byte_len, size = Uint.decode_from(buffer, current_offset)
        current_offset += size
        utf8_bytes = buffer[current_offset:current_offset + byte_len]
        return cls(utf8_bytes.decode('utf-8')), current_offset + byte_len - offset
    
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