"""Base process class for all supervisor processes."""

import logging
import time

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from finetune.config import Config
from finetune.utils.logging import setup_logging
from finetune.utils.redis_client import RedisClient
from finetune.utils.signals import SignalHandler


class BaseProcess(ABC):
    """Base class for all processes."""

    def __init__(self, config: Config = None, name: str = None):
        self.config = config or Config()
        self.name = name or self.__class__.__name__
        self.logger = logging.getLogger(self.name)
        self.running = True
        
        # Setup logging
        setup_logging(self.name, log_dir=Path(self.config.log_dir))
        
        # DON'T connect to Redis in __init__, do it lazily
        self._redis_client = None
        
        # Setup signal handling
        self.signal_handler = SignalHandler(self._shutdown)
    
    @property
    def redis_client(self):
        """Lazy Redis client initialization."""
        if self._redis_client is None:
            try:
                self._redis_client = RedisClient(self.config.redis)
            except Exception as e:
                self.logger.error(f"Failed to connect to Redis: {e}")
                # Return a mock client or handle gracefully
                raise
        return self._redis_client 
        
    def _shutdown(self, signum: int, frame: Any):
        """Handle shutdown signals."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    @abstractmethod
    def run(self):
        """Main process logic - must be implemented by subclasses."""
        pass
    
    def start(self):
        """Start the process."""
        try:
            self.logger.info(f"{self.name} starting...")
            self.run()
        except KeyboardInterrupt:
            self.logger.info("Process interrupted")
        except Exception as e:
            self.logger.error(f"Process failed: {e}")
            raise
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup resources."""
        self.logger.info(f"{self.name} shutting down")
        if hasattr(self, 'redis_client'):
            self.redis_client.close()