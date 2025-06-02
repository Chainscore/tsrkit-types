from dataclasses import dataclass

from tsrkit_types.integers import Uint as UInt


def test_int_type():
	a = UInt[8](28)
	assert a

def test_int_decodable():
	a = UInt[8].decode_from(b'08')[0]
	assert a > 0

def test_int_encode():
	a = UInt[8](100)
	encoded = a.encode()
	assert a == UInt[8].decode_from(encoded)[0]

def test_int_instance():
	class U8(UInt[8]): ...
	assert isinstance(U8(10), U8)
	assert isinstance(UInt[8](10), int)
	assert not isinstance(UInt[8](10), (UInt[16],))

def test_int_compare():
	assert UInt[8](10) == UInt[16](10)
	assert type(UInt[16](10)) != type(UInt[16](10))

def test_gen_int_type():
	a = UInt(1000)
	assert a

def test_gen_int_decodable():
	a = UInt.decode_from(b'08')[0]
	assert a > 0

def test_gen_int_encode():
	a = UInt(100)
	encoded = a.encode()
	assert a == UInt.decode_from(encoded)[0]

def test_static_type_checker():
	@dataclass
	class DataStore:
		a: UInt[8]
		b: UInt[16]

	# Shows error
	DataStore(a=19, b=288)
	DataStore(a=UInt[16](19), b=UInt[32](288))
	# This is fine
	DataStore(a=UInt[8](19), b=UInt[16](288))

