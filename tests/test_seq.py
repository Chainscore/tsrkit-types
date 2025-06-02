import pytest

from tsrkit_types.integers import Uint
from tsrkit_types.sequences import Vector, TypedArray, TypedVector, TypedBoundedVector


def test_list_init():
	class MyList(TypedVector[Uint[32]]): ...
	a = MyList([Uint[32](10)])
	assert a == [Uint[32](10)]

def test_list_typecheck():
	class MyList(TypedVector[Uint[32]]): ...
	a = MyList([Uint[32](10)])

	with pytest.raises(TypeError):
		MyList([10])
	with pytest.raises(TypeError):
		a.append(100)

	b = Vector([100])
	b.append(Uint[32](100))

def test_array_init():
	class Arr10(TypedArray[Uint[32], 10]): ...

	a = Arr10([Uint[32](1000)] * 10)
	assert len(a) == 10

	with pytest.raises(ValueError):
		Arr10([])

def test_typed_array_init():
	a = TypedArray[Uint[32], 10]([Uint[32](1000)] * 10)
	assert len(a) == 10

	with pytest.raises(ValueError):
		TypedArray[Uint[32], 10]([])
	with pytest.raises(TypeError):
		TypedArray[Uint[32], 10]([10] * 10)

def test_cls_flow():
	class IntVec(TypedVector[Uint]): ...
	a = IntVec([])

	class Uint32Vec(TypedVector[Uint[32]]): ...
	b = Uint32Vec([Uint[32](10)] * 10)

	class BytesVec(TypedVector[bytes]): ...
	
	BytesVec([bytes(1)] * 10)

	with pytest.raises(TypeError):
		b.append(100)

	with pytest.raises(TypeError):
		a.append(Uint[8](100))

	with pytest.raises(TypeError):
		a.append(Uint[32](100))

def test_codec():
	a = TypedArray[Uint[32], 10]([Uint[32](1)] * 10)
	assert a.encode_size() == 4*10
	assert len(a.encode()) == 4*10

	b = TypedArray[Uint[32], 20]([Uint[32](1)] * 20)

	assert b._min_length == 20
	assert a._min_length == 10

def test_repr_vector():
	assert TypedBoundedVector[Uint[32], 0, 10]([]).__class__.__name__ == "TypedBoundedVector[U32,max=10]"
