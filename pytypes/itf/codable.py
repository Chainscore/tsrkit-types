from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Tuple, Union

T = TypeVar("T")


class Codable(ABC, Generic[T]):
    """Abstract base class defining the interface for encoding and decoding data."""

    @abstractmethod
    def encode_size(self) -> int:
        """
        Calculate the number of bytes needed to encode the value.

        Returns:
            The number of bytes needed to encode the value.
        """
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    def encode_into(self, buffer: bytearray, offset: int = 0) -> int:
        """
        Encode the value into the provided buffer at the specified offset.
        
        Args:
            buffer: The buffer to encode the value into.
            offset: The offset at which to start encoding the value.

        Returns:
            The number of bytes written to the buffer.
        """
        raise NotImplementedError("Subclasses must implement this method")

    def encode(self) -> bytes:
        """
        Encode the value into a new bytes object.

        Returns:
            The encoded value as a bytes object.
        """
        size = self.encode_size()
        buffer = bytearray(size)
        written = self.encode_into(buffer)
        return bytes(buffer[:written])

    @classmethod
    def decode_from(cls, buffer: Union[bytes, bytearray, memoryview], offset: int = 0) -> Tuple[T, int]:
        """
        Decode a value from the provided buffer starting at the specified offset.

        Args:
            buffer: The buffer to decode the value from.
            offset: The offset at which to start decoding the value.

        Returns:
            A tuple containing the decoded value and the number of bytes read from the buffer.
        """
        raise NotImplementedError("Subclasses must implement this method")

    @classmethod
    def decode(cls, buffer: Union[bytes, bytearray, memoryview], offset: int = 0) -> T:
        """
        Decode a value from the provided buffer starting at the specified offset.

        Args:
            buffer: The buffer to decode the value from.
            offset: The offset at which to start decoding the value.
        """
        value, bytes_read = cls.decode_from(buffer, offset)
        return value
    
    def _check_buffer_size(self, buffer: bytearray, size: int, offset: int) -> None:
        """
        Check if the buffer has enough space to encode the value.

        Args:
            buffer: The buffer to check the size of.
            size: The size of the value to encode.
            offset: The offset at which to start encoding the value.
        """
        if len(buffer) - offset < size:
            raise ValueError("Buffer too small to encode value")