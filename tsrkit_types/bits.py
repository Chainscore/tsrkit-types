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
			# Encode the bit length first - use fast path for small lengths
			bit_len = len(self)
			if bit_len < 128:
				buffer[current_offset] = bit_len
				current_offset += 1
			else:
				current_offset += Uint(bit_len).encode_into(buffer, current_offset)
		else:
			# Ensure bit length matches expected size for fixed-length types
			if len(self) != self._min_length:
				raise ValueError(f"Bit sequence length mismatch: expected {self._min_length}, got {len(self)}")

		# Direct bit packing - avoid intermediate conversions
		bit_count = len(self)
		byte_count = (bit_count + 7) // 8

		if self._order == "lsb":
			# LSB: pack bits with bit 0 in LSB position
			for byte_idx in range(byte_count):
				val = 0
				bit_start = byte_idx * 8
				bit_end = min(bit_start + 8, bit_count)
				for bit_pos in range(bit_start, bit_end):
					if self[bit_pos]:
						val |= (1 << (bit_pos - bit_start))
				buffer[current_offset + byte_idx] = val
		else:  # msb
			# MSB: pack bits with bit 0 in MSB position
			for byte_idx in range(byte_count):
				val = 0
				bit_start = byte_idx * 8
				bit_end = min(bit_start + 8, bit_count)
				for bit_pos in range(bit_start, bit_end):
					if self[bit_pos]:
						val |= (1 << (7 - (bit_pos - bit_start)))
				buffer[current_offset + byte_idx] = val

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

		Returns:
			Tuple of (decoded bit list, bytes read)

		Raises:
			DecodeError: If buffer too small or bit_length not specified
		"""
		from tsrkit_types.constants import MAX_BITS_LENGTH

		# Check if this is a fixed-length Bits type
		is_fixed_length = (cls._min_length == cls._max_length and cls._min_length > 0)

		original_offset = offset

		if is_fixed_length:
			_len = cls._min_length
		else:
			# Variable length - decode length from buffer - use fast path
			if len(buffer) > offset:
				tag = buffer[offset]
				if tag < 128:
					_len = tag
					offset += 1
				else:
					_len, size = Uint.decode_from(buffer, offset)
					offset += size
			else:
				# Empty buffer or buffer too small - delegate to Uint for consistent error
				_len, size = Uint.decode_from(buffer, offset)
				offset += size

			# Security: Prevent DoS via unbounded allocation
			if _len > MAX_BITS_LENGTH:
				raise ValueError(
					f"Bits length {_len} exceeds maximum {MAX_BITS_LENGTH}"
				)

		if _len == 0:
			return cls([]), offset - original_offset

		# Security: Prevent integer overflow in byte_count calculation
		if _len > (2**63 - 8):
			raise ValueError(
				f"Bits length {_len} too large for byte_count calculation (overflow risk)"
			)

		# Calculate required bytes
		byte_count = (_len + 7) // 8
		cls._check_buffer_size(buffer, byte_count, offset)

		# Direct bit unpacking - avoid intermediate conversions
		result_bits = []

		if cls._order == "lsb":
			# LSB: unpack bits with bit 0 in LSB position
			for byte_idx in range(byte_count):
				byte_val = buffer[offset + byte_idx]
				for bit_offset in range(8):
					if len(result_bits) >= _len:
						break
					result_bits.append(bool((byte_val >> bit_offset) & 1))
		else:  # msb
			# MSB: unpack bits with bit 0 in MSB position
			for byte_idx in range(byte_count):
				byte_val = buffer[offset + byte_idx]
				for bit_offset in range(8):
					if len(result_bits) >= _len:
						break
					result_bits.append(bool((byte_val >> (7 - bit_offset)) & 1))

		total_bytes_read = offset + byte_count - original_offset
		return cls(result_bits), total_bytes_read