import asyncio
import json
from datetime import datetime, timedelta
import hashlib
from typing import Dict, Optional, List

import hmac
from nacl.public import PrivateKey, PublicKey, Box
from nacl.encoding import Base64Encoder
import secrets
import websockets

from utils.utils import logger

class NetworkClient:
    def __init__(self):
        self.private_key = PrivateKey.generate()
        self.public_key = self.private_key.public_key
        self.websocket = None
        self.peer_key = None
        self.connected = False
        self.message_queue: List[Dict] = []
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5  # seconds
        
        # Security settings
        self.session_token = secrets.token_hex(16)
        self.message_counter = 0
        self.max_message_size = 1024 * 1024  # 1MB
        self.connection_timeout = 10  # seconds
        self.message_timeout = 30  # seconds

    async def connect(self, host: str, port: int = 8765):
        """Connect to a remote BookmarkManager instance with enhanced security."""
        if self.connected:
            logger.warning("Already connected to a peer", browser="NetworkClient")
            return

        try:
            # Connect with timeout
            self.websocket = await asyncio.wait_for(
                websockets.connect(f"ws://{host}:{port}"),
                timeout=self.connection_timeout
            )
            
            # Exchange public keys with timeout
            try:
                await self.websocket.send(self.public_key.encode(Base64Encoder).decode())
                peer_public_key = await asyncio.wait_for(self.websocket.recv(), timeout=5.0)
                self.peer_key = PublicKey(peer_public_key.encode())
            except asyncio.TimeoutError:
                logger.error("Key exchange timeout", browser="NetworkClient")
                await self._close_connection()
                raise ConnectionError("Key exchange timeout")
            
            self.connected = True
            self.reconnect_attempts = 0
            logger.info(f"Connected to {host}:{port}", browser="NetworkClient")
            
            # Start message processing
            asyncio.create_task(self._process_message_queue())
            asyncio.create_task(self._monitor_connection())
            
        except Exception as e:
            logger.error(f"Failed to connect to {host}:{port}: {e}", browser="NetworkClient")
            await self._close_connection()
            raise

    async def _monitor_connection(self):
        """Monitor the connection and attempt reconnection if lost."""
        while self.connected:
            try:
                # Send ping to check connection
                await self._send_message({
                    "type": "ping",
                    "timestamp": datetime.now().isoformat(),
                    "session_token": self.session_token
                })
                await asyncio.sleep(30)  # Ping every 30 seconds
            except Exception as e:
                logger.error(f"Connection monitoring error: {e}", browser="NetworkClient")
                await self._handle_connection_loss()
                break

    async def _handle_connection_loss(self):
        """Handle connection loss and attempt reconnection."""
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            delay = self.reconnect_delay * (2 ** (self.reconnect_attempts - 1))
            logger.info(f"Attempting to reconnect in {delay} seconds...", browser="NetworkClient")
            await asyncio.sleep(delay)
            await self.connect(self.websocket.remote_address[0], self.websocket.remote_address[1])
        else:
            logger.error("Max reconnection attempts reached", browser="NetworkClient")
            self.connected = False
            if hasattr(self, 'connection_lost'):
                self.connection_lost.emit()

    async def _send_message(self, message: Dict):
        """Send an encrypted message with security headers."""
        if not self.connected:
            raise ConnectionError("Not connected to peer")
        
        try:
            # Add security headers
            message['message_id'] = self.message_counter
            message['timestamp'] = datetime.now().isoformat()
            message['session_token'] = self.session_token
            
            # Create HMAC signature
            message_str = json.dumps(message)
            signature = self._create_signature(message_str)
            
            # Encrypt the message
            encrypted = self._encrypt_message(message_str)
            
            # Send with timeout
            await asyncio.wait_for(
                self.websocket.send(json.dumps({
                    'data': encrypted,
                    'signature': signature
                })),
                timeout=self.message_timeout
            )
            
            self.message_counter += 1
            logger.debug(f"Message sent: {message['type']}", browser="NetworkClient")
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}", browser="NetworkClient")
            raise

    def _create_signature(self, message: str) -> str:
        """Create HMAC signature for a message."""
        return hmac.new(
            self.session_token.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

    def _verify_signature(self, message: str, signature: str) -> bool:
        """Verify HMAC signature of a message."""
        expected = self._create_signature(message)
        return hmac.compare_digest(expected, signature)

    async def send_bookmarks(self, bookmarks: List[Dict]):
        """Send bookmarks to the connected peer."""
        if not self.connected:
            self.message_queue.append({
                "type": "bookmarks",
                "data": bookmarks
            })
            raise ConnectionError("Not connected to peer")
        
        try:
            await self._send_message({
                "type": "bookmarks",
                "data": bookmarks
            })
        except Exception as e:
            logger.error(f"Failed to send bookmarks: {e}", browser="NetworkClient")
            raise

    async def _process_message_queue(self):
        """Process queued messages when connection is restored."""
        while self.connected:
            if self.message_queue:
                message = self.message_queue.pop(0)
                try:
                    await self._send_message(message)
                except Exception as e:
                    logger.error(f"Failed to process queued message: {e}", browser="NetworkClient")
                    self.message_queue.append(message)  # Put back in queue
            await asyncio.sleep(1)

    async def receive_bookmarks(self) -> List[Dict]:
        """Receive bookmarks from the connected peer."""
        if not self.connected:
            raise ConnectionError("Not connected to peer")
        
        try:
            message = await asyncio.wait_for(self.websocket.recv(), timeout=self.message_timeout)
            message_data = json.loads(message)
            
            # Verify message format
            if 'data' not in message_data or 'signature' not in message_data:
                raise ValueError("Invalid message format")
            
            # Decrypt and verify
            decrypted = self._decrypt_message(message_data['data'])
            if not self._verify_signature(decrypted, message_data['signature']):
                raise ValueError("Invalid message signature")
            
            data = json.loads(decrypted)
            
            # Verify session token
            if data.get('session_token') != self.session_token:
                raise ValueError("Invalid session token")
            
            if data['type'] == 'bookmarks':
                if hasattr(self, 'bookmarks_received'):
                    self.bookmarks_received.emit(data['data'])
                return data['data']
            else:
                raise ValueError(f"Unexpected message type: {data['type']}")
                
        except Exception as e:
            logger.error(f"Failed to receive bookmarks: {e}", browser="NetworkClient")
            raise

    def _encrypt_message(self, message: str) -> str:
        """Encrypt a message using the peer's public key."""
        if not self.peer_key:
            raise ValueError("No peer key available")
        
        box = Box(self.private_key, self.peer_key)
        encrypted = box.encrypt(message.encode())
        return encrypted.decode()

    def _decrypt_message(self, encrypted_message: str) -> str:
        """Decrypt a message using our private key."""
        if not self.peer_key:
            raise ValueError("No peer key available")
        
        box = Box(self.private_key, self.peer_key)
        decrypted = box.decrypt(encrypted_message.encode())
        return decrypted.decode()

    async def disconnect(self):
        """Disconnect from the peer."""
        await self._close_connection()

    async def _close_connection(self):
        """Close the connection and clean up."""
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.error(f"Error closing connection: {e}", browser="NetworkClient")
            finally:
                self.websocket = None
                self.peer_key = None
                self.connected = False

    async def cleanup(self):
        """Clean up resources."""
        await self._close_connection()
        # Clear sensitive data
        self.session_token = None
        self.message_counter = 0
        self.message_queue.clear() 