from typing import ClassVar, Sequence, Tuple, Union

from tsrkit_types.bytes import Bytes
from tsrkit_types.integers import Uint
from tsrkit_types.sequences import Seq


class Bits(Seq):
	"""Bits[size, order]"""
	_element_type = bool
	_min_length: ClassVar[int] = 0
	_max_length: ClassVar[int] = 2 ** 64
	_order: ClassVar[str] = "msb"

	def __class_getitem__(cls, params):
		min_l, max_l, _bo = 0, 2**64, "msb"
		if isinstance(params, tuple):
			min_l, max_l, _bo = params[0], params[0], params[1]
		else:
			if isinstance(params, int):
				min_l, max_l = params, params
			else:
				_bo = params

		return type(cls.__class__.__name__, (cls,), {"_min_length": min_l, "_max_length": max_l, "_order": _bo})
	

	# ---------------------------------------------------------------------------- #
	#                                  JSON Parse                                  #
	# ---------------------------------------------------------------------------- #
	
	def to_json(self) -> str:
		return Bytes.from_bits(self, bit_order=self._order).hex()
	
	@classmethod
	def from_json(cls, json_str: str) -> "Bits":
		bits = Bytes.from_json(json_str).to_bits(bit_order=cls._order)
		
		# For fixed-length types, trim to exact size
		if cls._min_length == cls._max_length and cls._min_length > 0:
			bits = bits[:cls._min_length]
		
		return cls(bits)

	# ---------------------------------------------------------------------------- #
	#                                 Serialization                                #
	# ---------------------------------------------------------------------------- #
	
	def encode_size(self) -> int:
		# Calculate the number of bytes needed
		bit_enc = 0
		# Check if this is a variable-length type (needs length prefix)
		is_fixed_length = (self._min_length == self._max_length and self._min_length > 0)
		if not is_fixed_length:
			bit_enc = Uint(len(self)).encode_size()

		return bit_enc + ((len(self) + 7) // 8)

	def encode_into(
		self, buffer: bytearray, offset: int = 0
	) -> int:
		total_size = self.encode_size()
		self._check_buffer_size(buffer, total_size, offset)

		current_offset = offset
		
		# Check if this is a variable-length type (needs length prefix)
		is_fixed_length = (self._min_length == self._max_length and self._min_length > 0)
		
		if not is_fixed_length:
			# Encode the bit length first
			current_offset += Uint(len(self)).encode_into(buffer, current_offset)
		else:
			# Ensure bit length matches expected size for fixed-length types
			if len(self) != self._min_length:
				raise ValueError(f"Bit sequence length mismatch: expected {self._min_length}, got {len(self)}")

		if not all(
			isinstance(bit, (bool, int)) and bit in (0, 1, True, False)
			for bit in self
		):
			raise ValueError(f"Bit sequence must contain only 0s and 1s, got an sequence of {self}")

		# Convert bits to bytes and write to buffer
		bit_bytes = Bytes.from_bits(self, bit_order=self._order)
		buffer[current_offset : current_offset + len(bit_bytes)] = bit_bytes

		return total_size

	@classmethod
	def decode_from(
		cls,
		buffer: Union[bytes, bytearray, memoryview],
		offset: int = 0,
	) -> Tuple[Sequence[bool], int]:
		"""
		Decode bit sequence from buffer.

		Args:
			buffer: Source buffer
			offset: Starting offset
			bit_length: Expected number of bits (required)

		Returns:
			Tuple of (decoded bit list, bytes read)

		Raises:
			DecodeError: If buffer too small or bit_length not specified
		"""
		# Check if this is a fixed-length Bits type
		is_fixed_length = (cls._min_length == cls._max_length and cls._min_length > 0)
		
		original_offset = offset
		
		if is_fixed_length:
			_len = cls._min_length
		else:
			# Variable length - decode length from buffer
			_len, size = Uint.decode_from(buffer, offset)
			offset += size

		if _len == 0:
			return cls([]), offset - original_offset

		# Calculate required bytes
		byte_count = (_len + 7) // 8
		cls._check_buffer_size(buffer, byte_count, offset)

		result_bits = Bytes(buffer[offset : offset + byte_count]).to_bits(bit_order=cls._order)
		# Trim to exact bit length
		result_bits = result_bits[:_len]
		
		total_bytes_read = offset + byte_count - original_offset
		return cls(result_bits), total_bytes_read