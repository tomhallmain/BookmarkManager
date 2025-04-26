from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTreeView,
                             QLabel, QLineEdit, QMessageBox, QComboBox,
                             QDialog, QFormLayout, QDialogButtonBox,
                             QTreeWidget, QTreeWidgetItem, QMenu, QTabWidget)
from PySide6.QtCore import Qt, QModelIndex, QTimer
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon, QAction

from models.bookmark_manager import BrowserBookmarks
from models.bookmark import Bookmark, BookmarkFolder
from ui.cross_browser_window import CrossBrowserWindow
from utils.utils import logger
from ui.network_tab import NetworkTab
from models.network.network_handler import NetworkHandler
import asyncio
import threading

## TODO add a way to access bookmarks from other computers on the same network or via HFS etc

class BookmarkDialog(QDialog):
    """Dialog for adding/editing bookmarks"""
    def __init__(self, parent=None, bookmark=None):
        super().__init__(parent)
        self.bookmark = bookmark
        self.setWindowTitle("Add Bookmark" if not bookmark else "Edit Bookmark")
        
        layout = QFormLayout(self)
        
        # Title field
        self.title_input = QLineEdit()
        self.title_input.setText(bookmark.title if bookmark else "")
        layout.addRow("Title:", self.title_input)
        
        # URL field
        self.url_input = QLineEdit()
        self.url_input.setText(bookmark.url if bookmark else "")
        layout.addRow("URL:", self.url_input)
        
        # Description field
        self.description_input = QLineEdit()
        self.description_input.setText(bookmark.description if bookmark and bookmark.description else "")
        layout.addRow("Description:", self.description_input)
        
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
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BookmarkManager")
        self.setGeometry(100, 100, 800, 600)
        
        # Initialize bookmark manager
        self.bookmark_manager = BrowserBookmarks()
        
        # Initialize network components
        self.network_handler = NetworkHandler()
        self.network_tab = NetworkTab(self.network_handler)
        
        # Start network server in a separate thread
        self.server_thread = threading.Thread(target=self._run_server)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        self.setup_ui()

    def setup_ui(self):
        # Create tab widget
        tab_widget = QTabWidget()
        
        # Create main tab for bookmarks
        main_tab = QWidget()
        main_layout = QVBoxLayout(main_tab)
        
        # Browser selection
        browser_layout = QHBoxLayout()
        self.browser_combo = QComboBox()
        self.browser_combo.currentIndexChanged.connect(self.on_browser_changed)
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_bookmarks)
        
        browser_layout.addWidget(QLabel("Browser:"))
        browser_layout.addWidget(self.browser_combo)
        browser_layout.addWidget(refresh_button)
        main_layout.addLayout(browser_layout)
        
        # Bookmark tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Bookmarks")
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        main_layout.addWidget(self.tree)
        
        # Add tabs
        tab_widget.addTab(main_tab, "Bookmarks")
        tab_widget.addTab(self.network_tab, "Network")
        
        self.setCentralWidget(tab_widget)
        
        # Load supported browsers
        self.load_supported_browsers()

    def _run_server(self):
        """Run the network server in a separate thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.network_handler.start())
        except Exception as e:
            logger.error(f"Error starting network server: {e}", browser="MainWindow")
        finally:
            loop.close()

    async def _cleanup_network(self):
        """Clean up network resources."""
        await self.network_handler.stop()
        self.network_tab.cleanup()

    def closeEvent(self, event):
        """Clean up resources when closing the window."""
        # Create a new event loop for cleanup
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._cleanup_network())
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", browser="MainWindow")
        finally:
            loop.close()
        event.accept()

    def load_supported_browsers(self):
        """Load supported browsers into the combo box, only showing those with valid paths"""
        logger.info("Loading supported browsers")
        supported_browsers = self.bookmark_manager.get_supported_browsers()
        available_browsers = []
        
        for browser, is_supported in supported_browsers.items():
            if is_supported and self.bookmark_manager.has_valid_bookmark_path(browser):
                logger.debug("Adding to available browsers", browser=browser.value)
                available_browsers.append(browser)
        
        if not available_browsers:
            logger.error("No available browsers found")
            QMessageBox.critical(self, "Error", "No browser bookmark paths were found")
            return
        
        for browser in available_browsers:
            self.browser_combo.addItem(browser.value, browser)
        
        # Try to find a browser with bookmarks to start with
        logger.debug("Looking for browser with bookmarks to start with")
        for browser in available_browsers:
            if self.bookmark_manager.load_browser_bookmarks(browser) and self.bookmark_manager.has_bookmarks():
                logger.info("Starting with browser as it has bookmarks", browser=browser.value)
                self.browser_combo.setCurrentText(browser.value)
                break
        else:
            # If no browser has bookmarks, just select the first one
            logger.info("No browser with bookmarks found, selecting first available browser")
            self.browser_combo.setCurrentIndex(0)
    
    def refresh_bookmarks(self):
        """Refresh bookmarks for the current browser"""
        browser = self.browser_combo.currentData()
        logger.debug("Refreshing bookmarks", browser=browser.value if browser else None)
        if self.bookmark_manager.refresh_bookmarks():
            logger.info("Successfully refreshed bookmarks, updating tree view", browser=browser.value if browser else None)
            self.tree.clear()
            self.populate_tree(self.bookmark_manager.root_folder)
        else:
            logger.error("Failed to refresh bookmarks", browser=browser.value if browser else None)
            QMessageBox.critical(self, "Error", "Failed to refresh bookmarks")
    
    def on_browser_changed(self, index: int):
        """Handle browser selection change"""
        if index >= 0:
            browser = self.browser_combo.currentData()
            logger.debug(f"Browser changed to index {index}", browser=browser.value if browser else None)
            self.load_bookmarks()
    
    def load_bookmarks(self):
        """Load bookmarks for the selected browser"""
        browser = self.browser_combo.currentData()
        if not browser:
            logger.warning("No browser selected")
            return
        
        logger.info("Loading bookmarks", browser=browser.value)
        if self.bookmark_manager.load_browser_bookmarks(browser):
            logger.info("Successfully loaded bookmarks, updating tree view", browser=browser.value)
            self.tree.clear()
            self.populate_tree(self.bookmark_manager.root_folder)
        else:
            logger.error("Failed to load bookmarks", browser=browser.value)
            QMessageBox.critical(self, "Error", f"Failed to load bookmarks for {browser.value}")
    
    def populate_tree(self, folder: BookmarkFolder, parent_item: QTreeWidgetItem = None):
        """Populate the tree widget with bookmarks"""
        if parent_item is None:
            parent_item = self.tree
        
        for child in folder.children:
            if isinstance(child, BookmarkFolder):
                folder_item = QTreeWidgetItem(parent_item)
                folder_item.setText(0, child.title)
                folder_item.setData(0, Qt.UserRole, child.id)
                folder_item.setIcon(0, QIcon("icons/folder.png"))
                self.populate_tree(child, folder_item)
            else:
                bookmark_item = QTreeWidgetItem(parent_item)
                bookmark_item.setText(0, child.title)
                bookmark_item.setData(0, Qt.UserRole, child.id)
                bookmark_item.setIcon(0, QIcon("icons/bookmark.png"))
    
    def show_context_menu(self, position):
        """Show context menu for the selected item"""
        item = self.tree.itemAt(position)
        if not item:
            return
        
        menu = QMenu()
        
        # Get the bookmark/folder ID from the item
        item_id = item.data(0, Qt.UserRole)
        
        # Find the corresponding bookmark/folder
        bookmark_item = self.bookmark_manager.root_folder.find_child(item_id)
        
        if isinstance(bookmark_item, Bookmark):
            # Bookmark actions
            open_action = QAction("Open in Browser", self)
            open_action.triggered.connect(lambda: self.open_bookmark(bookmark_item))
            menu.addAction(open_action)
            
            edit_action = QAction("Edit", self)
            edit_action.triggered.connect(lambda: self.edit_bookmark(bookmark_item))
            menu.addAction(edit_action)
            
            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self.delete_bookmark(item_id))
            menu.addAction(delete_action)
        else:
            # Folder actions
            add_bookmark_action = QAction("Add Bookmark", self)
            add_bookmark_action.triggered.connect(lambda: self.add_bookmark(item_id))
            menu.addAction(add_bookmark_action)
            
            add_folder_action = QAction("Add Folder", self)
            add_folder_action.triggered.connect(lambda: self.add_folder(item_id))
            menu.addAction(add_folder_action)
            
            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self.delete_bookmark(item_id))
            menu.addAction(delete_action)
        
        menu.exec_(self.tree.mapToGlobal(position))
    
    def open_bookmark(self, bookmark: Bookmark):
        """Open the bookmark in the default browser"""
        import webbrowser
        webbrowser.open(bookmark.url)
    
    def edit_bookmark(self, bookmark: Bookmark):
        """Edit a bookmark's title and URL"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Bookmark")
        layout = QFormLayout(dialog)
        
        title_edit = QLineEdit(bookmark.title)
        url_edit = QLineEdit(bookmark.url)
        
        layout.addRow("Title:", title_edit)
        layout.addRow("URL:", url_edit)
        
        buttons = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        
        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addRow(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            bookmark.title = title_edit.text()
            bookmark.url = url_edit.text()
            self.bookmark_manager.save_bookmarks()
            self.load_bookmarks()
    
    def add_bookmark(self, parent_id: str = None):
        """Add a new bookmark"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Bookmark")
        layout = QFormLayout(dialog)
        
        title_edit = QLineEdit()
        url_edit = QLineEdit()
        
        layout.addRow("Title:", title_edit)
        layout.addRow("URL:", url_edit)
        
        buttons = QHBoxLayout()
        ok_button = QPushButton("OK")
        cancel_button = QPushButton("Cancel")
        
        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        
        buttons.addWidget(ok_button)
        buttons.addWidget(cancel_button)
        layout.addRow(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            title = title_edit.text()
            url = url_edit.text()
            
            if title and url:
                self.bookmark_manager.add_bookmark(title, url, parent_id)
                self.bookmark_manager.save_bookmarks()
                self.load_bookmarks()
    
    def add_folder(self, parent_id: str = None):
        """Add a new folder"""
        title, ok = QInputDialog.getText(self, "Add Folder", "Enter folder name:")
        if ok and title:
            self.bookmark_manager.add_folder(title, parent_id)
            self.bookmark_manager.save_bookmarks()
            self.load_bookmarks()
    
    def delete_bookmark(self, item_id: str):
        """Delete a bookmark or folder"""
        if self.bookmark_manager.delete_item(item_id):
            self.bookmark_manager.save_bookmarks()
            self.load_bookmarks()
    
    def open_cross_browser_window(self):
        """Open the cross-browser operations window"""
        self.cross_browser_window = CrossBrowserWindow(self)
        self.cross_browser_window.show() 
