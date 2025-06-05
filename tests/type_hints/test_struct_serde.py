from tsrkit_types.integers import Uint
from tsrkit_types.string import String
from tsrkit_types.struct import structure


def test_struct_serde_type_hints():
    @structure
    class Person:
        name: String
        age: Uint[8]
        email: String

    person = Person(name=String("John"), age=Uint[8](30), email=String("john@example.com"))

    encoded = person.encode()
    decoded = Person.decode(encoded)

    assert decoded.name == "John"
    assert decoded.age == 30
    assert decoded.email == "john@example.com"

    assert person == decoded