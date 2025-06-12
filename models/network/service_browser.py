from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
import asyncio

from zeroconf import ServiceBrowser, Zeroconf, ServiceListener, ServiceInfo
import socket
# from nacl.public import PublicKey
# from nacl.encoding import Base64Encoder

from utils.logger import logger
from models.network.network_events import ServiceDiscoveredEvent


class NetworkServiceListener(ServiceListener):
    def __init__(self, discovery_handler: Callable[[ServiceDiscoveredEvent], None]):
        self.services: Dict[str, Dict] = {}
        self.last_seen: Dict[str, datetime] = {}  # name -> last seen timestamp
        self.stale_threshold = timedelta(minutes=5)
        self.discovery_handler = discovery_handler

    def add_service(self, zeroconf, type, name):
        try:
            info = zeroconf.get_service_info(type, name)
            if info:
                address = socket.inet_ntoa(info.addresses[0])
                properties = {
                    'address': address,
                    'port': info.port,
                    'name': name,
                    'public_key': info.properties.get(b'public_key', b'').decode(),
                    'last_updated': datetime.now()
                }
                self.services[name] = properties
                self.last_seen[name] = datetime.now()
                
                # Create and emit discovery event
                event = ServiceDiscoveredEvent(
                    name=name,
                    address=address,
                    port=info.port,
                    properties={k.decode(): v.decode() for k, v in info.properties.items()}
                )
                self.discovery_handler(event)
                
                logger.info(f"Discovered service: {name} at {address}", browser="ServiceBrowser")
        except Exception as e:
            logger.error(f"Error adding service {name}: {e}", browser="ServiceBrowser")

    def remove_service(self, zeroconf, type, name):
        try:
            if name in self.services:
                del self.services[name]
                del self.last_seen[name]
                logger.info(f"Service removed: {name}", browser="ServiceBrowser")
        except Exception as e:
            logger.error(f"Error removing service {name}: {e}", browser="ServiceBrowser")

    def update_service(self, zeroconf, type, name):
        try:
            self.add_service(zeroconf, type, name)
        except Exception as e:
            logger.error(f"Error updating service {name}: {e}", browser="ServiceBrowser")

    def cleanup_stale_services(self):
        """Remove services that haven't been seen for a while."""
        now = datetime.now()
        stale_services = [
            name for name, last_seen in self.last_seen.items()
            if (now - last_seen) > self.stale_threshold
        ]
        
        for name in stale_services:
            logger.info(f"Removing stale service: {name}", browser="ServiceBrowser")
            if name in self.services:
                del self.services[name]
            if name in self.last_seen:
                del self.last_seen[name]


class ServiceBrowser:
    def __init__(self):
        self.services: Dict[str, Dict] = {}
        self.zeroconf = Zeroconf()
        self._discovery_handlers: List[Callable[[ServiceDiscoveredEvent], None]] = []
        self._cleanup_task = None
        self._is_running = False
        self.listener = None  # Initialize listener as None

    def add_discovery_handler(self, handler: Callable[[ServiceDiscoveredEvent], None]):
        """Add a handler for service discovery events"""
        self._discovery_handlers.append(handler)

    def _notify_discovery(self, event: ServiceDiscoveredEvent):
        """Notify all registered handlers of a service discovery event"""
        for handler in self._discovery_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in service discovery handler: {e}", browser="ServiceBrowser")

    async def start(self):
        """Start the service browser and its background tasks."""
        if self._is_running:
            return
        
        self._is_running = True
        self._start_cleanup_task()
        await self.start_browser()

    def _start_cleanup_task(self):
        """Start background cleanup task."""
        loop = asyncio.get_event_loop()
        self._cleanup_task = loop.create_task(self._cleanup_stale_services())

    async def _cleanup_stale_services(self):
        """Periodically clean up stale services."""
        while self._is_running:
            try:
                if self.listener:  # Check if listener exists
                    self.listener.cleanup_stale_services()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}", browser="ServiceBrowser")
                await asyncio.sleep(60)

    async def stop(self):
        """Stop the service browser and its background tasks."""
        if not self._is_running:
            return
        
        self._is_running = False
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Clean up resources
        self.cleanup()

    async def start_browser(self):
        """Start browsing for services."""
        try:
            self.listener = NetworkServiceListener(self._notify_discovery)
            self.zeroconf.add_service_listener("_bookmarkmanager._tcp.local.", self.listener)
            logger.info("Service browser started", browser="ServiceBrowser")
        except Exception as e:
            logger.error(f"Failed to start service browser: {e}", browser="ServiceBrowser")
            raise

    def cleanup(self):
        """Clean up resources."""
        if self.listener:
            try:
                self.zeroconf.remove_service_listener(self.listener)
            except Exception as e:
                logger.error(f"Error removing service listener: {e}", browser="ServiceBrowser")
        self.zeroconf.close()
        logger.info("Service browser cleaned up", browser="ServiceBrowser")

    def get_available_services(self) -> List[Dict[str, Any]]:
        """Get list of available services."""
        if not self.listener:
            return []
        return list(self.listener.services.values())

    def get_service_by_name(self, name: str) -> Optional[Dict]:
        """Get service information by name."""
        try:
            if not self.listener:
                return None
            return self.listener.services.get(name)
        except Exception as e:
            logger.error(f"Error getting service {name}: {e}", browser="ServiceBrowser")
            return None

    def stop_discovery(self):
        """Stop service discovery and clean up."""
        try:
            if self.listener:
                self.zeroconf.remove_service_listener(self.listener)
            self.zeroconf.close()
            logger.info("Service discovery stopped", browser="ServiceBrowser")
        except Exception as e:
            logger.error(f"Error stopping service discovery: {e}", browser="ServiceBrowser")
            raise 