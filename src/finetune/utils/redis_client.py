import json
import logging
from typing import Any, Dict, List, Optional

import redis
from redis.exceptions import ConnectionError, RedisError

from finetune.config import RedisConfig
from finetune.exceptions import RedisConnectionError


class RedisClient:
    """Enhanced Redis client with JSON serialization and error handling."""
    
    def __init__(self, config: RedisConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self._client = None
        self._pubsub = None
        self._connect()
    
    def _connect(self):
        """Establish Redis connection."""
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
            self.logger.info(f"Connected to Redis at {self.config.host}:{self.config.port}")
            
        except ConnectionError as e:
            raise RedisConnectionError(f"Failed to connect to Redis: {e}")
    
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
    
    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Set a key-value pair with optional expiration."""
        try:
            serialized_value = self._serialize(value)
            return self._client.set(key, serialized_value, ex=ex)
        except RedisError as e:
            self.logger.error(f"Failed to set key '{key}': {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value by key with JSON deserialization."""
        try:
            value = self._client.get(key)
            return self._deserialize(value) if value is not None else default
        except RedisError as e:
            self.logger.error(f"Failed to get key '{key}': {e}")
            return default
    
    def delete(self, *keys: str) -> int:
        """Delete one or more keys."""
        try:
            return self._client.delete(*keys)
        except RedisError as e:
            self.logger.error(f"Failed to delete keys {keys}: {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            return bool(self._client.exists(key))
        except RedisError as e:
            self.logger.error(f"Failed to check existence of key '{key}': {e}")
            return False
    
    def publish(self, channel: str, message: Any) -> int:
        """Publish message to channel."""
        try:
            serialized_message = self._serialize(message)
            return self._client.publish(channel, serialized_message)
        except RedisError as e:
            self.logger.error(f"Failed to publish to channel '{channel}': {e}")
            return 0
    
    def get_pubsub(self) -> 'PubSubWrapper':
        """Get a pubsub instance."""
        if self._pubsub is None:
            self._pubsub = PubSubWrapper(self._client.pubsub(), self.logger)
        return self._pubsub
    
    def lpush(self, key: str, *values: Any) -> int:
        """Push values to the left of a list."""
        try:
            serialized_values = [self._serialize(v) for v in values]
            return self._client.lpush(key, *serialized_values)
        except RedisError as e:
            self.logger.error(f"Failed to lpush to key '{key}': {e}")
            return 0
    
    def lrange(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        """Get range of values from a list."""
        try:
            values = self._client.lrange(key, start, end)
            return [self._deserialize(v) for v in values]
        except RedisError as e:
            self.logger.error(f"Failed to lrange key '{key}': {e}")
            return []
    
    def close(self):
        """Close Redis connections."""
        if self._pubsub:
            self._pubsub.close()
        if self._client:
            self._client.close()
        self.logger.info("Redis connections closed")


class PubSubWrapper:
    """Wrapper for Redis pubsub with JSON deserialization."""
    
    def __init__(self, pubsub: redis.client.PubSub, logger: logging.Logger):
        self.pubsub = pubsub
        self.logger = logger
    
    def subscribe(self, *channels: str):
        """Subscribe to channels."""
        try:
            self.pubsub.subscribe(*channels)
            self.logger.info(f"Subscribed to channels: {', '.join(channels)}")
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
    
    def close(self):
        """Close pubsub connection."""
        try:
            self.pubsub.close()
            self.logger.info("PubSub connection closed")
        except RedisError as e:
            self.logger.error(f"Error closing pubsub: {e}")
