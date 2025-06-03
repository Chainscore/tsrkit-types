from typing import Optional, Tuple, Union


class NullType:
    def __repr__(self):
        return "Null"

    def __eq__(self, other):
        return not other

    def __bool__(self):
        return False
    
    # ---------------------------------------------------------------------------- #
    #                                 Serialization                                #
    # ---------------------------------------------------------------------------- #
    
    def encode_size(self) -> int:
        return 0
    
    def encode_into(self, buffer: bytearray, offset: int = 0) -> int:
        return 0
    
    @classmethod
    def decode_from(cls, buffer: Union[bytes, bytearray, memoryview], offset: int = 0) -> Tuple['NullType', int]:
        return cls(), 0
    
    # ---------------------------------------------------------------------------- #
    #                                  JSON Parse                                  #
    # ---------------------------------------------------------------------------- #

    def to_json(self) -> str:
        return None
    
    @classmethod
    def from_json(cls, json_str: Optional[str]) -> 'NullType':
        if json_str is None:
            return cls()
        raise ValueError("Invalid JSON string for NullType")
    
    
    
Null = NullType()