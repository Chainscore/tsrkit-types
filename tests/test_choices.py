import pytest
from tsrkit_types.choice import Choice
from tsrkit_types.null import Null
from tsrkit_types.option import Option
from tsrkit_types.integers import U8, U16, U32
from tsrkit_types.string import String
from tsrkit_types.bool import Bool


class TestChoiceBasics:
    """Test basic Choice functionality."""

    def test_anonymous_choice(self):
        """Test basic Choice with anonymous types."""
        IntOrString = Choice[U8, String]

        choice1 = IntOrString(U8(42))
        choice2 = IntOrString(String("hello"))

        assert choice1.unwrap() == 42
        assert isinstance(choice1.unwrap(), U8)
        assert str(choice2.unwrap()) == "hello"
        assert isinstance(choice2.unwrap(), String)

        # Switch values
        choice1.set(String("switched"))
        assert str(choice1.unwrap()) == "switched"

        choice1.set(U8(100))
        assert choice1.unwrap() == 100

    def test_named_choice(self):
        """Test named Choice with custom keys."""
        class Result(Choice):
            success: String
            error: U32

        success_result = Result(String("Success"))
        error_result = Result(U32(404), key="error")

        assert str(success_result.unwrap()) == "Success"
        assert error_result.unwrap() == 404
        assert success_result._choice_key == "success"
        assert error_result._choice_key == "error"

    @pytest.mark.parametrize("value,expected,value_type", [
        (U8(255), 255, U8),
        (U16(65535), 65535, U16),
        (U32(4294967295), 4294967295, U32),
        (String("text data"), "text data", String),
        (Bool(True), True, Bool),
    ], ids=["u8", "u16", "u32", "string", "bool"])
    def test_complex_choice_types(self, value, expected, value_type):
        """Test Choice with multiple types."""
        DataValue = Choice[U8, U16, U32, String, Bool]
        choice = DataValue(value)
        inner = choice.unwrap()

        if isinstance(inner, String):
            assert str(inner) == expected
        elif isinstance(inner, Bool):
            assert bool(inner) == expected
        else:
            assert inner == expected
        assert isinstance(inner, value_type)


class TestChoiceEncoding:
    """Test Choice encoding/decoding."""

    @pytest.mark.parametrize("value", [
        U16(12345),
        String("encoded string"),
    ], ids=["u16", "string"])
    def test_encoding_roundtrip(self, value):
        """Test encoding/decoding for different types."""
        NumberOrText = Choice[U16, String]
        original = NumberOrText(value)
        encoded = original.encode()
        decoded = NumberOrText.decode(encoded)

        assert len(encoded) > 0

        orig_val = original.unwrap()
        dec_val = decoded.unwrap()

        if isinstance(orig_val, String):
            assert str(orig_val) == str(dec_val)
        else:
            assert orig_val == dec_val
        assert type(orig_val) == type(dec_val)


class TestChoiceJSON:
    """Test Choice JSON serialization."""

    @pytest.mark.parametrize("value,key", [
        (Bool(True), "active"),
        (String("System offline"), "message"),
        (U32(500), "code"),
    ], ids=["bool-active", "string-message", "u32-code"])
    def test_json_serialization(self, value, key):
        """Test JSON serialization for named choices."""
        class Status(Choice):
            active: Bool
            message: String
            code: U32

        status = Status(value, key=key) if key != "active" else Status(value)
        json_data = status.to_json()
        restored = Status.from_json(json_data)

        assert status._choice_key == restored._choice_key

        orig_val = status.unwrap()
        rest_val = restored.unwrap()

        if isinstance(orig_val, String):
            assert str(orig_val) == str(rest_val)
        elif isinstance(orig_val, Bool):
            assert bool(orig_val) == bool(rest_val)
        else:
            assert orig_val == rest_val


class TestOptionBasics:
    """Test Option type functionality."""

    def test_basic_option(self):
        """Test basic Option usage."""
        maybe_number = Option[U32](U32(100))
        empty_option = Option[U32]()

        assert bool(maybe_number) is True
        assert bool(empty_option) is False

        if maybe_number:
            assert maybe_number.unwrap() == 100

        if empty_option:
            pytest.fail("Empty option should be falsy")

    def test_option_operations(self):
        """Test Option operations and patterns."""
        name_option = Option[String](String("Alice"))
        age_option = Option[U8]()

        def get_display_name(opt):
            return String(f"User: {opt.unwrap()}") if opt else String("Unknown User")

        def get_display_age(opt):
            return String(f"Age: {int(opt.unwrap())}") if opt else String("Age: Not specified")

        assert str(get_display_name(name_option)) == "User: Alice"
        assert str(get_display_age(age_option)) == "Age: Not specified"

        # Change values
        age_option.set(U8(25))
        assert str(get_display_age(age_option)) == "Age: 25"

        name_option.set(Null)
        assert str(get_display_name(name_option)) == "Unknown User"

    @pytest.mark.parametrize("option_val,has_value", [
        (Option[String](String("optional text")), True),
        (Option[String](), False),
        (Option[U32](U32(42)), True),
        (Option[U32](), False),
    ])
    def test_option_encoding(self, option_val, has_value):
        """Test Option encoding efficiency."""
        encoded = option_val.encode()
        decoded = type(option_val).decode(encoded)

        assert len(encoded) > 0
        assert bool(option_val) == bool(decoded) == has_value

        if has_value:
            orig_val = option_val.unwrap()
            dec_val = decoded.unwrap()

            if isinstance(orig_val, String):
                assert str(orig_val) == str(dec_val)
            else:
                assert orig_val == dec_val


class TestNestedChoices:
    """Test nested Choice and Option types."""

    @pytest.mark.parametrize("opt_val,should_have_value", [
        ("success", True),
        ("error", True),
        ("empty", False),
    ])
    def test_nested_option_choice(self, opt_val, should_have_value):
        """Test Option containing Choice."""
        StrIntChoice = Choice[String, U32]
        OptionalResult = Option[StrIntChoice]

        if opt_val == "success":
            opt = OptionalResult(StrIntChoice(String("Success!")))
        elif opt_val == "error":
            opt = OptionalResult(StrIntChoice(U32(404)))
        else:
            opt = OptionalResult()

        assert bool(opt) == should_have_value

        if opt:
            inner_choice = opt.unwrap()
            inner_value = inner_choice.unwrap()
            assert inner_value is not None

        # Encoding roundtrip
        encoded = opt.encode()
        decoded = OptionalResult.decode(encoded)
        assert bool(opt) == bool(decoded)


class TestChoiceValidation:
    """Test type safety and validation."""

    def test_choice_type_safety(self):
        """Test type safety in Choice."""
        StrictChoice = Choice[U8, String]

        # Valid constructions
        valid1 = StrictChoice(U8(42))
        assert valid1.unwrap() == 42

        valid2 = StrictChoice(String("hello"))
        assert str(valid2.unwrap()) == "hello"

        # Invalid constructions
        with pytest.raises((TypeError, ValueError)):
            StrictChoice(42)  # Raw int

        with pytest.raises((TypeError, ValueError)):
            StrictChoice("hello")  # Raw string

        with pytest.raises((TypeError, ValueError)):
            StrictChoice(U16(100))  # Wrong type

    @pytest.mark.parametrize("value,key", [
        (U8(42), "first"),
        (U16(1000), "second"),
        (String("test"), "third"),
    ], ids=["u8-first", "u16-second", "string-third"])
    def test_choice_key_management(self, value, key):
        """Test choice key selection."""
        class MultiChoice(Choice):
            first: U8
            second: U16
            third: String

        choice = MultiChoice(value, key=key) if key != "first" else MultiChoice(value)
        assert choice._choice_key == key

    def test_invalid_key(self):
        """Test invalid key raises error."""
        class MultiChoice(Choice):
            first: U8
            second: U16

        with pytest.raises((KeyError, ValueError)):
            MultiChoice(U8(42), key="invalid")


class TestOptionNoneHandling:
    """Test Option None and null handling."""

    def test_option_none_operations(self):
        """Test Option with None values."""
        empty = Option[U32]()
        assert not empty

        with_value = Option[U32](U32(42))
        assert with_value
        assert with_value.unwrap() == 42

        # Clear to None
        with_value.set(None)
        assert not with_value

        # Set to value
        with_value.set(U32(100))
        assert with_value
        assert with_value.unwrap() == 100


class TestChoiceOptionComprehensive:
    """Comprehensive tests of Choice and Option."""

    def test_complex_nested_structure(self):
        """Test complex nested Choice/Option structure."""
        OptionalString = Option[String]
        BoolChoice = Choice[Bool]

        class ComplexChoice(Choice):
            simple: U32
            optional: OptionalString
            nested: BoolChoice

        # Simple case
        simple = ComplexChoice(U32(42))
        assert simple._choice_key == "simple"
        assert simple.unwrap() == 42

        # Optional case
        optional = ComplexChoice(OptionalString(String("test")), key="optional")
        assert optional._choice_key == "optional"
        assert str(optional.unwrap().unwrap()) == "test"

        # Nested case
        nested = ComplexChoice(BoolChoice(Bool(True)), key="nested")
        assert nested._choice_key == "nested"
        assert bool(nested.unwrap().unwrap()) is True

        # Encoding roundtrips
        for case in [simple, optional, nested]:
            encoded = case.encode()
            decoded = ComplexChoice.decode(encoded)
            assert case._choice_key == decoded._choice_key


class TestJAMCodecDiscriminators:
    """JAM codec discriminator compliance: Option ⟪x⟫ ≡ 0 when x = ∅, else (1, x)."""

    def test_option_none_discriminator_zero(self):
        """Option(None) must encode discriminator byte as 0."""
        opt = Option[U32]()
        encoded = opt.encode()
        assert encoded[0] == 0

    def test_option_some_discriminator_one(self):
        """Option(Some(x)) must encode discriminator byte as 1."""
        opt = Option[U32](U32(42))
        encoded = opt.encode()
        assert encoded[0] == 1

    def test_option_zero_vs_none(self):
        """Option(Some(0)) must differ from Option(None)."""
        opt_zero = Option[U8](U8(0))
        opt_none = Option[U8]()

        enc_zero = opt_zero.encode()
        enc_none = opt_none.encode()

        assert enc_zero != enc_none
        assert enc_zero[0] == 1  # Some
        assert enc_none[0] == 0  # None

        # Roundtrip verifies distinction
        assert Option[U8].decode(enc_zero).unwrap() == 0
        assert not Option[U8].decode(enc_none)

    @pytest.mark.parametrize("IntType,value", [
        (U8, 0), (U8, 255),
        (U16, 0), (U16, 65535),
        (U32, 0), (U32, 4294967295),
    ])
    def test_option_boundary_values(self, IntType, value):
        """Option with min/max values encodes correctly."""
        opt = Option[IntType](IntType(value))
        decoded = Option[IntType].decode(opt.encode())
        # Fixed: Option(Some(0)) is now correctly truthy
        assert decoded and decoded.unwrap() == value

    def test_choice_discriminators_unique(self):
        """Each Choice variant has unique discriminator."""
        IntOrStr = Choice[U8, String]

        c1 = IntOrStr(U8(42))
        c2 = IntOrStr(String("test"))

        enc1 = c1.encode()
        enc2 = c2.encode()

        # Encodings must differ (different discriminators)
        assert enc1 != enc2

        # Roundtrip maintains distinction
        assert isinstance(IntOrStr.decode(enc1).unwrap(), U8)
        assert isinstance(IntOrStr.decode(enc2).unwrap(), String)
