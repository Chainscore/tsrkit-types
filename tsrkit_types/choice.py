from typing import ClassVar, Optional, Union, Tuple, Any

from tsrkit_types.integers import Uint
from tsrkit_types.itf.codable import Codable

ChoiceType = Tuple[Optional[str], type] | type

class Choice(Codable):
    """
    Can either be defined as:
        

    Usage:
        >>> dir_choice = Choice[T1, T2, ...](T1(XYZ))
        -> makes _opt_types = (None, T1), (None, T2), ...

        >>> dir_choice.set(T2(ABC))
        -> changes the choice to T2(ABC)

        >>> class NamedChoice(Choice):
        >>>    type1: T1
        >>>    type2: T2
        >>>    type3: T2
        -> makes _opt_types = (type1, T1), (type2, T2), ... 
        >>> a = NamedChoice(T1(XYZ))
        # If setting a choice with multiple types, the first type is the default, or give an optional key string
        >>> b = NamedChoice(T2(ABC))
        >>> b.to_json()
        -> {"type2": "ABC"}
        >>> c = NamedChoice(T2(ABC), key="type3")
        >>> c.to_json()
        -> {"type3": "ABC"}
    """
    _opt_types: ClassVar[Tuple[ChoiceType]]
    _choice_key: Optional[str]
    _value: Any

    @property
    def _choice_types(self) -> Tuple[type]:
        return tuple(self._choice[1] for self._choice in self._opt_types)
    
    @property
    def _choice_keys(self) -> Tuple[Optional[str]]:
        return tuple(self._choice[0] for self._choice in self._opt_types)

    def __class_getitem__(cls, opt_t: Tuple[type] | type):
        _opt_types = []
        if isinstance(opt_t, type):
            _opt_types.append((None, opt_t))
        else:
            for op in opt_t:
                _opt_types.append((None, op))
        name = f"Choice[{'/'.join(op[1].__class__.__name__ for op in _opt_types)}]"
        return type(name,
                    (Choice,),
                    {"_opt_types": tuple(_opt_types)})
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        ann = getattr(cls, "__annotations__", {})
        if ann:
            cls._opt_types = tuple((field, ann[field]) for field in ann)

    def __init__(self, value: Any, key: Optional[str] = None) -> None:
        super().__init__()
        self.set(value, key)

    def unwrap(self) -> Any:
        return self._value

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._value!r})"

    def __eq__(self, other):
        if isinstance(other, Choice):
            return other._value == self._value
        return other == self._value

    def set(self, value: Any, key: Optional[str] = None):
        if not isinstance(value, self._choice_types):
            raise TypeError(f"{value!r} is not a {self._choice_types}")
        
        key = key or tuple(self._choice[0] for self._choice in self._opt_types if isinstance(value, self._choice[1]))[0]
        if key not in self._choice_keys:
            raise ValueError(f"Key {key!r} not in {self._choice_keys}")
        
        self._choice_key = key
        self._value = value

    # ---------------------------------------------------------------------------- #
    #                                  JSON Serde                                  #
    # ---------------------------------------------------------------------------- #

    def to_json(self):
        return self._value.to_json() if not self._choice_key else {self._choice_key: self._value.to_json()}

    @classmethod
    def from_json(cls, data: dict | Any) -> "Choice":
        if isinstance(data, dict):
            opt_type = next((x for x in cls._opt_types if x[0] == list(data.keys())[0]), None)
            if opt_type is None:
                raise ValueError(f"Key {list(data.keys())[0]} not in {cls._opt_types}")
            return cls(opt_type[1].from_json(list(data.values())[0]), key=opt_type[0])
        return cls(cls._opt_types[0][1].from_json(data), key=cls._opt_types[0][0])

    # ---------------------------------------------------------------------------- #
    #                                 Serialization                                #
    # ---------------------------------------------------------------------------- #

    def encode_size(self) -> int:
        return Uint(len(self._opt_types)).encode_size() + self._value.encode_size()

    def encode_into(self, buf: bytearray, offset: int = 0) -> int:
        current_offset = offset
        # Find the first isinstance(self._value, type) for self._choice_types
        for i, t in enumerate(self._choice_types):
            if isinstance(self._value, t):
                current_offset += Uint(i).encode_into(buf, current_offset)
                break
        else:
            raise ValueError(f"Value {self._value} is not a valid choice")
        current_offset += self._value.encode_into(buf, current_offset)
        return current_offset - offset

    @classmethod
    def decode_from(
        cls, buffer: Union[bytes, bytearray, memoryview], offset: int = 0
    ) -> Tuple[Any, int]:
        tag, tag_size = Uint.decode_from(buffer, offset)
        value, val_size = cls._opt_types[tag][1].decode_from(buffer, offset+tag_size)

        return cls(value), tag_size+val_size