from typing import Tuple, Union
from tsrkit_types.integers import Uint
from tsrkit_types.itf.codable import Codable
from tsrkit_types.bytes_common import BytesMixin


class ByteArray(bytearray, Codable, BytesMixin):
    """Variable Size ByteArray"""

    # Bit conversion and JSON methods inherited from BytesMixin
    
    # ---------------------------------------------------------------------------- #
    #                                 Serialization                                #
    # ---------------------------------------------------------------------------- #
    def encode_size(self) -> int:
        return Uint(len(self)).encode_size() + len(self)
    
    def encode_into(self, buf: bytearray, offset: int = 0) -> int:
        current_offset = offset
        _len = len(self)
        current_offset += Uint(_len).encode_into(buf, current_offset)
        buf[current_offset:current_offset+_len] = self
        current_offset += _len
        return current_offset - offset
    
    @classmethod
    def decode_from(cls, buffer: Union[bytes, bytearray, memoryview], offset: int = 0) -> Tuple["ByteArray", int]:
        current_offset = offset
        _len, _inc_offset = Uint.decode_from(buffer, offset)
        current_offset += _inc_offset
        if len(buffer[current_offset:current_offset+_len]) < _len:
            raise TypeError("Insufficient buffer")
        return cls(buffer[current_offset:current_offset+_len]), current_offset + _len - offset
    
    # ---------------------------------------------------------------------------- #
    #                               JSON Serialization                             #
    # ---------------------------------------------------------------------------- #
    # JSON methods inherited from BytesMixin
    
