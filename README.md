# TSRKit Types

Performant Python Typings library for type-safe binary serialization, JSON encoding, and data validation with zero dependencies.

Perfect for network protocols, game state serialization, configuration files, and any application requiring efficient, validated data handling.

## Features

- **🔒 Type Safe**: Strong typing with runtime validation and type hints
- **⚡ High Performance**: Efficient binary encoding with zero-copy operations where possible  
- **📦 Zero Dependencies**: No external runtime dependencies
- **🔄 Dual Serialization**: Both binary and JSON serialization support
- **🧩 Generic Support**: Parameterized types for flexible, reusable code
- **🎯 Memory Efficient**: Minimal overhead, extends built-in Python types
- **🚀 Easy to Use**: Intuitive API with comprehensive type system

## Installation

```bash
pip install tsrkit-types
```

## Type Categories

### Integer Types (extension of Python int)

#### Unsigned Integers (`Uint`)

The `Uint` class provides both fixed-size and variable-size unsigned integers.

**Fixed-Size Integers:**
```python
from tsrkit_types.integers import Uint

# Pre-defined types
value = Uint[8](255)        # 8-bit unsigned integer (0-255)
value = Uint[16](65535)     # 16-bit unsigned integer (0-65535) 
value = Uint[32](42949)     # 32-bit unsigned integer
value = Uint[64](1844674)   # 64-bit unsigned integer

# Dynamic size specification
U128 = Uint[128]       # 128-bit unsigned integer
value = U128(123456789)

# Encoding/Decoding
encoded = value.encode()           # Encode to bytes
decoded = U8.decode(encoded)       # Decode from bytes
size = value.encode_size()         # Get encoded size
```

**Variable-Size General Integers:**
```python
# General integers (supports up to 2^64 - 1 with variable encoding)
num = Uint(1000)       # Variable-length encoding
encoded = num.encode()
decoded = Uint.decode(encoded)

# Arithmetic operations preserve type
a = Uint[8](10)
b = Uint[8](20)
result = a + b         # result is Uint[8](30)
```

**Encoding Details:**
- Fixed-size integers use little-endian encoding
- Variable-size integers use a compact encoding scheme that optimizes for smaller values
- Values < 2^7 are encoded in 1 byte
- Larger values use a variable-length prefix encoding

### String Types (extension of Python str)

#### UTF-8 Strings (`String`)

```python
from tsrkit_types.string import String

# Creation
text = String("Hello, World!")
text = String("Unicode: 🚀🔥")

# Properties
length = len(text)               # Character count
text_str = str(text)            # Convert to Python str

# Encoding/Decoding
encoded = text.encode()          # [length][utf8_bytes]
decoded = String.decode(encoded)

# JSON serialization
json_data = text.to_json()       # Returns the string value
restored = String.from_json(json_data)
```

**Encoding Format:**
- Length prefix (variable-length `Uint`) followed by UTF-8 bytes
- String length is measured in UTF-16 code units (like Python strings)

### Boolean Types

#### Boolean (`Bool`)

```python
from tsrkit_types.bool import Bool

# Creation
true_val = Bool(True)
false_val = Bool(False)

# Usage
if true_val:                     # Supports truthiness testing
    print("It's true!")

# Encoding/Decoding
encoded = true_val.encode()      # 1 byte: 0x01 or 0x00
decoded = Bool.decode(encoded)

# JSON serialization
json_str = true_val.to_json()    # "true" or "false"
restored = Bool.from_json("true")
```

### Null Types

```python
from tsrkit_types.null import Null

# Null type
null_val = Null                  # Singleton null value
```

### Choice and Option Types

#### Choice (Union Types)

```python
from tsrkit_types.choice import Choice
from tsrkit_types.integers import U8, U16
from tsrkit_types.string import String

# Anonymous choice
IntOrString = Choice[U8, String]
value = IntOrString(U8(42))
value = IntOrString(String("hello"))

# Switch the choice
value.set(String("world"))
inner = value.unwrap()           # Get the inner value

# Named choice with custom keys
class Result(Choice):
    success: String
    error: U8

result = Result(String("OK"))
result = Result(U8(404), key="error")

# JSON serialization
json_data = result.to_json()     # {"success": "OK"} or {"error": 404}
restored = Result.from_json(json_data)

# Encoding
encoded = result.encode()        # [variant_index][value]
decoded = Result.decode(encoded)
```

#### Option (Optional Value - T | Null)

```python
from tsrkit_types.option import Option
from tsrkit_types.integers import U32

# Optional value
opt_val = Option[U32](U32(100))  # Some value
empty_opt = Option[U32]()        # None/Null

# Check if has value
if opt_val:                      # Truthiness test
    value = opt_val.unwrap()     # Get the U32 value

# Encoding (more efficient than general Choice)
encoded = opt_val.encode()       # 1 byte tag + optional value
decoded = Option[U32].decode(encoded)
```

### Container Types

#### Sequences (Extension of Python list)

```python
from tsrkit_types.sequences import Array, Vector, TypedArray, TypedVector
from tsrkit_types.integers import U16

# Fixed-size array
FixedArray = Array[10]           # Array of exactly 10 elements
arr = FixedArray([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

# Typed fixed-size array  
TypedFixedArray = TypedArray[U16, 5]  # 5 U16 elements
typed_arr = TypedFixedArray([U16(1), U16(2), U16(3), U16(4), U16(5)])

# Variable-size vector
DynamicVector = Vector[100]       # Vector with max 100 elements
vec = DynamicVector([1, 2, 3])

# Typed variable-size vector
TypedDynamicVector = TypedVector[U16]  # Vector of U16 elements
typed_vec = TypedDynamicVector([U16(1), U16(2)])

# Operations
vec.append(4)                    # Add element with validation
vec.extend([5, 6, 7])           # Add multiple elements
vec[0] = 100                    # Set element with validation

# Encoding
encoded = typed_vec.encode()     # [length?][element1][element2]...
decoded = TypedDynamicVector.decode(encoded)
```

**Sequence Types:**
- `Array[N]`: Fixed size, any element type
- `Vector`: Variable size, any element type  
- `TypedArray[T, N]`: Fixed size with typed elements
- `TypedVector[T]`: Variable size with typed elements
- `BoundedVector[min, max]`: Size constrained vector
- `TypedBoundedVector[T, min, max]`: Typed and size constrained

#### Dictionary

```python
from tsrkit_types.dictionary import Dictionary
from tsrkit_types.string import String
from tsrkit_types.integers import U32

# Create dictionary type
StringToInt = Dictionary[String, U32]
data = StringToInt({
    String("key1"): U32(100),
    String("key2"): U32(200)
})

# Operations
data[String("key3")] = U32(300)   # Add entry
value = data[String("key1")]      # Get value
del data[String("key2")]          # Remove entry

# Iteration
for key, value in data.items():
    print(f"{key}: {value}")

# Encoding
encoded = data.encode()           # [length][key1][value1][key2][value2]...
decoded = StringToInt.decode(encoded)

# JSON serialization
json_data = data.to_json()        # {"key1": 100, "key3": 300}
restored = StringToInt.from_json(json_data)
```

### Bytes Types

#### Bytes (extension of Python in-built bytes)

```python
from tsrkit_types.bytes import Bytes

# Creation
data = Bytes(b"Hello, binary world!")
data = Bytes([0x01, 0x02, 0x03, 0x04])

# Bytes <-> Bits Operations
data.to_bits()          # [True, False, True, ...]
Bytes.from_bits([True, False, True, ...])

# Operations
length = len(data)               # Byte length
raw_bytes = bytes(data)         # Convert to Python bytes

# Encoding
encoded = data.encode()          # [length][raw_bytes]
decoded = Bytes.decode(encoded)

# JSON serialization (hex encoded)
json_str = data.to_json()        # "48656c6c6f2c2062696e61727920776f726c6421"
restored = Bytes.from_json(json_str)
```

#### Bit Arrays (Sequence of bool)

```python
from tsrkit_types.bits import BitArray

# Creation
bits = BitArray([True, False, True, True, False])
bits = BitArray.from_hex("1A3F")    # From hex string
bits = BitArray.from_int(42, 8)     # From integer with bit width

# Operations
bit_val = bits[0]                # Get bit at index
bits[1] = True                   # Set bit at index
bits.append(False)               # Add bit
bits.extend([True, False])       # Add multiple bits

# Conversion
hex_str = bits.to_hex()          # Convert to hex string
int_val = bits.to_int()          # Convert to integer

# Encoding
encoded = bits.encode()          # [length][packed_bits]
decoded = BitArray.decode(encoded)
```

### Enum (Extension of Python Enum, with Codable + JSON support)

```python
from tsrkit_types.enum import Enum

# Define enum
class Color(Enum):
    RED = 0
    GREEN = 1
    BLUE = 2

# Usage
color = Color.RED
color_val = Color(1)             # Color.GREEN

# String conversion
name = color.name                # "RED"
value = color.value              # 0

# Encoding
encoded = color.encode()         # Variable-length uint encoding
decoded = Color.decode(encoded)

# JSON serialization
json_data = color.to_json()      # "RED"
restored = Color.from_json("GREEN")
```

### Structured Types

#### Struct Decorator (Extension of dataclasses)

```python
from tsrkit_types.struct import struct
from tsrkit_types.string import String
from tsrkit_types.integers import U8, U32
from dataclasses import field

@structure
class Person:
    name: String
    age: U8
    
@structure  
class Employee:
    person: Person
    employee_id: U32
    department: String = field(metadata={"default": String("Unknown")})

# Creation
person = Person(name=String("John Doe"), age=U8(30))
employee = Employee(
    person=person,
    employee_id=U32(12345),
    department=String("Engineering")
)

# Access fields
print(employee.person.name)      # "John Doe"
print(employee.employee_id)      # 12345

# Encoding/Decoding
encoded = employee.encode()      # Concatenated field encodings
decoded = Employee.decode(encoded)

# JSON serialization with custom field names
@structure
class CustomPerson:
    name: String = field(metadata={"name": "full_name"})
    age: U8

person = CustomPerson(name=String("Jane"), age=U8(25))
json_data = person.to_json()     # {"full_name": "Jane", "age": 25}
restored = CustomPerson.from_json({"full_name": "Jane", "age": 25})
```

**Struct Features:**
- Automatic `Codable` implementation
- Field validation and type checking
- Default values via metadata
- Custom JSON field mapping
- Inheritance support
- Frozen/immutable variants

## Advanced Usage

### Custom Types

Implement your own `Codable` types:

```python
from tsrkit_types.itf.codable import Codable
from typing import Tuple, Union

class Point3D(Codable):
    def __init__(self, x: float, y: float, z: float):
        self.x, self.y, self.z = x, y, z
    
    def encode_size(self) -> int:
        return 24  # 3 doubles = 24 bytes
    
    def encode_into(self, buffer: bytearray, offset: int = 0) -> int:
        import struct
        struct.pack_into('<ddd', buffer, offset, self.x, self.y, self.z)
        return 24
    
    @classmethod
    def decode_from(cls, buffer: Union[bytes, bytearray, memoryview], 
                   offset: int = 0) -> Tuple['Point3D', int]:
        import struct
        x, y, z = struct.unpack_from('<ddd', buffer, offset)
        return cls(x, y, z), 24
```

### Configuration and Optimization

```python
# Optimize for specific use cases
@structure(frozen=True)             # Immutable structs
class ImmutableData:
    value: U64

# Memory-efficient sequences
CompactArray = TypedArray[U8, 1000]  # 1000 bytes exactly
data = CompactArray([0] * 1000)

# Bounded containers for validation
BoundedList = BoundedVector[10, 100]  # Between 10 and 100 elements
safe_list = BoundedList([0] * 50)
```

### Error Handling

```python
from tsrkit_types.integers import U8

try:
    # Value out of range
    invalid = U8(256)               # Raises ValueError
except ValueError as e:
    print(f"Range error: {e}")

try:
    # Type mismatch in Choice
    choice = Choice[U8, String](42) # Raises TypeError
except TypeError as e:
    print(f"Type error: {e}")

try:
    # Buffer too small for decoding
    corrupted = b"\x01"
    U32.decode(corrupted)           # Raises ValueError
except ValueError as e:
    print(f"Decode error: {e}")
```


## Core Interface

All types implement the `Codable` interface:

```python
from tsrkit_types.itf.codable import Codable

class MyType(Codable):
    def encode_size(self) -> int: ...      # Size needed for encoding
    def encode_into(self, buffer: bytearray, offset: int = 0) -> int: ...  # Encode into buffer
    def encode(self) -> bytes: ...         # Encode to new bytes object
    
    @classmethod
    def decode_from(cls, buffer: bytes, offset: int = 0) -> Tuple[T, int]: ...  # Decode from buffer
    @classmethod
    def decode(cls, buffer: bytes, offset: int = 0) -> T: ...  # Decode from buffer (convenience)
```

## Performance Considerations

### Encoding Efficiency

- **Fixed-size types** (U8, U16, etc.) have constant encoding size
- **Variable-size types** (general Uint) optimize for smaller values
- **Sequences** encode length only when necessary (variable-size)
- **Strings** use UTF-8 encoding with variable-length prefix

### Memory Usage

- Types extend built-in Python types where possible (int, str, list, dict)
- Zero-copy operations where feasible
- Minimal overhead for type metadata

### Best Practices

```python
# Prefer fixed-size types when range is known
user_id = U32(123456)            # Better than Uint(123456)

# Use typed containers for homogeneous data
scores = TypedVector[U16]([100, 95, 87, 92])

# Batch operations for better performance
data = TypedArray[U8, 1000]([0] * 1000)
encoded = data.encode()          # Single operation vs. encoding each element

# Reuse buffer for multiple encodings
buffer = bytearray(1024)
offset = 0
offset += value1.encode_into(buffer, offset)
offset += value2.encode_into(buffer, offset)
```

## Examples

### Network Protocol

```**python**
@structure
class NetworkPacket:
    packet_type: U8
    session_id: U32
    payload_length: U16
    payload: Bytes

# Create packet
packet = NetworkPacket(
    packet_type=U8(1),
    session_id=U32(0x12345678),
    payload_length=U16(13),
    payload=Bytes(b"Hello, World!")
)

# Serialize for transmission
wire_data = packet.encode()

# Deserialize on receiver
received_packet = NetworkPacket.decode(wire_data)
```

### Configuration File

```python
@structure
class DatabaseConfig:
    host: String
    port: U16
    username: String 
    password: String
    max_connections: U8 = field(metadata={"default": U8(10)})
    ssl_enabled: Bool = field(metadata={"default": Bool(True)})

# Create config
config = DatabaseConfig(
    host=String("localhost"),
    port=U16(5432),
    username=String("admin"),
    password=String("secret")
)

# Save to JSON
import json
with open("db_config.json", "w") as f:
    json.dump(config.to_json(), f)

# Load from JSON
with open("db_config.json", "r") as f:
    data = json.load(f)
    config = DatabaseConfig.from_json(data)
```

### Game State Serialization

```python
class GameEntityType(Enum):
    PLAYER = 0
    ENEMY = 1
    ITEM = 2

@structure
class Position:
    x: U16
    y: U16

@structure  
class GameEntity:
    entity_type: GameEntityType
    position: Position
    health: U8
    name: String

@structure
class GameState:
    level: U8
    score: U32
    entities: TypedVector[GameEntity]

# Create game state
state = GameState(
    level=U8(1),
    score=U32(1500),
    entities=TypedVector[GameEntity]([
        GameEntity(
            entity_type=GameEntityType.PLAYER,
            position=Position(x=U16(100), y=U16(200)),
            health=U8(100),
            name=String("Hero")
        )
    ])
)

# Save/load game
save_data = state.encode()
loaded_state = GameState.decode(save_data)
```

## Development

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/chainscore/tsrkit-types.git
   cd tsrkit-types
   ```

2. **Install development dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

### Running Tests

**Run the full test suite:**
```bash
pytest
```

**Run tests with coverage:**
```bash
pytest --cov=tsrkit_types --cov-report=html
```

**Run tests in parallel (faster):**
```bash
pytest -n auto
```

**Run specific test categories:**
```bash
pytest tests/test_integers.py      # Integer type tests
pytest tests/test_strings.py       # String type tests  
pytest tests/test_containers.py    # Container type tests
pytest tests/test_structs.py       # Struct tests
pytest tests/test_network.py       # Network protocol tests
```

**Run tests with verbose output:**
```bash
pytest -v
```

**Skip slow tests:**
```bash
pytest -m "not slow"
```

### Test Coverage

View the test coverage report:
```bash
# Generate HTML coverage report
pytest --cov=tsrkit_types --cov-report=html
open htmlcov/index.html  # macOS
# or xdg-open htmlcov/index.html  # Linux
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Requirements

- **Python**: >= 3.11
- **Runtime Dependencies**: None (zero dependencies!)
- **Development Dependencies**: pytest and plugins (see `pyproject.toml`) 