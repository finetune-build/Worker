import time
from datetime import datetime
from typing import Dict, Any

from .base import BaseProcess


class ServerProcess(BaseProcess):
    """Process that handles commands and maintains state."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.alert_count = 0
        self.pubsub = None
    
    def setup_subscriptions(self):
        """Setup Redis subscriptions."""
        self.pubsub = self.redis_client.get_pubsub()
        self.pubsub.subscribe(['commands'])
        self.logger.info("Subscribed to commands channel")
    
    def handle_alert(self, command_data: Dict[str, Any]):
        """Handle alert commands."""
        self.alert_count += 1
        message = command_data.get('message')
        event_id = command_data.get('event_id')
        
        self.logger.warning(f"ALERT #{self.alert_count}: {message} (Event ID: {event_id})")
        
        # Store alert record
        alert_record = {
            'alert_id': self.alert_count,
            'message': message,
            'event_id': event_id,
            'timestamp': datetime.now().isoformat(),
            'status': 'active'
        }
        
        self.redis_client.lpush('alerts', alert_record)
        
        # Publish response
        response = {
            'type': 'alert_response',
            'alert_id': self.alert_count,
            'status': 'processed',
            'source': self.name
        }
        self.redis_client.publish('responses', response)
    
    def process_command(self, command_data: Dict[str, Any]):
        """Process incoming commands."""
        command_type = command_data.get('type')
        
        if command_type == 'alert':
            self.handle_alert(command_data)
        else:
            self.logger.info(f"Unknown command type: {command_type}")
    
    def send_heartbeat(self):
        """Send periodic status updates."""
        status = {
            'type': 'heartbeat',
            'status': 'running',
            'alerts_processed': self.alert_count,
            'timestamp': datetime.now().isoformat(),
            'source': self.name
        }
        
        self.redis_client.set('server_status', status)
        self.redis_client.publish('status', status)
    
    def run(self):
        """Main server loop."""
        self.setup_subscriptions()
        last_heartbeat = time.time()
        
        while self.running:
            try:
                # Process commands
                message = self.pubsub.get_message(timeout=1.0)
                
                if message and message['type'] == 'message':
                    data = message.get('data')
                    if data:
                        self.process_command(data)
                
                # Send heartbeat every 5 seconds
                if time.time() - last_heartbeat > 5:
                    self.send_heartbeat()
                    last_heartbeat = time.time()
                
            except Exception as e:
                self.logger.error(f"Error in server loop: {e}")
                time.sleep(1)
    
    def cleanup(self):
        """Cleanup resources."""
        if self.pubsub:
            self.pubsub.close()
        super().cleanup()


def main():
    """Entry point for running as module."""
    process = ServerProcess(name="server")
    process.start()


if __name__ == "__main__":
    main()
