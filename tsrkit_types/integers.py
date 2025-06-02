import abc
from decimal import Decimal
import math
from typing import Any, Tuple, Union, Callable
from tsrkit_types.itf.codable import Codable


class IntCheckMeta(abc.ABCMeta):
    """Meta class to check if the instance is an integer with the same byte size"""
    def __instancecheck__(cls, instance):
        return isinstance(instance, int) and getattr(instance, "byte_size", 0) == cls.byte_size


class Uint(int, Codable, metaclass=IntCheckMeta):
    """
    Unsigned integer type.
    
    
    Usage:
        >>> # Fixed Integer with defined class
        >>> U8 = Uint[8]
        >>> U8(10)
        U8(10)
        >>> U8.encode(10)
        b'\n'
        >>> U8.decode(b'\n')
        U8(10)

        >>> # Fixed Integer w dynamic usage
        >>> num = Uint[8](10)
        >>> num
        U8(10)
        >>> num.encode()
        b'\n'
        >>> Uint[8].decode(b'\n')
        U8(10)


        >>> # If you want to use the General Integer (supports up to 2**64 - 1), 
        >>> # you can use the Uint class without specifying the byte size.
        >>>
        >>> num = Uint(10)
        >>> num
        Uint(10)
        >>> num.encode()
        b'\n'
        >>> Uint.decode(b'\n')
        Uint(10)

    """

    # If the byte_size is set, the integer is fixed size.
    # Otherwise, the integer is General Integer (supports up to 2**64 - 1)
    byte_size: int = 0

    def __class_getitem__(cls, size: int):
        return type(f"U{size}" if size else "Int", (cls,), {"byte_size": size // 8})

    def __new__(cls, value: Any):
        value = int(value)
        if cls.byte_size > 0:
            bits = 8 * cls.byte_size
            min_v = 0
            max_v = (1 << bits) - 1
            if not (min_v <= value <= max_v):
                raise ValueError(f"Fixed Int: {cls.__name__} out of range: {value!r} "
                                f"not in [{min_v}, {max_v}]")
        else:
            if not 0 <= value < 2 ** 64:
                raise ValueError(f"General Int: Value must be between 0 and 2**64 - 1, got {value}")

        return super().__new__(cls, value)

    def __repr__(self):
        return f"{self.__class__.__name__}({int(self)})"

    def _wrap_op(self, other: Any, op: Callable[[int, int], int]):
        res = op(int(self), int(other))
        return type(self)(res)
    
    # ---------------------------------------------------------------------------- #
    #                                  Arithmetic                                  #
    # ---------------------------------------------------------------------------- #
    def __add__(self, other):
        return self._wrap_op(other, int.__add__)

    def __sub__(self, other):
        return self._wrap_op(other, int.__sub__)

    def __mul__(self, other):
        return self._wrap_op(other, int.__mul__)

    def __floordiv__(self, other):
        return self._wrap_op(other, int.__floordiv__)

    def __and__(self, other):
        return self._wrap_op(other, int.__and__)

    def __or__(self, other):
        return self._wrap_op(other, int.__or__)

    def __xor__(self, other):
        return self._wrap_op(other, int.__xor__)
    
    # ---------------------------------------------------------------------------- #
    #                                  JSON Serde                                  #
    # ---------------------------------------------------------------------------- #
    def to_json(self) -> str:
        return int(self)
    
    @classmethod
    def from_json(cls, json_str: str) -> "Uint":
        return cls(int(json_str))

    # ---------------------------------------------------------------------------- #
    #                                  Serialization                               #
    # ---------------------------------------------------------------------------- #
    @staticmethod
    def l(x):
        return math.floor(Decimal(x).ln() / (Decimal(7) * Decimal(2).ln()))


    def encode_size(self) -> int:
        if self.byte_size > 0:
            return self.byte_size 
        else:
            if self < 2**7:
                return 1
            elif self < 2 ** (7 * 9):
                return 1 + self.l(self)
            elif self < 2**64:
                return 9
            else:
                raise ValueError("Value too large for encoding. General Uint support up to 2**64 - 1")

    def encode_into(self, buffer: bytearray, offset: int = 0) -> int:
        if self.byte_size > 0:
            buffer[offset:offset+self.byte_size] = self.to_bytes(self.byte_size, "little")
            return self.byte_size
        else:
            if self < 2**7:
                buffer[offset:offset+1] = self.to_bytes(1, "little")
                return 1

            size = self.encode_size()
            self._check_buffer_size(buffer, size, offset)
            if self < 2 ** (7 * 8):
                _l = self.l(self)
                # Create temporary U8 for encoding the prefix
                prefix_value = (2**8 - 2 ** (8 - _l) + 
                               math.floor(Decimal(self) / (Decimal(2) ** (_l * 8))))
                buffer[offset] = int(prefix_value)
                offset += 1
                # Encode the remaining bytes
                remaining = self % (2 ** (_l * 8))
                remaining_bytes = remaining.to_bytes(_l, "little")
                buffer[offset : offset + _l] = remaining_bytes
            elif self < 2**64:
                buffer[offset] = 2**8 - 1  # Full 64-bit marker
                offset += 1
                buffer[offset : offset + 8] = self.to_bytes(8, "little")
            else:
                raise ValueError(
                    f"Value too large for encoding. General Uint support up to 2**64 - 1, got {self}"
                )
            return size
    
    @classmethod
    def decode_from(
            cls, buffer: Union[bytes, bytearray, memoryview], offset: int = 0
    ) -> Tuple[Any, int]:
        if cls.byte_size > 0:
            value, size = int.from_bytes(buffer[offset : offset + cls.byte_size], "little"), cls.byte_size
            return cls.__new__(cls, value), size
        else:
            tag = int.from_bytes(buffer[offset:offset+1], "little")

            if tag < 2**7:
                return cls(tag), 1

            if tag == 2**8 - 1:
                # Full 64-bit encoding
                if len(buffer) - offset < 9:
                    raise ValueError("Buffer too small to decode 64-bit integer")
                value = int.from_bytes(buffer[offset + 1 : offset + 9], "little")
                return cls(value), 9
            else:
                # Variable length encoding
                _l = math.floor(
                    Decimal(8) - (Decimal(2**8) - Decimal(tag)).ln() / Decimal(2).ln()
                )
                if len(buffer) - offset < _l + 1:
                    raise ValueError("Buffer too small to decode variable-length integer")
                alpha = tag + 2 ** (8 - _l) - 2**8
                beta = int.from_bytes(buffer[offset + 1 : offset + 1 + _l], "little")
                value = alpha * 2 ** (_l * 8) + beta
                return cls(value), _l + 1


U8 = Uint[8]
U16 = Uint[16]
U32 = Uint[32]
U64 = Uint[64]