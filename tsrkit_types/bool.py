from typing import Tuple, Union
from tsrkit_types.itf.codable import Codable


class Bool(Codable):
    _value: bool
    def __init__(self, value: bool):
        self._value = value

    def __bool__(self):
        return bool(self._value)
    
    # ---------------------------------------------------------------------------- #
    #                                 Serialization                                #
    # ---------------------------------------------------------------------------- #
    
    def encode_size(self) -> int:
        return 1
    
    def encode_into(self, buffer: bytearray, offset: int = 0) -> int:
        buffer[offset] = int(self._value)
        return 1
    
    @classmethod
    def decode_from(cls, buffer: Union[bytes, bytearray, memoryview], offset: int = 0) -> Tuple["Bool", int]:
        return cls(bool(buffer[offset])), 1
    
    # ---------------------------------------------------------------------------- #
    #                                  JSON Parse                                  #
    # ---------------------------------------------------------------------------- #
    
    def to_json(self) -> bool:
        return bool(self)
    
    @classmethod
    def from_json(cls, data: bool) -> "Bool":
        return cls(data)