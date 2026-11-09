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
from models.network.network_events import ServiceDiscoveredEvent, ConnectionStatusEvent, NetworkCallType, NetworkConnectionStatusType
import asyncio
from typing import List, Dict
import threading
from datetime import datetime
from models.bookmark import Bookmark, BookmarkFolder
from models.bookmark_manager import BookmarkManager

from utils.logger import logger
from utils.translations import _

class NetworkTab(QWidget):
    network_status = Signal(str, bool)  # message, is_error
    
    def __init__(self, network_handler: NetworkHandler, bookmark_manager: BookmarkManager):
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
            logger.error(_("Error starting service browser: {0}").format(e), browser="NetworkTab")
        finally:
            loop.close()

    async def _cleanup_browser(self):
        """Clean up service browser resources."""
        await self.service_browser.stop()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Manual connection section
        manual_group = QGroupBox(_("Manual Connection"))
        manual_layout = QHBoxLayout()
        
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText(_("Enter IP address or hostname"))
        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText(_("Port (default: {0})").format(8765))
        self.port_input.setText("8765")
        
        connect_button = QPushButton(_("Connect"))
        connect_button.clicked.connect(self.connect_manual)
        
        manual_layout.addWidget(QLabel(_("Host:")))
        manual_layout.addWidget(self.host_input)
        manual_layout.addWidget(QLabel(_("Port:")))
        manual_layout.addWidget(self.port_input)
        manual_layout.addWidget(connect_button)
        manual_group.setLayout(manual_layout)
        layout.addWidget(manual_group)
        
        # Auto-discovery section
        auto_group = QGroupBox(_("Automatic Discovery"))
        auto_layout = QVBoxLayout()
        
        self.instance_list = QListWidget()
        refresh_button = QPushButton(_("Refresh"))
        refresh_button.clicked.connect(self.refresh_instances)
        
        auto_layout.addWidget(self.instance_list)
        auto_layout.addWidget(refresh_button)
        auto_group.setLayout(auto_layout)
        layout.addWidget(auto_group)
        
        # Bookmarks section
        bookmarks_group = QGroupBox(_("Bookmark Operations"))
        bookmarks_layout = QVBoxLayout()
        
        # Share options
        share_options = QHBoxLayout()
        self.share_all_checkbox = QCheckBox(_("Share All Bookmarks"))
        self.share_all_checkbox.setChecked(True)  # Default to sharing all
        share_options.addWidget(self.share_all_checkbox)
        
        # Sync options
        sync_options = QHBoxLayout()
        self.sync_checkbox = QCheckBox(_("Enable Two-Way Sync"))
        self.sync_checkbox.setChecked(True)  # Default to enabling sync
        sync_options.addWidget(self.sync_checkbox)
        
        # Operation buttons
        buttons_layout = QHBoxLayout()
        share_button = QPushButton(_("Share Bookmarks"))
        share_button.clicked.connect(self.share_bookmarks)
        sync_button = QPushButton(_("Sync Bookmarks"))
        sync_button.clicked.connect(self.sync_bookmarks)
        
        buttons_layout.addWidget(share_button)
        buttons_layout.addWidget(sync_button)
        
        bookmarks_layout.addLayout(share_options)
        bookmarks_layout.addLayout(sync_options)
        bookmarks_layout.addLayout(buttons_layout)
        bookmarks_group.setLayout(bookmarks_layout)
        layout.addWidget(bookmarks_group)
        
        # Status section
        self.status_label = QLabel(_("Not connected"))
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
            QMessageBox.warning(self, _("Error"), _("Please enter a host address"))
            return
            
        try:
            port = int(port) if port else 8765
            self.network_client.connect(host, port)
            self.connection_status.update_from_event(ConnectionStatusEvent(
                service_info={
                    'name': host,
                    'address': f"{host}:{port}"
                },
                status_type=NetworkConnectionStatusType.CONNECTED
            ))
            self.load_bookmarks()
        except Exception as e:
            QMessageBox.critical(self, _("Connection Error"), str(e))
            self.connection_status.update_from_event(ConnectionStatusEvent(
                error_message=_("Connection failed"),
                status_type=NetworkConnectionStatusType.ERROR
            ))

    def connect_to_instance(self):
        selected = self.instance_list.currentItem()
        if not selected:
            QMessageBox.warning(self, _("Error"), _("Please select an instance to connect to"))
            return
            
        service = selected.data(Qt.UserRole)
        try:
            self.network_client.connect(service['address'], service['port'])
            self.connection_status.update_from_event(ConnectionStatusEvent(
                service_info=service,
                status_type=NetworkConnectionStatusType.CONNECTED
            ))
            self.load_bookmarks()
        except Exception as e:
            QMessageBox.critical(self, _("Connection Error"), str(e))
            self.connection_status.update_from_event(ConnectionStatusEvent(
                error_message=_("Connection failed"),
                status_type=NetworkConnectionStatusType.ERROR
            ))

    def load_bookmarks(self):
        # Load bookmarks from your bookmark manager
        # This is a placeholder - implement your bookmark loading logic
        pass

    def share_bookmarks(self):
        """Share bookmarks with connected peers."""
        try:
            if self.share_all_checkbox.isChecked():
                # Get all bookmarks from the current browser
                browser = self.bookmark_manager.current_browser
                if not browser:
                    QMessageBox.warning(self, _("Warning"), _("No browser selected"))
                    return
                
                # Get the bookmarks for the current browser
                browser_instance = self.bookmark_manager.get_browser_instance(browser)
                bookmarks = browser_instance.get_all_bookmarks() if browser_instance else []
                if not bookmarks:
                    QMessageBox.warning(self, _("Warning"), _("No bookmarks to share"))
                    return
                
                # Convert bookmarks to dict format for network transmission
                bookmark_dicts = [b.to_dict() for b in bookmarks]
                self.network_client.send_bookmarks(bookmark_dicts, NetworkCallType.SHARE_BOOKMARKS)
                self.network_status.emit(_("All bookmarks shared successfully"), False)
            else:
                # NetworkTab has no bookmark list widget to select from.
                QMessageBox.information(self, _("Share Bookmarks"),
                                        _("Sharing selected bookmarks is not available yet. Check \"{0}\" to share all bookmarks.").format(_("Share All Bookmarks")))
                return
                
        except Exception as e:
            QMessageBox.critical(self, _("Error"), _("Failed to share bookmarks: {0}").format(e))
            self.network_status.emit(_("Failed to share bookmarks"), True)

    def sync_bookmarks(self):
        """Sync bookmarks with connected peers."""
        try:
            if not self.sync_checkbox.isChecked():
                QMessageBox.warning(self, _("Warning"), _("Two-way sync is disabled"))
                return
                
            # Get the current browser
            browser = self.bookmark_manager.current_browser
            if not browser:
                QMessageBox.warning(self, _("Warning"), _("No browser selected"))
                return
                
            # Request remote bookmarks
            self.network_client.request_bookmarks(NetworkCallType.SYNC_BOOKMARKS)
            self.network_status.emit(_("Sync initiated"), False)
            
        except Exception as e:
            QMessageBox.critical(self, _("Error"), _("Failed to sync bookmarks: {0}").format(e))
            self.network_status.emit(_("Failed to sync bookmarks"), True)

    def handle_bookmarks_received(self, bookmark_dicts: List[Dict], call_type: NetworkCallType):
        """Handle received bookmarks from peers."""
        try:
            if self.sync_checkbox.isChecked():
                if call_type == NetworkCallType.SYNC_FOLDER_STRUCTURE:
                    # Handle folder structure sync
                    remote_bookmarks = [BookmarkFolder.from_dict(d) for d in bookmark_dicts]
                else:
                    # Handle individual bookmarks sync
                    remote_bookmarks = [Bookmark.from_dict(d) for d in bookmark_dicts]
                
                # Get the current browser
                browser = self.bookmark_manager.current_browser
                if not browser:
                    QMessageBox.warning(self, _("Warning"), _("No browser selected"))
                    return
                
                # Get local bookmarks
                browser_instance = self.bookmark_manager.get_browser_instance(browser)
                local_bookmarks = browser_instance.get_all_bookmarks() if browser_instance else []
                
                # Merge bookmarks using the bookmark manager
                self.bookmark_manager.merge_bookmarks(local_bookmarks, remote_bookmarks)
                
                # Save merged bookmarks
                self.bookmark_manager.save_bookmarks()
                
                # Refresh the UI
                self.parent().parent().load_bookmarks()
                
                QMessageBox.information(
                    self, 
                    _("Sync Complete"), 
                    _("Successfully synced {0} bookmarks with local collection").format(len(bookmark_dicts))
                )
            else:
                QMessageBox.information(
                    self, 
                    _("Bookmarks Received"), 
                    _("Received {0} bookmarks from remote instance").format(len(bookmark_dicts))
                )
                
        except Exception as e:
            QMessageBox.critical(self, _("Error"), _("Failed to process received bookmarks: {0}").format(e))
            self.status_label.setText(_("Failed to process received bookmarks"))

    def handle_connection_lost(self):
        self.connection_status.update_from_event(ConnectionStatusEvent(
            error_message=_("Connection lost"),
            status_type=NetworkConnectionStatusType.DISCONNECTED
        ))
        QMessageBox.warning(self, _("Connection Lost"), _("The connection to the remote instance was lost"))

    def handle_service_discovered(self, event: ServiceDiscoveredEvent):
        """Handle a discovered service event"""
        self.connection_status.update_from_service_discovery(event)
        self.network_status.emit(self.connection_status.get_status_message(), False)

    def handle_connection_status(self, event: ConnectionStatusEvent):
        """Handle a connection status event"""
        self.connection_status.update_from_event(event)
        self.network_status.emit(
            self.connection_status.get_status_message(), 
            self.connection_status.is_status_type(NetworkConnectionStatusType.ERROR)
        )

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
            logger.error(_("Error during browser cleanup: {0}").format(e), browser="NetworkTab")
        finally:
            loop.close()

        self.timer.stop()
        self.network_client.cleanup() 