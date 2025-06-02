import pytest
from tsrkit_types.integers import Uint
from tsrkit_types.sequences import Array, Vector, TypedArray, TypedVector, BoundedVector, TypedBoundedVector
from tsrkit_types.dictionary import Dictionary
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
    Uint16Array5 = TypedArray[Uint[16], 5]  # 5 Uint[16] elements
    StringArray3 = TypedArray[String, 3]  # 3 String elements
    
    # Create instances with proper types
    coordinates = Uint16Array5([Uint[16](100), Uint[16](200), Uint[16](150), Uint[16](300), Uint[16](250)])
    names = StringArray3([String("Alice"), String("Bob"), String("Carol")])
    
    assert len(coordinates) == 5
    assert len(names) == 3
    assert coordinates[0] == 100
    assert str(names[0]) == "Alice"
    
    # Type validation
    with pytest.raises(TypeError):
        Uint16Array5([100, 200, 150, 300, 250])  # Raw ints, not Uint[16]
    
    # Element access and modification
    assert isinstance(coordinates[0], Uint[16])
    coordinates[0] = Uint[16](500)
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
    Uint16Vector = TypedVector[Uint[16]]
    StringVector = TypedVector[String]
    BoolVector = TypedVector[Bool]
    
    # Create instances
    numbers = Uint16Vector([Uint[16](1), Uint[16](2), Uint[16](3)])
    words = StringVector([String("hello"), String("world")])
    flags = BoolVector([Bool(True), Bool(False), Bool(True)])
    
    assert len(numbers) == 3
    assert len(words) == 2
    assert len(flags) == 3
    
    # Add elements with type checking
    numbers.append(Uint[16](4))
    words.append(String("example"))
    flags.append(Bool(False))
    
    assert len(numbers) == 4
    assert len(words) == 3
    assert len(flags) == 4
    
    # Type checking on assignment
    with pytest.raises(TypeError):
        numbers[0] = 42  # Raw int, not Uint[16]


def test_bounded_vectors():
    """Test size-constrained vectors."""
    # Vectors with minimum and maximum size constraints
    BoundedList = BoundedVector[5, 10]  # 5-10 elements
    TypedBoundedList = TypedBoundedVector[Uint[8], 3, 7]  # 3-7 Uint[8] elements
    
    # Valid sizes
    medium_list = BoundedList([1, 2, 3, 4, 5, 6, 7])  # 7 elements (valid)
    typed_list = TypedBoundedList([Uint[8](10), Uint[8](20), Uint[8](30), Uint[8](40)])  # 4 elements (valid)
    
    assert len(medium_list) == 7
    assert len(typed_list) == 4
    
    # Test size constraints
    with pytest.raises(ValueError):
        BoundedList([1, 2])  # 2 < 5
    
    with pytest.raises(ValueError):
        TypedBoundedList([Uint[8](i) for i in range(20)])  # 20 > 7


def test_sequence_encoding():
    """Test sequence encoding and decoding."""
    # Test different sequence types
    sequences = [
        Array[Uint[8], 3]([Uint[8](1), Uint[8](2), Uint[8](3)]),
        TypedArray[Uint[8], 3]([Uint[8](1), Uint[8](2), Uint[8](3)]),
        Vector[Uint[8], 0, 10]([Uint[8](1), Uint[8](2), Uint[8](3), Uint[8](4)]),
        TypedVector[Uint[16]]([Uint[16](100), Uint[16](200), Uint[16](300)]),
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
    StringToInt = Dictionary[String, Uint[32]]
    IntToString = Dictionary[Uint[8], String]
    
    # Create instances
    scores = StringToInt({
        String("alice"): Uint[32](95),
        String("bob"): Uint[32](87),
        String("carol"): Uint[32](92)
    })
    
    names = IntToString({
        Uint[8](1): String("First"),
        Uint[8](2): String("Second"),
        Uint[8](3): String("Third")
    })
    
    assert len(scores) == 3
    assert len(names) == 3
    assert scores[String("alice")] == 95
    assert str(names[Uint[8](1)]) == "First"
    
    # Dictionary operations
    scores[String("dave")] = Uint[32](88)
    assert len(scores) == 4
    assert scores[String("dave")] == 88
    
    # Access values
    alice_score = scores[String("alice")]
    assert alice_score == 95
    assert isinstance(alice_score, Uint[32])


def test_complex_dictionary():
    """Test dictionaries with complex value types."""
    # Dictionary with nested types
    ConfigDict = Dictionary[String, TypedVector[Uint[16]]]
    
    config = ConfigDict({
        String("ports"): TypedVector[Uint[16]]([Uint[16](80), Uint[16](443), Uint[16](8080)]),
        String("timeouts"): TypedVector[Uint[16]]([Uint[16](30), Uint[16](60), Uint[16](120)]),
        String("limits"): TypedVector[Uint[16]]([Uint[16](100), Uint[16](1000), Uint[16](10000)])
    })
    
    assert len(config) == 3
    assert len(config[String("ports")]) == 3
    assert config[String("ports")][0] == 80
    
    # Modify nested values
    config[String("ports")].append(Uint[16](9000))
    assert len(config[String("ports")]) == 4
    assert config[String("ports")][3] == 9000


def test_dictionary_encoding():
    """Test dictionary encoding and decoding."""
    # Simple dictionary
    StringToUint8 = Dictionary[String, Uint[8]]
    data = StringToUint8({
        String("a"): Uint[8](1),
        String("b"): Uint[8](2),
        String("c"): Uint[8](3)
    })
    
    # Encode and decode
    encoded = data.encode()
    decoded = StringToUint8.decode(encoded)
    
    assert len(encoded) > 0
    assert len(decoded) == len(data)
    assert decoded[String("a")] == 1
    assert decoded[String("b")] == 2
    assert decoded[String("c")] == 3


def test_dictionary_json():
    """Test dictionary JSON serialization."""
    # Create a dictionary with various types
    MixedDict = Dictionary[String, Uint[32]]
    data = MixedDict({
        String("count"): Uint[32](42),
        String("limit"): Uint[32](100),
        String("offset"): Uint[32](0)
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
    StrictVector = TypedVector[Uint[16]]
    
    # Valid operations
    valid_vec = StrictVector([Uint[16](1), Uint[16](2), Uint[16](3)])
    valid_vec.append(Uint[16](4))
    valid_vec.insert(0, Uint[16](0))
    assert len(valid_vec) == 5
    assert list(valid_vec) == [0, 1, 2, 3, 4]
    
    # Invalid operations
    with pytest.raises(TypeError):
        StrictVector([1, 2, 3])  # Raw integers
    
    with pytest.raises(TypeError):
        StrictVector([Uint[16](1), Uint[8](2)])  # Mixed types
    
    with pytest.raises(TypeError):
        valid_vec.append(42)  # Wrong append type


def test_nested_containers():
    """Test nested container structures."""
    # Matrix-like structure: Vector of Vectors
    MatrixRow = TypedVector[Uint[8]]
    Matrix = TypedVector[MatrixRow]
    
    # Create a 3x3 matrix
    matrix = Matrix([
        MatrixRow([Uint[8](1), Uint[8](2), Uint[8](3)]),
        MatrixRow([Uint[8](4), Uint[8](5), Uint[8](6)]),
        MatrixRow([Uint[8](7), Uint[8](8), Uint[8](9)])
    ])
    
    assert len(matrix) == 3
    assert len(matrix[0]) == 3
    assert matrix[1][1] == 5
    
    # Access and modify elements
    assert matrix[1][1] == 5
    matrix[1][1] = Uint[8](99)
    assert matrix[1][1] == 99
    
    # Dictionary of vectors
    GroupData = Dictionary[String, TypedVector[Uint[32]]]
    groups = GroupData({
        String("admins"): TypedVector[Uint[32]]([Uint[32](1), Uint[32](2)]),
        String("users"): TypedVector[Uint[32]]([Uint[32](10), Uint[32](11), Uint[32](12)]),
        String("guests"): TypedVector[Uint[32]]([Uint[32](100)])
    })
    
    assert len(groups) == 3
    assert len(groups[String("users")]) == 3
    assert groups[String("guests")][0] == 100


def test_container_edge_cases():
    """Test edge cases for container types."""
    # Empty containers
    empty_vector = TypedVector[Uint[32]]([])
    empty_dict = Dictionary[String, Uint[32]]({})
    
    assert len(empty_vector) == 0
    assert len(empty_dict) == 0
    
    # Single element containers
    single_vector = TypedVector[Uint[32]]([Uint[32](42)])
    single_dict = Dictionary[String, Uint[32]]({String("key"): Uint[32](42)})
    
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
    vector = TypedVector[Uint[16]]([Uint[16](10), Uint[16](20), Uint[16](30)])
    values = []
    for item in vector:
        values.append(int(item))
    assert values == [10, 20, 30]
    
    # Dictionary iteration
    dictionary = Dictionary[String, Uint[8]]({
        String("a"): Uint[8](1),
        String("b"): Uint[8](2)
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
        assert isinstance(value, Uint[8])


def test_container_comprehensive():
    """Comprehensive test of container features."""
    # Complex nested structure
    ComplexData = Dictionary[String, TypedVector[Dictionary[String, Uint[32]]]]
    
    data = ComplexData({
        String("users"): TypedVector[Dictionary[String, Uint[32]]]([
            Dictionary[String, Uint[32]]({
                String("id"): Uint[32](1),
                String("age"): Uint[32](25)
            }),
            Dictionary[String, Uint[32]]({
                String("id"): Uint[32](2),
                String("age"): Uint[32](30)
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