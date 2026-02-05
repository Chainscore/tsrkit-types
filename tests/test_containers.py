import pytest
from tsrkit_types.integers import Uint
from tsrkit_types.sequences import Array, Vector, TypedArray, TypedVector, BoundedVector, TypedBoundedVector
from tsrkit_types.dictionary import Dictionary
from tsrkit_types.string import String
from tsrkit_types.bool import Bool


class TestFixedArrays:
    """Test fixed-size array types."""

    @pytest.mark.parametrize("size,elements", [
        (10, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]),
        (5, ['a', 'b', 'c', 'd', 'e']),
        (3, [True, False, True]),
    ])
    def test_array_creation(self, size, elements):
        """Test fixed-size array creation."""
        ArrayType = Array[size]
        arr = ArrayType(elements)

        assert len(arr) == size
        assert list(arr) == elements

    def test_array_fixed_size_constraint(self):
        """Test arrays cannot grow beyond fixed size."""
        Array10 = Array[10]
        numbers = Array10([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

        with pytest.raises((ValueError, AttributeError)):
            numbers.append(11)


class TestTypedArrays:
    """Test typed fixed-size arrays."""

    @pytest.mark.parametrize("array_type,elements,first_value", [
        (TypedArray[Uint[16], 5], [Uint[16](i * 100) for i in range(1, 6)], 100),
        (TypedArray[String, 3], [String("Alice"), String("Bob"), String("Carol")], "Alice"),
        (TypedArray[Bool, 4], [Bool(True), Bool(False), Bool(True), Bool(False)], True),
    ])
    def test_typed_array_creation(self, array_type, elements, first_value):
        """Test typed array creation and access."""
        arr = array_type(elements)

        assert len(arr) == len(elements)

        if isinstance(first_value, str):
            assert str(arr[0]) == first_value
        elif isinstance(first_value, bool):
            assert bool(arr[0]) == first_value
        else:
            assert arr[0] == first_value

    def test_typed_array_validation(self):
        """Test typed array type validation."""
        Uint16Array5 = TypedArray[Uint[16], 5]

        with pytest.raises(TypeError):
            Uint16Array5([100, 200, 150, 300, 250])  # Raw ints

    def test_typed_array_modification(self):
        """Test typed array element modification."""
        Uint16Array5 = TypedArray[Uint[16], 5]
        coords = Uint16Array5([Uint[16](i) for i in range(5)])

        coords[0] = Uint[16](500)
        assert coords[0] == 500


class TestVectors:
    """Test variable-size vectors."""

    @pytest.mark.parametrize("min_size,max_size,elements", [
        (0, 100, [1, 2, 3]),
        (0, 1000, list(range(50))),
        (0, 10, []),
    ])
    def test_vector_creation(self, min_size, max_size, elements):
        """Test vector creation with bounds."""
        VectorType = Vector[min_size, max_size]
        vec = VectorType(elements)

        assert len(vec) == len(elements)
        assert list(vec) == elements

    def test_vector_growth(self):
        """Test vectors can grow dynamically."""
        Vector100 = Vector[0, 100]
        vec = Vector100([1, 2, 3])

        vec.append(4)
        vec.extend([5, 6, 7, 8, 9, 10])

        assert len(vec) == 10
        assert list(vec) == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    def test_vector_max_size_constraint(self):
        """Test vectors respect maximum size."""
        Vector100 = Vector[0, 100]

        with pytest.raises(ValueError):
            Vector100([0] * 150)


class TestTypedVectors:
    """Test typed variable-size vectors."""

    @pytest.mark.parametrize("vector_type,elements,expected_len", [
        (TypedVector[Uint[16]], [Uint[16](i) for i in [1, 2, 3]], 3),
        (TypedVector[String], [String("hello"), String("world")], 2),
        (TypedVector[Bool], [Bool(True), Bool(False), Bool(True)], 3),
    ])
    def test_typed_vector_creation(self, vector_type, elements, expected_len):
        """Test typed vector creation."""
        vec = vector_type(elements)
        assert len(vec) == expected_len

    def test_typed_vector_append(self):
        """Test typed vector append with type checking."""
        Uint16Vector = TypedVector[Uint[16]]
        vec = Uint16Vector([Uint[16](1), Uint[16](2)])

        vec.append(Uint[16](3))
        assert len(vec) == 3

        with pytest.raises(TypeError):
            vec.append(42)  # Raw int

    def test_typed_vector_type_validation(self):
        """Test type validation on assignment."""
        Uint16Vector = TypedVector[Uint[16]]
        vec = Uint16Vector([Uint[16](1), Uint[16](2)])

        with pytest.raises(TypeError):
            vec[0] = 42


class TestBoundedVectors:
    """Test size-constrained vectors."""

    @pytest.mark.parametrize("min_size,max_size,elements,expected_len", [
        (5, 10, [1, 2, 3, 4, 5, 6, 7], 7),
        (3, 7, [Uint[8](i * 10) for i in range(1, 5)], 4),
    ])
    def test_bounded_vector_creation(self, min_size, max_size, elements, expected_len):
        """Test bounded vector creation."""
        if all(isinstance(e, Uint[8]) for e in elements):
            BoundedType = TypedBoundedVector[Uint[8], min_size, max_size]
        else:
            BoundedType = BoundedVector[min_size, max_size]

        vec = BoundedType(elements)
        assert len(vec) == expected_len

    def test_bounded_vector_constraints(self):
        """Test size constraints."""
        BoundedList = BoundedVector[5, 10]

        with pytest.raises(ValueError):
            BoundedList([1, 2])  # Below minimum

        with pytest.raises(ValueError):
            BoundedList([i for i in range(15)])  # Above maximum


class TestSequenceEncoding:
    """Test sequence encoding/decoding."""

    @pytest.mark.parametrize("sequence", [
        TypedArray[Uint[8], 3]([Uint[8](1), Uint[8](2), Uint[8](3)]),
        TypedVector[Uint[16]]([Uint[16](100), Uint[16](200), Uint[16](300)]),
    ])
    def test_sequence_roundtrip(self, sequence):
        """Test encoding/decoding roundtrip."""
        encoded = sequence.encode()
        decoded = type(sequence).decode(encoded)

        assert len(encoded) > 0
        assert len(decoded) == len(sequence)
        assert list(decoded) == list(sequence)


class TestDictionaries:
    """Test dictionary functionality."""

    def test_basic_dictionary(self):
        """Test basic dictionary operations."""
        StringToInt = Dictionary[String, Uint[32]]
        scores = StringToInt({
            String("alice"): Uint[32](95),
            String("bob"): Uint[32](87),
            String("carol"): Uint[32](92)
        })

        assert len(scores) == 3
        assert scores[String("alice")] == 95

        scores[String("dave")] = Uint[32](88)
        assert len(scores) == 4
        assert scores[String("dave")] == 88

    def test_dictionary_types(self):
        """Test dictionary with different key/value types."""
        IntToString = Dictionary[Uint[8], String]
        names = IntToString({
            Uint[8](1): String("First"),
            Uint[8](2): String("Second"),
            Uint[8](3): String("Third")
        })

        assert len(names) == 3
        assert str(names[Uint[8](1)]) == "First"

    def test_complex_dictionary(self):
        """Test dictionaries with complex value types."""
        ConfigDict = Dictionary[String, TypedVector[Uint[16]]]
        config = ConfigDict({
            String("ports"): TypedVector[Uint[16]]([Uint[16](80), Uint[16](443)]),
            String("timeouts"): TypedVector[Uint[16]]([Uint[16](30), Uint[16](60)])
        })

        assert len(config) == 2
        assert len(config[String("ports")]) == 2
        assert config[String("ports")][0] == 80

        config[String("ports")].append(Uint[16](8080))
        assert len(config[String("ports")]) == 3

    def test_dictionary_encoding(self):
        """Test dictionary encoding/decoding."""
        StringToUint8 = Dictionary[String, Uint[8]]
        data = StringToUint8({
            String("a"): Uint[8](1),
            String("b"): Uint[8](2),
            String("c"): Uint[8](3)
        })

        encoded = data.encode()
        decoded = StringToUint8.decode(encoded)

        assert len(encoded) > 0
        assert len(decoded) == len(data)
        assert decoded[String("a")] == 1
        assert decoded[String("b")] == 2
        assert decoded[String("c")] == 3

    def test_dictionary_json(self):
        """Test dictionary JSON serialization."""
        MixedDict = Dictionary[String, Uint[32]]
        data = MixedDict({
            String("count"): Uint[32](42),
            String("limit"): Uint[32](100)
        })

        json_data = data.to_json()
        restored = MixedDict.from_json(json_data)

        assert len(restored) == len(data)
        assert restored[String("count")] == 42
        assert restored[String("limit")] == 100


class TestContainerValidation:
    """Test type validation in containers."""

    def test_typed_vector_strict_validation(self):
        """Test strict type validation."""
        StrictVector = TypedVector[Uint[16]]

        valid_vec = StrictVector([Uint[16](1), Uint[16](2), Uint[16](3)])
        valid_vec.append(Uint[16](4))
        valid_vec.insert(0, Uint[16](0))

        assert len(valid_vec) == 5
        assert list(valid_vec) == [0, 1, 2, 3, 4]

    @pytest.mark.parametrize("invalid_input", [
        [1, 2, 3],  # Raw integers
        [Uint[16](1), Uint[8](2)],  # Mixed types
    ])
    def test_typed_vector_rejects_invalid(self, invalid_input):
        """Test typed vector rejects invalid inputs."""
        StrictVector = TypedVector[Uint[16]]

        with pytest.raises(TypeError):
            StrictVector(invalid_input)


class TestNestedContainers:
    """Test nested container structures."""

    def test_vector_of_vectors(self):
        """Test matrix-like nested vectors."""
        MatrixRow = TypedVector[Uint[8]]
        Matrix = TypedVector[MatrixRow]

        matrix = Matrix([
            MatrixRow([Uint[8](1), Uint[8](2), Uint[8](3)]),
            MatrixRow([Uint[8](4), Uint[8](5), Uint[8](6)]),
            MatrixRow([Uint[8](7), Uint[8](8), Uint[8](9)])
        ])

        assert len(matrix) == 3
        assert len(matrix[0]) == 3
        assert matrix[1][1] == 5

        matrix[1][1] = Uint[8](99)
        assert matrix[1][1] == 99

    def test_dictionary_of_vectors(self):
        """Test dictionary containing vectors."""
        GroupData = Dictionary[String, TypedVector[Uint[32]]]
        groups = GroupData({
            String("admins"): TypedVector[Uint[32]]([Uint[32](1), Uint[32](2)]),
            String("users"): TypedVector[Uint[32]]([Uint[32](10), Uint[32](11)])
        })

        assert len(groups) == 2
        assert len(groups[String("admins")]) == 2
        assert groups[String("admins")][0] == 1


class TestContainerEdgeCases:
    """Test edge cases."""

    def test_empty_containers(self):
        """Test empty container creation."""
        empty_vec = TypedVector[Uint[8]]([])
        empty_dict = Dictionary[String, Uint[8]]({})

        assert len(empty_vec) == 0
        assert len(empty_dict) == 0

    def test_single_element_containers(self):
        """Test containers with single element."""
        single_vec = TypedVector[Uint[8]]([Uint[8](42)])
        single_dict = Dictionary[String, Uint[8]]({String("key"): Uint[8](1)})

        assert len(single_vec) == 1
        assert len(single_dict) == 1
        assert single_vec[0] == 42
        assert single_dict[String("key")] == 1


class TestContainerIteration:
    """Test container iteration."""

    def test_vector_iteration(self):
        """Test iterating over vectors."""
        vec = TypedVector[Uint[8]]([Uint[8](i) for i in range(5)])

        result = [int(x) for x in vec]
        assert result == [0, 1, 2, 3, 4]

    def test_dictionary_iteration(self):
        """Test iterating over dictionaries."""
        d = Dictionary[String, Uint[8]]({
            String("a"): Uint[8](1),
            String("b"): Uint[8](2)
        })

        keys = list(d.keys())
        values = list(d.values())
        items = list(d.items())

        assert len(keys) == 2
        assert len(values) == 2
        assert len(items) == 2
