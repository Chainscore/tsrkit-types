import abc
from decimal import Decimal
import math
from typing import Any, Tuple, Union, Callable
from tsrkit_types.itf.codable import Codable


class IntCheckMeta(abc.ABCMeta):
    """Meta class to check if the instance is an integer with the same byte size"""
    def __instancecheck__(cls, instance):
        return isinstance(instance, int) and getattr(instance, "byte_size", 0) == getattr(cls, "byte_size", 0)


class Int(int, Codable, metaclass=IntCheckMeta):
    """
    Integer type that supports both signed and unsigned integers.
    
    Usage:
        >>> # Fixed Integer with defined class
        >>> U8 = Int[8]
        >>> U8(10)
        U8(10)
        >>> U8.encode(10)
        b'\n'
        >>> U8.decode(b'\n')
        U8(10)

        >>> # Signed integer
        >>> I8 = Int[(8, True)]
        >>> I8(-10)
        I8(-10)
        >>> I8.encode(-10)
        b'\xf6'
        >>> I8.decode(b'\xf6')
        I8(-10)

        >>> # Fixed Integer w dynamic usage
        >>> num = Int[8](10)
        >>> num
        U8(10)
        >>> num.encode()
        b'\n'
        >>> Int[8].decode(b'\n')
        U8(10)

        >>> # If you want to use the General Integer (supports up to 2**64 - 1), 
        >>> # you can use the Int class without specifying the byte size.
        >>>
        >>> num = Int(10)
        >>> num
        Int(10)
        >>> num.encode()
        b'\n'
        >>> Int.decode(b'\n')
        Int(10)
    """

    # If the byte_size is set, the integer is fixed size.
    # Otherwise, the integer is General Integer (supports up to 2**64 - 1)
    byte_size: int = 0
    signed = False
    _bound = 0

    def __class_getitem__(cls, data: int | tuple):
        """
        Args:
            data: either byte_size or (byte_size, signed)
        """
        if data == None:
            size, signed = 0, False
        # If we have a single value arg - either byte_size or signed
        elif not isinstance(data, tuple):
            if isinstance(data, int):
                size, signed = data, False
            else: 
                size, signed = 0, bool(data)
        else:
            size, signed = data
        
        name_prefix = "I" if signed else "U"
        class_name = f"{name_prefix}{size}" if size else "Int"
        
        return type(class_name, (cls,), {
            "byte_size": size // 8, 
            "signed": signed, 
            "_bound": 1 << size if size > 0 else 1 << 64
        })

    def __new__(cls, value: Any):
        value = int(value)
        if cls.byte_size > 0:
            if cls.signed:
                max_v = (cls._bound // 2) - 1  # 2^(n-1) - 1
                min_v = -(cls._bound // 2)     # -2^(n-1)
            else:
                max_v = cls._bound - 1         # 2^n - 1
                min_v = 0
        else:
            if cls.signed:
                max_v = (cls._bound // 2) - 1  # 2^63 - 1
                min_v = -(cls._bound // 2)     # -2^63
            else:
                max_v = cls._bound - 1         # 2^64 - 1
                min_v = 0
        
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
        return math.floor(Decimal(x).ln() / (Decimal(7) * Decimal(2).ln()))
    
    def to_unsigned(self) -> int:
        """Convert signed integer to unsigned representation for encoding."""
        if not self.signed:
            return int(self)
        
        value = int(self)
        if value < 0:
            # Two's complement conversion
            if self.byte_size > 0:
                return value + self._bound
            else:
                return value + (1 << 64)  # For general 64-bit signed integers
        return value
    
    def from_unsigned(self, unsigned_value: int) -> int:
        """Convert unsigned representation back to signed integer during decoding."""
        if not self.signed:
            return unsigned_value
        
        if self.byte_size > 0:
            # Check if the sign bit is set
            sign_bit = 1 << (self.byte_size * 8 - 1)
            if unsigned_value >= sign_bit:
                return unsigned_value - self._bound
        else:
            # For general 64-bit signed integers
            sign_bit = 1 << 63
            if unsigned_value >= sign_bit:
                return unsigned_value - (1 << 64)
        
        return unsigned_value

    def encode_size(self) -> int:
        if self.byte_size > 0:
            return self.byte_size 
        else:
            value = self.to_unsigned()
            if value < 2**7:
                return 1
            elif value < 2 ** (7 * 9):
                return 1 + self.l(value)
            elif value < 2**64:
                return 9
            else:
                raise ValueError("Value too large for encoding. General Int support up to 2**64 - 1")

    def encode_into(self, buffer: bytearray, offset: int = 0) -> int:
        if self.byte_size > 0:
            # For fixed-size integers, convert to unsigned and encode
            unsigned_value = self.to_unsigned()
            buffer[offset:offset+self.byte_size] = unsigned_value.to_bytes(self.byte_size, "little")
            return self.byte_size
        else:
            # For variable-size integers, convert to unsigned first
            unsigned_value = self.to_unsigned()
            
            if unsigned_value < 2**7:
                buffer[offset:offset+1] = unsigned_value.to_bytes(1, "little")
                return 1

            size = self.encode_size()
            self._check_buffer_size(buffer, size, offset)
            if unsigned_value < 2 ** (7 * 8):
                _l = self.l(unsigned_value)
                # Create temporary value for encoding the prefix
                prefix_value = (2**8 - 2 ** (8 - _l) + 
                               math.floor(Decimal(unsigned_value) / (Decimal(2) ** (_l * 8))))
                buffer[offset] = int(prefix_value)
                offset += 1
                # Encode the remaining bytes
                remaining = unsigned_value % (2 ** (_l * 8))
                remaining_bytes = remaining.to_bytes(_l, "little")
                buffer[offset : offset + _l] = remaining_bytes
            elif unsigned_value < 2**64:
                buffer[offset] = 2**8 - 1  # Full 64-bit marker
                offset += 1
                buffer[offset : offset + 8] = unsigned_value.to_bytes(8, "little")
            else:
                raise ValueError(
                    f"Value too large for encoding. General Int support up to 2**64 - 1, got {unsigned_value}"
                )
            return size
    
    @classmethod
    def decode_from(
            cls, buffer: Union[bytes, bytearray, memoryview], offset: int = 0
    ) -> Tuple[Any, int]:
        if cls.byte_size > 0:
            # Decode as unsigned first
            unsigned_value = int.from_bytes(buffer[offset : offset + cls.byte_size], "little")
            # Convert back to signed if needed
            if cls.signed:
                # Check if the sign bit is set
                sign_bit = 1 << (cls.byte_size * 8 - 1)
                if unsigned_value >= sign_bit:
                    signed_value = unsigned_value - cls._bound
                else:
                    signed_value = unsigned_value
                return cls.__new__(cls, signed_value), cls.byte_size
            else:
                return cls.__new__(cls, unsigned_value), cls.byte_size
        else:
            # Variable-length decoding
            tag = int.from_bytes(buffer[offset:offset+1], "little")
            unsigned_value = None
            size = 0

            if tag < 2**7:
                unsigned_value = tag
                size = 1
            elif tag == 2**8 - 1:
                # Full 64-bit encoding
                if len(buffer) - offset < 9:
                    raise ValueError("Buffer too small to decode 64-bit integer")
                unsigned_value = int.from_bytes(buffer[offset + 1 : offset + 9], "little")
                size = 9
            else:
                # Variable length encoding
                _l = math.floor(
                    Decimal(8) - (Decimal(2**8) - Decimal(tag)).ln() / Decimal(2).ln()
                )
                if len(buffer) - offset < _l + 1:
                    raise ValueError("Buffer too small to decode variable-length integer")
                alpha = tag + 2 ** (8 - _l) - 2**8
                beta = int.from_bytes(buffer[offset + 1 : offset + 1 + _l], "little")
                unsigned_value = alpha * 2 ** (_l * 8) + beta
                size = _l + 1
            
            # Convert back to signed if needed
            if cls.signed:
                sign_bit = 1 << 63
                if unsigned_value >= sign_bit:
                    signed_value = unsigned_value - (1 << 64)
                else:
                    signed_value = unsigned_value
                return cls(signed_value), size
            else:
                return cls(unsigned_value), size
            
    def to_bits(self, bit_order: str = "msb") -> list[bool]:
        """Convert an int to bits"""
        # Use unsigned representation for bit operations
        unsigned_value = self.to_unsigned()
        bit_count = self.byte_size * 8 if self.byte_size > 0 else 64
        
        if bit_order == "msb":
            return [bool((unsigned_value >> i) & 1) for i in reversed(range(bit_count))]
        elif bit_order == "lsb":
            return [bool((unsigned_value >> i) & 1) for i in range(bit_count)]
        else:
            raise ValueError(f"Invalid bit order: {bit_order}")
        
    @classmethod
    def from_bits(cls, bits: list[bool], bit_order: str = "msb") -> "Int":
        """Convert bits to an int"""
        if bit_order == "msb":
            unsigned_value = int("".join(str(int(b)) for b in bits), 2)
        elif bit_order == "lsb":
            unsigned_value = int("".join(str(int(b)) for b in reversed(bits)), 2)
        else:
            raise ValueError(f"Invalid bit order: {bit_order}")
        
        # Convert back to signed if needed
        if cls.signed:
            bit_count = len(bits)
            sign_bit = 1 << (bit_count - 1)
            if unsigned_value >= sign_bit:
                signed_value = unsigned_value - (1 << bit_count)
            else:
                signed_value = unsigned_value
            return cls(signed_value)
        else:
            return cls(unsigned_value)


# Type aliases for convenience
# Variable-size unsigned integer (default)
Uint = Int[(0, False)]
U8 = Int[8]
U16 = Int[16]
U32 = Int[32]
U64 = Int[64]

# Signed integer aliases
I8 = Int[(8, True)]
I16 = Int[(16, True)]
I32 = Int[(32, True)]
I64 = Int[(64, True)]
