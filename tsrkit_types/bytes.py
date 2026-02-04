import abc
from typing import ClassVar, Optional
from tsrkit_types.itf.codable import Codable
from tsrkit_types.bytes_common import BytesMixin

from tsrkit_types import _native

class BytesCheckMeta(abc.ABCMeta):
    """Meta class to check if the instance is a bytes with the same key and value types"""
    def __instancecheck__(cls, instance):
        # TODO - This needs more false positive testing
        _matches_length = str(getattr(cls, "_length", None)) == str(getattr(instance, "_length", None))
        return isinstance(instance, bytes) and _matches_length


def _bytes_class_getitem(cls, params):
    _len = None
    name = cls.__class__.__name__
    if params and params > 0:
        _len = params
        name = f"ByteArray{_len}"
    return type(name, (cls,), {
        "_length": _len,
    })


class Bytes(_native.NativeBytes, Codable, BytesMixin, metaclass=BytesCheckMeta):
    """Fixed Size Bytes (native-backed)."""

    _length: ClassVar[Optional[int]] = None

    def __class_getitem__(cls, params):
        return _bytes_class_getitem(cls, params)

    def __deepcopy__(self, memo):
        # immutable; safe to reuse or create a new same-typed instance
        existing = memo.get(id(self))
        if existing is not None:
            return existing
        new = type(self)(bytes(self))
        memo[id(self)] = new
        return new
        
Bytes16 = Bytes[16]
Bytes32 = Bytes[32]
Bytes64 = Bytes[64]
Bytes128 = Bytes[128]
Bytes256 = Bytes[256]
Bytes512 = Bytes[512]
Bytes1024 = Bytes[1024]
