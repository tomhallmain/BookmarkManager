from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QTreeWidget, QTreeWidgetItem, QMenu,
                             QInputDialog, QDialog, QFormLayout, QLineEdit,
                             QComboBox, QMessageBox, QGroupBox, QSpinBox,
                             QDoubleSpinBox, QCheckBox, QTabWidget, QWidget,
                             QHeaderView)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QAction

from models.bookmark_manager import BookmarkManager
from models.browser_bookmarks import BrowserBookmarks
from models.bookmark import Bookmark, BookmarkFolder
from utils.utils import logger

class BookmarkTab(QWidget):
    def __init__(self, bookmark_manager: BookmarkManager):
        super().__init__()
        self.bookmark_manager = bookmark_manager
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Browser selection
        browser_layout = QHBoxLayout()
        self.browser_combo = QComboBox()
        self.browser_combo.currentIndexChanged.connect(self.on_browser_changed)
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_bookmarks)
        
        browser_layout.addWidget(QLabel("Browser:"))
        browser_layout.addWidget(self.browser_combo)
        browser_layout.addWidget(refresh_button)
        layout.addLayout(browser_layout)
        
        # Bookmark tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Bookmarks")
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.tree)
        
        # Load supported browsers
        self.load_supported_browsers()
        
    def load_supported_browsers(self):
        """Load supported browsers into the combo box, only showing those with valid paths"""
        available_browsers = self.bookmark_manager.load_supported_browsers()
        
        if not available_browsers:
            QMessageBox.critical(self, "Error", "No browser bookmark paths were found")
            return
        
        for browser in available_browsers:
            self.browser_combo.addItem(browser.value, browser)
        
        # Try to find a browser with bookmarks to start with
        logger.debug("Looking for browser with bookmarks to start with")
        for browser in available_browsers:
            browser_instance = self.bookmark_manager.get_browser_instance(browser)
            if browser_instance and browser_instance.has_bookmarks():
                logger.info("Starting with browser as it has bookmarks", browser=browser.value)
                self.browser_combo.setCurrentText(browser.value)
                self.bookmark_manager.current_browser = browser
                break
        else:
            # If no browser has bookmarks, just select the first one
            logger.info("No browser with bookmarks found, selecting first available browser")
            self.browser_combo.setCurrentIndex(0)
            if available_browsers:
                self.bookmark_manager.current_browser = available_browsers[0]
            
    def refresh_bookmarks(self):
        """Refresh bookmarks for the current browser"""
        browser_instance = self.bookmark_manager.get_current_browser_instance()
        if not browser_instance:
            return
            
        logger.debug("Refreshing bookmarks", browser=browser_instance.browser_type.value)
        if browser_instance.refresh_bookmarks():
            logger.info("Successfully refreshed bookmarks, updating tree view", browser=browser_instance.browser_type.value)
            self.tree.clear()
            self.populate_tree(browser_instance.root_folder)
        else:
            logger.error("Failed to refresh bookmarks", browser=browser_instance.browser_type.value)
            QMessageBox.critical(self, "Error", "Failed to refresh bookmarks")
            
    def on_browser_changed(self, index: int):
        """Handle browser selection change"""
        if index >= 0:
            browser = self.browser_combo.currentData()
            logger.debug(f"Browser changed to index {index}", browser=browser.value if browser else None)
            self.bookmark_manager.current_browser = browser
            self.load_bookmarks()
            
    def load_bookmarks(self):
        """Load bookmarks for the selected browser"""
        browser_instance = self.bookmark_manager.get_current_browser_instance()
        if not browser_instance:
            logger.warning("No browser selected")
            return
        
        logger.info("Loading bookmarks", browser=browser_instance.browser_type.value)
        if browser_instance.load_browser_bookmarks():
            logger.info("Successfully loaded bookmarks, updating tree view", browser=browser_instance.browser_type.value)
            self.tree.clear()
            self.populate_tree(browser_instance.root_folder)
        else:
            logger.error("Failed to load bookmarks", browser=browser_instance.browser_type.value)
            QMessageBox.critical(self, "Error", f"Failed to load bookmarks for {browser_instance.browser_type.value}")
            
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
        browser_instance = self.bookmark_manager.get_current_browser_instance()
        if not browser_instance or not browser_instance.root_folder:
            return
            
        bookmark_item = browser_instance.root_folder.find_child(item_id)
        
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
            browser_instance = self.bookmark_manager.get_current_browser_instance()
            if browser_instance:
                browser_instance.save_bookmarks()
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
                browser_instance = self.bookmark_manager.get_current_browser_instance()
                if browser_instance:
                    browser_instance.add_bookmark(title, url, parent_id)
                    browser_instance.save_bookmarks()
                    self.load_bookmarks()
                
    def add_folder(self, parent_id: str = None):
        """Add a new folder"""
        title, ok = QInputDialog.getText(self, "Add Folder", "Enter folder name:")
        if ok and title:
            browser_instance = self.bookmark_manager.get_current_browser_instance()
            if browser_instance:
                browser_instance.add_folder(title, parent_id)
                browser_instance.save_bookmarks()
                self.load_bookmarks()
            
    def delete_bookmark(self, item_id: str):
        """Delete a bookmark or folder"""
        browser_instance = self.bookmark_manager.get_current_browser_instance()
        if browser_instance and browser_instance.delete_item(item_id):
            browser_instance.save_bookmarks()
            self.load_bookmarks() 