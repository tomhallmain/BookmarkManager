from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTreeView,
                             QLabel, QLineEdit, QMessageBox, QComboBox,
                             QDialog, QFormLayout, QDialogButtonBox,
                             QTreeWidget, QTreeWidgetItem, QMenu)
from PySide6.QtCore import Qt, QModelIndex, QTimer
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon, QAction
from models.bookmark_manager import BrowserBookmarks, BookmarkManager, BrowserType
from models.bookmark import Bookmark, BookmarkFolder
from ui.cross_browser_window import CrossBrowserWindow

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
        self.setWindowTitle("Safari Bookmark Manager")
        self.setMinimumSize(800, 600)
        
        # Initialize bookmark manager
        self.bookmark_manager = BrowserBookmarks()
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create top toolbar
        toolbar = QHBoxLayout()
        
        # Browser selection
        self.browser_combo = QComboBox()
        self.browser_combo.currentIndexChanged.connect(self.on_browser_changed)
        toolbar.addWidget(QLabel("Browser:"))
        toolbar.addWidget(self.browser_combo)
        
        # Add cross-browser button
        self.cross_browser_btn = QPushButton("Cross-Browser Operations")
        self.cross_browser_btn.clicked.connect(self.open_cross_browser_window)
        toolbar.addWidget(self.cross_browser_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Create bookmark tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Bookmarks"])
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.tree)
        
        # Load supported browsers and try to load bookmarks
        self.load_supported_browsers()
    
    def load_supported_browsers(self):
        """Load supported browsers into the combo box, only showing those with valid paths and bookmarks"""
        supported_browsers = self.bookmark_manager.get_supported_browsers()
        available_browsers = []
        
        for browser, is_supported in supported_browsers.items():
            if is_supported and self.bookmark_manager.has_valid_bookmark_path(browser):
                available_browsers.append(browser)
        
        if not available_browsers:
            QMessageBox.critical(self, "Error", "No browser bookmark paths were found")
            return
        
        for browser in available_browsers:
            self.browser_combo.addItem(browser.value, browser)
        
        # Try to load bookmarks for the first available browser
        if self.browser_combo.count() > 0:
            self.load_bookmarks()
    
    def on_browser_changed(self, index: int):
        """Handle browser selection change"""
        if index >= 0:
            self.load_bookmarks()
    
    def load_bookmarks(self):
        """Load bookmarks for the selected browser, trying next browser if current fails"""
        browser = self.browser_combo.currentData()
        if not browser:
            return
        
        if self.bookmark_manager.load_browser_bookmarks(browser):
            self.tree.clear()
            self.populate_tree(self.bookmark_manager.root_folder)
        else:
            # Try next browser if available
            current_index = self.browser_combo.currentIndex()
            if current_index < self.browser_combo.count() - 1:
                self.browser_combo.setCurrentIndex(current_index + 1)
            else:
                # We've tried all browsers and none worked
                browsers_tried = [self.browser_combo.itemText(i) for i in range(self.browser_combo.count())]
                QMessageBox.critical(
                    self, 
                    "Error", 
                    f"Tried to gather bookmarks for browsers {', '.join(browsers_tried)}, but none were successful."
                )
    
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