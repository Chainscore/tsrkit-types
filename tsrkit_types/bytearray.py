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
        # Fast path: inline length encoding for small sizes
        if _len < 128:
            buf[current_offset] = _len
            current_offset += 1
        else:
            current_offset += Uint(_len).encode_into(buf, current_offset)
        buf[current_offset:current_offset+_len] = self
        current_offset += _len
        return current_offset - offset
    
    @classmethod
    def decode_from(cls, buffer: Union[bytes, bytearray, memoryview], offset: int = 0) -> Tuple["ByteArray", int]:
        from tsrkit_types.constants import MAX_BYTEARRAY_SIZE

        current_offset = offset
        # Inline length decoding for small sizes
        if len(buffer) > offset:
            tag = buffer[offset]
            if tag < 128:
                _len = tag
                current_offset += 1
            else:
                _len, _inc_offset = Uint.decode_from(buffer, offset)
                current_offset += _inc_offset
        else:
            # Empty buffer or buffer too small - delegate to Uint for consistent error
            _len, _inc_offset = Uint.decode_from(buffer, offset)
            current_offset += _inc_offset

        # Security: Prevent DoS via unbounded allocation
        if _len > MAX_BYTEARRAY_SIZE:
            raise ValueError(
                f"ByteArray length {_len} exceeds maximum {MAX_BYTEARRAY_SIZE}"
            )

        # Security: Verify buffer has enough bytes
        if len(buffer) - current_offset < _len:
            raise ValueError(
                f"Insufficient buffer: expected {_len} bytes at offset {current_offset}, "
                f"have {len(buffer) - current_offset} bytes"
            )

        return cls(buffer[current_offset:current_offset+_len]), current_offset + _len - offset
    
    # ---------------------------------------------------------------------------- #
    #                               JSON Serialization                             #
    # ---------------------------------------------------------------------------- #
    # JSON methods inherited from BytesMixin
    
