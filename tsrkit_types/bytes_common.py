"""
Common functionality for Bytes and ByteArray types.
"""

from typing import Union


class BytesMixin:
    """Mixin providing common functionality for bytes-like types."""
    
    @classmethod
    def from_bits(cls, bits: list[bool], bit_order: str = "msb"):
        """Convert a list of bits to bytes with specified bit order."""
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
            byte_arr.append(val)
        return cls(bytes(byte_arr))

    def to_bits(self, bit_order: str = "msb") -> list[bool]:
        """Convert bytes to a list of bits with specified bit order."""
        bits = []
        for byte in self:
            if bit_order == "msb":
                bits.extend([bool((byte >> i) & 1) for i in reversed(range(8))])
            elif bit_order == "lsb":
                bits.extend([bool((byte >> i) & 1) for i in range(8)])
            else:
                raise ValueError(f"Unknown bit_order: {bit_order}")
        return bits
    
    def to_json(self):
        """Convert bytes to hex string for JSON serialization."""
        return self.hex()
    
    @classmethod
    def from_json(cls, data: str):
        """Create instance from hex string."""
        data = data.replace("0x", "")
        return cls(bytes.fromhex(data))
    
    def __str__(self):
        return f"{self.__class__.__name__}({self.hex()})"


def validate_bit_order(bit_order: str) -> None:
    """Validate bit order parameter."""
    if bit_order not in ("msb", "lsb"):
        raise ValueError(f"Unknown bit_order: {bit_order}. Must be 'msb' or 'lsb'") 