import abc
from typing import Any, Optional, Tuple, Union, Callable

from tsrkit_types import _native

try:
    from typing import Self
except ImportError:
    # For Python < 3.11, use TYPE_CHECKING and forward reference
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from typing import Self
    else:
        Self = "Uint"  # Forward reference string

from tsrkit_types.itf.codable import Codable


class IntCheckMeta(abc.ABCMeta):
    """Meta class to check if the instance is an integer with the same byte size"""
    def __instancecheck__(cls, instance):
        return isinstance(instance, int) and getattr(instance, "byte_size", 0) == cls.byte_size


class Int(int, Codable, metaclass=IntCheckMeta):
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
    signed = False
    _bound = 1 << 64
    
    @classmethod
    def __class_getitem__(cls, data: Optional[Union[int, tuple, bool]]):
        """
        Args:
            data: either byte_size or (byte_size, signed)
        """
        if data == None:
            size, signed = 0, False
        # If we have a single value arg - wither byte_size or signed
        elif not isinstance(data, tuple):
            if isinstance(data, int):
                size, signed = data, False
            else: 
                size, signed = 0, bool(data)
        else:
            size, signed = data 

        return type(f"U{size}" if size else "Int", (cls,), {
            "byte_size": size // 8, 
            "signed": signed, 
            "_bound": 1 << size if size > 0 else 1 << 64,
        })

    def __new__(cls, value: Any):
        value = int(value)
        if cls.byte_size > 0:
            max_v = (cls._bound // 2 if cls.signed else cls._bound) - 1  
            min_v = -1 * cls._bound // 2 if cls.signed else 0
        else:
            min_v = -1 * cls._bound // 2 if cls.signed else 0
            max_v = (cls._bound // 2 if cls.signed else cls._bound) - 1  
        
        if not (min_v <= value <= max_v):
                raise ValueError(f"Int: {cls.__name__} out of range: {value!r} "
                                f"not in [{min_v}, {max_v}]")
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
    def to_json(self) -> int:
        return int(self)
    
    @classmethod
    def from_json(cls, json_str: str) -> "Int":
        return cls(int(json_str))

    # ---------------------------------------------------------------------------- #
    #                                  Serialization                               #
    # ---------------------------------------------------------------------------- #
    @staticmethod
    def l(x: int) -> int:
        """Return variable-length byte count helper for non-trivial encoding."""
        if x <= 0:
            return 0
        return (int(x).bit_length() - 1) // 7
    
    def to_unsigned(self) -> "Int":
        if not self.signed: return self
        return int(self) + (self._bound // 2)

    def encode_size(self) -> int:
        if self.byte_size > 0:
            return self.byte_size 
        else:
            value = int(self)
            if self.signed:
                value += (self._bound >> 1)
            if value < (1 << 7):
                return 1
            elif value < (1 << 56):
                return 1 + ((value.bit_length() - 1) // 7)
            elif value < (1 << 64):
                return 9
            else:
                raise ValueError("Value too large for encoding. General Int support up to 2**64 - 1")

    def encode(self) -> bytes:
        return _native.uint_encode(int(self), self.byte_size, bool(self.signed))

    def encode_into(self, buffer: bytearray, offset: int = 0) -> int:
        data = _native.uint_encode(int(self), self.byte_size, bool(self.signed))
        self._check_buffer_size(buffer, len(data), offset)
        buffer[offset : offset + len(data)] = data
        return len(data)
    
    @classmethod
    def decode_from(
            cls, buffer: Union[bytes, bytearray, memoryview], offset: int = 0
    ) -> Tuple[Any, int]:
        value, size = _native.uint_decode(buffer, offset, cls.byte_size, bool(cls.signed))
        return cls(value), size
            
    def to_bits(self, bit_order: str = "msb") -> list[bool]:
        """Convert an int to bits"""
        if bit_order == "msb":
            return [bool((self >> i) & 1) for i in reversed(range(self.byte_size * 8 if self.byte_size > 0 else 64))]
        elif bit_order == "lsb":
            return [bool((self >> i) & 1) for i in range(self.byte_size * 8 if self.byte_size > 0 else 64)]
        else:
            raise ValueError(f"Invalid bit order: {bit_order}")
        
    @classmethod
    def from_bits(cls, bits: list[bool], bit_order: str = "msb") -> "Int":
        """Convert bits to an int"""
        if bit_order == "msb":
            return cls(int("".join(str(int(b)) for b in bits), 2))
        elif bit_order == "lsb":
            return cls(int("".join(str(int(b)) for b in reversed(bits)), 2))


Uint = Int
U8 = Int[8]
U16 = Int[16]
U32 = Int[32]
U64 = Int[64]
