import time
from typing import Dict, Any

from .base import BaseProcess


class EventListenerProcess(BaseProcess):
    """Process that generates and publishes events."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.event_counter = 0
    
    def generate_event(self) -> Dict[str, Any]:
        """Generate a new event."""
        self.event_counter += 1
        return {
            'event_id': self.event_counter,
            'type': 'sensor_reading',
            'value': self.event_counter * 10,
            'timestamp': time.time(),
            'source': self.name
        }
    
    def publish_event(self, event_data: Dict[str, Any]):
        """Publish event to Redis."""
        # Publish to events channel
        # self.redis_client.publish('events', event_data)
        
        # Store latest event
        # self.redis_client.set('latest_event', event_data)
        
        self.logger.info(f"Published event {event_data['event_id']}: {event_data['value']}")
    
    def run(self):
        """Main event listener loop."""
        while self.running:
            try:
                # Generate and publish event
                event_data = self.generate_event()
                self.publish_event(event_data)
                
                # Wait before next event
                time.sleep(2)
                
            except Exception as e:
                self.logger.error(f"Error generating event: {e}")
                time.sleep(1)


def main():
    """Entry point for running as module."""
    process = EventListenerProcess(name="event_listener")
    process.start()


if __name__ == "__main__":
    main()