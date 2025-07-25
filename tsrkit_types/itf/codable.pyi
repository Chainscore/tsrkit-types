"""
Stub interface for types that can be encoded and decoded.

This file supports the `Codable` protocol, which defines methods for encoding,
decoding, and JSON serialization/deserialization of objects.

It is intended to be used with type checking tools and does not contain
actual implementations.
"""
from typing import Protocol, Tuple, TypeVar, Union, runtime_checkable

_ReadBuf = Union[bytes, bytearray, memoryview]
_T = TypeVar("_T", bound="Codable")

@runtime_checkable
class Codable(Protocol):
    def encode(self) -> bytes: ...
    def encode_size(self) -> int: ...
    def encode_into(self, buffer: bytearray, offset: int = 0) -> int: ...
    def to_json(self) -> dict: ...

    @classmethod
    def decode(cls: type[_T], data: _ReadBuf) -> _T: ...
    @classmethod
    def decode_from(cls: type[_T], buffer: _ReadBuf, offset: int = 0) -> Tuple[_T, int]: ...
    @classmethod
    def from_json(cls: type[_T], data: dict) -> _T: ...