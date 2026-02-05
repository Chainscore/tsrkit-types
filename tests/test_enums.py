import pytest
from tsrkit_types.enum import Enum


class TestEnumBasics:
    """Test basic enum creation and usage."""

    def test_basic_enum_creation(self):
        """Test basic enum creation."""
        class Color(Enum):
            RED = 0
            GREEN = 1
            BLUE = 2
            YELLOW = 3

        primary_color = Color.RED
        secondary_color = Color(1)

        assert primary_color._name_ == "RED"
        assert primary_color.value == 0
        assert secondary_color._name_ == "GREEN"
        assert secondary_color.value == 1
        assert primary_color == Color.RED
        assert primary_color != secondary_color

    def test_enum_iteration(self):
        """Test iterating over enum members."""
        class Color(Enum):
            RED = 0
            GREEN = 1
            BLUE = 2
            YELLOW = 3

        all_colors = [color._name_ for color in Color]
        assert all_colors == ["RED", "GREEN", "BLUE", "YELLOW"]


class TestEnumWithCustomValues:
    """Test enums with custom integer values."""

    def test_http_status_enum(self):
        """Test enum with HTTP status code values."""
        class HttpStatus(Enum):
            OK = 200
            NOT_FOUND = 404
            INTERNAL_ERROR = 500
            BAD_REQUEST = 400

        members = [("OK", 200), ("NOT_FOUND", 404), ("INTERNAL_ERROR", 500), ("BAD_REQUEST", 400)]
        for name, value in members:
            member = HttpStatus(value)
            assert member._name_ == name
            assert member.value == value

    def test_priority_enum(self):
        """Test enum with priority values."""
        class Priority(Enum):
            LOW = 1
            NORMAL = 2
            HIGH = 3
            CRITICAL = 4

        members = [("LOW", 1), ("NORMAL", 2), ("HIGH", 3), ("CRITICAL", 4)]
        for name, value in members:
            member = Priority(value)
            assert member._name_ == name
            assert member.value == value


class TestEnumEncoding:
    """Test enum encoding and decoding."""

    def test_encode_decode_sequential(self):
        """Test encoding/decoding with sequential values."""
        class TestEnum1(Enum):
            VALUE_0 = 1
            VALUE_1 = 2
            VALUE_2 = 3
            VALUE_3 = 4

        for member in TestEnum1:
            encoded = member.encode()
            decoded = TestEnum1.decode(encoded)

            assert len(encoded) > 0
            assert decoded._name_ == member._name_
            assert decoded.value == member.value
            assert decoded == member

    def test_encode_decode_zero_based(self):
        """Test encoding/decoding with zero-based values."""
        class TestEnum2(Enum):
            VALUE_0 = 0
            VALUE_1 = 1
            VALUE_2 = 2
            VALUE_3 = 3

        for member in TestEnum2:
            encoded = member.encode()
            decoded = TestEnum2.decode(encoded)

            assert len(encoded) > 0
            assert decoded._name_ == member._name_
            assert decoded.value == member.value
            assert decoded == member

    def test_encode_decode_sparse(self):
        """Test encoding/decoding with sparse values."""
        class TestEnum3(Enum):
            VALUE_0 = 200
            VALUE_1 = 404
            VALUE_2 = 500

        for member in TestEnum3:
            encoded = member.encode()
            decoded = TestEnum3.decode(encoded)

            assert len(encoded) > 0
            assert decoded._name_ == member._name_
            assert decoded.value == member.value
            assert decoded == member


class TestEnumJSON:
    """Test enum JSON serialization."""

    def test_json_by_value(self):
        """Test JSON serialization by value."""
        class GameState(Enum):
            MENU = 0
            PLAYING = 1
            PAUSED = 2

        for state in [GameState.MENU, GameState.PLAYING, GameState.PAUSED]:
            json_value = state.to_json()
            restored = GameState.from_json(json_value)
            assert restored._name_ == state._name_
            assert restored == state

    def test_json_by_name(self):
        """Test JSON serialization by name."""
        class GameState(Enum):
            MENU = 0
            PLAYING = 1
            PAUSED = 2

        for state in [GameState.MENU, GameState.PLAYING, GameState.PAUSED]:
            restored = GameState.from_json(state._name_)
            assert restored._name_ == state._name_
            assert restored == state


class TestEnumValidation:
    """Test enum validation and error handling."""

    @pytest.mark.parametrize("invalid_value", [5, 999, -1])
    def test_invalid_integer_value(self, invalid_value):
        """Test invalid integer values raise ValueError."""
        class Direction(Enum):
            NORTH = 0
            EAST = 1
            SOUTH = 2
            WEST = 3

        with pytest.raises(ValueError):
            Direction(invalid_value)

    @pytest.mark.parametrize("invalid_name", ["INVALID", "UNKNOWN", ""])
    def test_invalid_name_from_json(self, invalid_name):
        """Test invalid names raise ValueError."""
        class Direction(Enum):
            NORTH = 0
            EAST = 1
            SOUTH = 2
            WEST = 3

        with pytest.raises(ValueError):
            Direction.from_json(invalid_name)


class TestEnumComparison:
    """Test enum comparison operations."""

    def test_enum_equality(self):
        """Test enum equality comparisons."""
        class Size(Enum):
            SMALL = 1
            MEDIUM = 2
            LARGE = 3

        small = Size.SMALL
        large = Size.LARGE

        assert small == Size.SMALL
        assert small != large

    def test_enum_sorting(self):
        """Test sorting enums by value."""
        class Size(Enum):
            SMALL = 1
            MEDIUM = 2
            LARGE = 3
            EXTRA_LARGE = 4

        sizes = [Size.LARGE, Size.SMALL, Size.EXTRA_LARGE, Size.MEDIUM]
        sorted_sizes = sorted(sizes, key=lambda s: s.value)
        expected = [Size.SMALL, Size.MEDIUM, Size.LARGE, Size.EXTRA_LARGE]

        assert sorted_sizes == expected

    def test_value_comparison(self):
        """Test comparing enum values."""
        class Size(Enum):
            SMALL = 1
            LARGE = 3

        assert Size.SMALL.value < Size.LARGE.value


class TestEnumInDataStructures:
    """Test enums in collections."""

    def test_enum_as_dict_keys(self):
        """Test using enums as dictionary keys."""
        class TaskPriority(Enum):
            LOW = 1
            MEDIUM = 2
            HIGH = 3
            URGENT = 4

        priority_colors = {
            TaskPriority.LOW: "green",
            TaskPriority.MEDIUM: "yellow",
            TaskPriority.HIGH: "orange",
            TaskPriority.URGENT: "red"
        }

        assert len(priority_colors) == 4
        assert priority_colors[TaskPriority.LOW] == "green"
        assert priority_colors[TaskPriority.URGENT] == "red"

    def test_enum_in_lists(self):
        """Test enums in lists."""
        class TaskPriority(Enum):
            LOW = 1
            MEDIUM = 2
            HIGH = 3
            URGENT = 4

        priorities = [TaskPriority.HIGH, TaskPriority.LOW, TaskPriority.URGENT]

        assert len(priorities) == 3
        assert TaskPriority.HIGH in priorities
        assert TaskPriority.MEDIUM not in priorities

    def test_enum_filtering(self):
        """Test filtering enums by value."""
        class TaskPriority(Enum):
            LOW = 1
            MEDIUM = 2
            HIGH = 3
            URGENT = 4

        priorities = [TaskPriority.HIGH, TaskPriority.LOW, TaskPriority.URGENT, TaskPriority.MEDIUM]
        high_priority = [p for p in priorities if p.value >= TaskPriority.HIGH.value]

        assert len(high_priority) == 2
        assert TaskPriority.HIGH in high_priority
        assert TaskPriority.URGENT in high_priority


class TestEnumEdgeCases:
    """Test edge cases."""

    def test_single_value_enum(self):
        """Test enum with single value."""
        class SingleEnum(Enum):
            ONLY = 42

        value = SingleEnum.ONLY
        assert value._name_ == "ONLY"
        assert value.value == 42

    def test_enum_with_zero(self):
        """Test enum with zero value."""
        class Status(Enum):
            INACTIVE = 0
            ACTIVE = 1

        inactive = Status.INACTIVE
        assert inactive.value == 0
        assert inactive._name_ == "INACTIVE"

    def test_large_value_enum(self):
        """Test enum with large values."""
        class LargeEnum(Enum):
            BIG = 999999
            BIGGER = 1000000

        big = LargeEnum.BIG
        assert big.value == 999999


class TestEnumUseCases:
    """Test practical enum use cases."""

    def test_state_machine_transitions(self):
        """Test enum in state machine."""
        class OrderStatus(Enum):
            PENDING = 0
            CONFIRMED = 1
            PROCESSING = 2
            SHIPPED = 3
            DELIVERED = 4

        def advance_status(status):
            transitions = {
                OrderStatus.PENDING: OrderStatus.CONFIRMED,
                OrderStatus.CONFIRMED: OrderStatus.PROCESSING,
                OrderStatus.PROCESSING: OrderStatus.SHIPPED,
                OrderStatus.SHIPPED: OrderStatus.DELIVERED,
            }
            return transitions.get(status, status)

        current = OrderStatus.PROCESSING
        next_status = advance_status(current)
        assert next_status == OrderStatus.SHIPPED

    def test_enum_for_configuration(self):
        """Test enum for configuration options."""
        class LogLevel(Enum):
            DEBUG = 0
            INFO = 1
            WARNING = 2
            ERROR = 3

        current_level = LogLevel.INFO
        assert current_level.value == 1

        # Can compare for filtering
        assert LogLevel.WARNING.value > current_level.value
        assert LogLevel.DEBUG.value < current_level.value
