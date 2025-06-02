from tsrkit_types.string import String


def test_basic_strings():
    """Test basic string creation and usage."""
    # Create strings
    greeting = String("Hello, World!")
    name = String("Alice")
    empty = String("")
    
    assert len(greeting) == 13
    assert len(name) == 5
    assert len(empty) == 0
    assert str(greeting) == "Hello, World!"
    assert str(name) == "Alice"
    assert str(empty) == ""
    
    # String operations (inherits from str)
    combined = String(str(greeting) + " My name is " + str(name))
    assert "Hello, World! My name is Alice" in str(combined)
    
    # String methods work as expected
    upper_name = String(str(name).upper())
    assert str(upper_name) == "ALICE"


def test_unicode_support():
    """Test Unicode and emoji support."""
    # Unicode strings with various characters
    unicode_strings = [
        String("🚀 Rocket Launch! 🔥"),
        String("Café naïve résumé"),  # Accented characters
        String("こんにちは世界"),        # Japanese
        String("Привет мир"),          # Russian Cyrillic
        String("مرحبا بالعالم"),        # Arabic
        String("𝕳𝖊𝖑𝖑𝖔 𝖂𝖔𝖗𝖑𝖉"),     # Mathematical alphanumeric symbols
    ]
    
    for text in unicode_strings:
        utf8_bytes = str(text).encode('utf-8')
        assert len(utf8_bytes) > 0
        assert len(text) > 0
        
        # Test encoding/decoding
        encoded = text.encode()
        decoded = String.decode(encoded)
        assert str(decoded) == str(text)


def test_encoding_format():
    """Test the encoding format with length prefix."""
    test_strings = [
        String("A"),                    # Single character
        String("Hello"),                # Short string
        String("The quick brown fox"),  # Medium string
        String("🌟✨💫"),              # Unicode emojis
    ]
    
    for text in test_strings:
        encoded = text.encode()
        decoded = String.decode(encoded)
        
        # Verify round-trip
        assert str(text) == str(decoded)
        assert len(encoded) > len(str(text).encode('utf-8'))  # Should include length prefix


def test_encoding_efficiency():
    """Test encoding size calculation and efficiency."""
    strings = [
        String(""),                     # Empty string
        String("Hi"),                   # 2 ASCII chars
        String("Hello"),                # 5 ASCII chars  
        String("🚀"),                   # 1 emoji (4 UTF-8 bytes)
        String("🚀🔥💫"),              # 3 emojis (12 UTF-8 bytes)
        String("A" * 100),              # 100 ASCII chars
        String("🌟" * 50),              # 50 emojis (200 UTF-8 bytes)
    ]
    
    for text in strings:
        utf8_len = len(str(text).encode('utf-8'))
        encoded_size = text.encode_size()
        overhead = encoded_size - utf8_len
        
        assert encoded_size >= utf8_len  # Must include at least the UTF-8 bytes
        assert overhead >= 0  # Length prefix adds some overhead
        
        # Test actual encoding
        encoded = text.encode()
        assert len(encoded) == encoded_size


def test_json_serialization():
    """Test JSON serialization of strings."""
    test_strings = [
        String("Simple text"),
        String("Text with \"quotes\" and 'apostrophes'"),
        String("Text with\nnewlines\tand\ttabs"),
        String("🎉 Unicode party! 🎊"),
        String(""),  # Empty string
    ]
    
    for text in test_strings:
        json_data = text.to_json()
        restored = String.from_json(json_data)
        
        assert str(text) == str(restored)
        assert isinstance(restored, String)


def test_string_operations():
    """Test various string operations and compatibility."""
    text = String("Hello, World!")
    
    # Standard string operations
    assert len(text) == 13
    assert text.upper() == "HELLO, WORLD!"
    assert text.lower() == "hello, world!"
    assert text[0:5] == "Hello"
    assert text.split(',') == ["Hello", " World!"]
    assert text.replace('World', 'Python') == "Hello, Python!"
    assert text.startswith('Hello')
    assert text.endswith('!')
    
    # Type checking
    assert isinstance(text, str)
    assert isinstance(text, String)


def test_comparison_with_builtin():
    """Test String type with built-in str for encoding."""
    test_text = "Hello, 世界! 🌍"
    
    # Built-in string
    builtin_str = test_text
    builtin_utf8 = builtin_str.encode('utf-8')
    
    # TSRKit String  
    tsrkit_str = String(test_text)
    tsrkit_encoded = tsrkit_str.encode()
    
    # Verify that TSRKit encoding includes the UTF-8 content
    assert len(tsrkit_encoded) > len(builtin_utf8)  # Should include length prefix
    
    # Verify round-trip
    decoded = String.decode(tsrkit_encoded)
    assert str(decoded) == test_text


def test_string_edge_cases():
    """Test edge cases for string handling."""
    # Empty string
    empty = String("")
    assert len(empty) == 0
    assert str(empty) == ""
    
    encoded_empty = empty.encode()
    decoded_empty = String.decode(encoded_empty)
    assert str(decoded_empty) == ""
    
    # Very long string
    long_text = "A" * 10000
    long_string = String(long_text)
    assert len(long_string) == 10000
    
    encoded_long = long_string.encode()
    decoded_long = String.decode(encoded_long)
    assert str(decoded_long) == long_text
    
    # String with null bytes (if supported)
    null_text = "Hello\x00World"
    null_string = String(null_text)
    encoded_null = null_string.encode()
    decoded_null = String.decode(encoded_null)
    assert str(decoded_null) == null_text


def test_string_immutability():
    """Test that String behaves as an immutable type."""
    original = String("Hello")
    
    # String operations should return new strings, not modify original
    upper = original.upper()
    assert str(original) == "Hello"
    assert upper == "HELLO"
    
    replaced = original.replace("H", "J")
    assert str(original) == "Hello"
    assert replaced == "Jello"


def test_string_comparison():
    """Test string comparison operations."""
    str1 = String("Hello")
    str2 = String("Hello")
    str3 = String("World")
    
    assert str1 == str2
    assert str1 != str3
    assert str1 == "Hello"  # Should work with regular strings
    assert str1 != "World"
    
    # Lexicographic comparison
    assert str1 < str3  # "Hello" < "World"
    assert str3 > str1


def test_string_encoding_round_trip():
    """Comprehensive round-trip testing for various string types."""
    test_cases = [
        "",
        "A",
        "Hello, World!",
        "🚀🔥💫⭐️🌟",
        "Mixed ASCII and 中文 text",
        "Special chars: !@#$%^&*()[]{}|\\:;\"'<>,.?/",
        "Line\nBreaks\nAnd\tTabs",
        "Very " + "long " * 1000 + "string",
    ]
    
    for test_text in test_cases:
        original = String(test_text)
        encoded = original.encode()
        decoded = String.decode(encoded)
        
        assert str(original) == str(decoded)
        assert len(original) == len(decoded)
        assert original == decoded 