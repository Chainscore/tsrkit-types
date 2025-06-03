import abc
from typing import TypeVar, Type, ClassVar, Tuple, Generic
from tsrkit_types.integers import Uint
from tsrkit_types.itf.codable import Codable

T = TypeVar("T")

class SeqCheckMeta(abc.ABCMeta):
    """Meta class to check if the instance is an integer with the same byte size"""
    def __instancecheck__(cls, instance):
        # String comparison is used to avoid identity comparison issues - like Uint[8] and Uint[8]
        # TODO - This needs more false positive testing
        _matches_element_type = str(getattr(cls, "_element_type", None)) == str(getattr(instance, "_element_type", None))
        _matches_min_length = getattr(cls, "_min_length", 0) == getattr(instance, "_min_length", 0)
        _matches_max_length = getattr(cls, "_max_length", 2**64) == getattr(instance, "_max_length", 2**64)
        return isinstance(instance, list) and _matches_element_type and _matches_min_length and _matches_max_length


class Seq(list, Codable, Generic[T], metaclass=SeqCheckMeta):
    """
    Sequence Type

    Usage:
        >>> # Create a reusable type
        >>> class Eta(Seq[bytes, 4]): ...
        >>>
        >>> # (or) Disposable
        >>> val_indexes = Seq[int, 1023]([0] * 1028)
        >>>
        >>> # Supports codec [both variable and fixed length] given that the element type must support codec
        >>> Seq[U16, 1023]([0] * 1028).encode()
    """
    _element_type: ClassVar[Type[T]]
    _min_length: ClassVar[int] = 0
    _max_length: ClassVar[int] = 2 ** 64

    def __class_getitem__(cls, params):
        # To overwrite previous cls values
        min_l, max_l, elem_t = 0, 2**64, None

        if isinstance(params, int) or isinstance(params, (type, TypeVar)):
            if isinstance(params, (type, TypeVar)): 
                elem_t = params
            elif isinstance(params, int): 
                max_l, min_l = params, params
            else: 
                raise TypeError(f"Invalid param to define {__class__.__name__}: {params}")
        elif len(params) == 2:
            if isinstance(params[0], type) and isinstance(params[1], int): 
                elem_t, min_l, max_l = params[0], params[1], params[1]
            elif isinstance(params[0], int) and isinstance(params[1], int): 
                min_l, max_l = params[0], params[1]
            else: 
                raise TypeError(f"Invalid param to define {cls.__class__.__name__}: {params}")
        elif len(params) == 3 and isinstance(params[0], (type, TypeVar)) and isinstance(params[1], int) and isinstance(params[2], int): 
            elem_t, min_l, max_l = params
        else:
            raise TypeError(f"Invalid param to define {cls.__class__.__name__}: {params}")

        # build a nice name
        parts = []
        if elem_t:
            parts.append(elem_t.__name__)
        if min_l == max_l:
            parts.append(f"N={min_l}")
        else:
            if min_l: 
                parts.append(f"min={min_l}")
            if max_l != 2 ** 64: 
                parts.append(f"max={max_l}")

        name = f"{cls.__name__}[{','.join(parts)}]"

        return type(name, (cls,), {
            "_element_type": elem_t,
            "_min_length": min_l,
            "_max_length": max_l,
        })

    def _validate(self, value):
        """For TypeChecks - added to fns that alter elements"""
        if getattr(self, "_element_type", None) is not None:
            if not isinstance(value, self._element_type):
                raise TypeError(f"{value!r} is not an instance of {self._element_type!r}")

    def _validate_self(self):
        """For Resultant self check - added to fns that alter size"""
        if  len(self) < self._min_length:
            raise ValueError(f"Vector: Expected sequence size to be >= {self._min_length}, resultant size {len(self)}")
        elif len(self) > self._max_length:
            raise ValueError(f"Vector: Expected sequence size to be <= {self._max_length}, resultant size {len(self)}")

    def __init__(self, initial: list[T]):
        super().__init__()
        self.extend(initial)

    def append(self, v: T):
        self._validate(v)
        super().append(v)
        self._validate_self()

    def insert(self, i, v: T):
        self._validate(v)
        super().insert(i, v)
        self._validate_self()

    def extend(self, seq: list[T]):
        for val in seq:
            self._validate(val)
        super().extend(seq)
        self._validate_self()

    def __setitem__(self, i, v: T):
        self._validate(v)
        super().__setitem__(i, v)

    def __repr__(self):
        return f"{self.__class__.__name__}({list(self)})"
    
    @property
    def _length(self):
        if self._min_length == self._max_length:
            return self._min_length
        return None
    
    # ---------------------------------------------------------------------------- #
    #                                 Serialization                                #
    # ---------------------------------------------------------------------------- #
    def encode_size(self):
        size = 0

        # If length is not defined
        if self._length is None:
            size += Uint(len(self)).encode_size()
            
        for item in self:
            if not isinstance(item, Codable):
                raise TypeError(0, 0, f"Expected Codable, got {type(item)}")
            size += item.encode_size()

        return size
    
    def encode_into(self, buffer: bytearray, offset: int = 0) -> int:
        current_offset = offset
        # If length is not defined
        if(self._min_length != len(self)) and (self._max_length != len(self)):
            current_offset += Uint(len(self)).encode_into(buffer, current_offset)

        for item in self:
            written = item.encode_into(buffer, current_offset)
            current_offset += written

        return current_offset - offset
    
    @classmethod
    def decode_from(cls, buffer: bytes, offset: int = 0) -> Tuple["Seq", int]:
        current_offset = offset
        
        # Determine if this is variable length
        if cls._min_length == cls._max_length:
            # Fixed length
            _len = cls._min_length
        else:
            # Variable length - decode length from buffer
            _len, _inc_offset = Uint.decode_from(buffer, current_offset)
            current_offset += _inc_offset

        items = []
        for _ in range(_len):
            item, _inc_offset = cls._element_type.decode_from(buffer, current_offset)
            current_offset += _inc_offset
            items.append(item)

        return cls(items), current_offset - offset

    # ---------------------------------------------------------------------------- #
    #                                  JSON Serde                                  #
    # ---------------------------------------------------------------------------- #
    def to_json(self):
        """Convert to JSON representation."""
        return [item.to_json() for item in self]

    @classmethod
    def from_json(cls, data):
        """Create instance from JSON representation."""
        if cls._element_type:
            items = [cls._element_type.from_json(item) for item in data]
        else:
            items = data
        return cls(items)


# All params supported-
# Union[Type, int, Tuple[Type, int], Tuple[int, int], Tuple[Type, int, int]]

class Vector(Seq):
    def __class_getitem__(cls, params: None): return super().__class_getitem__(params)

class Array(Seq):
    def __class_getitem__(cls, params: int): return super().__class_getitem__(params)

class TypedArray(Seq):
    def __class_getitem__(cls, params: Tuple[Type, int]): return super().__class_getitem__(params)

class TypedVector(Seq):
    def __class_getitem__(cls, params: Type): return super().__class_getitem__(params)

class BoundedVector(Seq):
    def __class_getitem__(cls, params: Tuple[int, int]): return super().__class_getitem__(params)

class TypedBoundedVector(Seq):
    def __class_getitem__(cls, params: Tuple[Type, int, int]): return super().__class_getitem__(params)