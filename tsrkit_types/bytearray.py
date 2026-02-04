from tsrkit_types.itf.codable import Codable
from tsrkit_types.bytes_common import BytesMixin

from tsrkit_types import _native


class ByteArray(_native.NativeByteArray, Codable, BytesMixin):
    """Variable Size ByteArray (native-backed)."""

    pass
    
