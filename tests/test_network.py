"""
Tests for network protocol simulation using TSRKit types.
Demonstrates real-world usage in networking applications.
"""

import pytest
import time
import hashlib
from dataclasses import field
from typing import Optional, List

from tsrkit_types.integers import U8, U16, U32, U64
from tsrkit_types.string import String
from tsrkit_types.bool import Bool
from tsrkit_types.bytes import Bytes
from tsrkit_types.sequences import TypedVector
from tsrkit_types.option import Option
from tsrkit_types.choice import Choice
from tsrkit_types.struct import struct, structure
from tsrkit_types.enum import Enum


def test_network_protocol():
    """Test a complete network protocol implementation."""
    # Define message types
    class MessageType(Enum):
        HEARTBEAT = 0
        DATA = 1
        ERROR = 2
        AUTH = 3
        CONFIG = 4
    
    # Define error codes
    class ErrorCode(Enum):
        NONE = 0
        INVALID_MESSAGE = 1
        AUTHENTICATION_FAILED = 2
        PERMISSION_DENIED = 3
        SERVER_ERROR = 4
    
    # Common header for all messages
    @structure
    class MessageHeader:
        version: U8 = field(metadata={"default": U8(1)})
        message_type: MessageType
        sequence_id: U32
        timestamp: U64
        flags: U8 = field(metadata={"default": U8(0)})
    
    # Authentication message
    @structure
    class AuthMessage:
        header: MessageHeader
        username: String
        password_hash: Bytes
        client_info: String = field(metadata={"default": String("Unknown")})
    
    # Data payload message
    @structure
    class DataMessage:
        header: MessageHeader
        payload: Bytes
        checksum: U32
        compression: Bool = field(metadata={"default": Bool(False)})
    
    # Error message
    @structure
    class ErrorMessage:
        header: MessageHeader
        error_code: ErrorCode
        error_message: String
        context: Option[String]
    
    # Heartbeat message (minimal)
    @structure
    class HeartbeatMessage:
        header: MessageHeader
        load_average: U16 = field(metadata={"default": U16(0)})
    
    # Configuration message
    @structure
    class ConfigEntry:
        key: String
        value: String
        
    @structure
    class ConfigMessage:
        header: MessageHeader
        entries: TypedVector[ConfigEntry]
        reset_required: Bool = field(metadata={"default": Bool(False)})
    
    # Create sample messages
    current_time = int(time.time() * 1000)
    
    # 1. Authentication message
    password = "secure_password_123"
    password_hash = hashlib.sha256(password.encode()).digest()
    
    auth_msg = AuthMessage(
        header=MessageHeader(
            message_type=MessageType.AUTH,
            sequence_id=U32(1),
            timestamp=U64(current_time)
        ),
        username=String("alice"),
        password_hash=Bytes(password_hash),
        client_info=String("Python Client v1.0")
    )
    
    # 2. Data message
    data_payload = b"Important business data that needs to be transmitted securely"
    checksum = sum(data_payload) % (2**32)
    
    data_msg = DataMessage(
        header=MessageHeader(
            message_type=MessageType.DATA,
            sequence_id=U32(2),
            timestamp=U64(current_time + 1000)
        ),
        payload=Bytes(data_payload),
        checksum=U32(checksum),
        compression=Bool(False)
    )
    
    # 3. Error message
    error_msg = ErrorMessage(
        header=MessageHeader(
            message_type=MessageType.ERROR,
            sequence_id=U32(3),
            timestamp=U64(current_time + 2000)
        ),
        error_code=ErrorCode.PERMISSION_DENIED,
        error_message=String("Access denied for requested resource"),
        context=Option[String](String("/api/admin/users"))
    )
    
    # 4. Heartbeat message
    heartbeat_msg = HeartbeatMessage(
        header=MessageHeader(
            message_type=MessageType.HEARTBEAT,
            sequence_id=U32(4),
            timestamp=U64(current_time + 3000)
        ),
        load_average=U16(75)  # 75% load
    )
    
    # 5. Configuration message
    config_msg = ConfigMessage(
        header=MessageHeader(
            message_type=MessageType.CONFIG,
            sequence_id=U32(5),
            timestamp=U64(current_time + 4000)
        ),
        entries=TypedVector[ConfigEntry]([
            ConfigEntry(key=String("max_connections"), value=String("1000")),
            ConfigEntry(key=String("timeout_seconds"), value=String("30")),
            ConfigEntry(key=String("debug_mode"), value=String("false"))
        ]),
        reset_required=Bool(True)
    )
    
    messages = [auth_msg, data_msg, error_msg, heartbeat_msg, config_msg]
    
    # Test all messages
    total_bytes = 0
    for msg in messages:
        # Test basic properties
        assert msg.header.message_type in [MessageType.AUTH, MessageType.DATA, 
                                          MessageType.ERROR, MessageType.HEARTBEAT, 
                                          MessageType.CONFIG]
        assert msg.header.sequence_id > 0
        assert msg.header.timestamp > 0
        
        # Test encoding/decoding
        encoded = msg.encode()
        total_bytes += len(encoded)
        assert len(encoded) > 0
        
        # Verify round-trip
        decoded = type(msg).decode(encoded)
        assert msg.header.sequence_id == decoded.header.sequence_id
        assert msg.header.message_type == decoded.header.message_type
    
    # Verify we created different message types
    message_types = {msg.header.message_type for msg in messages}
    assert len(message_types) == 5  # All 5 different types
    
    # Verify total encoding worked
    assert total_bytes > 0


def test_message_routing():
    """Test message routing and processing."""
    class MessageType(Enum):
        REQUEST = 1
        RESPONSE = 2
        NOTIFICATION = 3
    
    class RequestType(Enum):
        GET_USER = 1
        UPDATE_USER = 2
        DELETE_USER = 3
        LIST_USERS = 4
    
    @structure
    class RequestMessage:
        message_type: MessageType = field(metadata={"default": MessageType.REQUEST})
        request_id: U32
        request_type: RequestType
        user_id: Option[U32]
        data: Option[Bytes]
    
    @structure
    class ResponseMessage:
        message_type: MessageType = field(metadata={"default": MessageType.RESPONSE})
        request_id: U32  # Matches original request
        success: Bool
        data: Option[Bytes]
        error_message: Option[String]
    
    # Message router class
    class MessageRouter:
        def __init__(self):
            self.handlers = {}
            self.next_request_id = 1
        
        def register_handler(self, request_type: RequestType, handler):
            self.handlers[request_type] = handler
        
        def create_request(self, request_type: RequestType, user_id=None, data=None):
            request = RequestMessage(
                request_id=U32(self.next_request_id),
                request_type=request_type,
                user_id=Option[U32](user_id) if user_id else Option[U32](),
                data=Option[Bytes](data) if data else Option[Bytes]()
            )
            self.next_request_id += 1
            return request
        
        def process_request(self, request: RequestMessage) -> ResponseMessage:
            handler = self.handlers.get(request.request_type)
            if not handler:
                return ResponseMessage(
                    request_id=request.request_id,
                    success=Bool(False),
                    data=Option[Bytes](),
                    error_message=Option[String](String(f"No handler for {request.request_type._name_}"))
                )
            
            try:
                result = handler(request)
                return ResponseMessage(
                    request_id=request.request_id,
                    success=Bool(True),
                    data=Option[Bytes](Bytes(result)) if result else Option[Bytes](),
                    error_message=Option[String]()
                )
            except Exception as e:
                return ResponseMessage(
                    request_id=request.request_id,
                    success=Bool(False),
                    data=Option[Bytes](),
                    error_message=Option[String](String(str(e)))
                )
    
    # Mock database
    users_db = {
        1: {"name": "Alice", "email": "alice@example.com"},
        2: {"name": "Bob", "email": "bob@example.com"},
        3: {"name": "Carol", "email": "carol@example.com"}
    }
    
    # Request handlers
    def handle_get_user(request: RequestMessage) -> bytes:
        if not request.user_id:
            raise ValueError("User ID required for GET_USER")
        
        user_id = int(request.user_id.unwrap())
        user = users_db.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        import json
        return json.dumps(user).encode()
    
    def handle_list_users(request: RequestMessage) -> bytes:
        import json
        return json.dumps(list(users_db.values())).encode()
    
    def handle_delete_user(request: RequestMessage) -> bytes:
        if not request.user_id:
            raise ValueError("User ID required for DELETE_USER")
        
        user_id = int(request.user_id.unwrap())
        if user_id not in users_db:
            raise ValueError(f"User {user_id} not found")
        
        del users_db[user_id]
        return b"User deleted"
    
    # Set up router
    router = MessageRouter()
    router.register_handler(RequestType.GET_USER, handle_get_user)
    router.register_handler(RequestType.LIST_USERS, handle_list_users)
    router.register_handler(RequestType.DELETE_USER, handle_delete_user)
    
    # Test successful requests
    list_request = router.create_request(RequestType.LIST_USERS)
    list_response = router.process_request(list_request)
    assert bool(list_response.success) is True
    assert list_response.data
    
    get_request = router.create_request(RequestType.GET_USER, user_id=U32(1))
    get_response = router.process_request(get_request)
    assert bool(get_response.success) is True
    assert get_response.data
    
    # Test error cases
    missing_user_request = router.create_request(RequestType.GET_USER, user_id=U32(999))
    missing_response = router.process_request(missing_user_request)
    assert bool(missing_response.success) is False
    assert missing_response.error_message
    
    # Test unhandled request type
    unhandled_request = router.create_request(RequestType.UPDATE_USER, user_id=U32(1))
    unhandled_response = router.process_request(unhandled_request)
    assert bool(unhandled_response.success) is False
    assert unhandled_response.error_message
    assert "No handler" in str(unhandled_response.error_message.unwrap())
    
    # Test encoding for all request/response pairs
    requests = [list_request, get_request, missing_user_request, unhandled_request]
    responses = [list_response, get_response, missing_response, unhandled_response]
    
    for req, resp in zip(requests, responses):
        # Test request encoding
        req_encoded = req.encode()
        req_decoded = RequestMessage.decode(req_encoded)
        assert req.request_id == req_decoded.request_id
        assert req.request_type == req_decoded.request_type
        
        # Test response encoding
        resp_encoded = resp.encode()
        resp_decoded = ResponseMessage.decode(resp_encoded)
        assert resp.request_id == resp_decoded.request_id
        assert bool(resp.success) == bool(resp_decoded.success)


def test_binary_protocol_comparison():
    """Test binary protocol efficiency compared to JSON."""
    @structure
    class SensorReading:
        sensor_id: U32
        timestamp: U64
        temperature: U32  # Temperature * 100 (to avoid floats)
        humidity: U16     # Humidity * 100
        pressure: U32     # Pressure in pascals
        battery_level: U8 # Battery percentage
    
    @structure
    class SensorBatch:
        device_id: String
        readings: TypedVector[SensorReading]
        checksum: U32
    
    # Create sample data
    current_time = int(time.time())
    
    readings = []
    for i in range(10):  # 10 sensor readings
        reading = SensorReading(
            sensor_id=U32(i + 1),
            timestamp=U64(current_time + i * 60),  # 1 minute intervals
            temperature=U32(2350 + i * 10),  # 23.50°C to 24.40°C
            humidity=U16(4500 + i * 50),     # 45.00% to 49.50%
            pressure=U32(101325 + i * 100), # ~1 atmosphere
            battery_level=U8(95 - i)         # Declining battery
        )
        readings.append(reading)
    
    batch = SensorBatch(
        device_id=String("SENSOR_STATION_001"),
        readings=TypedVector[SensorReading](readings),
        checksum=U32(0xDEADBEEF)  # Mock checksum
    )
    
    # Test basic properties
    assert str(batch.device_id) == "SENSOR_STATION_001"
    assert len(batch.readings) == 10
    assert batch.checksum == 0xDEADBEEF
    
    # Test individual readings
    first_reading = batch.readings[0]
    assert first_reading.sensor_id == 1
    assert first_reading.temperature == 2350  # 23.50°C * 100
    assert first_reading.humidity == 4500     # 45.00% * 100
    assert first_reading.battery_level == 95
    
    last_reading = batch.readings[9]
    assert last_reading.sensor_id == 10
    assert last_reading.temperature == 2440  # 24.40°C * 100
    assert last_reading.battery_level == 86
    
    # Binary encoding
    binary_data = batch.encode()
    assert len(binary_data) > 0
    
    # Test round-trip
    decoded_batch = SensorBatch.decode(binary_data)
    assert str(decoded_batch.device_id) == str(batch.device_id)
    assert len(decoded_batch.readings) == len(batch.readings)
    assert decoded_batch.checksum == batch.checksum
    
    # Verify first and last readings are preserved
    decoded_first = decoded_batch.readings[0]
    decoded_last = decoded_batch.readings[9]
    
    assert decoded_first.sensor_id == first_reading.sensor_id
    assert decoded_first.temperature == first_reading.temperature
    assert decoded_last.sensor_id == last_reading.sensor_id
    assert decoded_last.battery_level == last_reading.battery_level
    
    # JSON encoding for comparison
    json_data = batch.to_json()
    import json
    json_bytes = json.dumps(json_data).encode('utf-8')
    
    # Verify JSON is larger (binary should be more efficient)
    assert len(binary_data) < len(json_bytes)
    
    # Calculate space savings
    space_savings = ((len(json_bytes) - len(binary_data)) / len(json_bytes)) * 100
    assert space_savings > 0  # Binary should save some space


def test_network_message_types():
    """Test various network message type patterns."""
    # Message union type
    class MessageType(Enum):
        PING = 1
        PONG = 2
        DATA_TRANSFER = 3
        FILE_REQUEST = 4
        FILE_RESPONSE = 5
    
    @structure
    class BaseMessage:
        msg_type: MessageType
        sequence: U32
        timestamp: U64
    
    @structure
    class PingMessage:
        base: BaseMessage
        payload_size: U16 = field(metadata={"default": U16(0)})
    
    @structure
    class PongMessage:
        base: BaseMessage
        original_sequence: U32
        latency_ms: U16
    
    @structure
    class DataTransferMessage:
        base: BaseMessage
        chunk_id: U32
        total_chunks: U32
        data: Bytes
    
    # Create various message types
    current_time = int(time.time() * 1000)
    
    ping = PingMessage(
        base=BaseMessage(
            msg_type=MessageType.PING,
            sequence=U32(1),
            timestamp=U64(current_time)
        ),
        payload_size=U16(64)
    )
    
    pong = PongMessage(
        base=BaseMessage(
            msg_type=MessageType.PONG,
            sequence=U32(2),
            timestamp=U64(current_time + 100)
        ),
        original_sequence=U32(1),
        latency_ms=U16(50)
    )
    
    data_transfer = DataTransferMessage(
        base=BaseMessage(
            msg_type=MessageType.DATA_TRANSFER,
            sequence=U32(3),
            timestamp=U64(current_time + 200)
        ),
        chunk_id=U32(1),
        total_chunks=U32(10),
        data=Bytes(b"This is chunk 1 of 10")
    )
    
    messages = [ping, pong, data_transfer]
    
    # Test all messages
    for msg in messages:
        # Verify base message properties
        assert msg.base.msg_type in [MessageType.PING, MessageType.PONG, MessageType.DATA_TRANSFER]
        assert msg.base.sequence > 0
        assert msg.base.timestamp > 0
        
        # Test encoding/decoding
        encoded = msg.encode()
        decoded = type(msg).decode(encoded)
        
        assert decoded.base.msg_type == msg.base.msg_type
        assert decoded.base.sequence == msg.base.sequence
        assert decoded.base.timestamp == msg.base.timestamp
    
    # Test specific message properties
    assert ping.payload_size == 64
    assert pong.original_sequence == 1
    assert pong.latency_ms == 50
    assert data_transfer.chunk_id == 1
    assert data_transfer.total_chunks == 10
    assert len(data_transfer.data) > 0


def test_complex_protocol_state():
    """Test complex protocol state management."""
    class ConnectionState(Enum):
        DISCONNECTED = 0
        CONNECTING = 1
        CONNECTED = 2
        AUTHENTICATED = 3
        DISCONNECTING = 4
    
    class MessageType(Enum):
        CONNECT = 1
        AUTH = 2
        DATA = 3
        DISCONNECT = 4
        STATUS = 5
    
    @structure
    class ProtocolState:
        connection_state: ConnectionState
        session_id: Option[String]
        last_message_id: U32
        bytes_sent: U64
        bytes_received: U64
    
    @structure
    class ProtocolMessage:
        message_type: MessageType
        message_id: U32
        session_id: Option[String]
        payload: Bytes
        state: ProtocolState
    
    # Create initial state
    initial_state = ProtocolState(
        connection_state=ConnectionState.DISCONNECTED,
        session_id=Option[String](),
        last_message_id=U32(0),
        bytes_sent=U64(0),
        bytes_received=U64(0)
    )
    
    # Test state transitions through messages
    states = []
    
    # 1. Connect message
    connect_state = ProtocolState(
        connection_state=ConnectionState.CONNECTING,
        session_id=Option[String](String("session_123")),
        last_message_id=U32(1),
        bytes_sent=U64(100),
        bytes_received=U64(50)
    )
    
    connect_msg = ProtocolMessage(
        message_type=MessageType.CONNECT,
        message_id=U32(1),
        session_id=Option[String](String("session_123")),
        payload=Bytes(b"CONNECT request"),
        state=connect_state
    )
    states.append(connect_state)
    
    # 2. Auth message
    auth_state = ProtocolState(
        connection_state=ConnectionState.AUTHENTICATED,
        session_id=Option[String](String("session_123")),
        last_message_id=U32(2),
        bytes_sent=U64(250),
        bytes_received=U64(180)
    )
    
    auth_msg = ProtocolMessage(
        message_type=MessageType.AUTH,
        message_id=U32(2),
        session_id=Option[String](String("session_123")),
        payload=Bytes(b"AUTH credentials"),
        state=auth_state
    )
    states.append(auth_state)
    
    # Test all states and messages
    messages = [connect_msg, auth_msg]
    
    for msg, state in zip(messages, states):
        # Test message properties
        assert msg.message_type in [MessageType.CONNECT, MessageType.AUTH]
        assert msg.message_id > 0
        assert msg.session_id
        assert str(msg.session_id.unwrap()) == "session_123"
        
        # Test state properties
        assert state.connection_state in [ConnectionState.CONNECTING, ConnectionState.AUTHENTICATED]
        assert state.session_id
        assert state.last_message_id > 0
        assert state.bytes_sent > 0
        assert state.bytes_received > 0
        
        # Test encoding/decoding
        encoded = msg.encode()
        decoded = ProtocolMessage.decode(encoded)
        
        assert decoded.message_type == msg.message_type
        assert decoded.message_id == msg.message_id
        assert bool(decoded.session_id) == bool(msg.session_id)
        assert decoded.state.connection_state == msg.state.connection_state
    
    # Verify state progression
    assert states[0].connection_state == ConnectionState.CONNECTING
    assert states[1].connection_state == ConnectionState.AUTHENTICATED
    assert states[1].bytes_sent > states[0].bytes_sent
    assert states[1].bytes_received > states[0].bytes_received 