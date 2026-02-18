from tsrkit_types.integers import Uint
from tsrkit_types.string import String
from tsrkit_types.struct import structure
from tsrkit_types.itf.codable import Codable


def test_struct_serde_type_hints():
    @structure
    # Added `Codable` as a base class to ensure it has the necessary methods.
    # Updated Structure now supports both `Codable` and `dataclass` functionalities.
    class Person(Codable):
        name: String
        age: Uint[8]
        email: String

    person = Person(name=String("John"), age=Uint[8](30), email=String("john@example.com"))

    encoded = person.encode()
    decoded = Person.decode(encoded)

    encoded_size = person.encode_size()
    person_from_json = person.from_json({"name": "John", "age": 30, "email": "john@example.com"})
    decoded_from_json = Person.from_json({"name": "John", "age": 30, "email": "john@example.com"})
 
    assert decoded_from_json == person_from_json
    assert person_from_json == person
    assert encoded_size == len(encoded)
    
    assert decoded.name == "John"
    assert decoded.age == 30
    assert decoded.email == "john@example.com"

    assert person == decoded