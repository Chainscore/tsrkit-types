import pytest
from tsrkit_types.string import String


class TestStringBasics:
    """Test basic String creation and operations."""

    @pytest.mark.parametrize("text,expected_len", [
        ("Hello, World!", 13),
        ("Alice", 5),
        ("", 0),
        ("A", 1),
    ])
    def test_creation_and_length(self, text, expected_len):
        """Test String creation and length."""
        s = String(text)
        assert len(s) == expected_len
        assert str(s) == text

    def test_string_operations(self):
        """Test various string operations."""
        name = String("Alice")

        # String methods work as expected
        assert String(str(name).upper()) == "ALICE"
        assert String(str(name).lower()) == "alice"

        # Type checks
        assert isinstance(name, str)
        assert isinstance(name, String)


class TestStringUnicode:
    """Test Unicode and emoji support."""

    @pytest.mark.parametrize("text", [
        "🚀 Rocket Launch! 🔥",
        "Café naïve résumé",
        "こんにちは世界",
        "Привет мир",
        "مرحبا بالعالم",
        "𝕳𝖊𝖑𝖑𝖔 𝖂𝖔𝖗𝖑𝖉",
    ])
    def test_unicode_support(self, text):
        """Test Unicode and emoji support."""
        s = String(text)
        utf8_bytes = str(s).encode('utf-8')

        assert len(utf8_bytes) > 0
        assert len(s) > 0

        # Roundtrip
        encoded = s.encode()
        decoded = String.decode(encoded)
        assert str(decoded) == text


class TestStringEncoding:
    """Test encoding and decoding."""

    @pytest.mark.parametrize("text", [
        "A",
        "Hello",
        "The quick brown fox",
        "🌟✨💫",
        "",
        "Hi",
        "🚀",
        "🚀🔥💫",
        "A" * 100,
        "🌟" * 50,
    ])
    def test_encode_decode_roundtrip(self, text):
        """Test encoding/decoding roundtrip."""
        original = String(text)
        encoded = original.encode()
        decoded = String.decode(encoded)

        assert str(original) == str(decoded)
        assert len(encoded) >= len(text.encode('utf-8'))  # Includes length prefix

    def test_encode_size(self):
        """Test encode_size calculation."""
        strings = [
            String(""),
            String("Hello"),
            String("🚀🔥💫"),
        ]

        for s in strings:
            encoded_size = s.encode_size()
            encoded = s.encode()
            assert len(encoded) == encoded_size


class TestStringJSON:
    """Test JSON serialization."""

    @pytest.mark.parametrize("text", [
        "Simple text",
        "Text with \"quotes\" and 'apostrophes'",
        "Text with\nnewlines\tand\ttabs",
        "🎉 Unicode party! 🎊",
        "",
    ])
    def test_json_roundtrip(self, text):
        """Test JSON serialization roundtrip."""
        original = String(text)
        json_data = original.to_json()
        restored = String.from_json(json_data)

        assert str(original) == str(restored)
        assert isinstance(restored, String)


class TestStringComparison:
    """Test string comparisons."""

    @pytest.mark.parametrize("str1,str2,should_equal,should_lt", [
        ("Hello", "Hello", True, False),
        ("Hello", "World", False, True),
        ("World", "Hello", False, False),
    ])
    def test_comparison(self, str1, str2, should_equal, should_lt):
        """Test string comparison operations."""
        s1 = String(str1)
        s2 = String(str2)

        assert (s1 == s2) == should_equal
        assert (s1 == str1) == True  # Works with regular strings
        assert (s1 < s2) == should_lt

        if should_lt:
            assert s2 > s1


class TestStringEdgeCases:
    """Test edge cases."""

    @pytest.mark.parametrize("text", [
        "",
        "Very " + "long " * 1000 + "string",
        "Hello\x00World",  # Null bytes
    ])
    def test_edge_cases(self, text):
        """Test edge cases for string handling."""
        s = String(text)
        assert str(s) == text

        # Roundtrip
        encoded = s.encode()
        decoded = String.decode(encoded)
        assert str(decoded) == text

    def test_immutability(self):
        """Test String immutability."""
        original = String("Hello")

        # Operations return new strings
        upper = original.upper()
        assert str(original) == "Hello"
        assert upper == "HELLO"

        replaced = original.replace("H", "J")
        assert str(original) == "Hello"
        assert replaced == "Jello"

    @pytest.mark.parametrize("method,args,expected", [
        ("startswith", ("Hello",), True),
        ("endswith", ("!",), True),
        ("split", (",",), ["Hello", " World!"]),
        ("replace", ("World", "Python"), "Hello, Python!"),
    ])
    def test_string_methods(self, method, args, expected):
        """Test standard string methods."""
        text = String("Hello, World!")
        result = getattr(text, method)(*args)
        assert result == expected


class TestStringComprehensive:
    """Comprehensive roundtrip tests."""

    @pytest.mark.parametrize("text", [
        "",
        "A",
        "Hello, World!",
        "🚀🔥💫⭐️🌟",
        "Mixed ASCII and 中文 text",
        "Special chars: !@#$%^&*()[]{}|\\:;\"'<>,.?/",
        "Line\nBreaks\nAnd\tTabs",
    ])
    def test_comprehensive_roundtrip(self, text):
        """Comprehensive roundtrip testing."""
        original = String(text)
        encoded = original.encode()
        decoded = String.decode(encoded)

        assert str(original) == str(decoded)
        assert len(original) == len(decoded)
        assert original == decoded
