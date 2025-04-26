from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QMessageBox, 
    QInputDialog, QGroupBox, QLineEdit, QCheckBox
)
from PySide6.QtCore import Qt, QTimer, Signal
from models.network.service_browser import ServiceBrowser
from models.network.network_client import NetworkClient
from models.network.network_handler import NetworkHandler
from models.network.network_connection_status import NetworkConnectionStatus
from models.network.network_events import ServiceDiscoveredEvent, ConnectionStatusEvent
import asyncio
from typing import List, Dict
import threading
from datetime import datetime
from models.bookmark import Bookmark
from models.browser_bookmarks import BrowserBookmarks

from utils.utils import logger

class NetworkTab(QWidget):
    network_status = Signal(str, bool)  # message, is_error
    
    def __init__(self, network_handler: NetworkHandler, bookmark_manager: BrowserBookmarks):
        super().__init__()
        self.network_handler = network_handler
        self.bookmark_manager = bookmark_manager
        self.network_client = NetworkClient()
        self.service_browser = ServiceBrowser()
        self.connection_status = NetworkConnectionStatus()
        
        # Connect network handler events
        self.network_handler.add_service_discovered_handler(self.handle_service_discovered)
        self.network_handler.add_connection_status_handler(self.handle_connection_status)
        
        # Connect service browser events
        self.service_browser.add_discovery_handler(self.handle_service_discovered)
        
        # Start service browser in a separate thread
        self.browser_thread = threading.Thread(target=self._run_browser)
        self.browser_thread.daemon = True
        self.browser_thread.start()
        
        self.connected_peers: Dict[str, str] = {}  # name -> address
        self.setup_ui()
        self.setup_timer()
        self.refresh_instances()

    def _run_browser(self):
        """Run the service browser in a separate thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.service_browser.start())
        except Exception as e:
            logger.error(f"Error starting service browser: {e}", browser="NetworkTab")
        finally:
            loop.close()

    async def _cleanup_browser(self):
        """Clean up service browser resources."""
        await self.service_browser.stop()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Manual connection section
        manual_group = QGroupBox("Manual Connection")
        manual_layout = QHBoxLayout()
        
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("Enter IP address or hostname")
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("Port (default: 8765)")
        self.port_input.setText("8765")
        
        connect_button = QPushButton("Connect")
        connect_button.clicked.connect(self.connect_manual)
        
        manual_layout.addWidget(QLabel("Host:"))
        manual_layout.addWidget(self.host_input)
        manual_layout.addWidget(QLabel("Port:"))
        manual_layout.addWidget(self.port_input)
        manual_layout.addWidget(connect_button)
        manual_group.setLayout(manual_layout)
        layout.addWidget(manual_group)
        
        # Auto-discovery section
        auto_group = QGroupBox("Automatic Discovery")
        auto_layout = QVBoxLayout()
        
        self.instance_list = QListWidget()
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_instances)
        
        auto_layout.addWidget(self.instance_list)
        auto_layout.addWidget(refresh_button)
        auto_group.setLayout(auto_layout)
        layout.addWidget(auto_group)
        
        # Bookmarks section
        bookmarks_group = QGroupBox("Bookmark Operations")
        bookmarks_layout = QVBoxLayout()
        
        # Share options
        share_options = QHBoxLayout()
        self.share_all_checkbox = QCheckBox("Share All Bookmarks")
        self.share_all_checkbox.setChecked(True)  # Default to sharing all
        share_options.addWidget(self.share_all_checkbox)
        
        # Sync options
        sync_options = QHBoxLayout()
        self.sync_checkbox = QCheckBox("Enable Two-Way Sync")
        self.sync_checkbox.setChecked(True)  # Default to enabling sync
        sync_options.addWidget(self.sync_checkbox)
        
        # Operation buttons
        buttons_layout = QHBoxLayout()
        share_button = QPushButton("Share Bookmarks")
        share_button.clicked.connect(self.share_bookmarks)
        sync_button = QPushButton("Sync Bookmarks")
        sync_button.clicked.connect(self.sync_bookmarks)
        
        buttons_layout.addWidget(share_button)
        buttons_layout.addWidget(sync_button)
        
        bookmarks_layout.addLayout(share_options)
        bookmarks_layout.addLayout(sync_options)
        bookmarks_layout.addLayout(buttons_layout)
        bookmarks_group.setLayout(bookmarks_layout)
        layout.addWidget(bookmarks_group)
        
        # Status section
        self.status_label = QLabel("Not connected")
        layout.addWidget(self.status_label)

    def setup_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_instances)
        self.timer.start(5000)  # Refresh every 5 seconds

    def refresh_instances(self):
        """Refresh the list of available instances."""
        self.instance_list.clear()
        services = self.service_browser.get_available_services()
        for service in services:
            item = QListWidgetItem(f"{service['name']} ({service['address']}:{service['port']})")
            item.setData(Qt.UserRole, service)
            self.instance_list.addItem(item)

    def connect_manual(self):
        host = self.host_input.text().strip()
        port = self.port_input.text().strip()
        
        if not host:
            QMessageBox.warning(self, "Error", "Please enter a host address")
            return
            
        try:
            port = int(port) if port else 8765
            self.network_client.connect(host, port)
            self.connection_status.update_from_event(ConnectionStatusEvent(
                is_connected=True,
                service_info={
                    'name': host,
                    'address': f"{host}:{port}"
                }
            ))
            self.load_bookmarks()
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", str(e))
            self.connection_status.update_from_event(ConnectionStatusEvent(
                is_connected=False,
                error_message="Connection failed"
            ))

    def connect_to_instance(self):
        selected = self.instance_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Please select an instance to connect to")
            return
            
        service = selected.data(Qt.UserRole)
        try:
            self.network_client.connect(service['address'], service['port'])
            self.connection_status.update_from_event(ConnectionStatusEvent(
                is_connected=True,
                service_info=service
            ))
            self.load_bookmarks()
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", str(e))
            self.connection_status.update_from_event(ConnectionStatusEvent(
                is_connected=False,
                error_message="Connection failed"
            ))

    def load_bookmarks(self):
        self.bookmark_list.clear()
        # Load bookmarks from your bookmark manager
        # This is a placeholder - implement your bookmark loading logic
        pass

    def share_bookmarks(self):
        """Share bookmarks with connected peers."""
        try:
            if self.share_all_checkbox.isChecked():
                # Get all bookmarks from the current browser
                bookmarks = self.get_all_bookmarks()
                if not bookmarks:
                    QMessageBox.warning(self, "Warning", "No bookmarks to share")
                    return
                
                # Convert bookmarks to dict format for network transmission
                bookmark_dicts = [self._bookmark_to_dict(b) for b in bookmarks]
                self.network_client.send_bookmarks(bookmark_dicts)
                self.network_status.emit("All bookmarks shared successfully", False)
            else:
                # Share selected bookmarks (existing functionality)
                selected_items = self.bookmark_list.selectedItems()
                if not selected_items:
                    QMessageBox.warning(self, "Error", "Please select bookmarks to share")
                    return
                
                bookmarks = [item.data(Qt.UserRole) for item in selected_items]
                bookmark_dicts = [self._bookmark_to_dict(b) for b in bookmarks]
                self.network_client.send_bookmarks(bookmark_dicts)
                self.network_status.emit("Selected bookmarks shared successfully", False)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to share bookmarks: {e}")
            self.network_status.emit("Failed to share bookmarks", True)

    def sync_bookmarks(self):
        """Sync bookmarks with connected peers."""
        try:
            if not self.sync_checkbox.isChecked():
                QMessageBox.warning(self, "Warning", "Two-way sync is disabled")
                return
                
            # Get local bookmarks
            local_bookmarks = self.get_all_bookmarks()
            if not local_bookmarks:
                QMessageBox.warning(self, "Warning", "No local bookmarks to sync")
                return
            
            # Request remote bookmarks
            self.network_client.request_bookmarks()
            self.network_status.emit("Sync initiated", False)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to sync bookmarks: {e}")
            self.network_status.emit("Failed to sync bookmarks", True)

    def get_all_bookmarks(self) -> List[Bookmark]:
        """Get all bookmarks from the current browser."""
        try:
            # Get the current browser from the main window
            browser = self.parent().parent().browser_combo.currentData()
            if not browser:
                return []
            
            # Load bookmarks for the current browser
            if self.bookmark_manager.load_browser_bookmarks(browser):
                return self.bookmark_manager.get_all_bookmarks()
            return []
        except Exception as e:
            logger.error(f"Error getting all bookmarks: {e}", browser="NetworkTab")
            return []

    def handle_bookmarks_received(self, bookmark_dicts: List[Dict]):
        """Handle received bookmarks from peers."""
        try:
            if self.sync_checkbox.isChecked():
                # Convert received dicts to Bookmark objects
                remote_bookmarks = [self._dict_to_bookmark(d) for d in bookmark_dicts]
                
                # Get local bookmarks
                local_bookmarks = self.get_all_bookmarks()
                
                # Merge bookmarks using the bookmark manager
                self.bookmark_manager.merge_bookmarks(local_bookmarks, remote_bookmarks)
                
                # Save merged bookmarks
                self.bookmark_manager.save_bookmarks()
                
                # Refresh the UI
                self.parent().parent().load_bookmarks()
                
                QMessageBox.information(
                    self, 
                    "Sync Complete", 
                    f"Successfully synced {len(bookmark_dicts)} bookmarks with local collection"
                )
            else:
                QMessageBox.information(
                    self, 
                    "Bookmarks Received", 
                    f"Received {len(bookmark_dicts)} bookmarks from remote instance"
                )
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to process received bookmarks: {e}")
            self.status_label.setText("Failed to process received bookmarks")

    def _bookmark_to_dict(self, bookmark: Bookmark) -> Dict:
        """Convert a Bookmark object to a dictionary for network transmission."""
        return {
            'id': bookmark.id,
            'title': bookmark.title,
            'url': bookmark.url,
            'description': bookmark.description,
            'parent_id': bookmark.parent_id,
            'created_at': bookmark.created_at.isoformat() if bookmark.created_at else None,
            'last_modified': bookmark.last_modified.isoformat() if bookmark.last_modified else None
        }

    def _dict_to_bookmark(self, data: Dict) -> Bookmark:
        """Convert a dictionary to a Bookmark object."""
        return Bookmark(
            id=data.get('id'),
            title=data['title'],
            url=data['url'],
            description=data.get('description'),
            parent_id=data.get('parent_id'),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            last_modified=datetime.fromisoformat(data['last_modified']) if data.get('last_modified') else None
        )

    def handle_connection_lost(self):
        self.connection_status.update_from_event(ConnectionStatusEvent(
            is_connected=False,
            error_message="Connection lost"
        ))
        QMessageBox.warning(self, "Connection Lost", "The connection to the remote instance was lost")

    def handle_service_discovered(self, event: ServiceDiscoveredEvent):
        """Handle a discovered service event"""
        self.connection_status.update_from_service_discovery(event)
        self.network_status.emit(self.connection_status.get_status_message(), False)

    def handle_connection_status(self, event: ConnectionStatusEvent):
        """Handle a connection status event"""
        self.connection_status.update_from_event(event)
        self.network_status.emit(self.connection_status.get_status_message(), bool(event.error_message))

    def get_connection_status(self) -> NetworkConnectionStatus:
        """Get the network connection status object"""
        return self.connection_status

    def closeEvent(self, event):
        self.service_browser.stop_discovery()
        self.network_client.disconnect()
        super().closeEvent(event)

    def cleanup(self):
        """Clean up resources."""
        # Create a new event loop for cleanup
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._cleanup_browser())
        except Exception as e:
            logger.error(f"Error during browser cleanup: {e}", browser="NetworkTab")
        finally:
            loop.close()

        self.timer.stop()
        self.network_client.cleanup() 