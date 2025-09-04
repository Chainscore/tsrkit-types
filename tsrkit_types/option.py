from typing import Generic, Optional, TypeVar
from tsrkit_types.choice import Choice
from tsrkit_types.null import Null, NullType


T = TypeVar("T")

class Option(Choice, Generic[T]):
    """
    Option[T] wraps either no value (None) or a T.
    """

    def __class_getitem__(cls, opt_t: T):
        if not isinstance(opt_t, type):
            raise TypeError("Option[...] only accepts a single type")
        name = f"Option[{opt_t.__class__.__name__}]"
        return type(name,
                    (Option,),
                    {"_opt_types": ((None, NullType), (None, opt_t))})

    def __init__(self, val: T|NullType = Null, key = None):
        super().__init__(val)

    def set(self, value: T|NullType = Null, key: Optional[str] = None):
        if value is None:
            value = Null
        super().set(value, key)

    def __bool__(self):
        return self._value != Null
    
    # ---------------------------------------------------------------------------- #
    #                                  JSON Serde                                  #
    # ---------------------------------------------------------------------------- #
    
    def to_json(self):
        """Convert Option to JSON. Returns None for empty Options."""
        if self._value == Null:
            return None
        return self._value.to_json()
    
    @classmethod
    def from_json(cls, data):
        """Create Option from JSON data. None creates empty Option."""
        if data is None:
            return cls()  # Empty Option
        # Try to create the wrapped type from the data
        return cls(cls._opt_types[1][1].from_json(data))