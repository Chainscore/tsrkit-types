import abc
from typing import (
    Any,
    Dict,
    Generic,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from tsrkit_types.integers import Uint
from tsrkit_types.itf.codable import Codable

K = TypeVar("K", bound=Codable)
V = TypeVar("V", bound=Codable)

_MISSING = object()


class DictCheckMeta(abc.ABCMeta):
    """Meta class to check if the instance is a dictionary with the same key and value types"""
    def __instancecheck__(cls, instance):
        # TODO - This needs more false positive testing
        _matches_key_type = str(getattr(cls, "_key_type", None)) == str(getattr(instance, "_key_type", None))
        _matches_value_type = str(getattr(cls, "_value_type", None)) == str(getattr(instance, "_value_type", None))
        return isinstance(instance, dict) and _matches_key_type and _matches_value_type


class Dictionary(dict, Codable, Generic[K, V], metaclass=DictCheckMeta):
    """
    Dictionary implementation that supports codec operations.

    A dictionary that maps keys to values, providing both standard
    dictionary operations and codec functionality for serialization/deserialization.

    Examples:
        >>> from tsrkit_types.string import String
        >>> from tsrkit_types.integers import Uint
        >>> d = Dictionary({String("key"): Uint(42)})
        >>> d[String("key")]
        Uint(42)
        >>> encoded = d.encode()
        >>> decoded, _ = d.decode_from(encoded)
        >>> decoded == d
        True
    """

    _key_type: Type[K]
    _value_type: Type[V]

    _key_name: Optional[str]
    _value_name: Optional[str]

    def __class_getitem__(cls, params):
        if len(params) >= 2:
            return type(cls.__name__, (cls,), {
                "_key_type": params[0],
                "_value_type": params[1],
                "_key_name": params[2] if len(params) == 4 else None,
                "_value_name": params[3] if len(params) == 4 else None,
            })
        else:
            raise ValueError("Dictionary must be initialized with types as such - Dictionary[K, V, key_name(optional), value_name(optional)]")

    def __init__(self, initial: Optional[Mapping[K, V]] = None):
        self.update(initial or {})

    def _validate(self, key: K, value: V):
        if not isinstance(key, self._key_type):
            raise TypeError(f"Dictionary keys must be {self._key_type} but got {type(key)}")
        if not isinstance(value, self._value_type):
            raise TypeError(f"Dictionary values must be {self._value_type} but got {type(value)}")

    def __setitem__(self, key: K, value: V) -> None:
        """Set value for key."""
        self._validate(key, value)
        super().__setitem__(key, value)

    def __delitem__(self, key: K) -> None:
        super().__delitem__(key)

    def __repr__(self) -> str:
        """Get string representation."""
        items = [f"{k!r}: {v!r}" for k, v in self.items()]
        return f"Dictionary({{{', '.join(items)}}})"
    
    def update(self, other: Mapping[K, V]) -> None:
        if not other:
            return
        for key, value in other.items():
            self._validate(key, value)
        dict.update(self, other)

    def clear(self) -> None:
        if self:
            super().clear()

    def pop(self, key: K, default: object = _MISSING) -> V:
        value = super().pop(key, _MISSING)
        if value is _MISSING:
            if default is _MISSING:
                raise KeyError(key)
            return default  # type: ignore[return-value]
        return value  # type: ignore[return-value]

    def popitem(self) -> Tuple[K, V]:
        return super().popitem()

    def setdefault(self, key: K, default: Optional[V] = None) -> V:
        if key in self:
            return super().get(key)  # type: ignore[return-value]
        value = super().setdefault(key, default)  # type: ignore[arg-type]
        return value  # type: ignore[return-value]

    # ---------------------------------------------------------------------------- #
    #                                  JSON Serde                                  #
    # ---------------------------------------------------------------------------- #

    def to_json(self) -> Dict[Any, Any]:
        """Convert to JSON representation."""
        return {k.to_json(): v.to_json() for k, v in self.items()}

    @classmethod
    def from_json(cls: Type["Dictionary[K, V]"], data: Sequence[Any]) -> "Dictionary[K, V]":
        """Create instance from JSON representation."""
        if not isinstance(data, dict):
            _value = cls({})
            for val in data:
                _value[cls._key_type.from_json(val[cls._key_name])] = cls._value_type.from_json(val[cls._value_name])
            return _value
        else:
            return cls(
                {
                    cls._key_type.from_json(k): cls._value_type.from_json(v)
                    for k, v in data.items()
                }
            )

    # ---------------------------------------------------------------------------- #
    #                                  Serialization                               #
    # ---------------------------------------------------------------------------- #

    def encode_size(self) -> int:
        total_size = Uint(len(self)).encode_size()
        for k, v in sorted(self.items(), key=lambda item: item[0]):
            total_size += k.encode_size() + v.encode_size()
        return total_size
    
    def encode_into(self, buffer: bytearray, offset: int = 0) -> int:
        current_offset = offset
        current_offset += Uint(len(self)).encode_into(buffer, current_offset)
        for k, v in sorted(self.items(), key=lambda item: item[0]):
            current_offset += k.encode_into(buffer, current_offset)
            current_offset += v.encode_into(buffer, current_offset)
        return current_offset - offset

    @classmethod
    def decode_from(cls, buffer: Union[bytes, bytearray, memoryview], offset: int = 0) -> Tuple["Dictionary[K, V]", int]:
        current_offset = offset
        dict_len, size = Uint.decode_from(buffer, offset)
        current_offset += size
        res = cls()
        key_decode = cls._key_type.decode_from
        value_decode = cls._value_type.decode_from
        set_item = dict.__setitem__
        for _ in range(dict_len):
            key, size = key_decode(buffer, current_offset)
            current_offset += size
            value, size = value_decode(buffer, current_offset)
            current_offset += size
            set_item(res, key, value)
        return res, current_offset - offset
