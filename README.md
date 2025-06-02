# tsrkit-types

A comprehensive Python library providing fundamental data types with encoding and decoding capabilities.

## Features

- **Integer Types**: `U8`, `U16`, `U32`, `U64`, `U128`, `U256`, `Int`
- **String Types**: `String`
- **Boolean Types**: `Boolean`, `Bit`
- **Null Types**: `Null`, `Nullable`
- **Composite Types**: `Choice`, `Option`
- **Container Types**: `Dictionary`, `Array`, `Vector`
- **Byte Types**: `Bytes`
- **Enum Types**: Custom enumeration support
- **Struct Types**: Custom structured data types

All types implement the `Codable` interface, providing consistent encoding and decoding functionality.

## Installation

```bash
pip install tsrkit-types
```

## Quick Start

```python
from tsrkit_types.integers import Uint
from tsrkit_types.string import String
from tsrkit_types.struct import struct

@struct
class Person:
    name: String
    age: Uint[8]

person = Person(name=String("John"), age=Uint[8](30))
print(person.name)  # "John"
print(person.age)   # 30

# Encode/decode
encoded = person.encode()
decoded = Person.decode(encoded)
```

## License

[Add your license here] 