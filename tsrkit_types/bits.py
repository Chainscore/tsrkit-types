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
		return cls(Bytes.from_hex(json_str).to_bits(bit_order=cls._order))

	# ---------------------------------------------------------------------------- #
	#                                 Serialization                                #
	# ---------------------------------------------------------------------------- #
	
	def encode_size(self) -> int:
		# Calculate the number of bytes needed
		bit_enc = 0
		if self._length is None:
			bit_enc = Uint(len(self)).encode_size()

		return bit_enc + ((len(self) + 7) // 8)

	def encode_into(
		self, buffer: bytearray, offset: int = 0
	) -> int:
		total_size = self.encode_size()
		self._check_buffer_size(buffer, total_size, offset)

		# Initialize all bytes to 0
		for i in range(0, total_size):
			buffer[offset + i] = 0

		if self._length is None:
			# Encode the bit length first
			offset += Uint(len(self)).encode_into(buffer, offset)
		else:
			# Ensure bit length is size of value
			if len(self) != self._length:
				raise ValueError("Bit sequence length mismatch")

		if not all(
			isinstance(bit, (bool, int)) and bit in (0, 1, True, False)
			for bit in self
		):
			raise ValueError(f"Bit sequence must contain only 0s and 1s, got an sequence of {self}")

		buffer[offset : offset + total_size] = Bytes.from_bits(
			self, bit_order=self._order
		)

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
		_len = cls._length
		if _len is None:
			# Assume first byte is the bit length
			_len, size = Uint.decode_from(buffer, offset)
			offset += size

		if _len == 0:
			return [], 0

		# Calculate required bytes
		byte_count = (_len + 7) // 8
		cls._check_buffer_size(buffer, byte_count, offset)

		result = Bytes(buffer[offset : offset + byte_count]).to_bits(bit_order=cls._order)
		return cls(result), byte_count