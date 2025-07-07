import abc
from typing import Tuple, Union, ClassVar
from tsrkit_types.integers import Uint
from tsrkit_types.itf.codable import Codable
from tsrkit_types.bytes_common import BytesMixin

class BytesCheckMeta(abc.ABCMeta):
    """Meta class to check if the instance is a bytes with the same key and value types"""
    def __instancecheck__(cls, instance):
        # TODO - This needs more false positive testing
        _matches_length = str(getattr(cls, "_length", None)) == str(getattr(instance, "_length", None))
        return isinstance(instance, bytes) and _matches_length


class Bytes(bytes, Codable, BytesMixin, metaclass=BytesCheckMeta):
    """Fixed Size Bytes"""

    _length: ClassVar[Union[None, int]] = None

    def __class_getitem__(cls, params):
        _len = None
        name = cls.__class__.__name__
        if params and params > 0:
            _len = params
            name = f"ByteArray{_len}"
        return type(name, (cls,), {
            "_length": _len,
        })

    # Bit conversion methods inherited from BytesMixin
    
    # ---------------------------------------------------------------------------- #
    #                                 Serialization                                #
    # ---------------------------------------------------------------------------- #
    def encode_size(self) -> int:
        if self._length is None:
            return Uint(len(self)).encode_size() + len(self)
        return self._length
    
    def encode_into(self, buf: bytearray, offset: int = 0) -> int:
        current_offset = offset
        _len = self._length
        if _len is None:
            _len = len(self)
            current_offset += Uint(_len).encode_into(buf, current_offset)
        buf[current_offset:current_offset+_len] = self
        current_offset += _len
        return current_offset - offset
    
    @classmethod
    def decode_from(cls, buffer: Union[bytes, bytearray, memoryview], offset: int = 0) -> Tuple["Bytes", int]:
        current_offset = offset
        _len = cls._length

        if _len is None:
            _len, _inc_offset = Uint.decode_from(buffer, offset)
            current_offset += _inc_offset
        
        if len(buffer[current_offset:current_offset+_len]) < _len:
            raise TypeError("Insufficient buffer")
        return cls(buffer[current_offset:current_offset+_len]), current_offset + _len - offset
    
    # ---------------------------------------------------------------------------- #
    #                               JSON Serialization                             #
    # ---------------------------------------------------------------------------- #
    # JSON methods inherited from BytesMixin
        
Bytes16 = Bytes[16]
Bytes32 = Bytes[32]
Bytes64 = Bytes[64]
Bytes128 = Bytes[128]
Bytes256 = Bytes[256]
Bytes512 = Bytes[512]
Bytes1024 = Bytes[1024]
