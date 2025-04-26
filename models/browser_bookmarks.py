from typing import List, Optional, Union, Dict
from pathlib import Path
import os

from .bookmark import Bookmark, BookmarkFolder, BrowserType
from .browser_parsers import SafariParser, ChromeParser, EdgeParser, FirefoxParser
from .path_manager import PathManager
from utils.utils import url_similarity, logger

class BrowserBookmarks:
    """Manages bookmarks for a single browser instance"""
    
    def __init__(self, browser: BrowserType, path_manager: PathManager):
        self.browser_type = browser
        self.root_folder = None
        self.path_manager = path_manager
        self.is_modified = False
        
        # Initialize the appropriate parser based on browser type
        if browser == BrowserType.SAFARI:
            self.parser = SafariParser()
        elif browser == BrowserType.FIREFOX:
            self.parser = FirefoxParser()
        elif browser == BrowserType.EDGE:
            self.parser = EdgeParser()
        else:  # All Chromium-based browsers use Chrome's format
            self.parser = ChromeParser()

    def has_valid_bookmark_path(self) -> bool:
        """Check if the current browser has a valid bookmark path that exists and is accessible"""
        try:
            logger.debug("Checking bookmark path", browser=self.browser_type.value)
            bookmark_paths = self.path_manager.get_bookmark_paths(self.browser_type)
            if not bookmark_paths:
                logger.warning("No bookmark paths found", browser=self.browser_type.value)
                return False
            
            # Check if the main bookmark file exists and is accessible
            main_path = Path(bookmark_paths[0])
            if not main_path.exists():
                logger.warning(f"No bookmark file found at \"{main_path}\"", browser=self.browser_type.value)
                return False
            
            if not main_path.is_file():
                logger.warning(f"Bookmark path at \"{main_path}\" is not a file", browser=self.browser_type.value)
                return False
            
            # Check if we have read access
            if not os.access(main_path, os.R_OK):
                logger.warning(f"No read access to bookmark file at \"{main_path}\"", browser=self.browser_type.value)
                return False
            
            # Try to load bookmarks to verify they can be read
            logger.debug("Attempting to load bookmarks", browser=self.browser_type.value)
            if not self.load_browser_bookmarks():
                logger.error("Failed to load bookmarks", browser=self.browser_type.value)
                return False
            
            logger.debug("Successfully validated bookmark path", browser=self.browser_type.value)
            return True
        except Exception as e:
            logger.error(f"Error checking bookmark path: {e}", browser=self.browser_type.value)
            return False

    def has_bookmarks(self) -> bool:
        """Check if the current browser has any bookmarks"""
        if not self.root_folder:
            logger.warning("No root folder found when checking for bookmarks", browser=self.browser_type.value)
            return False
        
        def count_bookmarks(folder: BookmarkFolder) -> int:
            count = 0
            for child in folder.children:
                if isinstance(child, Bookmark):
                    count += 1
                elif isinstance(child, BookmarkFolder):
                    count += count_bookmarks(child)
            return count
        
        bookmark_count = count_bookmarks(self.root_folder)
        logger.debug(f"Found {bookmark_count} bookmarks", browser=self.browser_type.value)
        return bookmark_count > 0

    def refresh_bookmarks(self) -> bool:
        """Reload bookmarks from disk for the current browser"""
        logger.debug("Refreshing bookmarks", browser=self.browser_type.value)
        success = self.load_browser_bookmarks()
        if success:
            logger.debug("Successfully refreshed bookmarks", browser=self.browser_type.value)
        else:
            logger.error("Failed to refresh bookmarks", browser=self.browser_type.value)
        return success

    def get_supported_browsers(self) -> Dict[BrowserType, bool]:
        """Get a dictionary of supported browsers for the current platform"""
        return self.path_manager.get_supported_browsers()

    def load_browser_bookmarks(self) -> bool:
        """Load bookmarks from the current browser"""
        try:
            bookmark_paths = self.path_manager.get_bookmark_paths(self.browser_type)
            if not bookmark_paths:
                return False
                
            # Parse the main bookmarks file
            self.root_folder = self.parser.parse(bookmark_paths[0])
            
            # For Chromium-based browsers, we need to handle the root structure
            if self.browser_type.is_chromium_based():
                logger.debug(f"Initial root folder title: {self.root_folder.title}", browser=self.browser_type.value)
                logger.debug(f"Initial root folder children: {[child.title for child in self.root_folder.children]}", browser=self.browser_type.value)
                
                # Create a new root folder to hold all the special folders
                new_root = BookmarkFolder(title="Bookmarks")
                
                # The parser should have created three folders: bookmark_bar, other, and synced
                # We need to rename them appropriately
                for child in self.root_folder.children:
                    if isinstance(child, BookmarkFolder):
                        if child.title == "Bookmarks Bar":  # bookmark_bar
                            new_root.add_child(child)
                            logger.debug(f"Added Bookmarks Bar folder with {len(child.children)} children", browser=self.browser_type.value)
                        elif child.title == "Other Bookmarks":  # other
                            new_root.add_child(child)
                            logger.debug(f"Added Other Bookmarks folder with {len(child.children)} children", browser=self.browser_type.value)
                        elif child.title == "Mobile Bookmarks":  # synced
                            new_root.add_child(child)
                            logger.debug(f"Added Mobile Bookmarks folder with {len(child.children)} children", browser=self.browser_type.value)
                    else:
                        logger.debug(f"Skipped non-folder item: {type(child)} with title '{child.title}'", browser=self.browser_type.value)
                
                logger.debug(f"Final root folder children: {[child.title for child in new_root.children]}", browser=self.browser_type.value)
                # Set the new root folder
                self.root_folder = new_root
            
            # Set the browser type for the entire bookmark tree
            self.root_folder.set_browser(self.browser_type)
            return True
        except Exception as e:
            logger.error(f"Error loading bookmarks: {e}", browser=self.browser_type.value)
            return False

    def save_bookmarks(self) -> bool:
        """Save current bookmarks back to the browser's file"""
        if not self.parser or not self.root_folder:
            return False
        
        try:
            bookmark_paths = self.path_manager.get_bookmark_paths(self.browser_type)
            if not bookmark_paths:
                return False
                
            # Save to the main bookmarks file
            self.parser.save(bookmark_paths[0])

            return True
        except Exception as e:
            logger.error(f"Error saving bookmarks: {e}", browser=self.browser_type.value)
            return False

    def add_bookmark(self, title: str, url: str, parent_id: Optional[str] = None) -> Optional[Bookmark]:
        """Add a new bookmark to the specified folder"""
        if not self.root_folder:
            return None
        
        bookmark = Bookmark(title=title, url=url)
        target_folder = self.root_folder
        
        if parent_id:
            found = self.root_folder.find_child(parent_id)
            if found and isinstance(found, BookmarkFolder):
                target_folder = found
        
        target_folder.add_child(bookmark)
        self.is_modified = True  # Set modified flag
        return bookmark

    def add_folder(self, title: str, parent_id: Optional[str] = None) -> Optional[BookmarkFolder]:
        """Add a new folder to the specified parent folder"""
        if not self.root_folder:
            return None
        
        folder = BookmarkFolder(title=title)
        target_folder = self.root_folder
        
        if parent_id:
            found = self.root_folder.find_child(parent_id)
            if found and isinstance(found, BookmarkFolder):
                target_folder = found
        
        target_folder.add_child(folder)
        self.is_modified = True  # Set modified flag
        return folder

    def delete_item(self, item_id: str) -> bool:
        """Delete a bookmark or folder by its ID"""
        if not self.root_folder:
            return False
        
        # Find the parent folder
        def find_parent(folder: BookmarkFolder, target_id: str) -> Optional[BookmarkFolder]:
            for child in folder.children:
                if child.id == target_id:
                    return folder
                if isinstance(child, BookmarkFolder):
                    found = find_parent(child, target_id)
                    if found:
                        return found
            return None
        
        parent = find_parent(self.root_folder, item_id)
        if parent:
            parent.remove_child(item_id)
            self.is_modified = True  # Set modified flag
            return True
        return False

    def edit_bookmark(self, bookmark: Bookmark, title: str, url: str) -> bool:
        """Edit a bookmark's title and URL"""
        if not bookmark:
            return False
        
        bookmark.title = title
        bookmark.url = url
        self.is_modified = True  # Set modified flag
        return True

    def search_bookmarks(self, query: str) -> List[Bookmark]:
        """Search for bookmarks matching the query"""
        if not self.root_folder:
            return []
        
        results = []
        query = query.lower()
        
        def search_folder(folder: BookmarkFolder):
            for child in folder.children:
                if isinstance(child, Bookmark):
                    if (query in child.title.lower() or 
                        query in child.url.lower() or 
                        (child.description and query in child.description.lower())):
                        results.append(child)
                else:
                    search_folder(child)
        
        search_folder(self.root_folder)
        return results

    def get_folder_contents(self, folder_id: Optional[str] = None) -> List[Union[Bookmark, BookmarkFolder]]:
        """Get the contents of a specific folder or the root folder"""
        if not self.root_folder:
            return []
        
        if folder_id:
            found = self.root_folder.find_child(folder_id)
            if found and isinstance(found, BookmarkFolder):
                return found.children
            return []
        
        return self.root_folder.children 