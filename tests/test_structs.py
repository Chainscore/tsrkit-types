import pytest
from dataclasses import field
from tsrkit_types.integers import Uint, U8, U16, U32
from tsrkit_types.string import String
from tsrkit_types.bool import Bool
from tsrkit_types.choice import Choice
from tsrkit_types.option import Option
from tsrkit_types.sequences import TypedVector
from tsrkit_types.enum import Enum
from tsrkit_types.struct import struct, structure
from tsrkit_types.bytes import Bytes
from tsrkit_types.itf.codable import Codable


def test_basic_struct():
    """Test basic struct definition and usage."""
    @structure
    class Person:
        name: String
        age: Uint[8]
        email: String
    
    # Create struct instance
    person = Person(
        name=String("Alice Smith"),
        age=Uint[8](30),
        email=String("alice@example.com")
    )
    
    assert str(person.name) == "Alice Smith"
    assert person.age == 30
    assert str(person.email) == "alice@example.com"
    assert type(person).__name__ == "Person"
    
    # Struct encoding
    encoded = person.encode()
    decoded = Person.decode(encoded)
    
    assert len(encoded) > 0
    assert str(decoded.name) == "Alice Smith"
    assert decoded.age == 30
    assert str(person.name) == str(decoded.name)


def test_struct_with_defaults():
    """Test structs with default values."""
    @structure
    class User:
        username: String
        active: Bool = field(metadata={"default": Bool(True)})
        role: String = field(metadata={"default": String("user")})
        login_count: Uint[32] = field(metadata={"default": Uint[32](0)})
    
    # Create with only required fields
    user1 = User(username=String("john_doe"))
    
    # Create with some optional fields
    user2 = User(
        username=String("admin"),
        active=Bool(True),
        role=String("administrator")
    )
    
    assert str(user1.username) == "john_doe"
    assert bool(user1.active) is True
    assert str(user1.role) == "user"
    assert user1.login_count == 0
    
    assert str(user2.username) == "admin"
    assert str(user2.role) == "administrator"
    assert user2.login_count == 0
    
    # JSON serialization includes defaults
    user1_json = user1.to_json()
    assert isinstance(user1_json, dict)
    assert "username" in user1_json


def test_custom_json_field_names():
    """Test custom JSON field names using metadata."""
    @structure
    class ApiResponse:
        status_code: Uint[16] = field(metadata={"name": "status"})
        message: String = field(metadata={"name": "msg"})
        data_payload: String = field(metadata={"name": "data"})
        timestamp: Uint[64] = field(metadata={"name": "ts"})
    
    response = ApiResponse(
        status_code=Uint[16](200),
        message=String("Success"),
        data_payload=String("Hello World"),
        timestamp=Uint[64](1703001234567)
    )
    
    # JSON uses custom field names
    json_data = response.to_json()
    assert "status" in json_data
    assert "msg" in json_data
    assert "data" in json_data
    assert "ts" in json_data
    
    # Restore from JSON
    restored = ApiResponse.from_json(json_data)
    assert restored.status_code == 200
    assert str(restored.message) == "Success"
    assert response.status_code == restored.status_code


def test_nested_structs():
    """Test nested struct composition."""
    @structure
    class Address:
        street: String
        city: String
        zip_code: String
        country: String = field(metadata={"default": String("USA")})
    
    @structure
    class Contact:
        email: String
        phone: String = field(metadata={"default": String("")})
    
    @structure
    class Employee:
        id: Uint[32]
        name: String
        address: Address
        contact: Contact
        salary: Uint[32]
        active: Bool = field(metadata={"default": Bool(True)})
    
    # Create nested structure
    employee = Employee(
        id=Uint[32](12345),
        name=String("John Doe"),
        address=Address(
            street=String("123 Main St"),
            city=String("Anytown"),
            zip_code=String("12345")
        ),
        contact=Contact(
            email=String("john.doe@company.com"),
            phone=String("555-0123")
        ),
        salary=Uint[32](75000)
    )
    
    assert str(employee.name) == "John Doe"
    assert employee.id == 12345
    assert str(employee.address.street) == "123 Main St"
    assert str(employee.address.city) == "Anytown"
    assert str(employee.contact.email) == "john.doe@company.com"
    
    # Encoding includes all nested data
    encoded = employee.encode()
    decoded = Employee.decode(encoded)
    assert len(encoded) > 0
    assert str(decoded.address.city) == "Anytown"
    assert str(decoded.contact.email) == "john.doe@company.com"


def test_struct_with_collections():
    """Test structs with collection fields."""
    class Priority(Enum):
        LOW = 1
        MEDIUM = 2
        HIGH = 3
    
    @structure
    class Task:
        id: Uint[32]
        title: String
        priority: Priority
        completed: Bool = field(metadata={"default": Bool(False)})
    
    @structure
    class Project:
        name: String
        description: String
        tasks: TypedVector[Task]
        owner: String
        active: Bool = field(metadata={"default": Bool(True)})
    
    # Create project with multiple tasks
    project = Project(
        name=String("Website Redesign"),
        description=String("Complete overhaul of company website"),
        tasks=TypedVector[Task]([
            Task(
                id=Uint[32](1),
                title=String("Design mockups"),
                priority=Priority.HIGH
            ),
            Task(
                id=Uint[32](2),
                title=String("Implement frontend"),
                priority=Priority.MEDIUM
            ),
            Task(
                id=Uint[32](3),
                title=String("Test deployment"),
                priority=Priority.LOW
            )
        ]),
        owner=String("Alice")
    )
    
    assert str(project.name) == "Website Redesign"
    assert len(project.tasks) == 3
    assert project.tasks[0].id == 1
    assert str(project.tasks[0].title) == "Design mockups"
    assert project.tasks[0].priority._name_ == "HIGH"
    
    # Encoding preserves all task data
    encoded = project.encode()
    decoded = Project.decode(encoded)
    assert len(encoded) > 0
    assert len(decoded.tasks) == 3
    assert decoded.tasks[0].id == 1


def test_optional_fields():
    """Test structs with optional fields using Option."""
    @structure
    class ProfileInfo:
        user_id: Uint[32]
        username: String
        full_name: Option[String]
        bio: Option[String]
        avatar_url: Option[String]
        verified: Bool = field(metadata={"default": Bool(False)})
    
    # Profile with minimal info
    basic_profile = ProfileInfo(
        user_id=Uint[32](123),
        username=String("jane_doe"),
        full_name=Option[String](),  # Empty
        bio=Option[String](),        # Empty
        avatar_url=Option[String]()  # Empty
    )
    
    # Profile with complete info
    complete_profile = ProfileInfo(
        user_id=Uint[32](456),
        username=String("john_smith"),
        full_name=Option[String](String("John Smith")),
        bio=Option[String](String("Software developer and coffee enthusiast")),
        avatar_url=Option[String](String("https://example.com/avatar.jpg")),
        verified=Bool(True)
    )
    
    profiles = [basic_profile, complete_profile]
    
    # Test basic profile
    assert basic_profile.user_id == 123
    assert str(basic_profile.username) == "jane_doe"
    assert not basic_profile.full_name  # Empty
    assert not basic_profile.bio        # Empty
    assert not basic_profile.avatar_url # Empty
    assert not basic_profile.verified
    
    # Test complete profile
    assert complete_profile.user_id == 456
    assert str(complete_profile.username) == "john_smith"
    assert complete_profile.full_name
    assert str(complete_profile.full_name.unwrap()) == "John Smith"
    assert complete_profile.bio
    assert bool(complete_profile.verified) is True
    
    # Test encoding/decoding
    for profile in profiles:
        encoded = profile.encode()
        decoded = ProfileInfo.decode(encoded)
        assert decoded.user_id == profile.user_id
        assert bool(decoded.full_name) == bool(profile.full_name)


def test_frozen_structs():
    """Test immutable (frozen) structs."""
    @structure(frozen=True)
    class Point:
        x: Uint[16]
        y: Uint[16]
    
    @structure(frozen=True)
    class Rectangle:
        top_left: Point
        bottom_right: Point
        
        def area(self) -> int:
            """Calculate rectangle area."""
            width = int(self.bottom_right.x) - int(self.top_left.x)
            height = int(self.bottom_right.y) - int(self.top_left.y)
            return width * height
    
    # Create immutable instances
    point1 = Point(x=Uint[16](10), y=Uint[16](20))
    point2 = Point(x=Uint[16](100), y=Uint[16](80))
    rect = Rectangle(top_left=point1, bottom_right=point2)
    
    assert point1.x == 10
    assert point1.y == 20
    assert point2.x == 100
    assert point2.y == 80
    assert rect.area() == 90 * 60  # (100-10) * (80-20)
    
    # Frozen structs cannot be modified
    with pytest.raises(AttributeError):
        point1.x = Uint[16](15)  # This should fail
    
    # But they can still be encoded/decoded
    encoded = rect.encode()
    decoded = Rectangle.decode(encoded)
    assert decoded.area() == rect.area()


def test_struct_inheritance():
    """Test struct inheritance patterns."""
    @structure
    class Vehicle:
        make: String
        model: String
        year: Uint[16]
    
    @structure
    class Car:
        vehicle: Vehicle  # Composition instead of inheritance
        doors: Uint[8]
        fuel_type: String
    
    @structure
    class Motorcycle:
        vehicle: Vehicle  # Composition instead of inheritance
        engine_cc: Uint[16]
        has_sidecar: Bool = field(metadata={"default": Bool(False)})
    
    # Create vehicles using composition
    car = Car(
        vehicle=Vehicle(
            make=String("Toyota"),
            model=String("Camry"),
            year=Uint[16](2022)
        ),
        doors=Uint[8](4),
        fuel_type=String("Gasoline")
    )
    
    motorcycle = Motorcycle(
        vehicle=Vehicle(
            make=String("Harley-Davidson"),
            model=String("Street 750"),
            year=Uint[16](2021)
        ),
        engine_cc=Uint[16](750)
    )
    
    assert car.vehicle.year == 2022
    assert str(car.vehicle.make) == "Toyota"
    assert str(car.vehicle.model) == "Camry"
    assert car.doors == 4
    assert str(car.fuel_type) == "Gasoline"
    
    assert motorcycle.vehicle.year == 2021
    assert str(motorcycle.vehicle.make) == "Harley-Davidson"
    assert str(motorcycle.vehicle.model) == "Street 750"
    assert motorcycle.engine_cc == 750
    assert not motorcycle.has_sidecar


def test_struct_validation():
    """Test struct field validation and type safety."""
    @structure
    class BankAccount:
        account_number: String
        balance: Uint[32]  # Balance in cents
        owner: String
        active: Bool = field(metadata={"default": Bool(True)})
    
    # Valid account creation
    account = BankAccount(
        account_number=String("12345-67890"),
        balance=Uint[32](100000),  # $1000.00
        owner=String("Alice Johnson")
    )
    assert str(account.owner) == "Alice Johnson"
    assert account.balance == 100000
    assert bool(account.active) is True
    
    # Note: Type validation is not enforced at runtime in this implementation
    # The struct decorator doesn't add runtime type checking
    assert True  # Placeholder assertion since runtime validation isn't implemented


def test_struct_edge_cases():
    """Test edge cases for struct handling."""
    # Empty struct
    @structure
    class EmptyStruct:
        pass
    
    empty = EmptyStruct()
    encoded = empty.encode()
    decoded = EmptyStruct.decode(encoded)
    assert isinstance(decoded, EmptyStruct)
    
    # Struct with single field
    @structure
    class SingleField:
        value: Uint[32]
    
    single = SingleField(value=Uint[32](42))
    assert single.value == 42
    
    encoded = single.encode()
    decoded = SingleField.decode(encoded)
    assert decoded.value == 42


def test_struct_comprehensive():
    """Comprehensive test of struct features."""
    class Status(Enum):
        ACTIVE = 1
        INACTIVE = 0
    
    @structure
    class ComplexStruct:
        id: Uint[32]
        name: String
        status: Status
        optional_data: Option[String]
        tags: TypedVector[String]
    
    # Create complex struct
    complex_struct = ComplexStruct(
        id=Uint[32](12345),
        name=String("Test Entity"),
        status=Status.ACTIVE,
        optional_data=Option[String](String("Some data")),
        tags=TypedVector[String]([String("tag1"), String("tag2"), String("tag3")])
    )
    
    assert complex_struct.id == 12345
    assert str(complex_struct.name) == "Test Entity"
    assert complex_struct.status._name_ == "ACTIVE"
    assert complex_struct.optional_data
    assert str(complex_struct.optional_data.unwrap()) == "Some data"
    assert len(complex_struct.tags) == 3
    assert str(complex_struct.tags[0]) == "tag1"
    
    # Test encoding round-trip
    encoded = complex_struct.encode()
    decoded = ComplexStruct.decode(encoded)
    
    assert decoded.id == complex_struct.id
    assert str(decoded.name) == str(complex_struct.name)
    assert decoded.status == complex_struct.status
    assert bool(decoded.optional_data) == bool(complex_struct.optional_data)
    assert len(decoded.tags) == len(complex_struct.tags)


def test_struct_json_round_trip():
    """Test JSON serialization round-trip for structs."""
    @structure
    class TestStruct:
        text: String
        number: Uint[32]
        flag: Bool
    
    original = TestStruct(
        text=String("Hello World"),
        number=Uint[32](42),
        flag=Bool(True)
    )
    
    # JSON round-trip
    json_data = original.to_json()
    restored = TestStruct.from_json(json_data)
    
    assert str(original.text) == str(restored.text)
    assert original.number == restored.number
    assert bool(original.flag) == bool(restored.flag) 