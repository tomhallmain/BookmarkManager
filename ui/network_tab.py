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

class NetworkTab(QWidget):
    def __init__(self, network_handler: NetworkHandler, parent=None):
        super().__init__(parent)
        self.network_handler = network_handler
        self.network_client = NetworkClient()
        self.service_browser = ServiceBrowser()
        self.connected_peers: Dict[str, str] = {}  # name -> address
        self.setup_ui()
        self.setup_timer()
        self.setup_connections()
        self.refresh_instances()

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

    def setup_connections(self):
        self.service_browser.service_added.connect(self.add_instance)
        self.service_browser.service_removed.connect(self.remove_instance)
        self.network_client.connection_lost.connect(self.handle_connection_lost)
        self.network_client.bookmarks_received.connect(self.handle_bookmarks_received)

    def refresh_instances(self):
        self.instance_list.clear()
        self.service_browser.start_browsing()

    def add_instance(self, name: str, info: ServiceInfo):
        item = QListWidgetItem(f"{name} ({info.address})")
        item.setData(Qt.UserRole, info)
        self.instance_list.addItem(item)

    def remove_instance(self, name: str):
        for i in range(self.instance_list.count()):
            item = self.instance_list.item(i)
            if item.text().startswith(name):
                self.instance_list.takeItem(i)
                break

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
            
        info = selected.data(Qt.UserRole)
        try:
            self.network_client.connect(info.address, info.port)
            self.status_label.setText(f"Connected to {info.name}")
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
        self.service_browser.stop_browsing()
        self.network_client.disconnect()
        super().closeEvent(event)

    def cleanup(self):
        self.timer.stop()
        self.service_browser.cleanup()
        asyncio.get_event_loop().run_until_complete(self.network_client.cleanup()) 