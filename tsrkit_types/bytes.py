import abc
from typing import Tuple, Union, ClassVar
from tsrkit_types.integers import Uint
from tsrkit_types.itf.codable import Codable
from tsrkit_types.bytes_common import BytesMixin

# Global decode cache for bytes performance optimization
_BYTES_DECODE_CACHE = {}
_BYTES_CACHE_MAX_SIZE = 1000
_BYTES_CACHE_HITS = 0
_BYTES_CACHE_MISSES = 0

def clear_bytes_decode_cache():
    """Clear the global decode cache"""
    global _BYTES_DECODE_CACHE, _BYTES_CACHE_HITS, _BYTES_CACHE_MISSES
    _BYTES_DECODE_CACHE.clear()
    _BYTES_CACHE_HITS = 0
    _BYTES_CACHE_MISSES = 0

def get_bytes_cache_stats():
    """Get cache statistics"""
    global _BYTES_DECODE_CACHE, _BYTES_CACHE_HITS, _BYTES_CACHE_MISSES
    total_requests = _BYTES_CACHE_HITS + _BYTES_CACHE_MISSES
    hit_rate = (_BYTES_CACHE_HITS / total_requests * 100) if total_requests > 0 else 0
    return {
        'cache_size': len(_BYTES_DECODE_CACHE),
        'max_size': _BYTES_CACHE_MAX_SIZE,
        'hits': _BYTES_CACHE_HITS,
        'misses': _BYTES_CACHE_MISSES,
        'hit_rate': hit_rate
    }

class BytesCheckMeta(abc.ABCMeta):
    """Meta class to check if the instance is a bytes with the same key and value types"""
    def __instancecheck__(cls, instance):
        # TODO - This needs more false positive testing
        _matches_length = str(getattr(cls, "_length", None)) == str(getattr(instance, "_length", None))
        return isinstance(instance, bytes) and _matches_length


class Bytes(bytes, Codable, BytesMixin, metaclass=BytesCheckMeta):
    """Fixed Size Bytes"""

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

    # Bit conversion methods inherited from BytesMixin
    
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
        global _BYTES_DECODE_CACHE, _BYTES_CACHE_MAX_SIZE, _BYTES_CACHE_HITS, _BYTES_CACHE_MISSES
        
        # Create cache key for this decode operation
        cache_key = (cls, cls._length, buffer[offset:offset+min(64, len(buffer)-offset)], offset)
        
        # Check cache first
        if cache_key in _BYTES_DECODE_CACHE:
            _BYTES_CACHE_HITS += 1
            return _BYTES_DECODE_CACHE[cache_key]
        
        _BYTES_CACHE_MISSES += 1
        current_offset = offset
        _len = cls._length

        if _len is None:
            _len, _inc_offset = Uint.decode_from(buffer, offset)
            current_offset += _inc_offset
        
        if len(buffer[current_offset:current_offset+_len]) < _len:
            raise TypeError("Insufficient buffer")
        
        result = (cls(buffer[current_offset:current_offset+_len]), current_offset + _len - offset)
        
        # Cache the result if we're not at capacity
        if len(_BYTES_DECODE_CACHE) < _BYTES_CACHE_MAX_SIZE:
            _BYTES_DECODE_CACHE[cache_key] = result
        elif len(_BYTES_DECODE_CACHE) >= _BYTES_CACHE_MAX_SIZE:
            # Simple eviction: clear 25% of cache when full
            keys_to_remove = list(_BYTES_DECODE_CACHE.keys())[:_BYTES_CACHE_MAX_SIZE // 4]
            for key in keys_to_remove:
                del _BYTES_DECODE_CACHE[key]
            _BYTES_DECODE_CACHE[cache_key] = result
        
        return result

    def __deepcopy__(self, memo):
        # immutable; safe to reuse or create a new same-typed instance
        existing = memo.get(id(self))
        if existing is not None:
            return existing
        new = type(self)(bytes(self))
        memo[id(self)] = new
        return new

    # ---------------------------------------------------------------------------- #
    #                               JSON Serialization                             #
    # ---------------------------------------------------------------------------- #
    # JSON methods inherited from BytesMixin
        
Bytes16 = Bytes[16]
Bytes32 = Bytes[32]
Bytes64 = Bytes[64]
Bytes128 = Bytes[128]
Bytes256 = Bytes[256]
Bytes512 = Bytes[512]
Bytes1024 = Bytes[1024]
