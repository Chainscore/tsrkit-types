from typing import Tuple, Union, ClassVar
from tsrkit_types.integers import Uint
from tsrkit_types.itf.codable import Codable

class Bytes(bytes, Codable):

    _length: ClassVar[Union[None, int]] = None

    def __class_getitem__(cls, params):
        _len = None
        name = cls.__class__.__name__
        if params and params > 0:
            _len = params
            name = f"ByteArray{_len}"
        return type(name, (cls,), {
            "_length": _len,
        })

    def __str__(self):
        return f"{self.__class__.__name__}({self.hex()})"

    @classmethod
    def from_bits(cls, bits: list[bool], bit_order = "msb") -> "Bytes":
        # Sanitize input: make sure bits are 0 or 1
        bits = [int(bool(b)) for b in bits]
        n = len(bits)
        # Pad with zeros to multiple of 8
        pad = (8 - n % 8) % 8
        bits += [0] * pad

        byte_arr = []
        for i in range(0, len(bits), 8):
            byte_bits = bits[i:i + 8]
            if bit_order == "msb":
                # Most significant bit first
                val = 0
                for bit in byte_bits:
                    val = (val << 1) | bit
            elif bit_order == "lsb":
                # Least significant bit first
                val = 0
                for bit in reversed(byte_bits):
                    val = (val << 1) | bit
            else:
                raise ValueError(f"Unknown bit_order: {bit_order}")
            # noinspection PyUnreachableCode
            byte_arr.append(val)
        return cls(bytes(byte_arr))

    def to_bits(self, bit_order="msb") -> list[bool]:
        bits = []
        for byte in self:
            if bit_order == "msb":
                bits.extend([(byte >> i) & 1 for i in reversed(range(8))])
            elif bit_order == "lsb":
                bits.extend([(byte >> i) & 1 for i in range(8)])
            else:
                raise ValueError(f"Unknown bit_order: {bit_order}")
        return bits
    
    # ---------------------------------------------------------------------------- #
    #                                 Serialization                                #
    # ---------------------------------------------------------------------------- #
    def encode_size(self) -> int:
        if self._length is None:
            return Uint(len(self)).encode_size() + len(self)
        return self._length
    
    def encode_into(self, buf: bytearray, offset: int = 0) -> int:
        current_offset = offset
        _len = self._length
        if _len is None:
            _len = len(self)
            current_offset += Uint(_len).encode_into(buf, current_offset)
        buf[current_offset:current_offset+_len] = self
        current_offset += _len
        return current_offset - offset
    
    @classmethod
    def decode_from(cls, buffer: Union[bytes, bytearray, memoryview], offset: int = 0) -> Tuple["Bytes", int]:
        current_offset = offset
        _len = cls._length
        if _len is None:
            _len, _inc_offset = Uint.decode_from(buffer, offset)
            current_offset += _inc_offset
        return cls(buffer[current_offset:current_offset+_len]), current_offset + _len - offset
    
    # ---------------------------------------------------------------------------- #
    #                               JSON Serialization                             #
    # ---------------------------------------------------------------------------- #
    def to_json(self):
        """Convert bytes to hex string for JSON serialization"""
        return self.hex()
    
    @classmethod
    def from_json(cls, data: str):
        """Create Bytes instance from hex string"""
        data = data.replace("0x", "")
        return cls(bytes.fromhex(data))
        