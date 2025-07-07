# PEP 681 – Data Class Transforms (built-in from Python 3.12).
# Fall back to ``typing_extensions`` for older interpreters so that
# static analysers can still understand the decorator without
# adding a hard runtime dependency.

from typing import Any, Tuple, Union, Type, TypeVar, Sequence, cast, Protocol, overload
from dataclasses import dataclass, fields

try:
    from typing import dataclass_transform  # type: ignore
except ImportError:  # pragma: no cover – <3.12
    from typing_extensions import dataclass_transform  # type: ignore
from tsrkit_types.itf.codable import Codable
from tsrkit_types.null import NullType
from tsrkit_types.option import Option


# Protocol for classes decorated with @structure
class StructuredClass(Protocol):
    """Protocol for classes decorated with @structure."""
    
    def encode_size(self) -> int: ...
    def encode_into(self, buffer: bytearray, offset: int = 0) -> int: ...
    def encode(self) -> bytes: ...
    def to_json(self) -> dict: ...
    
    @classmethod
    def decode_from(cls, buffer: Union[bytes, bytearray, memoryview], offset: int = 0) -> Tuple[Any, int]: ...
    @classmethod
    def decode(cls, buffer: Union[bytes, bytearray, memoryview], offset: int = 0) -> Any: ...
    @classmethod
    def from_json(cls, data: dict) -> Any: ...


@dataclass_transform(eq_default=True, order_default=False, kw_only_default=False)
def structure(_cls=None, *, frozen=False, **kwargs):
    """Extension of dataclass to support serialization and json operations. 

    Usage:
        >>> @structure
        >>> class Person:
        >>>     name: String = field(metadata={"name": "first_name"})
        >>>     age: Uint[8] = field(metadata={"default": 0})

    """
    def wrap(cls):
        # The *dataclass* decorator returns the class itself, but the
        # ``dataclasses.dataclass`` helper is typed to accept only a
        # subset of keyword-arguments.  Because we forward whatever the
        # user passes in *kwargs*, add a narrow ``type: ignore`` so that
        # static type-checkers don’t complain while runtime behaviour is
        # unchanged.

        new_cls = dataclass(cls, frozen=frozen, **kwargs)  # type: ignore[arg-type]

        orig_init = new_cls.__init__

        def __init__(self, *args, **kwargs):
            for field in fields(self):
                # If the field is not found, but has a default, set it
                if field.name not in kwargs and field.metadata.get("default") is not None:
                    kwargs[field.name] = field.metadata.get("default")
            orig_init(self, *args, **kwargs)

        def encode_size(self) -> int:
            total = 0
            for field in fields(self):
                item = getattr(self, field.name)
                if not (isinstance(item, Codable) or hasattr(item, "encode_size")):
                    raise TypeError(
                        f"Field '{field.name}' is expected to be Codable, "
                        f"got {type(item).__name__}"
                    )
                total += item.encode_size()
            return total

        def encode_into(self, buffer: bytearray, offset: int = 0) -> int:
            current_offset = offset
            for field in fields(self):
                item = getattr(self, field.name)
                if not (hasattr(item, "encode_into") and callable(item.encode_into)):
                    raise TypeError(
                        f"Field '{field.name}' is expected to implement 'encode_into', got {type(item).__name__}"
                    )
                size = cast(int, item.encode_into(buffer, current_offset))  # type: ignore[attr-defined]
                current_offset += size

            return current_offset - offset
            
        # ------------------------------------------------------------------
        # Decoding / JSON helpers – add type guards so static analysers know
        # the accessed attributes exist.
        # ------------------------------------------------------------------

        _T = TypeVar("_T", bound="Codable")

        @classmethod
        def decode_from(cls: Type[_T], buffer: Union[bytes, bytearray, memoryview], offset: int = 0) -> Tuple[_T, int]:  # type: ignore[name-defined]
            current_offset = offset
            decoded_values: dict[str, Any] = {}

            for field in fields(cast(Any, cls)):
                field_type: Any = field.type

                # Static guard – ensure the field’s annotation has the
                # required codec interface.
                if not (hasattr(field_type, "decode_from") and callable(field_type.decode_from)):
                    raise TypeError(
                        f"Type annotation for field '{field.name}' "
                        "does not implement 'decode_from'."
                    )

                value, size = cast(Any, field_type).decode_from(buffer, current_offset)
                decoded_values[field.name] = value
                current_offset += size

            instance = cls(**decoded_values)  # type: ignore[call-arg]
            return instance, current_offset - offset
        
        def to_json(self) -> dict:
            return {
                field.metadata.get("name", field.name): cast(Codable, getattr(self, field.name)).to_json()  # type: ignore[arg-type]
                for field in fields(self)
            }
        
        @classmethod
        def from_json(cls: Type[_T], data: dict) -> _T:  # type: ignore[name-defined]
            init_data: dict[str, Any] = {}

            for field in fields(cast(Any, cls)):
                k = field.metadata.get("name", field.name)
                v = data.get(k)

                if v is None and field.metadata.get("default") is not None:
                    init_data[field.name] = field.metadata.get("default")
                    continue

                field_type: Any = field.type
                if not (hasattr(field_type, "from_json") and callable(field_type.from_json)):
                    raise TypeError(
                        f"Type annotation for field '{field.name}' "
                        "does not implement 'from_json'."
                    )

                init_data[field.name] = cast(Any, field_type).from_json(v)

            return cls(**init_data)  # type: ignore[call-arg]


        new_cls.__init__ = __init__

        # Only overwrite if the method is not already defined
        if not new_cls.__dict__.get("encode_size"):
            new_cls.encode_size = encode_size
        if not new_cls.__dict__.get("decode_from"):
            new_cls.decode_from = decode_from
        if not new_cls.__dict__.get("encode_into"):
            new_cls.encode_into = encode_into
        if not new_cls.__dict__.get("to_json"):
            new_cls.to_json = to_json
        if not new_cls.__dict__.get("from_json"):
            new_cls.from_json = from_json

        new_cls = type(new_cls.__name__, (Codable, new_cls), dict(new_cls.__dict__))

        return new_cls

    return wrap if _cls is None else wrap(_cls)


# Backward compatibility alias
struct = structure
