from typing import ClassVar

from tsrkit_types import _native


def _bits_class_getitem(cls, params):
	min_l, max_l, _bo = 0, 2**64, "msb"
	if isinstance(params, tuple):
		min_l, max_l, _bo = params[0], params[0], params[1]
	else:
		if isinstance(params, int):
			min_l, max_l = params, params
		else:
			_bo = params
	return type(cls.__class__.__name__, (cls,), {"_min_length": min_l, "_max_length": max_l, "_order": _bo})


class Bits(_native.NativeBits):
	"""Bits[size, order] (native-backed)."""

	_element_type = bool
	_min_length: ClassVar[int] = 0
	_max_length: ClassVar[int] = 2 ** 64
	_order: ClassVar[str] = "msb"

	def __class_getitem__(cls, params):
		return _bits_class_getitem(cls, params)
