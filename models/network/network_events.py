from enum import Enum
from dataclasses import dataclass
from typing import Dict, Optional

class NetworkCallType(Enum):
    """Enum for different types of network calls"""
    SHARE_FOLDER_STRUCTURE = "share_folder_structure"
    SHARE_BOOKMARKS = "share_bookmarks"
    SYNC_FOLDER_STRUCTURE = "sync_folder_structure"
    SYNC_BOOKMARKS = "sync_bookmarks"

class NetworkConnectionStatusType(Enum):
    """Enum for different network connection status types"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    DISCOVERED = "discovered"
    ERROR = "error"

    def is_connected(self) -> bool:
        """Check if this status type represents a connected state"""
        return self == NetworkConnectionStatusType.CONNECTED

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
    service_info: Optional[Dict[str, str]] = None
    error_message: Optional[str] = None
    status_type: NetworkConnectionStatusType = NetworkConnectionStatusType.DISCONNECTED 