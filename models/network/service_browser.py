from datetime import datetime, timedelta
from typing import Dict, List, Optional

from zeroconf import ServiceBrowser, Zeroconf, ServiceListener
import socket
# from nacl.public import PublicKey
# from nacl.encoding import Base64Encoder

from utils.utils import logger


class BookmarkManagerListener(ServiceListener):
    def __init__(self):
        self.services: Dict[str, Dict] = {}
        self.last_seen: Dict[str, datetime] = {}  # name -> last seen timestamp
        self.stale_threshold = timedelta(minutes=5)

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
        self.zeroconf = Zeroconf()
        self.listener = BookmarkManagerListener()
        self._browser = None
        self._start_cleanup_task()

    def _start_cleanup_task(self):
        """Start background task to clean up stale services."""
        import asyncio
        asyncio.create_task(self._cleanup_stale_services())

    async def _cleanup_stale_services(self):
        """Periodically clean up stale services."""
        while True:
            try:
                self.listener.cleanup_stale_services()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}", browser="ServiceBrowser")
                await asyncio.sleep(60)

    def start_discovery(self):
        """Start discovering BookmarkManager services on the network."""
        try:
            self._browser = ServiceBrowser(
                self.zeroconf,
                "_bookmarkmanager._tcp.local.",
                handlers=[self._on_service_state_change]
            )
            logger.info("Started service discovery", browser="ServiceBrowser")
        except Exception as e:
            logger.error(f"Failed to start service discovery: {e}", browser="ServiceBrowser")
            raise

    def _on_service_state_change(self, zeroconf, service_type, name, state_change):
        """Handle service state changes."""
        try:
            if state_change == "Added":
                info = zeroconf.get_service_info(service_type, name)
                if info:
                    address = ".".join(map(str, info.addresses[0]))
                    self.listener.services[address] = {
                        'port': info.port,
                        'properties': info.properties,
                        'last_seen': info.last_seen
                    }
                    logger.info(f"Discovered service at {address}:{info.port}", browser="ServiceBrowser")
            elif state_change == "Removed":
                # Find and remove the service
                for address, service in list(self.listener.services.items()):
                    if service['port'] == info.port:
                        del self.listener.services[address]
                        logger.info(f"Service removed: {address}", browser="ServiceBrowser")
                        break
        except Exception as e:
            logger.error(f"Error handling service state change: {e}", browser="ServiceBrowser")

    def get_available_services(self) -> List[Dict]:
        """Get list of available services with their details."""
        try:
            # Clean up stale services before returning
            self.listener.cleanup_stale_services()
            return [
                {
                    'address': address,
                    'port': service['port'],
                    'public_key': service['properties'].get(b'public_key', b'').decode(),
                    'last_seen': service['last_seen']
                }
                for address, service in self.listener.services.items()
            ]
        except Exception as e:
            logger.error(f"Error getting available services: {e}", browser="ServiceBrowser")
            return []

    def get_service_by_name(self, name: str) -> Optional[Dict]:
        """Get service information by name."""
        try:
            return self.listener.services.get(name)
        except Exception as e:
            logger.error(f"Error getting service {name}: {e}", browser="ServiceBrowser")
            return None

    def stop_discovery(self):
        """Stop service discovery and clean up."""
        try:
            if self._browser:
                self._browser.cancel()
            self.zeroconf.close()
            self.listener.services.clear()
            logger.info("Service discovery stopped", browser="ServiceBrowser")
        except Exception as e:
            logger.error(f"Error stopping service discovery: {e}", browser="ServiceBrowser")
            raise

    def cleanup(self):
        """Clean up resources."""
        try:
            if self._browser:
                self._browser.cancel()
            self.zeroconf.close()
            logger.info("Service browser cleaned up", browser="ServiceBrowser")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", browser="ServiceBrowser") 