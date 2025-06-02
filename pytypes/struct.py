from dataclasses import dataclass, fields
from typing import Any, Tuple, Union

from pytypes.itf.codable import Codable


def struct(_cls=None, *, frozen=False, **kwargs):
    """Extension of dataclass to support serialization and json operations. 

    Usage:
        >>> @struct
        >>> class Person:
        >>>     name: String @field(json_meta={"name": "first_name"})
        >>>     age: Uint[8] @field(json_meta={"default": 0})

    """
    def wrap(cls):
        new_cls = type(cls.__name__, (Codable, cls), dict(cls.__dict__))
        new_cls = dataclass(new_cls, frozen=frozen, **kwargs)

        def encode_into(self, buffer: bytes, offset = 0) -> int:
            current_offset = offset
            for field in fields(self):
                item = getattr(self, field.name)
                size = item.encode_into(buffer, current_offset)
                current_offset += size

            return current_offset - offset
            
        @classmethod
        def decode_from(cls, buffer: Union[bytes, bytearray, memoryview], offset: int = 0) -> Tuple[Any, int]:
            current_offset = offset
            decoded_values = []
            for field in fields(cls): 
                field_type = field.type
                value, size = field_type.decode_from(buffer, current_offset)
                decoded_values.append(value)
                current_offset += size
            instance = cls(*decoded_values)
            return instance, current_offset - offset 
        
        def to_json(self) -> dict:
            return {field.get("json_meta", {}).get("name", field.name): getattr(self, field.name).to_json() for field in fields(self)}
        
        @classmethod
        def from_json(cls, data: dict) -> Any:
            for k, v in data.items():
                field = next((f for f in fields(cls) if f.get("json_meta", {}).get("name", f.name) == k), None)
                if field is None:
                    if field.get("json_meta", {}).get("default") is not None:
                        setattr(cls, field.name, field.get("json_meta", {}).get("default"))
                    else:
                        raise ValueError(f"Field {k} not found in {cls}")
                else:
                    setattr(cls, field.name, field.type.from_json(v))
            return cls()


        new_cls.decode_from = decode_from
        new_cls.encode_into = encode_into
        new_cls.to_json = to_json
        new_cls.from_json = from_json

        return new_cls

    return wrap if _cls is None else wrap(_cls)
