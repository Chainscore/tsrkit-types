from typing import ClassVar, Sequence, Tuple, Union

from tsrkit_types.bytes import Bytes
from tsrkit_types.bytes_common import _BYTE_TO_BITS_MSB, _init_lookup_tables
from tsrkit_types.integers import Uint
from tsrkit_types.sequences import Seq


class Bits(Seq):
	"""Bits[size, order]"""
	_element_type = bool
	_min_length: ClassVar[int] = 0
	_max_length: ClassVar[int] = 2 ** 64
	_order: ClassVar[str] = "msb"
	_bool_type = bool

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

	def __init__(self, initial: Sequence[bool]):
		isinstance_local = isinstance
		bool_type = self._bool_type
		for bit in initial:
			if not isinstance_local(bit, bool_type):
				raise TypeError(f"{bit!r} is not an instance of {bool_type!r}")
		list.__init__(self, initial)
		self._validate_self()

	def _validate(self, value):
		if not isinstance(value, self._bool_type):
			raise TypeError(f"{value!r} is not an instance of {self._bool_type!r}")

	def append(self, v: bool):
		if not isinstance(v, self._bool_type):
			raise TypeError(f"{v!r} is not an instance of {self._bool_type!r}")
		list.append(self, v)
		self._validate_self()

	def insert(self, i, v: bool):
		if not isinstance(v, self._bool_type):
			raise TypeError(f"{v!r} is not an instance of {self._bool_type!r}")
		list.insert(self, i, v)
		self._validate_self()

	def extend(self, seq: Sequence[bool]):
		isinstance_local = isinstance
		bool_type = self._bool_type
		for val in seq:
			if not isinstance_local(val, bool_type):
				raise TypeError(f"{val!r} is not an instance of {bool_type!r}")
		list.extend(self, seq)
		self._validate_self()
	

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
		bit_len = len(self)
		is_fixed_length = (self._min_length == self._max_length and self._min_length > 0)

		if is_fixed_length and bit_len != self._min_length:
			raise ValueError(f"Bit sequence length mismatch: expected {self._min_length}, got {bit_len}")

		byte_count = (bit_len + 7) // 8
		total_size = byte_count
		if not is_fixed_length:
			total_size += Uint(bit_len).encode_size()

		self._check_buffer_size(buffer, total_size, offset)

		current_offset = offset
		if not is_fixed_length:
			current_offset += Uint(bit_len).encode_into(buffer, current_offset)

		if bit_len:
			bit_bytes = _pack_bits_to_bytes(self, bit_len, self._order)
			buffer[current_offset : current_offset + byte_count] = bit_bytes

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

		view = memoryview(buffer)[offset : offset + byte_count]

		if cls._order == "msb":
			_init_lookup_tables()
			table = _get_bits_table_msb()
			result_bits = []
			extend_bits = result_bits.extend
			for byte in view:
				extend_bits(table[byte])
		else:
			result_bits = []
			extend_bits = result_bits.extend
			for byte in view:
				extend_bits([bool((byte >> i) & 1) for i in range(8)])

		# Trim to exact bit length
		result_bits = result_bits[:_len]

		total_bytes_read = offset + byte_count - original_offset
		return _bits_from_list(cls, result_bits), total_bytes_read


_BYTE_TO_BITS_MSB_BOOL = None


def _get_bits_table_msb():
	global _BYTE_TO_BITS_MSB_BOOL
	if _BYTE_TO_BITS_MSB_BOOL is None:
		_init_lookup_tables()
		_BYTE_TO_BITS_MSB_BOOL = [tuple(bool(b) for b in row) for row in _BYTE_TO_BITS_MSB]
	return _BYTE_TO_BITS_MSB_BOOL


def _pack_bits_to_bytes(bits: Sequence[bool], bit_len: int, order: str) -> bytearray:
	byte_count = (bit_len + 7) // 8
	out = bytearray(byte_count)
	idx = 0
	if order == "msb":
		for i in range(byte_count):
			val = 0
			for j in range(8):
				if idx < bit_len and bits[idx]:
					val |= 1 << (7 - j)
				idx += 1
			out[i] = val
	else:
		for i in range(byte_count):
			val = 0
			for j in range(8):
				if idx < bit_len and bits[idx]:
					val |= 1 << j
				idx += 1
			out[i] = val
	return out


def _bits_from_list(cls, bits: list[bool]):
	# Fast path to skip per-item validation in Seq.__init__
	inst = cls.__new__(cls)
	list.__init__(inst, bits)
	inst._validate_self()
	return inst
