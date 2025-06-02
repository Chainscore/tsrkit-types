import pytest
from tsrkit_types.choice import Choice
from tsrkit_types.null import Null
from tsrkit_types.option import Option
from tsrkit_types.integers import U8, U16, U32
from tsrkit_types.string import String
from tsrkit_types.bool import Bool


def test_basic_choice():
    """Test basic Choice usage with anonymous types."""
    # Create a choice type that can hold either U8 or String
    IntOrString = Choice[U8, String]
    
    # Create instances with different types
    choice1 = IntOrString(U8(42))
    choice2 = IntOrString(String("hello"))
    
    assert choice1.unwrap() == 42
    assert isinstance(choice1.unwrap(), U8)
    assert str(choice2.unwrap()) == "hello"
    assert isinstance(choice2.unwrap(), String)
    
    # Switch the choice value
    choice1.set(String("switched to string"))
    assert str(choice1.unwrap()) == "switched to string"
    
    # Switch back
    choice1.set(U8(100))
    assert choice1.unwrap() == 100


def test_named_choice():
    """Test named Choice with custom keys."""
    # Define a Result type that can represent success or error
    class Result(Choice):
        success: String
        error: U32
    
    # Create success and error instances
    success_result = Result(String("Operation completed successfully"))
    error_result = Result(U32(404), key="error")
    
    assert str(success_result.unwrap()) == "Operation completed successfully"
    assert error_result.unwrap() == 404
    
    # Check which variant is active
    assert success_result._choice_key == "success"
    assert error_result._choice_key == "error"


def test_complex_choice():
    """Test Choice with multiple complex types."""
    # Choice between different data types
    DataValue = Choice[U8, U16, U32, String, Bool]
    
    values = [
        DataValue(U8(255)),
        DataValue(U16(65535)),
        DataValue(U32(4294967295)),
        DataValue(String("text data")),
        DataValue(Bool(True)),
    ]
    
    expected_values = [255, 65535, 4294967295, "text data", True]
    expected_types = [U8, U16, U32, String, Bool]
    
    for value, expected_val, expected_type in zip(values, expected_values, expected_types):
        inner = value.unwrap()
        if isinstance(inner, String):
            assert str(inner) == expected_val
        elif isinstance(inner, Bool):
            assert bool(inner) == expected_val
        else:
            assert inner == expected_val
        assert isinstance(inner, expected_type)


def test_choice_encoding():
    """Test Choice encoding and decoding."""
    # Simple choice type
    NumberOrText = Choice[U16, String]
    
    test_values = [
        NumberOrText(U16(12345)),
        NumberOrText(String("encoded string")),
    ]
    
    for original in test_values:
        encoded = original.encode()
        decoded = NumberOrText.decode(encoded)
        
        assert len(encoded) > 0
        # Compare the unwrapped values
        orig_val = original.unwrap()
        dec_val = decoded.unwrap()
        
        if isinstance(orig_val, String):
            assert str(orig_val) == str(dec_val)
        else:
            assert orig_val == dec_val
        assert type(orig_val) == type(dec_val)


def test_choice_json():
    """Test Choice JSON serialization."""
    # Named choice for better JSON representation
    class Status(Choice):
        active: Bool
        message: String
        code: U32
    
    test_cases = [
        Status(Bool(True)),  # Will use default key "active"
        Status(String("System offline"), key="message"),
        Status(U32(500), key="code"),
    ]
    
    for status in test_cases:
        json_data = status.to_json()
        restored = Status.from_json(json_data)
        
        assert status._choice_key == restored._choice_key
        
        # Compare unwrapped values
        orig_val = status.unwrap()
        rest_val = restored.unwrap()
        
        if isinstance(orig_val, String):
            assert str(orig_val) == str(rest_val)
        elif isinstance(orig_val, Bool):
            assert bool(orig_val) == bool(rest_val)
        else:
            assert orig_val == rest_val


def test_basic_option():
    """Test basic Option usage."""
    # Option is like Choice[T, Null] but more convenient
    maybe_number = Option[U32](U32(100))
    empty_option = Option[U32]()
    
    assert bool(maybe_number) is True
    assert bool(empty_option) is False
    
    # Extract values safely
    if maybe_number:
        assert maybe_number.unwrap() == 100
    
    if empty_option:
        pytest.fail("Empty option should be falsy")


def test_option_operations():
    """Test Option operations and patterns."""
    # Create options with and without values
    name_option = Option[String](String("Alice"))
    age_option = Option[U8]()  # Empty
    
    # Safe value extraction
    def get_display_name(opt: Option[String]) -> String:
        if opt:
            return String(f"User: {opt.unwrap()}")
        else:
            return String("Unknown User")
    
    def get_display_age(opt: Option[U8]) -> String:
        if opt:
            return String(f"Age: {int(opt.unwrap())}")  # Convert to int for display
        else:
            return String("Age: Not specified")
    
    assert str(get_display_name(name_option)) == "User: Alice"
    assert str(get_display_age(age_option)) == "Age: Not specified"
    
    # Change option values
    age_option.set(U8(25))
    assert str(get_display_age(age_option)) == "Age: 25"
    
    # Clear option
    name_option.set(Null)  # or any null-like value
    assert str(get_display_name(name_option)) == "Unknown User"


def test_option_encoding():
    """Test Option encoding (more efficient than general Choice)."""
    values = [
        Option[String](String("optional text")),
        Option[String](),  # Empty option
        Option[U32](U32(42)),
        Option[U32](),  # Empty option
    ]
    
    for opt in values:
        encoded = opt.encode()
        decoded = type(opt).decode(encoded)
        
        has_value = bool(opt)
        
        assert len(encoded) > 0
        assert bool(opt) == bool(decoded)
        
        if has_value:
            orig_val = opt.unwrap()
            dec_val = decoded.unwrap()
            
            if isinstance(orig_val, String):
                assert str(orig_val) == str(dec_val)
            else:
                assert orig_val == dec_val


def test_nested_choices():
    """Test nested Choice and Option types."""
    # Nested: Option containing a Choice
    StrIntChoice = Choice[String, U32]
    OptionalResult = Option[StrIntChoice]
    
    # Create instances
    success_opt = OptionalResult(StrIntChoice(String("Success!")))
    error_opt = OptionalResult(StrIntChoice(U32(404)))
    empty_opt = OptionalResult()
    
    cases = [
        ("Success option", success_opt, True),
        ("Error option", error_opt, True),
        ("Empty option", empty_opt, False),
    ]
    
    for name, opt, should_have_value in cases:
        assert bool(opt) == should_have_value
        
        if opt:
            inner_choice = opt.unwrap()
            inner_value = inner_choice.unwrap()
            assert inner_value is not None
        
        # Test encoding round-trip
        encoded = opt.encode()
        decoded = OptionalResult.decode(encoded)
        assert bool(opt) == bool(decoded)


def test_choice_type_safety():
    """Test type safety and validation in Choice."""
    # Define a strict choice type
    StrictChoice = Choice[U8, String]
    
    # Valid constructions
    valid1 = StrictChoice(U8(42))
    assert valid1.unwrap() == 42
    
    valid2 = StrictChoice(String("hello"))
    assert str(valid2.unwrap()) == "hello"
    
    # Invalid constructions should fail
    with pytest.raises((TypeError, ValueError)):
        StrictChoice(42)  # Raw integer, not U8
    
    with pytest.raises((TypeError, ValueError)):
        StrictChoice("hello")  # Raw string, not String
    
    with pytest.raises((TypeError, ValueError)):
        StrictChoice(U16(100))  # U16 not in choice


def test_choice_key_management():
    """Test choice key selection and management."""
    class MultiChoice(Choice):
        first: U8
        second: U16
        third: String
    
    # Test automatic key assignment
    choice1 = MultiChoice(U8(42))  # Should use "first"
    assert choice1._choice_key == "first"
    
    # Test explicit key assignment
    choice2 = MultiChoice(U16(1000), key="second")
    assert choice2._choice_key == "second"
    
    choice3 = MultiChoice(String("test"), key="third")
    assert choice3._choice_key == "third"
    
    # Test invalid key
    with pytest.raises((KeyError, ValueError)):
        MultiChoice(U8(42), key="invalid")


def test_option_none_handling():
    """Test Option handling of None and null values."""
    # Empty option
    empty = Option[U32]()
    assert not empty
    
    # Option with value
    with_value = Option[U32](U32(42))
    assert with_value
    assert with_value.unwrap() == 42
    
    # Setting to None/null should clear the option
    with_value.set(None)
    assert not with_value
    
    # Setting to a value should populate the option
    with_value.set(U32(100))
    assert with_value
    assert with_value.unwrap() == 100


def test_choice_option_comprehensive():
    """Comprehensive test of Choice and Option features."""
    OptionalString = Option[String]
    BoolChoice = Choice[Bool]
    # Complex nested structure
    class ComplexChoice(Choice):
        simple: U32
        optional: OptionalString
        nested: BoolChoice
    
    # Test various combinations
    simple_case = ComplexChoice(U32(42))
    assert simple_case._choice_key == "simple"
    assert simple_case.unwrap() == 42
    
    optional_case = ComplexChoice(OptionalString(String("test")), key="optional")
    assert optional_case._choice_key == "optional"
    inner_option = optional_case.unwrap()
    assert inner_option
    assert str(inner_option.unwrap()) == "test"
    
    nested_case = ComplexChoice(BoolChoice(Bool(True)), key="nested")
    assert nested_case._choice_key == "nested"
    inner_choice = nested_case.unwrap()
    assert bool(inner_choice.unwrap()) is True
    
    # Test encoding round-trips for all cases
    for case in [simple_case, optional_case, nested_case]:
        encoded = case.encode()
        decoded = ComplexChoice.decode(encoded)
        assert case._choice_key == decoded._choice_key 