from typing import Generic, TypeVar
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
                    {"_opt_types": ((None, opt_t), (None, NullType))})

    def __init__(self, val: T|NullType = Null):
        super().__init__(val)

    def __bool__(self):
        return self._value != Null