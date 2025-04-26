import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
import hmac
import hashlib
import json
import socket
from typing import Dict, List


from nacl.public import PrivateKey, PublicKey, Box
from nacl.encoding import Base64Encoder
import secrets
import websockets
from zeroconf import ServiceInfo, Zeroconf

from utils.utils import logger

class NetworkHandler:
    def __init__(self, port: int = 8765):
        self.port = port
        self.private_key = PrivateKey.generate()
        self.public_key = self.private_key.public_key
        self.connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.peer_keys: Dict[str, PublicKey] = {}
        self.connection_states: Dict[str, Dict] = {}  # address -> state info
        self.zeroconf = Zeroconf()
        self.service_info = None
        
        # Security settings
        self.max_connections = 10  # Maximum concurrent connections
        self.rate_limit = 100  # Messages per minute
        self.message_sizes: Dict[str, List[int]] = defaultdict(list)  # Track message sizes
        self.max_message_size = 1024 * 1024  # 1MB max message size
        self.connection_attempts: Dict[str, Dict] = defaultdict(lambda: {
            'count': 0,
            'first_attempt': None,
            'last_attempt': None
        })
        self.blacklist: Dict[str, datetime] = {}  # IP -> unblock time
        self.blacklist_duration = timedelta(minutes=30)
        
        self._setup_service_discovery()
        self._cleanup_tasks = []
        self._is_running = False

    async def start(self):
        """Start the network handler and its background tasks."""
        if self._is_running:
            return
        
        self._is_running = True
        self._start_cleanup_tasks()
        await self.start_server()

    def _start_cleanup_tasks(self):
        """Start background cleanup tasks."""
        loop = asyncio.get_event_loop()
        self._cleanup_tasks = [
            loop.create_task(self._cleanup_stale_connections()),
            loop.create_task(self._cleanup_security_data())
        ]

    async def _cleanup_stale_connections(self):
        """Periodically clean up stale connections."""
        while self._is_running:
            try:
                now = datetime.now()
                stale_threshold = timedelta(minutes=5)
                
                for address in list(self.connections.keys()):
                    state = self.connection_states.get(address, {})
                    last_message = state.get('last_message')
                    
                    if last_message and (now - last_message) > stale_threshold:
                        logger.info(f"Cleaning up stale connection: {address}", browser="NetworkHandler")
                        await self._close_connection(address)
                
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}", browser="NetworkHandler")
                await asyncio.sleep(60)

    async def _cleanup_security_data(self):
        """Clean up security-related data."""
        while self._is_running:
            try:
                now = datetime.now()
                # Clean up old connection attempts
                for address in list(self.connection_attempts.keys()):
                    if (now - self.connection_attempts[address]['last_attempt']) > timedelta(hours=1):
                        del self.connection_attempts[address]
                
                # Clean up message size history
                for address in list(self.message_sizes.keys()):
                    if address not in self.connections:
                        del self.message_sizes[address]
                
                await asyncio.sleep(300)  # Check every 5 minutes
            except Exception as e:
                logger.error(f"Error in security cleanup task: {e}", browser="NetworkHandler")
                await asyncio.sleep(60)

    async def stop(self):
        """Stop the network handler and its background tasks."""
        if not self._is_running:
            return
        
        self._is_running = False
        
        # Cancel all cleanup tasks
        for task in self._cleanup_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self._cleanup_tasks, return_exceptions=True)
        
        # Clean up resources
        await self.cleanup()

    def _setup_service_discovery(self):
        """Set up Zeroconf service discovery for the application."""
        try:
            desc = {'version': '1.0', 'public_key': self.public_key.encode(Base64Encoder).decode()}
            self.service_info = ServiceInfo(
                "_bookmarkmanager._tcp.local.",
                "BookmarkManager._bookmarkmanager._tcp.local.",
                addresses=[socket.inet_aton(socket.gethostbyname(socket.gethostname()))],
                port=self.port,
                properties=desc,
            )
            self.zeroconf.register_service(self.service_info)
            logger.info("Service discovery setup complete", browser="NetworkHandler")
        except Exception as e:
            logger.error(f"Failed to setup service discovery: {e}", browser="NetworkHandler")
            raise

    async def start_server(self):
        """Start the WebSocket server with enhanced security."""
        try:
            async with websockets.serve(
                self._handle_connection,
                "0.0.0.0",
                self.port,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=10,
                max_size=self.max_message_size,
                max_queue=32
            ):
                logger.info(f"WebSocket server started on port {self.port}", browser="NetworkHandler")
                await asyncio.Future()  # run forever
        except Exception as e:
            logger.error(f"WebSocket server error: {e}", browser="NetworkHandler")
            raise

    async def _handle_connection(self, websocket, path):
        """Handle incoming WebSocket connections with security checks."""
        address = websocket.remote_address[0]
        
        # Security checks
        if self._is_blacklisted(address):
            logger.warning(f"Rejected connection from blacklisted address: {address}", browser="NetworkHandler")
            await websocket.close(4001, "Connection rejected")
            return
        
        if not self._check_connection_attempts(address):
            await websocket.close(4002, "Too many connection attempts")
            return
        
        if len(self.connections) >= self.max_connections:
            logger.warning(f"Rejected connection: maximum connections reached", browser="NetworkHandler")
            await websocket.close(4003, "Server at capacity")
            return
        
        try:
            # Exchange public keys with timeout
            try:
                peer_public_key = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                peer_key = PublicKey(peer_public_key.encode())
            except asyncio.TimeoutError:
                logger.warning(f"Key exchange timeout from {address}", browser="NetworkHandler")
                await websocket.close(4004, "Key exchange timeout")
                return
            
            # Send our public key
            await websocket.send(self.public_key.encode(Base64Encoder).decode())
            
            # Store the connection
            self.connections[address] = websocket
            self.peer_keys[address] = peer_key
            self.connection_states[address] = {
                'connected': True,
                'last_connected': datetime.now(),
                'last_message': datetime.now(),
                'message_count': 0,
                'rate_limit_reset': datetime.now(),
                'session_token': secrets.token_hex(16)
            }
            
            logger.info(f"New connection from {address}", browser="NetworkHandler")
            
            # Handle messages
            async for message in websocket:
                try:
                    if not self._check_rate_limit(address):
                        await websocket.close(4005, "Rate limit exceeded")
                        break
                    
                    if not self._check_message_size(address, len(message)):
                        await websocket.close(4006, "Message size limit exceeded")
                        break
                    
                    await self._handle_message(websocket, message)
                except Exception as e:
                    logger.error(f"Error handling message from {address}: {e}", browser="NetworkHandler")
                    break
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Connection closed by {address}", browser="NetworkHandler")
        except Exception as e:
            logger.error(f"Connection error with {address}: {e}", browser="NetworkHandler")
        finally:
            await self._close_connection(address)

    async def _close_connection(self, address: str):
        """Close a connection with cleanup."""
        if address in self.connections:
            try:
                await self.connections[address].close()
            except Exception as e:
                logger.error(f"Error closing connection to {address}: {e}", browser="NetworkHandler")
            finally:
                del self.connections[address]
        if address in self.peer_keys:
            del self.peer_keys[address]
        if address in self.connection_states:
            del self.connection_states[address]
        logger.info(f"Connection to {address} closed and cleaned up", browser="NetworkHandler")

    def _validate_message(self, data: Dict) -> bool:
        """Validate incoming message structure."""
        required_fields = {'type', 'data'}
        return all(field in data for field in required_fields)

    async def _handle_message(self, websocket, message: str):
        """Handle incoming messages with validation."""
        try:
            # Parse the message format
            message_data = json.loads(message)
            encrypted = message_data.get('data')
            signature = message_data.get('signature')
            
            if not encrypted or not signature:
                raise ValueError("Invalid message format")
            
            # Decrypt the message
            decrypted = self._decrypt_message(encrypted, websocket.remote_address[0])
            data = json.loads(decrypted)
            
            if not self._validate_message(data):
                raise ValueError("Invalid message structure")
            
            # Update last message timestamp
            self.connection_states[websocket.remote_address[0]]['last_message'] = datetime.now()
            
            # Handle different message types
            if data['type'] == 'ping':
                response = {
                    "type": "pong",
                    "timestamp": datetime.now().isoformat(),
                    "session_token": data.get('session_token', '')
                }
            elif data['type'] == 'bookmarks':
                # Process bookmarks (implement your logic here)
                response = {
                    "type": "ack",
                    "status": "received",
                    "session_token": data.get('session_token', '')
                }
            else:
                response = {
                    "type": "error",
                    "message": "Unknown message type",
                    "session_token": data.get('session_token', '')
                }
            
            # Create and sign the response
            response_str = json.dumps(response)
            signature = hmac.new(
                data.get('session_token', '').encode(),
                response_str.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Encrypt and send the response
            encrypted_response = self._encrypt_message(response_str, websocket.remote_address[0])
            await websocket.send(json.dumps({
                'data': encrypted_response,
                'signature': signature
            }))
            
        except json.JSONDecodeError:
            logger.error("Invalid JSON message", browser="NetworkHandler")
            await websocket.close(4007, "Invalid message format")
        except Exception as e:
            logger.error(f"Error processing message: {e}", browser="NetworkHandler")
            await websocket.close(4008, str(e))

    async def send_message(self, peer_address: str, message: str):
        """Send an encrypted message to a peer with error handling."""
        if peer_address not in self.connections:
            raise ValueError("No connection to peer")
        
        try:
            encrypted = self._encrypt_message(message, peer_address)
            await self.connections[peer_address].send(encrypted)
            self.connection_states[peer_address]['last_message'] = datetime.now()
        except Exception as e:
            logger.error(f"Failed to send message to {peer_address}: {e}", browser="NetworkHandler")
            raise

    def cleanup(self):
        """Clean up resources."""
        if self.service_info:
            try:
                self.zeroconf.unregister_service(self.service_info)
            except Exception as e:
                logger.error(f"Error unregistering service: {e}", browser="NetworkHandler")
        self.zeroconf.close()
        
        # Close all connections
        for address in list(self.connections.keys()):
            asyncio.create_task(self._close_connection(address))
        
        logger.info("Network handler cleaned up", browser="NetworkHandler")

    def _encrypt_message(self, message: str, peer_address: str) -> str:
        """Encrypt a message for a specific peer."""
        if peer_address not in self.peer_keys:
            raise ValueError("No public key available for peer")
        
        box = Box(self.private_key, self.peer_keys[peer_address])
        encrypted = box.encrypt(message.encode())
        return encrypted.decode()

    def _decrypt_message(self, encrypted_message: str, peer_address: str) -> str:
        """Decrypt a message from a specific peer."""
        if peer_address not in self.peer_keys:
            raise ValueError("No public key available for peer")
        
        box = Box(self.private_key, self.peer_keys[peer_address])
        decrypted = box.decrypt(encrypted_message.encode())
        return decrypted.decode()

    def _is_blacklisted(self, address: str) -> bool:
        """Check if an address is blacklisted."""
        if address in self.blacklist:
            if datetime.now() < self.blacklist[address]:
                return True
            else:
                del self.blacklist[address]
        return False

    def _check_connection_attempts(self, address: str) -> bool:
        """Check if connection attempts are suspicious."""
        attempts = self.connection_attempts[address]
        now = datetime.now()
        
        if attempts['first_attempt'] is None:
            attempts['first_attempt'] = now
            attempts['count'] = 1
            return True
        
        time_since_first = now - attempts['first_attempt']
        if time_since_first < timedelta(minutes=1):
            attempts['count'] += 1
            if attempts['count'] > 5:  # More than 5 attempts in a minute
                self.blacklist[address] = now + self.blacklist_duration
                logger.warning(f"Blacklisted {address} for suspicious connection attempts", browser="NetworkHandler")
                return False
        else:
            # Reset counter after a minute
            attempts['first_attempt'] = now
            attempts['count'] = 1
        
        return True

    def _check_rate_limit(self, address: str) -> bool:
        """Check if a peer is exceeding rate limits."""
        state = self.connection_states.get(address, {})
        messages = state.get('message_count', 0)
        last_reset = state.get('rate_limit_reset')
        
        now = datetime.now()
        if last_reset is None or (now - last_reset) > timedelta(minutes=1):
            state['message_count'] = 0
            state['rate_limit_reset'] = now
            return True
        
        if messages >= self.rate_limit:
            logger.warning(f"Rate limit exceeded for {address}", browser="NetworkHandler")
            return False
        
        state['message_count'] = messages + 1
        return True

    def _check_message_size(self, address: str, size: int) -> bool:
        """Check if message size is suspicious."""
        self.message_sizes[address].append(size)
        if len(self.message_sizes[address]) > 10:
            self.message_sizes[address].pop(0)
        
        avg_size = sum(self.message_sizes[address]) / len(self.message_sizes[address])
        if size > self.max_message_size or size > avg_size * 3:
            logger.warning(f"Suspicious message size from {address}: {size} bytes", browser="NetworkHandler")
            return False
        
        return True 