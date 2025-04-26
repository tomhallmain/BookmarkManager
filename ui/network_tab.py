from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QLabel, QMessageBox, QInputDialog, QGroupBox, QLineEdit
)
from PySide6.QtCore import Qt, QTimer
from models.network.service_browser import ServiceBrowser
from models.network.network_client import NetworkClient
from models.network.network_handler import NetworkHandler
from zeroconf import ServiceInfo
import asyncio
from typing import List, Dict
import threading
import logging

logger = logging.getLogger(__name__)

class NetworkTab(QWidget):
    def __init__(self, network_handler: NetworkHandler):
        super().__init__()
        self.network_handler = network_handler
        self.network_client = NetworkClient()
        self.service_browser = ServiceBrowser()
        
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
        bookmarks_group = QGroupBox("Bookmarks to Share")
        bookmarks_layout = QVBoxLayout()
        
        self.bookmark_list = QListWidget()
        self.bookmark_list.setSelectionMode(QListWidget.MultiSelection)
        
        share_button = QPushButton("Share Selected Bookmarks")
        share_button.clicked.connect(self.share_bookmarks)
        
        bookmarks_layout.addWidget(self.bookmark_list)
        bookmarks_layout.addWidget(share_button)
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
            self.status_label.setText(f"Connected to {host}:{port}")
            self.load_bookmarks()
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", str(e))
            self.status_label.setText("Connection failed")

    def connect_to_instance(self):
        selected = self.instance_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "Error", "Please select an instance to connect to")
            return
            
        service = selected.data(Qt.UserRole)
        try:
            self.network_client.connect(service['address'], service['port'])
            self.status_label.setText(f"Connected to {service['name']}")
            self.load_bookmarks()
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", str(e))
            self.status_label.setText("Connection failed")

    def load_bookmarks(self):
        self.bookmark_list.clear()
        # Load bookmarks from your bookmark manager
        # This is a placeholder - implement your bookmark loading logic
        pass

    def share_bookmarks(self):
        selected_items = self.bookmark_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Error", "Please select bookmarks to share")
            return
            
        bookmarks = [item.data(Qt.UserRole) for item in selected_items]
        try:
            self.network_client.send_bookmarks(bookmarks)
            self.status_label.setText("Bookmarks shared successfully")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to share bookmarks: {e}")
            self.status_label.setText("Failed to share bookmarks")

    def handle_connection_lost(self):
        self.status_label.setText("Connection lost")
        QMessageBox.warning(self, "Connection Lost", "The connection to the remote instance was lost")

    def handle_bookmarks_received(self, bookmarks):
        QMessageBox.information(self, "Bookmarks Received", 
                              f"Received {len(bookmarks)} bookmarks from remote instance")
        # Handle received bookmarks - implement your bookmark import logic
        pass

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