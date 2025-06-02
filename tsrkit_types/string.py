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
    def encode_size(self) -> int:
        return len(self.encode())
    
    def encode_into(self, buffer: bytearray, offset: int = 0) -> int:
        current_offset = offset
        current_offset += Uint(len(self)).encode_into(buffer, current_offset)
        buffer[current_offset:current_offset + len(self)] = self.encode()
        return current_offset + len(self) - offset
    
    @classmethod
    def decode_from(cls, buffer: Union[bytes, bytearray, memoryview], offset: int = 0) -> Tuple["String", int]:
        current_offset = offset
        str_len, size = Uint.decode_from(buffer, current_offset)
        current_offset += size
        return cls(buffer[current_offset:current_offset + str_len].decode()), current_offset + str_len - offset
    
    # ---------------------------------------------------------------------------- #
    #                                  JSON Serde                                  #
    # ---------------------------------------------------------------------------- #
    def to_json(self) -> str:
        return self
    
    @classmethod
    def from_json(cls, data: str) -> "String":
        return cls(data)