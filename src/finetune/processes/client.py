import time
from typing import Dict, Any

from .base import BaseProcess


class ClientProcess(BaseProcess):
    """Process that consumes events and sends commands."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pubsub = None
    
    def setup_subscriptions(self):
        """Setup Redis subscriptions."""
        self.pubsub = self.redis_client.get_pubsub()
        self.pubsub.subscribe(['events', 'commands'])
        self.logger.info("Subscribed to events and commands channels")
    
    def process_event(self, event_data: Dict[str, Any]):
        """Process incoming events."""
        print(f"event_data: {event_data}")
        event_id = event_data.get('event_id')
        value = event_data.get('value', 0)
        
        self.logger.info(f"Processing event {event_id} with value {value}")
        
        # Send alert command if value is high
        if value > 50:
            command = {
                'type': 'alert',
                'message': f'High value detected: {value}',
                'event_id': event_id,
                'source': self.name
            }
            self.redis_client.publish('commands', command)
            self.logger.info(f"Sent alert command for event {event_id}")
    
    def process_message(self, message: Dict[str, Any]):
        """Process incoming Redis message."""
        channel = message.get('channel')
        data = message.get('data')
        
        if not data:
            return
            
        if channel == 'events':
            self.process_event(data)
        elif channel == 'commands':
            self.logger.info(f"Received command: {data}")
    
    def run(self):
        """Main client loop."""
        self.setup_subscriptions()
        
        while self.running:
            try:
                # Get message with timeout
                message = self.pubsub.get_message(timeout=1.0)
                
                if message and message['type'] == 'message':
                    self.process_message(message)
                
            except Exception as e:
                self.logger.error(f"Error processing message: {e}")
                time.sleep(1)
    
    def cleanup(self):
        """Cleanup resources."""
        if self.pubsub:
            self.pubsub.close()
        super().cleanup()


def main():
    """Entry point for running as module."""
    process = ClientProcess(name="client")
    process.start()


if __name__ == "__main__":
    main()