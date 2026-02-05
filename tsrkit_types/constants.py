"""Security limits for codec operations to prevent DoS attacks."""

# Maximum lengths for variable-size types
# These prevent unbounded memory allocation from malicious/malformed data

MAX_SEQUENCE_LENGTH = 10_000_000      # 10M items max in sequences
MAX_DICTIONARY_SIZE = 1_000_000       # 1M key-value pairs max
MAX_BYTEARRAY_SIZE = 100_000_000      # 100 MB max for ByteArray
MAX_STRING_BYTES = 10_000_000         # 10 MB UTF-8 bytes max
MAX_BITS_LENGTH = 80_000_000          # 10 MB of bits max (80M bits)
MAX_NESTING_DEPTH = 100               # Max nesting depth for structures
