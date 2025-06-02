import pytest

from tsrkit_types.integers import U32, U8, Uint
from tsrkit_types.sequences import Vector, TypedArray, TypedVector, TypedBoundedVector


def test_list_init():
	class MyList(TypedVector[U32]): ...
	a = MyList([U32(10)])
	assert a == [U32(10)]

def test_list_typecheck():
	class MyList(TypedVector[U32]): ...
	a = MyList([U32(10)])

	with pytest.raises(TypeError):
		MyList([10])
	with pytest.raises(TypeError):
		a.append(100)

	b = Vector([100])
	b.append(U32(100))

def test_array_init():
	class Arr10(TypedArray[U32, 10]): ...

	a = Arr10([U32(1000)] * 10)
	assert len(a) == 10

	with pytest.raises(ValueError):
		Arr10([])

def test_typed_array_init():
	a = TypedArray[U32, 10]([U32(1000)] * 10)
	assert len(a) == 10

	with pytest.raises(ValueError):
		TypedArray[U32, 10]([])
	with pytest.raises(TypeError):
		TypedArray[U32, 10]([10] * 10)

def test_cls_flow():
	class IntVec(TypedVector[Uint]): ...
	a = IntVec([])

	class U32Vec(TypedVector[U32]): ...
	b = U32Vec([U32(10)] * 10)

	class BytesVec(TypedVector[bytes]): ...
	
	BytesVec([bytes(1)] * 10)

	with pytest.raises(TypeError):
		b.append(100)

	with pytest.raises(TypeError):
		a.append(U8(100))

	with pytest.raises(TypeError):
		a.append(U32(100))

def test_codec():
	a = TypedArray[U32, 10]([U32(1)] * 10)
	assert a.encode_size() == 4*10
	assert len(a.encode()) == 4*10

	b = TypedArray[U32, 20]([U32(1)] * 20)

	assert b._min_length == 20
	assert a._min_length == 10

def test_repr_vector():
	assert TypedBoundedVector[U32, 0, 10]([]).__class__.__name__ == "TypedBoundedVector[U32,max=10]"
