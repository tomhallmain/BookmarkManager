from dataclasses import dataclass
from typing import Optional, Dict
from models.network.network_events import ServiceDiscoveredEvent, ConnectionStatusEvent

@dataclass
class NetworkConnectionStatus:
    """Manages the state of network connections and services"""
    
    is_connected: bool = False
    connected_service: Optional[Dict] = None
    last_status_message: str = "Not connected"
    last_discovered_service: Optional[Dict] = None
    
    def update_from_event(self, event: ConnectionStatusEvent):
        """Update status from a connection status event"""
        self.is_connected = event.is_connected
        if event.is_connected:
            self.connected_service = event.service_info
            self.last_status_message = f"Connected to {event.service_info['name']} at {event.service_info['address']}"
        else:
            self.connected_service = None
            self.last_status_message = event.error_message if event.error_message else "Not connected"
            
    def update_from_service_discovery(self, event: ServiceDiscoveredEvent):
        """Update status from a service discovery event"""
        self.last_discovered_service = {
            'name': event.name,
            'address': event.address,
            'port': event.port,
            'properties': event.properties
        }
        self.last_status_message = f"Discovered service: {event.name} at {event.address}"
        
    def get_status_message(self) -> str:
        """Get the current status message"""
        return self.last_status_message 