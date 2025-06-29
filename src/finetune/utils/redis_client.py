# finetune/utils/redis_client.py

import json
import logging
import time
from typing import Any, Dict, List, Optional

import redis
from redis.exceptions import ConnectionError, RedisError

from finetune.config import RedisConfig
from finetune.exceptions import RedisConnectionError


class RedisClient:
    """Enhanced Redis client with JSON serialization, error handling, and retry logic."""
    
    def __init__(self, config: RedisConfig, max_retries: int = 3, retry_delay: float = 1.0):
        self.config = config
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = logging.getLogger(self.__class__.__name__)
        self._client = None
        self._pubsub = None
        self._connect()
    
    def _connect(self):
        """Establish Redis connection with retry logic."""
        self.connect_with_retry(self.max_retries, self.retry_delay)
    
    def connect_with_retry(self, max_retries: int = 3, retry_delay: float = 1.0):
        """Connect to Redis with retry logic."""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                self._client = redis.Redis(
                    host=self.config.host,
                    port=self.config.port,
                    db=self.config.db,
                    password=self.config.password,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True
                )
                
                # Test connection
                self._client.ping()
                self.logger.info(f"Connected to Redis at {self.config.host}:{self.config.port} (attempt {attempt + 1})")
                return True
                
            except (ConnectionError, RedisError) as e:
                last_error = e
                self.logger.warning(f"Redis connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
        
        raise RedisConnectionError(f"Failed to connect to Redis after {max_retries} attempts: {last_error}")
    
    def _serialize(self, data: Any) -> str:
        """Serialize data to JSON string."""
        try:
            return json.dumps(data, default=str)
        except (TypeError, ValueError) as e:
            self.logger.error(f"Failed to serialize data: {e}")
            raise
    
    def _deserialize(self, data: str) -> Any:
        """Deserialize JSON string to Python object."""
        if data is None:
            return None
        try:
            return json.loads(data)
        except (TypeError, ValueError) as e:
            self.logger.error(f"Failed to deserialize data: {e}")
            return data  # Return raw string if JSON parsing fails
    
    def safe_redis_operation(self, operation, *args, **kwargs):
        """Safely execute Redis operations with error handling and auto-reconnect."""
        try:
            return operation(*args, **kwargs)
        except (ConnectionError, RedisError) as e:
            self.logger.error(f"Redis operation failed: {e}")
            # Try to reconnect
            try:
                self.logger.info("Attempting to reconnect to Redis...")
                self._connect()
                return operation(*args, **kwargs)
            except Exception as reconnect_error:
                self.logger.error(f"Redis reconnection failed: {reconnect_error}")
                return None
        except Exception as e:
            self.logger.error(f"Unexpected error in Redis operation: {e}")
            return None
    
    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Set a key-value pair with optional expiration."""
        def _set_operation():
            serialized_value = self._serialize(value)
            return self._client.set(key, serialized_value, ex=ex)
        
        result = self.safe_redis_operation(_set_operation)
        if result is None:
            self.logger.error(f"Failed to set key '{key}'")
            return False
        return result
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value by key with JSON deserialization."""
        def _get_operation():
            value = self._client.get(key)
            return self._deserialize(value) if value is not None else default
        
        result = self.safe_redis_operation(_get_operation)
        return result if result is not None else default
    
    def delete(self, *keys: str) -> int:
        """Delete one or more keys."""
        def _delete_operation():
            return self._client.delete(*keys)
        
        result = self.safe_redis_operation(_delete_operation)
        return result if result is not None else 0
    
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        def _exists_operation():
            return bool(self._client.exists(key))
        
        result = self.safe_redis_operation(_exists_operation)
        return result if result is not None else False
    
    def publish(self, channel: str, message: Any) -> int:
        """Publish message to channel."""
        def _publish_operation():
            serialized_message = self._serialize(message)
            return self._client.publish(channel, serialized_message)
        
        result = self.safe_redis_operation(_publish_operation)
        return result if result is not None else 0
    
    def get_pubsub(self) -> 'PubSubWrapper':
        """Get a pubsub instance."""
        if self._pubsub is None:
            self._pubsub = PubSubWrapper(self._client.pubsub(), self.logger)
        return self._pubsub
    
    def lpush(self, key: str, *values: Any) -> int:
        """Push values to the left of a list."""
        def _lpush_operation():
            serialized_values = [self._serialize(v) for v in values]
            return self._client.lpush(key, *serialized_values)
        
        result = self.safe_redis_operation(_lpush_operation)
        return result if result is not None else 0
    
    def lrange(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        """Get range of values from a list."""
        def _lrange_operation():
            values = self._client.lrange(key, start, end)
            return [self._deserialize(v) for v in values]
        
        result = self.safe_redis_operation(_lrange_operation)
        return result if result is not None else []
    
    def ping(self) -> bool:
        """Test Redis connection."""
        def _ping_operation():
            return self._client.ping()
        
        result = self.safe_redis_operation(_ping_operation)
        return result if result is not None else False
    
    def info(self, section: Optional[str] = None) -> Dict[str, Any]:
        """Get Redis server information."""
        def _info_operation():
            return self._client.info(section) if section else self._client.info()
        
        result = self.safe_redis_operation(_info_operation)
        return result if result is not None else {}
    
    def flushdb(self) -> bool:
        """Clear all keys in the current database."""
        def _flushdb_operation():
            return self._client.flushdb()
        
        result = self.safe_redis_operation(_flushdb_operation)
        return result if result is not None else False
    
    def keys(self, pattern: str = "*") -> List[str]:
        """Get all keys matching a pattern."""
        def _keys_operation():
            return self._client.keys(pattern)
        
        result = self.safe_redis_operation(_keys_operation)
        return result if result is not None else []
    
    def close(self):
        """Close Redis connections."""
        try:
            if self._pubsub:
                self._pubsub.close()
            if self._client:
                self._client.close()
            self.logger.info("Redis connections closed")
        except Exception as e:
            self.logger.error(f"Error closing Redis connections: {e}")


class PubSubWrapper:
    """Wrapper for Redis pubsub with JSON deserialization and error handling."""
    
    def __init__(self, pubsub: redis.client.PubSub, logger: logging.Logger):
        self.pubsub = pubsub
        self.logger = logger

    def subscribe(self, *channels: str):
        """Subscribe to channels."""
        try:
            # Flatten the channels if a list is passed
            flat_channels = []
            for channel in channels:
                if isinstance(channel, list):
                    flat_channels.extend(channel)
                else:
                    flat_channels.append(channel)

            self.pubsub.subscribe(*flat_channels)
            self.logger.info(f"Subscribed to channels: {', '.join(flat_channels)}")
        except RedisError as e:
            self.logger.error(f"Failed to subscribe to channels: {e}")
    
    def unsubscribe(self, *channels: str):
        """Unsubscribe from channels."""
        try:
            self.pubsub.unsubscribe(*channels)
            self.logger.info(f"Unsubscribed from channels: {', '.join(channels)}")
        except RedisError as e:
            self.logger.error(f"Failed to unsubscribe from channels: {e}")
    
    def get_message(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Get message with JSON deserialization."""
        try:
            message = self.pubsub.get_message(timeout=timeout)
            
            if message and message['type'] == 'message':
                # Deserialize the data field
                try:
                    message['data'] = json.loads(message['data'])
                except (TypeError, ValueError):
                    # Keep original data if not JSON
                    pass
            
            return message
        except RedisError as e:
            self.logger.error(f"Failed to get message: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error getting message: {e}")
            return None
    
    def listen(self):
        """Listen for messages (generator)."""
        try:
            for message in self.pubsub.listen():
                if message['type'] == 'message':
                    try:
                        message['data'] = json.loads(message['data'])
                    except (TypeError, ValueError):
                        pass
                yield message
        except RedisError as e:
            self.logger.error(f"Error listening for messages: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error listening: {e}")
    
    def close(self):
        """Close pubsub connection."""
        try:
            self.pubsub.close()
            self.logger.info("PubSub connection closed")
        except RedisError as e:
            self.logger.error(f"Error closing pubsub: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error closing pubsub: {e}")


# Context manager for Redis operations
class RedisContext:
    """Context manager for Redis operations with automatic cleanup."""
    
    def __init__(self, config: RedisConfig):
        self.config = config
        self.client = None
    
    def __enter__(self) -> RedisClient:
        self.client = RedisClient(self.config)
        return self.client
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            self.client.close()


# Utility function for quick Redis operations
def with_redis(config: RedisConfig, operation):
    """Execute a Redis operation with automatic connection management."""
    with RedisContext(config) as client:
        return operation(client)
