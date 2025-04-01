from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTreeView,
                             QLabel, QLineEdit, QMessageBox, QComboBox,
                             QDialog, QFormLayout, QDialogButtonBox)
from PySide6.QtCore import Qt, QModelIndex, QTimer
from PySide6.QtGui import QStandardItemModel, QStandardItem
from models.bookmark_manager import BookmarkManager
from models.bookmark import BrowserType, Bookmark, BookmarkFolder
from typing import Optional, Union, List

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
        self.setWindowTitle("Bookmark Manager")
        self.setMinimumSize(800, 600)
        
        # Initialize bookmark manager
        self.bookmark_manager = BookmarkManager()
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create browser selection area
        browser_layout = QHBoxLayout()
        browser_label = QLabel("Browser:")
        self.browser_combo = QComboBox()
        self._populate_browser_combo()
        browser_layout.addWidget(browser_label)
        browser_layout.addWidget(self.browser_combo)
        browser_layout.addStretch()
        main_layout.addLayout(browser_layout)
        
        # Create search area
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search bookmarks...")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        search_layout.addWidget(self.search_input)
        main_layout.addLayout(search_layout)
        
        # Create bookmark tree view
        self.bookmark_tree = QTreeView()
        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels(["Bookmarks"])
        self.bookmark_tree.setModel(self.tree_model)
        self.bookmark_tree.setSelectionMode(QTreeView.SelectionMode.SingleSelection)
        self.bookmark_tree.setSelectionBehavior(QTreeView.SelectionBehavior.SelectRows)
        main_layout.addWidget(self.bookmark_tree)
        
        # Create button area
        button_layout = QHBoxLayout()
        add_button = QPushButton("Add Bookmark")
        add_button.clicked.connect(self.add_bookmark)
        edit_button = QPushButton("Edit Bookmark")
        edit_button.clicked.connect(self.edit_bookmark)
        delete_button = QPushButton("Delete Bookmark")
        delete_button.clicked.connect(self.delete_bookmark)
        
        button_layout.addWidget(add_button)
        button_layout.addWidget(edit_button)
        button_layout.addWidget(delete_button)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        # Connect browser selection change
        self.browser_combo.currentIndexChanged.connect(self.load_bookmarks)
        
        # Initialize search timer
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.search_bookmarks)
        
        # Load initial bookmarks if a browser is selected
        if self.browser_combo.count() > 0:
            self.load_bookmarks()
    
    def _populate_browser_combo(self):
        """Populate the browser combo box with supported browsers"""
        supported_browsers = self.bookmark_manager.get_supported_browsers()
        for browser, is_supported in supported_browsers.items():
            if is_supported:
                self.browser_combo.addItem(browser.name, browser)
    
    def load_bookmarks(self):
        """Load bookmarks from the selected browser"""
        browser = self.browser_combo.currentData()
        if not browser:
            return
        
        try:
            if self.bookmark_manager.load_browser_bookmarks(browser):
                self._update_tree_view()
            else:
                QMessageBox.warning(self, "Error", "Failed to load bookmarks")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading bookmarks: {str(e)}")
    
    def _on_search_text_changed(self):
        """Handle search text changes with debouncing"""
        self.search_timer.start(300)  # Wait 300ms after last keystroke
    
    def search_bookmarks(self):
        """Search bookmarks based on the search input"""
        query = self.search_input.text().strip()
        if not query:
            self._update_tree_view()  # Reset to show all bookmarks
            return
        
        results = self.bookmark_manager.search_bookmarks(query)
        self._update_tree_view_with_results(results)
    
    def _update_tree_view_with_results(self, results: List[Bookmark]):
        """Update the tree view to show search results"""
        self.tree_model.clear()
        if not results:
            return
        
        # Create a temporary root folder for search results
        root_item = QStandardItem("Search Results")
        self.tree_model.appendRow(root_item)
        
        for bookmark in results:
            item = QStandardItem(bookmark.title)
            item.setData(bookmark, Qt.ItemDataRole.UserRole)
            root_item.appendRow(item)
        
        self.bookmark_tree.expandAll()

    def _update_tree_view(self):
        """Update the tree view with the current bookmark structure"""
        self.tree_model.clear()
        if not self.bookmark_manager.root_folder:
            return
        
        root_item = QStandardItem(self.bookmark_manager.root_folder.title)
        root_item.setData(self.bookmark_manager.root_folder, Qt.ItemDataRole.UserRole)
        self.tree_model.appendRow(root_item)
        
        def add_children(parent_item, folder):
            for child in folder.children:
                item = QStandardItem(child.title)
                item.setData(child, Qt.ItemDataRole.UserRole)
                parent_item.appendRow(item)
                if isinstance(child, BookmarkFolder):
                    add_children(item, child)
        
        add_children(root_item, self.bookmark_manager.root_folder)
        self.bookmark_tree.expandAll()

    def add_bookmark(self):
        """Add a new bookmark"""
        if not self.bookmark_manager.root_folder:
            QMessageBox.warning(self, "Error", "Please select a browser first")
            return
        
        dialog = BookmarkDialog(self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_bookmark_data()
            bookmark = self.bookmark_manager.add_bookmark(
                title=data['title'],
                url=data['url']
            )
            if bookmark:
                self._update_tree_view()
                QMessageBox.information(self, "Success", "Bookmark added successfully")
            else:
                QMessageBox.warning(self, "Error", "Failed to add bookmark")
    
    def edit_bookmark(self):
        """Edit the selected bookmark"""
        if not self.bookmark_manager.root_folder:
            QMessageBox.warning(self, "Error", "Please select a browser first")
            return
        
        selected_bookmark = self._get_selected_bookmark()
        
        if not selected_bookmark:
            QMessageBox.warning(self, "Error", "Please select a bookmark to edit")
            return
        
        dialog = BookmarkDialog(self, selected_bookmark)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_bookmark_data()
            # TODO: Implement bookmark editing in BookmarkManager
            QMessageBox.information(self, "Success", "Bookmark updated successfully")
    
    def delete_bookmark(self):
        """Delete the selected bookmark"""
        if not self.bookmark_manager.root_folder:
            QMessageBox.warning(self, "Error", "Please select a browser first")
            return
        
        selected_bookmark = self._get_selected_bookmark()
        
        if not selected_bookmark:
            QMessageBox.warning(self, "Error", "Please select a bookmark to delete")
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this bookmark?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.bookmark_manager.delete_item(selected_bookmark.id):
                self._update_tree_view()
                QMessageBox.information(self, "Success", "Bookmark deleted successfully")
            else:
                QMessageBox.warning(self, "Error", "Failed to delete bookmark")

    def _get_selected_bookmark(self) -> Optional[Union[Bookmark, BookmarkFolder]]:
        """Get the currently selected bookmark from the tree view"""
        print("Getting selected bookmark...")
        
        selection = self.bookmark_tree.selectedIndexes()
        print(f"Selected indexes: {selection}")
        if not selection:
            print("No selection found")
            return None
            
        index = selection[0]
        print(f"First selected index: {index}")
        if not index.isValid():
            print("Selected index is not valid")
            return None
            
        item = self.tree_model.itemFromIndex(index)
        print(f"Item from index: {item}")
        if not item:
            print("No item found for index")
            return None
            
        bookmark_data = item.data(Qt.ItemDataRole.UserRole)
        print(f"Bookmark data: {bookmark_data}")
        if not bookmark_data:
            print("No bookmark data found in item")
            return None
            
        print(f"Successfully retrieved bookmark: {bookmark_data.title}")
        return bookmark_data 