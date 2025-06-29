import signal
from typing import Callable, Any


class SignalHandler:
    """Handle process signals gracefully."""
    
    def __init__(self, shutdown_callback: Callable[[int, Any], None]):
        """Initialize signal handler.
        
        Args:
            shutdown_callback: Function to call when shutdown signal received
        """
        self.shutdown_callback = shutdown_callback
        self.setup_signals()
    
    def setup_signals(self):
        """Setup signal handlers."""
        # Handle termination signals
        signal.signal(signal.SIGTERM, self.shutdown_callback)
        signal.signal(signal.SIGINT, self.shutdown_callback)
        
        # Handle SIGHUP for configuration reload (Unix only)
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, self._handle_reload)
    
    def _handle_reload(self, signum: int, frame: Any):
        """Handle reload signal (SIGHUP)."""
        # For now, just log it. In a real implementation,
        # this could trigger configuration reload
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Received SIGHUP signal (reload requested)")
    
    @staticmethod
    def ignore_signals():
        """Ignore common signals (useful for cleanup operations)."""
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
    
    @staticmethod
    def restore_default_signals():
        """Restore default signal handlers."""
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, signal.SIG_DFL)