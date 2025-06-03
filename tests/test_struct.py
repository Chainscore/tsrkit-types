from tsrkit_types.integers import Uint
from tsrkit_types.itf.codable import Codable
from tsrkit_types.string import String
from tsrkit_types.struct import struct, structure


def test_struct_init():
    @structure
    class Person:
        name: String
        age: Uint[8]

    person = Person(name=String("John"), age=Uint[8](30))
    assert person.name == "John"
    assert person.age == 30


def test_struct_codable():
    @structure
    class Person:
        name: String
        age: Uint[8]

    person = Person(name=String("John"), age=Uint[8](30))
    assert person.encode_size() == 5 + 1  # String("John") = 5 bytes, Uint[8] = 1 byte
    encoded = person.encode()
    assert encoded == b"\x04John\x1e"
    assert Person.decode(encoded) == person

def test_struct_json():
    @structure
    class Person:
        name: String
        age: Uint[8]

    person = Person(name=String("John"), age=Uint[8](30))
    assert person.to_json() == {"name": "John", "age": 30}
    assert Person.from_json({"name": "John", "age": 30}) == person

def test_struct_json_default():
    from dataclasses import field

    @structure
    class Person:
        name: String 
        age: Uint[8] = field(metadata={"default": Uint[8](0)})

    person = Person(name=String("John"))
    assert person.to_json() == {"name": "John", "age": 0}
    assert Person.from_json({"name": "John"}) == person

def test_struct_inheritance():
    from dataclasses import field

    @structure
    class Person:
        name: String 
        age: Uint[8] = field(metadata={"default": Uint[8](0)})

    p = Person(name=String("John"), age=Uint[8](30))
    assert isinstance(p, Codable)
    assert isinstance(p, Person)