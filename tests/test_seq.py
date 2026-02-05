import pytest
from tsrkit_types.integers import Uint
from tsrkit_types.sequences import Vector, TypedArray, TypedVector, TypedBoundedVector


class TestTypedVector:
    """Test TypedVector functionality."""

    def test_typed_vector_init(self):
        """Test TypedVector initialization with correct types."""
        class MyList(TypedVector[Uint[32]]): ...

        a = MyList([Uint[32](10)])
        assert a == [Uint[32](10)]

    @pytest.mark.parametrize("invalid_input", [
        [10],  # Plain int instead of Uint[32]
        [Uint[8](100)],  # Wrong size Uint
        [Uint[16](100)],  # Wrong size Uint
    ])
    def test_typed_vector_type_validation(self, invalid_input):
        """Test TypedVector rejects wrong types."""
        class MyList(TypedVector[Uint[32]]): ...

        with pytest.raises(TypeError):
            MyList(invalid_input)

    def test_typed_vector_append_validation(self):
        """Test append validates types."""
        class MyList(TypedVector[Uint[32]]): ...
        a = MyList([Uint[32](10)])

        with pytest.raises(TypeError):
            a.append(100)

    def test_untyped_vector_allows_mixed(self):
        """Test untyped Vector allows mixed types."""
        b = Vector([100])
        b.append(Uint[32](100))
        # Should work - Vector is untyped

    @pytest.mark.parametrize("vector_type,element_type", [
        (TypedVector[Uint], Uint),
        (TypedVector[Uint[32]], Uint[32]),
        (TypedVector[bytes], bytes),
    ])
    def test_typed_vector_variants(self, vector_type, element_type):
        """Test different TypedVector type variants."""
        if element_type == Uint:
            vec = vector_type([])
            # Uint without size should reject sized Uints
            with pytest.raises(TypeError):
                vec.append(Uint[8](100))
            with pytest.raises(TypeError):
                vec.append(Uint[32](100))
        elif element_type == Uint[32]:
            vec = vector_type([Uint[32](10)] * 10)
            assert len(vec) == 10
            with pytest.raises(TypeError):
                vec.append(100)
        elif element_type == bytes:
            vec = vector_type([bytes(1)] * 10)
            assert len(vec) == 10


class TestTypedArray:
    """Test TypedArray (fixed-length) functionality."""

    @pytest.mark.parametrize("size", [10, 20])
    def test_typed_array_init(self, size):
        """Test TypedArray initialization."""
        arr = TypedArray[Uint[32], size]([Uint[32](1000)] * size)
        assert len(arr) == size
        assert arr._min_length == size

    def test_typed_array_subclass(self):
        """Test TypedArray with subclassing."""
        class Arr10(TypedArray[Uint[32], 10]): ...

        a = Arr10([Uint[32](1000)] * 10)
        assert len(a) == 10

        with pytest.raises(ValueError):
            Arr10([])

    @pytest.mark.parametrize("invalid_input", [
        [],
        [Uint[32](1)] * 5,  # Wrong length
    ])
    def test_typed_array_length_validation(self, invalid_input):
        """Test TypedArray validates length."""
        with pytest.raises(ValueError):
            TypedArray[Uint[32], 10](invalid_input)

    def test_typed_array_type_validation(self):
        """Test TypedArray validates element types."""
        with pytest.raises(TypeError):
            TypedArray[Uint[32], 10]([10] * 10)


class TestSequenceEncoding:
    """Test encoding/decoding for sequences."""

    @pytest.mark.parametrize("size,expected_bytes", [
        (10, 4 * 10),
        (20, 4 * 20),
    ])
    def test_typed_array_encoding(self, size, expected_bytes):
        """Test TypedArray encoding."""
        a = TypedArray[Uint[32], size]([Uint[32](1)] * size)

        assert a.encode_size() == expected_bytes
        assert len(a.encode()) == expected_bytes


class TestTypedBoundedVector:
    """Test TypedBoundedVector functionality."""

    def test_bounded_vector_repr(self):
        """Test TypedBoundedVector has correct repr."""
        vec = TypedBoundedVector[Uint[32], 0, 10]([])
        assert vec.__class__.__name__ == "TypedBoundedVector[U32,max=10]"


class TestJAMCodecSequenceEncoding:
    """JAM codec sequence: E([i₀, i₁, ...]) ≡ E(i₀) ∥ E(i₁) ∥ ... (concatenation)."""

    def test_empty_sequence(self):
        """Empty sequence encodes correctly."""
        vec = Vector[Uint[8]]([])
        encoded = vec.encode()
        decoded = Vector[Uint[8]].decode(encoded)
        assert len(decoded) == 0

    @pytest.mark.parametrize("values", [
        [0], [0, 1], [0, 1, 2, 3, 4],
        [255] * 10, list(range(100)),
    ])
    def test_sequence_concatenation(self, values):
        """Sequence elements concatenate in order."""
        vec = Vector[Uint[8]]([Uint[8](v) for v in values])
        decoded = Vector[Uint[8]].decode(vec.encode())
        assert len(decoded) == len(values)
        for i, v in enumerate(values):
            assert decoded[i] == v

    @pytest.mark.parametrize("size", [1, 10, 100, 1000])
    def test_large_sequences(self, size):
        """Large sequences maintain codec compliance."""
        vec = Vector[Uint[16]]([Uint[16](i % 65536) for i in range(size)])
        decoded = Vector[Uint[16]].decode(vec.encode())
        assert len(decoded) == size
        for i in range(size):
            assert decoded[i] == i % 65536

    def test_sequence_of_sequences(self):
        """Nested sequences encode correctly."""
        VecOfVec = Vector[Vector[Uint[8]]]
        inner1 = Vector[Uint[8]]([Uint[8](1), Uint[8](2)])
        inner2 = Vector[Uint[8]]([Uint[8](3), Uint[8](4)])
        outer = VecOfVec([inner1, inner2])

        decoded = VecOfVec.decode(outer.encode())
        assert len(decoded) == 2
        assert list(decoded[0]) == [1, 2]
        assert list(decoded[1]) == [3, 4]
