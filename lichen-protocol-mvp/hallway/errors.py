"""
Typed exception hierarchy for clean error handling and recovery.
"""


class HallwayError(Exception):
    """Base exception for all hallway-related errors."""

    def __init__(self, message: str, recoverable: bool = False):
        super().__init__(message)
        self.message = message
        self.recoverable = recoverable


class GateError(HallwayError):
    """Error during gate evaluation."""

    def __init__(self, reason: str, gate_name: str = "", recoverable: bool = True):
        super().__init__(f"Gate error: {reason}", recoverable)
        self.reason = reason
        self.gate_name = gate_name


class RoomError(HallwayError):
    """Error during room execution."""

    def __init__(self, reason: str, room_id: str = "", recoverable: bool = False):
        super().__init__(f"Room error: {reason}", recoverable)
        self.reason = reason
        self.room_id = room_id


class ValidationError(HallwayError):
    """Schema validation error."""

    def __init__(self, reason: str, schema_name: str = "", recoverable: bool = False):
        super().__init__(f"Validation error: {reason}", recoverable)
        self.reason = reason
        self.schema_name = schema_name


class BudgetExceededError(HallwayError):
    """Budget limit exceeded error."""

    def __init__(self, budget_type: str, limit: float, used: float):
        super().__init__(f"Budget exceeded: {budget_type} limit {limit}, used {used}", recoverable=False)
        self.budget_type = budget_type
        self.limit = limit
        self.used = used


class PortError(HallwayError):
    """Error from an external port/adapter."""

    def __init__(self, reason: str, port_name: str = "", recoverable: bool = True):
        super().__init__(f"Port error: {reason}", recoverable)
        self.reason = reason
        self.port_name = port_name
