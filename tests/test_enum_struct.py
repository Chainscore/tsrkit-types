"""
New tests for Enum fields inside @structure-decorated classes.
These were previously failing when Enum wasn\'t treated as Codable.
"""

from enum import Enum

import pytest

from tsrkit_types.struct import structure
from tsrkit_types.integers import U32


class SimpleEnum(Enum):
    ALPHA = 1
    BETA = 2
    GAMMA = 3


@structure
class Container:
    idx: U32
    flag: SimpleEnum


def test_enum_field_round_trip():
    original = Container(idx=U32(42), flag=SimpleEnum.BETA)

    # Encode / decode binary
    encoded = original.encode()  # type: ignore[attr-defined]
    decoded = Container.decode(encoded)  # type: ignore[attr-defined]
    assert decoded == original
    assert decoded.flag is SimpleEnum.BETA

    # JSON round-trip
    data = original.to_json()  # type: ignore[attr-defined]
    restored = Container.from_json(data)  # type: ignore[attr-defined]
    assert restored == original


# Quick param checks across enum values
@pytest.mark.parametrize("val", list(SimpleEnum))
def test_all_enum_variants(val):
    c = Container(idx=U32(1), flag=val)
    assert Container.decode(c.encode()).flag is val  # type: ignore[attr-defined]