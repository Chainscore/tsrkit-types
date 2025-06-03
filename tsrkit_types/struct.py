from dataclasses import dataclass, fields
from typing import Any, Tuple, Union
from tsrkit_types.itf.codable import Codable


def structure(_cls=None, *, frozen=False, **kwargs):
    """Extension of dataclass to support serialization and json operations. 

    Usage:
        >>> @structure
        >>> class Person:
        >>>     name: String = field(metadata={"name": "first_name"})
        >>>     age: Uint[8] = field(metadata={"default": 0})

    """
    def wrap(cls):
        new_cls = dataclass(cls, frozen=frozen, **kwargs)

        orig_init = new_cls.__init__

        def __init__(self, *args, **kwargs):
            for field in fields(self):
                # If the field is not found, but has a default, set it
                if field.name not in kwargs and field.metadata.get("default") is not None:
                    kwargs[field.name] = field.metadata.get("default")
            orig_init(self, *args, **kwargs)

        def encode_size(self) -> int:
            return sum(getattr(self, field.name).encode_size() for field in fields(self))

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
            decoded_values = {}
            for field in fields(cls): 
                field_type = field.type
                value, size = field_type.decode_from(buffer, current_offset)
                decoded_values[field.name] = value
                current_offset += size
            instance = cls(**decoded_values)
            return instance, current_offset - offset
        
        def to_json(self) -> dict:
            return {field.metadata.get("name", field.name): getattr(self, field.name).to_json() for field in fields(self)}
        
        @classmethod
        def from_json(cls, data: dict) -> Any:
            init_data = {}
            for field in fields(cls):
                k = field.metadata.get("name", field.name)
                v = data.get(k)
                if v is None:
                    if field.metadata.get("default") is not None:
                        init_data[field.name] = field.metadata.get("default")
                    else:
                        raise ValueError(f"Field {k} not found in {cls}")
                else:
                    init_data[field.name] = field.type.from_json(v)
            return cls(**init_data)


        new_cls.__init__ = __init__
        new_cls.encode_size = encode_size
        new_cls.decode_from = decode_from
        new_cls.encode_into = encode_into
        new_cls.to_json = to_json
        new_cls.from_json = from_json

        new_cls = type(new_cls.__name__, (Codable, new_cls), dict(new_cls.__dict__))

        return new_cls

    return wrap if _cls is None else wrap(_cls)


# Backward compatibility alias
struct = structure
