import pytest

from tsrkit_types.choice import Choice
from tsrkit_types.null import Null
from tsrkit_types.option import Option
from tsrkit_types.integers import U32, U8, U16


def test_option():
	# a = Option[U32] instance wrapping a U32
	a = Option[U32](U32(10))
	assert a is not None
	assert a.unwrap() == U32(10)

	# None case
	b = Option[U32]()
	assert b.unwrap() is Null
	assert not b

def test_opt_codec():
	a = Option[U32](U32(10))
	enc_a = a.encode()
	assert len(enc_a) == 4+1

	dec_a = a.decode(enc_a)
	assert dec_a == a

	n = Option[U32](Null)
	enc_n = n.encode()
	assert len(enc_n) == 1

	dec_n = n.decode(enc_n)
	assert dec_n == n

def test_opt_type():
	a = Option[U32](U32(10))
	with pytest.raises(TypeError):
		a.set(U8(10))

	with pytest.raises(TypeError):
		# Not possible to show warning here 🥲
		Option[U8](True)

	b = Option[U8](U8(100))
	b.set(U8(10))
	with pytest.raises(TypeError):
		b.set(False)

def test_choice_init():
	# Shows warning if invalid (non Type) choice added
	Choice[U8, bool](U8(10))
	# Should pass - valid choice and valid value
	a = Choice[U8, bool](U8(10))
	with pytest.raises(TypeError):
		# Should fail
		b = Choice[U8, bool](U16(10))

	a.set(U8(100))

	with pytest.raises(TypeError):
		# Should show warning as this is not a supported type by choice
		a.set(U16(100))