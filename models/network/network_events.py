from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class ServiceDiscoveredEvent:
    """Event representing a discovered network service"""
    name: str
    address: str
    port: int
    properties: Dict[str, str]

@dataclass
class ConnectionStatusEvent:
    """Event representing a change in connection status"""
    is_connected: bool
    service_info: Optional[Dict[str, str]] = None
    error_message: Optional[str] = None 