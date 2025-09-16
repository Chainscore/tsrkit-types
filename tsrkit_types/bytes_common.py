"""
Common functionality for Bytes and ByteArray types.
"""

from typing import Union

# Global lookup tables for maximum performance - initialized once
_BYTE_TO_BITS_MSB = []
_BITS_TO_BYTE_MSB = {}
_TABLES_INITIALIZED = False

def _init_lookup_tables():
    """Initialize lookup tables once for optimal performance."""
    global _BYTE_TO_BITS_MSB, _BITS_TO_BYTE_MSB, _TABLES_INITIALIZED
    if not _TABLES_INITIALIZED:
        for i in range(256):
            # Convert byte to 8 bits (MSB first)
            bits = [(i >> (7 - j)) & 1 for j in range(8)]
            _BYTE_TO_BITS_MSB.append(bits)
            # Reverse lookup: bits tuple to byte value
            _BITS_TO_BYTE_MSB[tuple(bits)] = i
        _TABLES_INITIALIZED = True


class BytesMixin:
    """Mixin providing common functionality for bytes-like types."""
    
    @classmethod
    def from_bits(cls, bits: list[bool], bit_order: str = "msb"):
        """Convert a list of bits to bytes with specified bit order."""
        # Fast path for MSB (most common case) using lookup tables
        if bit_order == "msb":
            _init_lookup_tables()
            
            # Convert and pad to multiple of 8
            int_bits = [int(bool(b)) for b in bits]
            pad = (8 - len(int_bits) % 8) % 8
            int_bits.extend([0] * pad)
            
            result = []
            for i in range(0, len(int_bits), 8):
                byte_bits = tuple(int_bits[i:i+8])
                result.append(_BITS_TO_BYTE_MSB[byte_bits])
            return cls(bytes(result))
        
        # LSB implementation
        elif bit_order == "lsb":
            int_bits = [int(bool(b)) for b in bits]
            pad = (8 - len(int_bits) % 8) % 8
            int_bits.extend([0] * pad)
            
            result = []
            for i in range(0, len(int_bits), 8):
                byte_bits = int_bits[i:i + 8]
                val = 0
                for bit in reversed(byte_bits):
                    val = (val << 1) | bit
                result.append(val)
            return cls(bytes(result))
        else:
            raise ValueError(f"Unknown bit_order: {bit_order}")

    def to_bits(self, bit_order: str = "msb") -> list[bool]:
        """Convert bytes to a list of bits with specified bit order."""
        # Fast path for MSB using lookup table
        if bit_order == "msb":
            _init_lookup_tables()
            
            result = []
            for byte in self:
                result.extend(_BYTE_TO_BITS_MSB[byte])
            return [bool(b) for b in result]
        
        # LSB implementation
        elif bit_order == "lsb":
            bits = []
            for byte in self:
                bits.extend([bool((byte >> i) & 1) for i in range(8)])
            return bits
        else:
            raise ValueError(f"Unknown bit_order: {bit_order}")
    
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

    def slice_bits(self, start_bit: int, end_bit: int) -> list[bool]:
        """Extract bit slice efficiently without converting entire byte array."""
        if start_bit >= end_bit:
            return []
        
        start_byte = start_bit // 8
        end_byte = (end_bit - 1) // 8 + 1
        start_bit_offset = start_bit % 8
        
        if start_byte >= len(self):
            return [False] * (end_bit - start_bit)
        
        # Extract relevant bytes and convert only what we need
        relevant_bytes = self[start_byte:min(end_byte, len(self))]
        
        # Use global lookup table for optimal performance
        _init_lookup_tables()
        
        result = []
        for byte in relevant_bytes:
            result.extend(_BYTE_TO_BITS_MSB[byte])
        
        # Slice to exact range
        local_start = start_bit_offset if start_byte < len(self) else 0
        local_end = len(result) if end_byte > len(self) else (end_bit - start_byte * 8)
        
        bits = result[local_start:local_end]
        
        # Pad with False if we ran out of data
        if len(bits) < (end_bit - start_bit):
            bits.extend([False] * (end_bit - start_bit - len(bits)))
        
        return [bool(b) for b in bits]


def validate_bit_order(bit_order: str) -> None:
    """Validate bit order parameter."""
    if bit_order not in ("msb", "lsb"):
        raise ValueError(f"Unknown bit_order: {bit_order}. Must be 'msb' or 'lsb'") 