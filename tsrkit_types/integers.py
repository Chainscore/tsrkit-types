import abc
import math
import struct
from typing import Any, Optional, Tuple, Union, Callable

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

    # Cached struct objects for fast encoding/decoding of fixed-size integers
    _struct_cache = {
        1: struct.Struct('<B'),  # unsigned char
        2: struct.Struct('<H'),  # unsigned short
        4: struct.Struct('<I'),  # unsigned int
        8: struct.Struct('<Q'),  # unsigned long long
    }
    
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
            "_bound": 1 << size if size > 0 else 1 << 64
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
    def l(x):
        """Calculate length parameter using bit operations instead of logarithm."""
        if x < 128:  # 2^7
            return 0
        # For variable length encoding: l = floor((bit_length - 1) / 7)
        # This is mathematically equivalent to floor(log_2(x) / 7)
        return (x.bit_length() - 1) // 7
    
    def to_unsigned(self) -> "Int":
        if not self.signed: return self
        return int(self) + (self._bound // 2)

    def encode_size(self) -> int:
        if self.byte_size > 0:
            return self.byte_size
        else:
            value = self.to_unsigned()
            if value < 128:  # 2**7
                return 1
            elif value < 2 ** 56:  # 2 ** (7 * 8)
                # Calculate length using bit operations
                _l = (value.bit_length() - 1) // 7
                return 1 + _l
            elif value < 2**64:
                return 9
            else:
                raise ValueError("Value too large for encoding. General Int support up to 2**64 - 1")

    def encode_into(self, buffer: bytearray, offset: int = 0) -> int:
        if self.byte_size > 0:
            # Fast path: use cached struct for common sizes
            s = self._struct_cache.get(self.byte_size)
            if s:
                s.pack_into(buffer, offset, int(self))
            else:
                buffer[offset:offset+self.byte_size] = self.to_bytes(self.byte_size, "little")
            return self.byte_size
        else:
            value = int(self)

            # Fast path: single byte
            if value < 128:  # 2^7
                buffer[offset] = value
                return 1

            size = self.encode_size()
            self._check_buffer_size(buffer, size, offset)

            if value < 2 ** 56:  # 2^(7*8)
                _l = (value.bit_length() - 1) // 7

                # Calculate prefix using bit shifts instead of Decimal division
                alpha = value >> (_l * 8)
                prefix = (256 - (1 << (8 - _l))) + alpha
                buffer[offset] = prefix
                offset += 1

                # Encode the remaining bytes using mask
                beta = value & ((1 << (_l * 8)) - 1)
                remaining_bytes = beta.to_bytes(_l, "little")
                buffer[offset : offset + _l] = remaining_bytes
            elif value < 2**64:
                buffer[offset] = 255  # 2**8 - 1, Full 64-bit marker
                offset += 1
                buffer[offset : offset + 8] = value.to_bytes(8, "little")
            else:
                raise ValueError(
                    f"Value too large for encoding. General Uint support up to 2**64 - 1, got {value}"
                )
            return size
    
    @classmethod
    def decode_from(
            cls, buffer: Union[bytes, bytearray, memoryview], offset: int = 0
    ) -> Tuple[Any, int]:
        if cls.byte_size > 0:
            # Check buffer has enough bytes
            if len(buffer) < offset + cls.byte_size:
                raise ValueError(f"Buffer too small: need {cls.byte_size} bytes at offset {offset}, but buffer has only {len(buffer)} bytes")

            # Fast path: use cached struct for common sizes
            s = cls._struct_cache.get(cls.byte_size)
            if s:
                value = s.unpack_from(buffer, offset)[0]
            else:
                value = int.from_bytes(buffer[offset : offset + cls.byte_size], "little")
            return cls.__new__(cls, value), cls.byte_size
        else:
            tag = int.from_bytes(buffer[offset:offset+1], "little")

            if tag < 128:  # 2^7
                return cls(tag), 1

            if tag == 255:  # 2**8 - 1
                # Full 64-bit encoding
                if len(buffer) - offset < 9:
                    raise ValueError("Buffer too small to decode 64-bit integer")
                value = int.from_bytes(buffer[offset + 1 : offset + 9], "little")
                return cls(value), 9
            else:
                # Variable length encoding - use bit operations
                # Calculate _l from tag: _l = floor(8 - log2(256 - tag))
                # bit_length() = floor(log2(x)) + 1, but floor doesn't distribute over subtraction
                # Special case: if (256-tag) is a power of 2, use 9-bit_length; otherwise 8-bit_length
                x = 256 - tag
                if x > 0 and (x & (x - 1)) == 0:  # x is a power of 2
                    _l = 9 - x.bit_length()
                else:
                    _l = 8 - x.bit_length()

                if len(buffer) - offset < _l + 1:
                    raise ValueError("Buffer too small to decode variable-length integer")

                alpha = tag + (1 << (8 - _l)) - 256
                beta = int.from_bytes(buffer[offset + 1 : offset + 1 + _l], "little")
                value = (alpha << (_l * 8)) + beta
                return cls(value), _l + 1
            
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
