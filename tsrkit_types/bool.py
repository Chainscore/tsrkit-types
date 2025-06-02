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
    
    def to_json(self) -> str:
        return "true" if self._value else "false"
    
    @classmethod
    def from_json(cls, json_str: str) -> "Bool":
        if json_str == "true":
            return cls(True)
        if json_str == "false":
            return cls(False)
        raise ValueError("Invalid JSON string for Bool")