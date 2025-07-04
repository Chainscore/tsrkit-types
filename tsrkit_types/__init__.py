"""
TSRKit Types - Performant Python types for binary serialization and JSON encoding.

This module provides a comprehensive set of typed data structures with built-in
serialization capabilities, including integers, strings, containers, and more.
"""

# Core interfaces
from .itf.codable import Codable

# Integer types
from .integers import Uint, U8, U16, U32, U64

# String types
from .string import String

# Boolean types
from .bool import Bool

# Null types
from .null import Null, NullType

# Choice and Option types
from .choice import Choice
from .option import Option

# Container types
from .sequences import (
    Seq, Vector, Array, 
    TypedVector, TypedArray, 
    BoundedVector, TypedBoundedVector
)

# Dictionary types
from .dictionary import Dictionary

# Bytes types
from .bytes import Bytes, Bytes16, Bytes32, Bytes64, Bytes128, Bytes256, Bytes512, Bytes1024
from .bytearray import ByteArray

# Bit types
from .bits import Bits

# Enum types
from .enum import Enum

# Structure decorator
from .struct import structure, struct

# Export all public types
__all__ = [
    # Core interfaces
    "Codable",
    
    # Integer types
    "Uint", "U8", "U16", "U32", "U64",
    
    # String types
    "String",
    
    # Boolean types
    "Bool",
    
    # Null types
    "Null", "NullType",
    
    # Choice and Option types
    "Choice", "Option",
    
    # Container types
    "Seq", "Vector", "Array",
    "TypedVector", "TypedArray", 
    "BoundedVector", "TypedBoundedVector",
    
    # Dictionary types
    "Dictionary",
    
    # Bytes types
    "Bytes", "Bytes16", "Bytes32", "Bytes64", "Bytes128", "Bytes256", "Bytes512", "Bytes1024",
    "ByteArray",
    
    # Bit types
    "Bits",
    
    # Enum types
    "Enum",
    
    # Structure decorator
    "structure", "struct",
]

# Version information
__version__ = "1.0.0"
__author__ = "TSRKit Team"
__license__ = "MIT"
