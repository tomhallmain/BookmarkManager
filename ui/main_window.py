from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTreeView,
                             QLabel, QLineEdit, QMessageBox, QComboBox,
                             QDialog, QFormLayout, QDialogButtonBox,
                             QTreeWidget, QTreeWidgetItem, QMenu, QTabWidget,
                             QInputDialog, QGroupBox, QSpinBox, QDoubleSpinBox,
                             QCheckBox)
from PySide6.QtCore import Qt, QModelIndex, QTimer, Signal
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon, QAction

from models.bookmark_manager import BookmarkManager
from models.browser_bookmarks import BrowserBookmarks
from models.bookmark import Bookmark, BookmarkFolder
from ui.cross_browser_tab import CrossBrowserTab
from utils.logger import logger
from utils.translations import _
from ui.network_tab import NetworkTab
from ui.bookmark_tab import BookmarkTab
from models.network.network_handler import NetworkHandler
from ui.app_style import AppStyle
import asyncio
import threading

## TODO add a way to access bookmarks from other computers on the same network or via HFS etc

class BookmarkDialog(QDialog):
    """Dialog for adding/editing bookmarks"""
    def __init__(self, parent=None, bookmark=None):
        super().__init__(parent)
        self.bookmark = bookmark
        self.setWindowTitle(_("Add Bookmark") if not bookmark else _("Edit Bookmark"))
        
        layout = QFormLayout(self)
        
        # Title field
        self.title_input = QLineEdit()
        self.title_input.setText(bookmark.title if bookmark else "")
        layout.addRow(_("Title:"), self.title_input)
        
        # URL field
        self.url_input = QLineEdit()
        self.url_input.setText(bookmark.url if bookmark else "")
        layout.addRow(_("URL:"), self.url_input)
        
        # Description field
        self.description_input = QLineEdit()
        self.description_input.setText(bookmark.description if bookmark and bookmark.description else "")
        layout.addRow(_("Description:"), self.description_input)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | 
            QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
    
    def get_bookmark_data(self):
        """Get the bookmark data from the dialog inputs"""
        return {
            'title': self.title_input.text(),
            'url': self.url_input.text(),
            'description': self.description_input.text()
        }

class MainWindow(QMainWindow):
    # Define a signal for status messages
    status_message = Signal(str, bool)  # message, is_error
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(_("Bookmark Manager"))
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize app style
        self.app_style = AppStyle(theme="dark")
        self.setStyleSheet(self.app_style.get_application_style())
        
        # Initialize bookmark manager
        self.bookmark_manager = BookmarkManager()
        
        # Initialize network handler
        self.network_handler = NetworkHandler()
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create status area at the top
        status_layout = QHBoxLayout()
        
        # Main status label
        self.status_label = QLabel(_("Ready"))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(self.app_style.get_status_style())
        self.status_label.setMinimumHeight(30)
        
        # Network status label
        self.network_status_label = QLabel(_("Network: {0}").format(_("Not connected")))
        self.network_status_label.setAlignment(Qt.AlignCenter)
        self.network_status_label.setStyleSheet(self.app_style.get_status_style(is_disabled=True))
        self.network_status_label.setMinimumHeight(30)
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.network_status_label)
        layout.addLayout(status_layout)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet(self.app_style.get_tab_style())
        
        # Create tabs
        self.bookmark_tab = BookmarkTab(self.bookmark_manager)
        self.network_tab = NetworkTab(self.network_handler, self.bookmark_manager)
        self.cross_browser_tab = CrossBrowserTab(self.bookmark_manager)
        
        # Add tabs
        self.tab_widget.addTab(self.bookmark_tab, _("Bookmarks"))
        self.tab_widget.addTab(self.network_tab, _("Network"))
        self.tab_widget.addTab(self.cross_browser_tab, _("Cross-Browser"))
        
        # Connect the status signals to the status labels
        self.bookmark_tab.status_message.connect(self.show_status)
        self.network_tab.network_status.connect(self.show_network_status)
        self.cross_browser_tab.status_message.connect(self.show_status)
        
        layout.addWidget(self.tab_widget)
        
        # Start network handler in a separate thread
        self.network_thread = threading.Thread(target=self._run_network_handler)
        self.network_thread.daemon = True
        self.network_thread.start()
        
        # Show initial loading status
        self.show_status(_("Loading bookmarks..."), False)
        
        # Load bookmarks after a short delay to ensure UI is ready
        QTimer.singleShot(100, self.cross_browser_tab.load_all_browsers)
        
    def _run_network_handler(self):
        """Run the network handler in a separate thread"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.network_handler.start())
        except Exception as e:
            logger.error(_("Error in network handler: {0}").format(e), browser="MainWindow")
        finally:
            loop.close()
            
    def closeEvent(self, event):
        """Handle window close event"""
        logger.info(_("Main window closing, cleaning up resources"))
        
        # Stop network handler in a separate thread
        stop_thread = threading.Thread(target=self._stop_network_handler)
        stop_thread.daemon = True
        stop_thread.start()
        stop_thread.join(timeout=5)  # Wait up to 5 seconds for cleanup
        
        # Only save bookmarks if they've been modified
        if self.bookmark_manager.is_modified:
            logger.info(_("Saving modified bookmarks before closing"))
            self.bookmark_manager.save_all_bookmarks()
        
        event.accept()
        
    def _stop_network_handler(self):
        """Stop the network handler in a separate thread"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.network_handler.stop())
        except Exception as e:
            logger.error(_("Error stopping network handler: {0}").format(e), browser="MainWindow")
        finally:
            loop.close()

    def show_status(self, message: str, is_error: bool = False):
        """Show a status message in the status label"""
        logger.debug(f"Showing status message: {message} (error: {is_error})")
        # Ensure we're on the main thread
        if threading.current_thread() is not threading.main_thread():
            QTimer.singleShot(0, lambda: self.show_status(message, is_error))
            return
            
        self.status_label.setText(message)
        self.status_label.setStyleSheet(self.app_style.get_status_style(is_error=is_error))
        # Make sure the label is visible
        self.status_label.show()
        
        # Only clear temporary status messages
        if message != _("Ready"):
            # Clear the status after 5 seconds
            QTimer.singleShot(5000, lambda: self.show_status(_("Ready"), False))

    def show_network_status(self, message: str, is_error: bool = False):
        """Show a network status message in the network status label"""
        # Ensure we're on the main thread
        if threading.current_thread() is not threading.main_thread():
            QTimer.singleShot(0, lambda: self.show_network_status(message, is_error))
            return
            
        logger.debug(f"Showing network status: {message} (error: {is_error})")
        self.network_status_label.setText(_("Network: {0}").format(message))
        
        # Set style based on status
        is_disabled = message == _("Not connected")
        self.network_status_label.setStyleSheet(self.app_style.get_status_style(is_error=is_error, is_disabled=is_disabled))
        self.network_status_label.show()
        
        # Only clear temporary network status messages
        if message != _("Not connected"):
            # Clear the status after 5 seconds
            QTimer.singleShot(5000, lambda: self.show_network_status(_("Not connected"), False))

    def handle_service_discovered(self, service_info: dict):
        """Handle service discovery events"""
        message = _("Discovered service: {0} at {1}").format(service_info['name'], service_info['address'])
        self.show_network_status(message, False)

    def emit_status(self, message: str, is_error: bool = False):
        """Emit a status message that will be shown in the status label"""
        self.status_message.emit(message, is_error)
