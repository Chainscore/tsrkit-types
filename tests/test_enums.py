import pytest
from tsrkit_types.enum import Enum


def test_basic_enum():
    """Test basic enum creation and usage."""
    # Define a simple enum
    class Color(Enum):
        RED = 0
        GREEN = 1  
        BLUE = 2
        YELLOW = 3
    
    # Create enum values
    primary_color = Color.RED
    secondary_color = Color(1)  # Color.GREEN from integer
    
    assert primary_color._name_ == "RED"
    assert primary_color.value == 0
    assert secondary_color._name_ == "GREEN"
    assert secondary_color.value == 1
    
    # Enum comparison
    assert primary_color == Color.RED
    assert primary_color != secondary_color
    
    # List all enum members
    all_colors = [color._name_ for color in Color]
    assert "RED" in all_colors
    assert "GREEN" in all_colors
    assert "BLUE" in all_colors
    assert "YELLOW" in all_colors


def test_enum_with_custom_values():
    """Test enums with custom integer values."""
    # HTTP status codes
    class HttpStatus(Enum):
        OK = 200
        NOT_FOUND = 404
        INTERNAL_ERROR = 500
        BAD_REQUEST = 400
        UNAUTHORIZED = 401
        FORBIDDEN = 403
    
    # Create status instances
    success = HttpStatus.OK
    error = HttpStatus(404)  # NOT_FOUND from integer
    
    assert success._name_ == "OK"
    assert success.value == 200
    assert error._name_ == "NOT_FOUND"
    assert error.value == 404
    
    # Helper function using enum
    def get_status_message(status: HttpStatus) -> str:
        if status == HttpStatus.OK:
            return "Request successful"
        elif status == HttpStatus.NOT_FOUND:
            return "Resource not found"
        elif status == HttpStatus.INTERNAL_ERROR:
            return "Server error"
        else:
            return f"Status: {status._name_}"
    
    assert get_status_message(success) == "Request successful"
    assert get_status_message(error) == "Resource not found"


def test_enum_encoding():
    """Test enum encoding and decoding."""
    class Priority(Enum):
        LOW = 1
        NORMAL = 2
        HIGH = 3
        CRITICAL = 4
    
    priorities = [Priority.LOW, Priority.NORMAL, Priority.HIGH, Priority.CRITICAL]
    
    for priority in priorities:
        encoded = priority.encode()
        decoded = Priority.decode(encoded)
        
        assert len(encoded) > 0
        assert decoded._name_ == priority._name_
        assert decoded.value == priority.value
        assert priority == decoded


def test_enum_json():
    """Test enum JSON serialization."""
    class GameState(Enum):
        MENU = 0
        PLAYING = 1
        PAUSED = 2
        GAME_OVER = 3
        LOADING = 4
    
    states = [GameState.MENU, GameState.PLAYING, GameState.PAUSED]
    
    for state in states:
        # JSON serialization by value (integer)
        json_value = state.to_json()
        restored_from_value = GameState.from_json(json_value)
        
        # JSON serialization by name (string)
        restored_from_name = GameState.from_json(state._name_)
        
        assert restored_from_value._name_ == state._name_
        assert restored_from_name._name_ == state._name_
        assert state == restored_from_value == restored_from_name


def test_enum_validation():
    """Test enum value validation and error handling."""
    class Direction(Enum):
        NORTH = 0
        EAST = 1
        SOUTH = 2
        WEST = 3
    
    # Valid enum creation
    valid_direction = Direction.NORTH
    assert valid_direction._name_ == "NORTH"
    
    valid_from_int = Direction(2)  # SOUTH
    assert valid_from_int._name_ == "SOUTH"
    
    # Invalid enum values
    with pytest.raises(ValueError):
        Direction(5)  # Invalid integer
    
    with pytest.raises(ValueError):
        Direction.from_json("INVALID")  # Invalid name
    
    with pytest.raises(ValueError):
        Direction.from_json(999)  # Invalid value


def test_enum_use_cases():
    """Test practical enum use cases."""
    # 1. Configuration options
    class LogLevel(Enum):
        DEBUG = 0
        INFO = 1
        WARNING = 2
        ERROR = 3
        CRITICAL = 4
    
    # 2. State machines
    class OrderStatus(Enum):
        PENDING = 0
        CONFIRMED = 1
        PROCESSING = 2
        SHIPPED = 3
        DELIVERED = 4
        CANCELLED = 5
    
    # 3. Game mechanics
    class WeaponType(Enum):
        SWORD = 0
        BOW = 1
        STAFF = 2
        DAGGER = 3
    
    # Usage examples
    current_log_level = LogLevel.INFO
    order_status = OrderStatus.PROCESSING
    player_weapon = WeaponType.SWORD
    
    assert current_log_level._name_ == "INFO"
    assert current_log_level.value == 1
    assert order_status._name_ == "PROCESSING"
    assert player_weapon._name_ == "SWORD"
    
    # State transitions
    def advance_order_status(status: OrderStatus) -> OrderStatus:
        transitions = {
            OrderStatus.PENDING: OrderStatus.CONFIRMED,
            OrderStatus.CONFIRMED: OrderStatus.PROCESSING,
            OrderStatus.PROCESSING: OrderStatus.SHIPPED,
            OrderStatus.SHIPPED: OrderStatus.DELIVERED,
        }
        return transitions.get(status, status)
    
    next_status = advance_order_status(order_status)
    assert next_status._name_ == "SHIPPED"


def test_enum_comparison():
    """Test enum comparison and sorting."""
    class Size(Enum):
        SMALL = 1
        MEDIUM = 2
        LARGE = 3
        EXTRA_LARGE = 4
    
    sizes = [Size.LARGE, Size.SMALL, Size.EXTRA_LARGE, Size.MEDIUM]
    
    # Sort by enum value
    sorted_sizes = sorted(sizes, key=lambda s: s.value)
    expected_order = [Size.SMALL, Size.MEDIUM, Size.LARGE, Size.EXTRA_LARGE]
    
    assert sorted_sizes == expected_order
    
    # Comparison operations
    small = Size.SMALL
    large = Size.LARGE
    
    assert small == Size.SMALL
    assert small != large
    assert small.value < large.value


def test_enum_inheritance():
    """Test enum inheritance patterns."""
    # Base enum behavior (though direct inheritance is limited)
    class BaseStatus(Enum):
        ACTIVE = 1
        INACTIVE = 0
    
    class UserStatus(Enum):
        PENDING = 0
        ACTIVE = 1
        SUSPENDED = 2
        DELETED = 3
    
    # Enums with similar patterns but different domains
    class ServiceStatus(Enum):
        DOWN = 0
        UP = 1
        MAINTENANCE = 2
    
    # Show different status types
    user_status = UserStatus.ACTIVE
    service_status = ServiceStatus.UP
    
    assert user_status._name_ == "ACTIVE"
    assert user_status.value == 1
    assert service_status._name_ == "UP"
    assert service_status.value == 1
    
    # Common pattern: status checking
    def is_operational(status_enum, status_value):
        """Generic function to check if a status indicates operational state."""
        active_values = {1}  # Assume 1 means active/up/operational
        return status_value.value in active_values
    
    assert is_operational(UserStatus, user_status) is True
    assert is_operational(ServiceStatus, service_status) is True


def test_enum_in_data_structures():
    """Test enums in data structures and collections."""
    class TaskPriority(Enum):
        LOW = 1
        MEDIUM = 2
        HIGH = 3
        URGENT = 4
    
    # Dictionary with enum keys
    priority_colors = {
        TaskPriority.LOW: "green",
        TaskPriority.MEDIUM: "yellow", 
        TaskPriority.HIGH: "orange",
        TaskPriority.URGENT: "red"
    }
    
    # List of enum values
    task_priorities = [
        TaskPriority.HIGH,
        TaskPriority.LOW,
        TaskPriority.URGENT,
        TaskPriority.MEDIUM
    ]
    
    assert len(priority_colors) == 4
    assert priority_colors[TaskPriority.LOW] == "green"
    assert priority_colors[TaskPriority.URGENT] == "red"
    
    assert len(task_priorities) == 4
    assert TaskPriority.HIGH in task_priorities
    assert TaskPriority.URGENT in task_priorities
    
    # Filter and process
    high_priority_tasks = [p for p in task_priorities if p.value >= TaskPriority.HIGH.value]
    assert len(high_priority_tasks) == 2  # HIGH and URGENT
    assert TaskPriority.HIGH in high_priority_tasks
    assert TaskPriority.URGENT in high_priority_tasks


def test_enum_edge_cases():
    """Test edge cases for enum handling."""
    # Enum with single value
    class SingleEnum(Enum):
        ONLY = 42
    
    value = SingleEnum.ONLY
    assert value._name_ == "ONLY"
    assert value.value == 42
    
    # Test encoding/decoding
    encoded = value.encode()
    decoded = SingleEnum.decode(encoded)
    assert decoded == value
    
    # Enum with zero value
    class ZeroEnum(Enum):
        ZERO = 0
        ONE = 1
    
    zero_val = ZeroEnum.ZERO
    assert zero_val._name_ == "ZERO"
    assert zero_val.value == 0
    
    # Test that zero value works correctly
    encoded_zero = zero_val.encode()
    decoded_zero = ZeroEnum.decode(encoded_zero)
    assert decoded_zero == zero_val


def test_enum_comprehensive():
    """Comprehensive test of enum features."""
    class ComplexEnum(Enum):
        FIRST = 10
        SECOND = 20
        THIRD = 30
        FOURTH = 40
        FIFTH = 50
    
    # Test all enum instances
    all_values = [ComplexEnum.FIRST, ComplexEnum.SECOND, ComplexEnum.THIRD, 
                  ComplexEnum.FOURTH, ComplexEnum.FIFTH]
    expected_names = ["FIRST", "SECOND", "THIRD", "FOURTH", "FIFTH"]
    expected_values = [10, 20, 30, 40, 50]
    
    for enum_val, exp_name, exp_value in zip(all_values, expected_names, expected_values):
        assert enum_val._name_ == exp_name
        assert enum_val.value == exp_value
        
        # Test round-trip encoding
        encoded = enum_val.encode()
        decoded = ComplexEnum.decode(encoded)
        assert decoded == enum_val
        
        # Test JSON round-trip
        json_data = enum_val.to_json()
        json_restored = ComplexEnum.from_json(json_data)
        assert json_restored == enum_val
        
        # Test creation from integer
        from_int = ComplexEnum(exp_value)
        assert from_int == enum_val


def test_enum_type_safety():
    """Test enum type safety and validation."""
    class StrictEnum(Enum):
        ALPHA = 1
        BETA = 2
        GAMMA = 3
    
    # Valid operations
    alpha = StrictEnum.ALPHA
    beta = StrictEnum(2)  # BETA
    
    assert alpha._name_ == "ALPHA"
    assert beta._name_ == "BETA"
    
    # Invalid operations
    with pytest.raises(ValueError):
        StrictEnum(999)  # Invalid value
    
    with pytest.raises(ValueError):
        StrictEnum.from_json("INVALID_NAME")
    
    # Test immutability
    original_value = alpha.value
    # Enums should be immutable - can't change value
    assert alpha.value == original_value


def test_enum_iteration():
    """Test iteration over enum members."""
    class IterableEnum(Enum):
        A = 1
        B = 2
        C = 3
        D = 4
    
    # Test iteration
    members = list(IterableEnum)
    assert len(members) == 4
    
    names = [member._name_ for member in IterableEnum]
    values = [member.value for member in IterableEnum]
    
    assert "A" in names
    assert "B" in names
    assert "C" in names
    assert "D" in names
    
    assert 1 in values
    assert 2 in values
    assert 3 in values
    assert 4 in values 