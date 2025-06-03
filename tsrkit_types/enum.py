from enum import EnumMeta
from typing import Tuple, Type, Union, Any, TypeVar, cast
from tsrkit_types.integers import Uint

T = TypeVar("T", bound="Enum")


class Enum(metaclass=EnumMeta):
    """Decodable Enum type - Extending the built-in Enum type to add encoding and decoding methods

    How to use it:
    >>> class MyEnum(Enum):
    >>>     A = 1
    >>>     B = 2
    >>>     C = 3
    >>>
    >>> value = MyEnum.A
    >>> encoded = value.encode()
    >>> decoded, bytes_read = MyEnum.decode_from(encoded)
    >>> assert decoded == value
    >>> assert bytes_read == 1
    >>>
    >>> assert MyEnum.from_json(1) == MyEnum.A
    >>> assert MyEnum.from_json("A") == MyEnum.A
    """
    
    @property
    def value(self) -> Any:
        return self._value_
    
    @classmethod
    def _missing_(cls, value: Any) -> T:
        raise ValueError(f"Invalid value: {value}")

    # ---------------------------------------------------------------------------- #
    #                                 Serialization                                #
    # ---------------------------------------------------------------------------- #

    def encode_size(self) -> int:
        """Return the size in bytes needed to encode this enum value"""
        return 1

    def encode(self) -> bytes:
        """Encode the value into a new bytes object."""
        size = self.encode_size()
        buffer = bytearray(size)
        written = self.encode_into(buffer)
        return bytes(buffer[:written])

    def encode_into(self, buffer: bytearray, offset: int = 0) -> int:
        """Encode this enum value into the given buffer at the given offset

        Args:
            buffer: The buffer to encode into
            offset: The offset to start encoding at

        Returns:
            The number of bytes written

        Raises:
            ValueError: If the enum has too many variants to encode in a byte
        """
        # Get the index of the enum value in all enums
        # Encode the index as a byte
        all_enums = self.__class__._member_names_
        index = all_enums.index(self._name_)
        if index > 255:
            raise ValueError("Enum index is too large to encode into a single byte")
        return Uint(index).encode_into(buffer, offset)

    @classmethod
    def decode_from(
        cls, buffer: Union[bytes, bytearray, memoryview], offset: int = 0
    ) -> Tuple[T, int]:
        """Decode an enum value from the given buffer at the given offset

        Args:
            buffer: The buffer to decode from
            offset: The offset to start decoding at

        Returns:
            A tuple of (decoded enum value, number of bytes read)

        Raises:
            ValueError: If the encoded index is invalid
        """
        # Decode the byte (index of enum) into an Enum
        # Return the enum value
        index, bytes_read = Uint.decode_from(buffer, offset)
        value = cast(T, cls._member_map_[cls._member_names_[index]])
        return value, bytes_read
    

    # ---------------------------------------------------------------------------- #
    #                                  JSON Serde                                  #
    # ---------------------------------------------------------------------------- #

    @classmethod
    def from_json(cls: Type[T], data: Any) -> T:
        """Convert a JSON value to an enum value

        Args:
            data: The JSON value (either the enum value or name)

        Returns:
            The corresponding enum value

        Raises:
            ValueError: If the value is invalid
        """
        for v in cls.__members__.values():
            if v._value_ == data or v._name_ == data:
                return cast(T, v)
        raise ValueError(f"Invalid value: {data}")

    def to_json(self) -> Any:
        """Convert this enum value to a JSON value

        Returns:
            The enum's value for JSON serialization
        """
        return self._value_

    @classmethod
    def decode(cls, buffer: Union[bytes, bytearray, memoryview], offset: int = 0) -> T:
        """Decode a value from the provided buffer starting at the specified offset."""
        value, bytes_read = cls.decode_from(buffer, offset)
        return value