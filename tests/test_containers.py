import pytest
from tsrkit_types.sequences import Array, Vector, TypedArray, TypedVector, BoundedVector, TypedBoundedVector
from tsrkit_types.dictionary import Dictionary
from tsrkit_types.integers import U8, U16, U32
from tsrkit_types.string import String
from tsrkit_types.bool import Bool


def test_fixed_arrays():
    """Test fixed-size arrays."""
    # Create fixed-size array types
    Array10 = Array[10]  # Exactly 10 elements
    Array5 = Array[5]    # Exactly 5 elements
    
    # Create instances
    numbers = Array10([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    letters = Array5(['a', 'b', 'c', 'd', 'e'])
    
    assert len(numbers) == 10
    assert len(letters) == 5
    assert list(numbers) == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert list(letters) == ['a', 'b', 'c', 'd', 'e']
    
    # Arrays have fixed size - cannot append
    with pytest.raises((ValueError, AttributeError)):
        numbers.append(11)


def test_typed_arrays():
    """Test typed fixed-size arrays."""
    # Create typed array types
    U16Array5 = TypedArray[U16, 5]  # 5 U16 elements
    StringArray3 = TypedArray[String, 3]  # 3 String elements
    
    # Create instances with proper types
    coordinates = U16Array5([U16(100), U16(200), U16(150), U16(300), U16(250)])
    names = StringArray3([String("Alice"), String("Bob"), String("Carol")])
    
    assert len(coordinates) == 5
    assert len(names) == 3
    assert coordinates[0] == 100
    assert str(names[0]) == "Alice"
    
    # Type validation
    with pytest.raises(TypeError):
        U16Array5([100, 200, 150, 300, 250])  # Raw ints, not U16
    
    # Element access and modification
    assert isinstance(coordinates[0], U16)
    coordinates[0] = U16(500)
    assert coordinates[0] == 500


def test_vectors():
    """Test variable-size vectors."""
    # Create vector types with maximum sizes
    Vector100 = Vector[0, 100]  # Up to 100 elements
    Vector1000 = Vector[0, 1000]  # Up to 1000 elements
    
    # Create instances
    small_list = Vector100([1, 2, 3])
    large_list = Vector1000(list(range(50)))  # 50 elements
    
    assert len(small_list) == 3
    assert len(large_list) == 50
    assert list(small_list) == [1, 2, 3]
    assert list(large_list) == list(range(50))
    
    # Vectors can grow
    small_list.append(4)
    small_list.extend([5, 6, 7, 8, 9, 10])
    assert len(small_list) == 10
    assert list(small_list) == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    
    # But not beyond maximum
    with pytest.raises(ValueError):
        Vector100([0] * 150)  # 150 > 100


def test_typed_vectors():
    """Test typed variable-size vectors."""
    # Create typed vector types
    U16Vector = TypedVector[U16]
    StringVector = TypedVector[String]
    BoolVector = TypedVector[Bool]
    
    # Create instances
    numbers = U16Vector([U16(1), U16(2), U16(3)])
    words = StringVector([String("hello"), String("world")])
    flags = BoolVector([Bool(True), Bool(False), Bool(True)])
    
    assert len(numbers) == 3
    assert len(words) == 2
    assert len(flags) == 3
    
    # Add elements with type checking
    numbers.append(U16(4))
    words.append(String("example"))
    flags.append(Bool(False))
    
    assert len(numbers) == 4
    assert len(words) == 3
    assert len(flags) == 4
    
    # Type checking on assignment
    with pytest.raises(TypeError):
        numbers[0] = 42  # Raw int, not U16


def test_bounded_vectors():
    """Test size-constrained vectors."""
    # Vectors with minimum and maximum size constraints
    BoundedList = BoundedVector[5, 10]  # 5-10 elements
    TypedBoundedList = TypedBoundedVector[U8, 3, 7]  # 3-7 U8 elements
    
    # Valid sizes
    medium_list = BoundedList([1, 2, 3, 4, 5, 6, 7])  # 7 elements (valid)
    typed_list = TypedBoundedList([U8(10), U8(20), U8(30), U8(40)])  # 4 elements (valid)
    
    assert len(medium_list) == 7
    assert len(typed_list) == 4
    
    # Test size constraints
    with pytest.raises(ValueError):
        BoundedList([1, 2])  # 2 < 5
    
    with pytest.raises(ValueError):
        TypedBoundedList([U8(i) for i in range(20)])  # 20 > 7


def test_sequence_encoding():
    """Test sequence encoding and decoding."""
    # Test different sequence types
    sequences = [
        Array[U8, 3]([U8(1), U8(2), U8(3)]),
        TypedArray[U8, 3]([U8(1), U8(2), U8(3)]),
        Vector[U8, 0, 10]([U8(1), U8(2), U8(3), U8(4)]),
        TypedVector[U16]([U16(100), U16(200), U16(300)]),
    ]
    
    for seq in sequences:
        encoded = seq.encode()
        decoded = type(seq).decode(encoded)
        
        assert len(encoded) > 0
        assert len(decoded) == len(seq)
        assert list(decoded) == list(seq)


def test_basic_dictionary():
    """Test basic dictionary usage."""
    # Create dictionary types
    StringToInt = Dictionary[String, U32]
    IntToString = Dictionary[U8, String]
    
    # Create instances
    scores = StringToInt({
        String("alice"): U32(95),
        String("bob"): U32(87),
        String("carol"): U32(92)
    })
    
    names = IntToString({
        U8(1): String("First"),
        U8(2): String("Second"),
        U8(3): String("Third")
    })
    
    assert len(scores) == 3
    assert len(names) == 3
    assert scores[String("alice")] == 95
    assert str(names[U8(1)]) == "First"
    
    # Dictionary operations
    scores[String("dave")] = U32(88)
    assert len(scores) == 4
    assert scores[String("dave")] == 88
    
    # Access values
    alice_score = scores[String("alice")]
    assert alice_score == 95
    assert isinstance(alice_score, U32)


def test_complex_dictionary():
    """Test dictionaries with complex value types."""
    # Dictionary with nested types
    ConfigDict = Dictionary[String, TypedVector[U16]]
    
    config = ConfigDict({
        String("ports"): TypedVector[U16]([U16(80), U16(443), U16(8080)]),
        String("timeouts"): TypedVector[U16]([U16(30), U16(60), U16(120)]),
        String("limits"): TypedVector[U16]([U16(100), U16(1000), U16(10000)])
    })
    
    assert len(config) == 3
    assert len(config[String("ports")]) == 3
    assert config[String("ports")][0] == 80
    
    # Modify nested values
    config[String("ports")].append(U16(9000))
    assert len(config[String("ports")]) == 4
    assert config[String("ports")][3] == 9000


def test_dictionary_encoding():
    """Test dictionary encoding and decoding."""
    # Simple dictionary
    StringToU8 = Dictionary[String, U8]
    data = StringToU8({
        String("a"): U8(1),
        String("b"): U8(2),
        String("c"): U8(3)
    })
    
    # Encode and decode
    encoded = data.encode()
    decoded = StringToU8.decode(encoded)
    
    assert len(encoded) > 0
    assert len(decoded) == len(data)
    assert decoded[String("a")] == 1
    assert decoded[String("b")] == 2
    assert decoded[String("c")] == 3


def test_dictionary_json():
    """Test dictionary JSON serialization."""
    # Create a dictionary with various types
    MixedDict = Dictionary[String, U32]
    data = MixedDict({
        String("count"): U32(42),
        String("limit"): U32(100),
        String("offset"): U32(0)
    })
    
    # JSON serialization
    json_data = data.to_json()
    restored = MixedDict.from_json(json_data)
    
    assert len(restored) == len(data)
    assert restored[String("count")] == 42
    assert restored[String("limit")] == 100
    assert restored[String("offset")] == 0


def test_container_validation():
    """Test type validation in containers."""
    # Typed vector with strict validation
    StrictVector = TypedVector[U16]
    
    # Valid operations
    valid_vec = StrictVector([U16(1), U16(2), U16(3)])
    valid_vec.append(U16(4))
    valid_vec.insert(0, U16(0))
    assert len(valid_vec) == 5
    assert list(valid_vec) == [0, 1, 2, 3, 4]
    
    # Invalid operations
    with pytest.raises(TypeError):
        StrictVector([1, 2, 3])  # Raw integers
    
    with pytest.raises(TypeError):
        StrictVector([U16(1), U8(2)])  # Mixed types
    
    with pytest.raises(TypeError):
        valid_vec.append(42)  # Wrong append type


def test_nested_containers():
    """Test nested container structures."""
    # Matrix-like structure: Vector of Vectors
    MatrixRow = TypedVector[U8]
    Matrix = TypedVector[MatrixRow]
    
    # Create a 3x3 matrix
    matrix = Matrix([
        MatrixRow([U8(1), U8(2), U8(3)]),
        MatrixRow([U8(4), U8(5), U8(6)]),
        MatrixRow([U8(7), U8(8), U8(9)])
    ])
    
    assert len(matrix) == 3
    assert len(matrix[0]) == 3
    assert matrix[1][1] == 5
    
    # Access and modify elements
    assert matrix[1][1] == 5
    matrix[1][1] = U8(99)
    assert matrix[1][1] == 99
    
    # Dictionary of vectors
    GroupData = Dictionary[String, TypedVector[U32]]
    groups = GroupData({
        String("admins"): TypedVector[U32]([U32(1), U32(2)]),
        String("users"): TypedVector[U32]([U32(10), U32(11), U32(12)]),
        String("guests"): TypedVector[U32]([U32(100)])
    })
    
    assert len(groups) == 3
    assert len(groups[String("users")]) == 3
    assert groups[String("guests")][0] == 100


def test_container_edge_cases():
    """Test edge cases for container types."""
    # Empty containers
    empty_vector = TypedVector[U32]([])
    empty_dict = Dictionary[String, U32]({})
    
    assert len(empty_vector) == 0
    assert len(empty_dict) == 0
    
    # Single element containers
    single_vector = TypedVector[U32]([U32(42)])
    single_dict = Dictionary[String, U32]({String("key"): U32(42)})
    
    assert len(single_vector) == 1
    assert len(single_dict) == 1
    assert single_vector[0] == 42
    assert single_dict[String("key")] == 42
    
    # Test encoding of edge cases
    for container in [empty_vector, empty_dict, single_vector, single_dict]:
        encoded = container.encode()
        decoded = type(container).decode(encoded)
        assert len(decoded) == len(container)


def test_container_iteration():
    """Test iteration over containers."""
    # Vector iteration
    vector = TypedVector[U16]([U16(10), U16(20), U16(30)])
    values = []
    for item in vector:
        values.append(int(item))
    assert values == [10, 20, 30]
    
    # Dictionary iteration
    dictionary = Dictionary[String, U8]({
        String("a"): U8(1),
        String("b"): U8(2)
    })
    
    keys = list(dictionary.keys())
    values = list(dictionary.values())
    items = list(dictionary.items())
    
    assert len(keys) == 2
    assert len(values) == 2
    assert len(items) == 2
    
    # Check that we get proper types
    for key in keys:
        assert isinstance(key, String)
    for value in values:
        assert isinstance(value, U8)


def test_container_comprehensive():
    """Comprehensive test of container features."""
    # Complex nested structure
    ComplexData = Dictionary[String, TypedVector[Dictionary[String, U32]]]
    
    data = ComplexData({
        String("users"): TypedVector[Dictionary[String, U32]]([
            Dictionary[String, U32]({
                String("id"): U32(1),
                String("age"): U32(25)
            }),
            Dictionary[String, U32]({
                String("id"): U32(2),
                String("age"): U32(30)
            })
        ])
    })
    
    # Verify structure
    assert len(data) == 1
    users = data[String("users")]
    assert len(users) == 2
    user1 = users[0]
    assert user1[String("id")] == 1
    assert user1[String("age")] == 25
    
    # Test encoding round-trip
    encoded = data.encode()
    decoded = ComplexData.decode(encoded)
    
    decoded_users = decoded[String("users")]
    decoded_user1 = decoded_users[0]
    assert decoded_user1[String("id")] == 1
    assert decoded_user1[String("age")] == 25 