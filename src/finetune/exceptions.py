class SupervisorAppError(Exception):
    """Base exception for supervisor app errors."""
    pass


class ProcessError(SupervisorAppError):
    """Exception raised for process-related errors."""
    pass


class ConfigurationError(SupervisorAppError):
    """Exception raised for configuration errors."""
    pass


class RedisConnectionError(SupervisorAppError):
    """Exception raised for Redis connection errors."""
    pass


class SupervisorError(SupervisorAppError):
    """Exception raised for supervisor daemon errors."""
    pass
