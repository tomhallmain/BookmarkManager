from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QLineEdit, QTreeWidget, QTreeWidgetItem,
                             QMessageBox, QGroupBox, QSpinBox, QDoubleSpinBox,
                             QCheckBox, QTabWidget, QMenu, QWidget, QHeaderView)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QIcon, QAction
from typing import Optional

from models.bookmark_manager import BookmarkManager
from models.bookmark import Bookmark, BrowserType
from utils.utils import are_urls_similar, url_similarity, logger

class CrossBrowserTab(QWidget):
    # Define a signal for status messages
    status_message = Signal(str, bool)  # message, is_error
    
    def __init__(self, bookmark_manager: BookmarkManager):
        super().__init__()
        
        # Store the provided bookmark manager and main window
        self.bookmark_manager = bookmark_manager
        
        # Create main layout
        layout = QVBoxLayout(self)
        
        # Create tab widget
        tabs = QTabWidget()
        
        # Add search tab
        search_tab = QWidget()
        search_layout = QVBoxLayout(search_tab)
        
        # Search controls
        search_controls = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search across all browsers...")
        self.search_input.returnPressed.connect(self.search_bookmarks)
        search_button = QPushButton("Search")
        search_button.clicked.connect(self.search_bookmarks)
        search_controls.addWidget(self.search_input)
        search_controls.addWidget(search_button)
        search_layout.addLayout(search_controls)
        
        # Search results
        self.search_results = QTreeWidget()
        self.search_results.setHeaderLabels(["Title", "URL", "Browser"])
        self.search_results.setContextMenuPolicy(Qt.CustomContextMenu)
        self.search_results.customContextMenuRequested.connect(self.show_search_context_menu)
        # Set columns to stretch
        header = self.search_results.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)  # Title
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)  # URL
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive) # Browser
        # Set initial column widths (percentages)
        self.search_results.setColumnWidth(0, int(self.width() * 0.4))  # Title: 40%
        self.search_results.setColumnWidth(1, int(self.width() * 0.4))  # URL: 40%
        self.search_results.setColumnWidth(2, int(self.width() * 0.2))  # Browser: 20%
        search_layout.addWidget(self.search_results)
        
        # Set the layout for search tab
        search_tab.setLayout(search_layout)
        
        # Add similar bookmarks tab
        similar_tab = QWidget()
        similar_layout = QVBoxLayout(similar_tab)
        
        # Similar bookmarks controls
        similar_controls = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter URL to find similar bookmarks...")
        self.url_input.returnPressed.connect(self.find_similar_bookmarks)
        find_button = QPushButton("Find Similar")
        find_button.clicked.connect(self.find_similar_bookmarks)
        similar_controls.addWidget(self.url_input)
        similar_controls.addWidget(find_button)
        
        # Similarity threshold
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Similarity threshold:"))
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.0, 1.0)
        self.threshold_spin.setValue(0.8)
        self.threshold_spin.setSingleStep(0.1)
        threshold_layout.addWidget(self.threshold_spin)
        
        similar_controls.addLayout(threshold_layout)
        similar_layout.addLayout(similar_controls)
        
        # Similar bookmarks results
        self.similar_results = QTreeWidget()
        self.similar_results.setHeaderLabels(["Title", "URL", "Browser", "Similarity"])
        self.similar_results.setContextMenuPolicy(Qt.CustomContextMenu)
        self.similar_results.customContextMenuRequested.connect(self.show_similar_context_menu)
        # Set columns to stretch
        header = self.similar_results.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)  # Title
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)  # URL
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive) # Browser
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive) # Similarity
        # Set initial column widths (percentages)
        self.similar_results.setColumnWidth(0, int(self.width() * 0.4))  # Title: 40%
        self.similar_results.setColumnWidth(1, int(self.width() * 0.4))  # URL: 40%
        self.similar_results.setColumnWidth(2, int(self.width() * 0.1))  # Browser: 10%
        self.similar_results.setColumnWidth(3, int(self.width() * 0.1))  # Similarity: 10%
        similar_layout.addWidget(self.similar_results)
        
        # Set the layout for similar tab
        similar_tab.setLayout(similar_layout)
        
        # Add tabs to widget
        tabs.addTab(search_tab, "Search")
        tabs.addTab(similar_tab, "Similar Bookmarks")
        
        layout.addWidget(tabs)
        
        # Add buttons
        button_layout = QHBoxLayout()
        load_button = QPushButton("Load All Browsers")
        load_button.clicked.connect(self.load_all_browsers)
        save_button = QPushButton("Save All Changes")
        save_button.clicked.connect(self.save_all_changes)
        
        button_layout.addWidget(load_button)
        button_layout.addWidget(save_button)
        layout.addLayout(button_layout)
        
        # Load all browsers initially
        self.load_all_browsers()

        # Add resize event handler to maintain column proportions
        self.resizeEvent = self.on_resize
        
        # Set focus to search input when shown
        self.search_input.setFocus()
    
    def load_all_browsers(self):
        """Load bookmarks from all supported browsers"""
        logger.info("Loading bookmarks from all supported browsers")
        results = self.bookmark_manager.load_all_browsers()
        success_count = sum(1 for success in results.values() if success)
        logger.debug(f"Browser load results: {results}")
        
        if success_count > 0:
            logger.info(f"Successfully loaded bookmarks from {success_count} browsers")
            # Emit status signal
            self.status_message.emit(f"Successfully loaded bookmarks from {success_count} browsers", False)
            # Try a test search to verify bookmarks are loaded
            self.search_input.setText("")
            self.search_bookmarks()
        else:
            logger.warning("No bookmarks were loaded from any browser")
            # Emit status signal
            self.status_message.emit("No bookmarks were loaded", True)
    
    def save_all_changes(self):
        """Save changes to all browsers"""
        logger.info("Saving changes to all browsers")
        results = self.bookmark_manager.save_all_bookmarks()
        success_count = sum(1 for success in results.values() if success)
        if success_count > 0:
            logger.info(f"Successfully saved changes to {success_count} browsers")
            QMessageBox.information(self, "Success", f"Saved changes to {success_count} browsers")
        else:
            logger.warning("No changes were saved to any browser")
            QMessageBox.warning(self, "Warning", "No changes were saved")
    
    def search_bookmarks(self):
        """Search for bookmarks across all browsers"""
        query = self.search_input.text().strip()
        if not query:
            logger.debug("Empty search query, clearing results")
            self.search_results.clear()
            return
        
        logger.info(f"Searching for bookmarks with query: {query}")
        self.status_message.emit(f"Searching for: {query}", False)
        
        try:
            results = self.bookmark_manager.search_all_bookmarks(query)
            logger.debug(f"Found {len(results)} results for query: {query}")
            
            self.search_results.clear()
            if not results:
                logger.info("No results found")
                self.status_message.emit("No results found", False)
                return
                
            logger.info(f"Found {len(results)} results")
            self.status_message.emit(f"Found {len(results)} results", False)
            
            for bookmark in results:
                item = QTreeWidgetItem(self.search_results)
                item.setText(0, bookmark.title)
                item.setText(1, bookmark.url)
                item.setText(2, bookmark.browser.value if bookmark.browser else "Unknown")
                item.setData(0, Qt.UserRole, bookmark)
                
        except Exception as e:
            logger.error(f"Error searching bookmarks: {e}")
            self.status_message.emit(f"Error searching: {str(e)}", True)
    
    def find_similar_bookmarks(self):
        """Find bookmarks with similar URLs"""
        url = self.url_input.text().strip()
        if not url:
            logger.debug("Empty URL input, clearing results")
            self.similar_results.clear()
            return
        
        threshold = self.threshold_spin.value()
        logger.info(f"Finding similar URLs to: {url} with threshold {threshold:.2f}")
        self.status_message.emit(f"Finding similar bookmarks...", False)
        
        try:
            results = self.bookmark_manager.find_similar_bookmarks(url, threshold)
            logger.debug(f"Found {len(results)} similar bookmarks for URL: {url}")
            
            self.similar_results.clear()
            if not results:
                logger.info("No similar bookmarks found")
                self.status_message.emit("No similar bookmarks found", False)
                return
                
            logger.info(f"Found {len(results)} similar bookmarks")
            self.status_message.emit(f"Found {len(results)} similar bookmarks", False)
            
            for bookmark in results:
                similarity = are_urls_similar(url, bookmark.url)
                item = QTreeWidgetItem(self.similar_results)
                item.setText(0, bookmark.title)
                item.setText(1, bookmark.url)
                item.setText(2, bookmark.browser.value if bookmark.browser else "Unknown")
                
                # Determine similarity type and display descriptive text
                sim_text = f"{similarity:.2f}"
                if similarity == 1.0:
                    sim_text = "Exact"
                elif similarity >= 0.9:
                    sim_text = "Word Match"
                elif similarity >= 0.8:
                    sim_text = "Substring"
                elif similarity >= 0.5:
                    sim_text = "Similar"
                else:
                    sim_text = f"Low ({similarity:.2f})"
                    
                item.setText(3, sim_text)
                item.setData(0, Qt.UserRole, bookmark)
                
        except Exception as e:
            logger.error(f"Error finding similar bookmarks: {e}")
            self.status_message.emit(f"Error finding similar bookmarks: {str(e)}", True)
    
    def show_search_context_menu(self, position):
        """Show context menu for search results"""
        item = self.search_results.itemAt(position)
        if not item:
            return
        
        bookmark = item.data(0, Qt.UserRole)
        if not isinstance(bookmark, Bookmark):
            return
        
        menu = QMenu()
        
        # Add actions
        open_action = QAction("Open in Browser", self)
        open_action.triggered.connect(lambda: self.open_bookmark(bookmark))
        menu.addAction(open_action)
        
        menu.exec_(self.search_results.mapToGlobal(position))
    
    def show_similar_context_menu(self, position):
        """Show context menu for similar bookmarks results"""
        item = self.similar_results.itemAt(position)
        if not item:
            return
        
        bookmark = item.data(0, Qt.UserRole)
        if not isinstance(bookmark, Bookmark):
            return
        
        menu = QMenu()
        
        # Add actions
        open_action = QAction("Open in Browser", self)
        open_action.triggered.connect(lambda: self.open_bookmark(bookmark))
        menu.addAction(open_action)
        
        menu.exec_(self.similar_results.mapToGlobal(position))
    
    def open_bookmark(self, bookmark: Bookmark):
        """Open the bookmark in the default browser"""
        logger.info(f"Opening bookmark: {bookmark.url}", browser=bookmark.browser.value if bookmark.browser else None)
        import webbrowser
        webbrowser.open(bookmark.url)
        self.status_message.emit(f"Opened: {bookmark.title}", False)

    def on_resize(self, event):
        """Handle window resize event to maintain column proportions"""
        logger.debug("Adjusting column widths after window resize")
        # Update column widths
        header = self.search_results.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)  # Title
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)  # URL
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive) # Browser
        # Set initial column widths (percentages)
        self.search_results.setColumnWidth(0, int(self.width() * 0.4))  # Title: 40%
        self.search_results.setColumnWidth(1, int(self.width() * 0.4))  # URL: 40%
        self.search_results.setColumnWidth(2, int(self.width() * 0.2))  # Browser: 20%

        header = self.similar_results.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)  # Title
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)  # URL
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive) # Browser
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive) # Similarity
        # Set initial column widths (percentages)
        self.similar_results.setColumnWidth(0, int(self.width() * 0.4))  # Title: 40%
        self.similar_results.setColumnWidth(1, int(self.width() * 0.4))  # URL: 40%
        self.similar_results.setColumnWidth(2, int(self.width() * 0.1))  # Browser: 10%
        self.similar_results.setColumnWidth(3, int(self.width() * 0.1))  # Similarity: 10% 