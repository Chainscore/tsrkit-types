import abc
from typing import Generic, Mapping, Optional, Tuple, Type, TypeVar

from tsrkit_types.itf.codable import Codable
from tsrkit_types import _native

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


def _dict_class_getitem(cls, params):
    if len(params) >= 2:
        return type(cls.__name__, (cls,), {
            "_key_type": params[0],
            "_value_type": params[1],
            "_key_name": params[2] if len(params) == 4 else None,
            "_value_name": params[3] if len(params) == 4 else None,
        })
    raise ValueError("Dictionary must be initialized with types as such - Dictionary[K, V, key_name(optional), value_name(optional)]")


class Dictionary(_native.NativeDict, Codable, Generic[K, V], metaclass=DictCheckMeta):
    """
    Dictionary implementation that supports codec operations (native-backed).
    """

    _key_type: Type[K]
    _value_type: Type[V]

    _key_name: Optional[str]
    _value_name: Optional[str]

    def __class_getitem__(cls, params):
        return _dict_class_getitem(cls, params)

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
