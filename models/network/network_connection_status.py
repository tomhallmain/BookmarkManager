from dataclasses import dataclass, asdict
from typing import Optional, Dict, List
from models.network.network_events import ServiceDiscoveredEvent, ConnectionStatusEvent, NetworkConnectionStatusType
import json
from datetime import datetime

@dataclass
class NetworkConnectionStatus:
    """Manages the state of network connections and services"""
    
    connected_service: Optional[Dict] = None
    last_status_message: str = "Not connected"
    last_discovered_service: Optional[Dict] = None
    status_type: NetworkConnectionStatusType = NetworkConnectionStatusType.DISCONNECTED
    service_history: Dict[str, Dict] = None  # service_address -> {status, timestamp, service_info}
    MAX_HISTORY_SIZE: int = 50
    
    def __post_init__(self):
        if self.service_history is None:
            self.service_history = {}
    
    @property
    def is_connected(self) -> bool:
        """Check if currently connected to a service"""
        return self.status_type.is_connected()
    
    def update_from_event(self, event: ConnectionStatusEvent):
        """Update status from a connection status event"""
        self.status_type = event.status_type
        
        if event.status_type == NetworkConnectionStatusType.CONNECTED:
            self.connected_service = event.service_info
            self.last_status_message = f"Connected to {event.service_info['name']} at {event.service_info['address']}"
            self._update_service_history(event.service_info['address'], event)
        elif event.status_type == NetworkConnectionStatusType.ERROR:
            self.connected_service = None
            self.last_status_message = event.error_message if event.error_message else "Connection error"
            if event.service_info:
                self._update_service_history(event.service_info['address'], event)
        else:  # DISCONNECTED
            self.connected_service = None
            self.last_status_message = "Not connected"
            if event.service_info:
                self._update_service_history(event.service_info['address'], event)
            
    def update_from_service_discovery(self, event: ServiceDiscoveredEvent):
        """Update status from a service discovery event"""
        service_info = {
            'name': event.name,
            'address': event.address,
            'port': event.port,
            'properties': event.properties
        }
        self.last_discovered_service = service_info
        self.status_type = NetworkConnectionStatusType.DISCOVERED
        self.last_status_message = f"Discovered service: {event.name} at {event.address}"
        self._update_service_history(f"{event.address}:{event.port}", ConnectionStatusEvent(
            service_info=service_info,
            status_type=NetworkConnectionStatusType.DISCOVERED
        ))
        
    def _update_service_history(self, service_address: str, event: ConnectionStatusEvent):
        """Update the service history with a new status event"""
        if len(self.service_history) >= self.MAX_HISTORY_SIZE and service_address not in self.service_history:
            # Remove oldest entry if we're at capacity
            oldest_timestamp = min(entry['timestamp'] for entry in self.service_history.values())
            for addr, entry in list(self.service_history.items()):
                if entry['timestamp'] == oldest_timestamp:
                    del self.service_history[addr]
                    break
        
        self.service_history[service_address] = {
            'status_type': event.status_type.value,
            'timestamp': datetime.now().isoformat(),
            'service_info': event.service_info,
            'error_message': event.error_message
        }
        
    def get_status_message(self) -> str:
        """Get the current status message"""
        return self.last_status_message
        
    def is_status_type(self, status_type: NetworkConnectionStatusType) -> bool:
        """Check if the current status matches the given type"""
        return self.status_type == status_type
        
    def get_service_history(self) -> List[Dict]:
        """Get the service history as a list of entries sorted by timestamp"""
        return sorted(
            self.service_history.values(),
            key=lambda x: x['timestamp'],
            reverse=True
        )
        
    def to_dict(self) -> Dict:
        """Convert the status to a dictionary for serialization"""
        return {
            'connected_service': self.connected_service,
            'last_status_message': self.last_status_message,
            'last_discovered_service': self.last_discovered_service,
            'status_type': self.status_type.value,
            'service_history': self.service_history
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'NetworkConnectionStatus':
        """Create a status from a dictionary"""
        return cls(
            connected_service=data.get('connected_service'),
            last_status_message=data.get('last_status_message', "Not connected"),
            last_discovered_service=data.get('last_discovered_service'),
            status_type=NetworkConnectionStatusType(data.get('status_type', NetworkConnectionStatusType.DISCONNECTED.value)),
            service_history=data.get('service_history', {})
        )
        
    def save_to_file(self, file_path: str):
        """Save the status to a file"""
        with open(file_path, 'w') as f:
            json.dump(self.to_dict(), f)
            
    @classmethod
    def load_from_file(cls, file_path: str) -> 'NetworkConnectionStatus':
        """Load a status from a file"""
        with open(file_path, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data) 