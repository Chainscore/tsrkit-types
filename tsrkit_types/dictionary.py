import abc
from typing import (
    Generic,
    Mapping,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    Dict,
    Any,
    Sequence,
)

from tsrkit_types.integers import Uint
from tsrkit_types.itf.codable import Codable

K = TypeVar("K", bound=Codable)
V = TypeVar("V", bound=Codable)


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

    # Cache for sorted keys to avoid sorting on every encode
    _sorted_keys_cache: Optional[list]
    _dirty: bool

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
        super().__init__()
        self._sorted_keys_cache = None
        self._dirty = True
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
        self._dirty = True
        self._sorted_keys_cache = None

    def __repr__(self) -> str:
        """Get string representation."""
        items = [f"{k!r}: {v!r}" for k, v in self.items()]
        return f"Dictionary({{{', '.join(items)}}})"
    
    def update(self, other: Mapping[K, V]) -> None:
        for key, value in other.items():
            self._validate(key, value)
        super().update(other)
        self._dirty = True
        self._sorted_keys_cache = None

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
        total_size = 0
        total_size += Uint(len(self)).encode_size()
        for k, v in self.items():
            total_size += k.encode_size() + v.encode_size()
        return total_size
    
    def _get_sorted_items(self):
        """Get items in sorted order, with caching."""
        if self._dirty or self._sorted_keys_cache is None:
            # Sort keys - check if keys have natural ordering
            try:
                # Try natural ordering first (faster for int/str keys)
                self._sorted_keys_cache = sorted(self.keys())
            except TypeError:
                # Fall back to encoding-based comparison
                key_encoded = [(k, k.encode()) for k in self.keys()]
                self._sorted_keys_cache = [k for k, _ in sorted(key_encoded, key=lambda x: x[1])]
            self._dirty = False

        return [(k, self[k]) for k in self._sorted_keys_cache]

    def encode_into(self, buffer: bytearray, offset: int = 0) -> int:
        current_offset = offset
        current_offset += Uint(len(self)).encode_into(buffer, current_offset)
        for k, v in self._get_sorted_items():
            current_offset += k.encode_into(buffer, current_offset)
            current_offset += v.encode_into(buffer, current_offset)
        return current_offset - offset

    @classmethod
    def decode_from(cls, buffer: Union[bytes, bytearray, memoryview], offset: int = 0) -> Tuple["Dictionary[K, V]", int]:
        from tsrkit_types.constants import MAX_DICTIONARY_SIZE

        current_offset = offset
        dict_len, size = Uint.decode_from(buffer, offset)
        current_offset += size

        # Security: Prevent DoS via unbounded allocation
        if dict_len > MAX_DICTIONARY_SIZE:
            raise ValueError(
                f"Dictionary size {dict_len} exceeds maximum {MAX_DICTIONARY_SIZE}"
            )

        res = cls()
        prev_key = None

        for _ in range(dict_len):
            key, size = cls._key_type.decode_from(buffer, current_offset)
            current_offset += size

            # Security: Enforce key ordering per JAM spec
            if prev_key is not None and key <= prev_key:
                raise ValueError(
                    "Dictionary keys must be in strictly ascending order per JAM spec"
                )
            prev_key = key

            value, size = cls._value_type.decode_from(buffer, current_offset)
            current_offset += size
            res[key] = value

        return res, current_offset - offset