from typing import List, Optional, Union, Dict
from pathlib import Path
from .bookmark import Bookmark, BookmarkFolder, BookmarkType, BrowserType
from .browser_parsers import BrowserParser, SafariParser, ChromeParser, EdgeParser, FirefoxParser
from .path_manager import PathManager
from utils.utils import url_similarity
import os

class BrowserBookmarks:
    """Manages bookmarks for a single browser instance"""
    
    def __init__(self):
        self.current_browser = None
        self.current_parser = None
        self.root_folder = None
        self.path_manager = PathManager()
        
        self._parsers = {
            BrowserType.SAFARI: SafariParser(),
            BrowserType.CHROME: ChromeParser(),
            BrowserType.FIREFOX: FirefoxParser(),
            BrowserType.EDGE: EdgeParser(),
            BrowserType.BRAVE: ChromeParser(),  # Brave uses Chrome's bookmark format
            BrowserType.OPERA: ChromeParser(),  # Opera uses Chrome's bookmark format
            BrowserType.VIVALDI: ChromeParser(),  # Vivaldi uses Chrome's bookmark format
            BrowserType.DUCKDUCKGO: ChromeParser(),  # DuckDuckGo uses Chrome's bookmark format
            BrowserType.YANDEX: ChromeParser()  # Yandex uses Chrome's bookmark format
        }

    def has_valid_bookmark_path(self, browser: BrowserType) -> bool:
        """Check if the browser has a valid bookmark path that exists and is accessible"""
        try:
            print(f"Checking bookmark path for {browser.value}")
            bookmark_paths = self.path_manager.get_bookmark_paths(browser)
            if not bookmark_paths:
                print(f"No bookmark paths found for {browser.value}")
                return False
            
            # Check if the main bookmark file exists and is accessible
            main_path = Path(bookmark_paths[0])
            if not main_path.exists():
                print(f"Bookmark file not found for {browser.value} at {main_path}")
                return False
            
            if not main_path.is_file():
                print(f"Bookmark path is not a file for {browser.value} at {main_path}")
                return False
            
            # Check if we have read access
            if not os.access(main_path, os.R_OK):
                print(f"No read access to bookmark file for {browser.value} at {main_path}")
                return False
            
            # Try to load bookmarks to verify they can be read
            print(f"Attempting to load bookmarks for {browser.value}")
            if not self.load_browser_bookmarks(browser):
                print(f"Failed to load bookmarks for {browser.value}")
                return False
            
            print(f"Successfully validated bookmark path for {browser.value}")
            return True
        except Exception as e:
            print(f"Error checking bookmark path for {browser.value}: {e}")
            return False

    def has_bookmarks(self) -> bool:
        """Check if the current browser has any bookmarks"""
        if not self.root_folder:
            print("No root folder found when checking for bookmarks")
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
        print(f"Found {bookmark_count} bookmarks for {self.current_browser.value}")
        return bookmark_count > 0

    def refresh_bookmarks(self) -> bool:
        """Reload bookmarks from disk for the current browser"""
        if not self.current_browser:
            print("No current browser selected for refresh")
            return False
        
        print(f"Refreshing bookmarks for {self.current_browser.value}")
        success = self.load_browser_bookmarks(self.current_browser)
        if success:
            print(f"Successfully refreshed bookmarks for {self.current_browser.value}")
        else:
            print(f"Failed to refresh bookmarks for {self.current_browser.value}")
        return success

    def get_supported_browsers(self) -> Dict[BrowserType, bool]:
        """Get a dictionary of supported browsers for the current platform"""
        return self.path_manager.get_supported_browsers()

    def load_browser_bookmarks(self, browser: BrowserType) -> bool:
        """Load bookmarks from the specified browser"""
        if browser not in self._parsers:
            raise ValueError(f"Unsupported browser: {browser}")
        
        self.current_browser = browser
        self.current_parser = self._parsers[browser]
        
        try:
            bookmark_paths = self.path_manager.get_bookmark_paths(browser)
            if not bookmark_paths:
                return False
                
            # Parse the main bookmarks file
            self.root_folder = self.current_parser.parse(bookmark_paths[0])
            
            # For Chromium-based browsers, we need to handle the root structure
            if browser.is_chromium_based():
                print(f"Initial root folder title: {self.root_folder.title}")
                print(f"Initial root folder children: {[child.title for child in self.root_folder.children]}")
                
                # Create a new root folder to hold all the special folders
                new_root = BookmarkFolder(title="Bookmarks")
                
                # The parser should have created three folders: bookmark_bar, other, and synced
                # We need to rename them appropriately
                for child in self.root_folder.children:
                    if isinstance(child, BookmarkFolder):
                        if child.title == "Bookmarks Bar":  # bookmark_bar
                            new_root.add_child(child)
                            print(f"Added Bookmarks Bar folder with {len(child.children)} children")
                        elif child.title == "Other Bookmarks":  # other
                            new_root.add_child(child)
                            print(f"Added Other Bookmarks folder with {len(child.children)} children")
                        elif child.title == "Mobile Bookmarks":  # synced
                            new_root.add_child(child)
                            print(f"Added Mobile Bookmarks folder with {len(child.children)} children")
                    else:
                        print(f"Skipped non-folder item: {type(child)} with title '{child.title}'")
                
                print(f"Final root folder children: {[child.title for child in new_root.children]}")
                # Set the new root folder
                self.root_folder = new_root
            
            # Set the browser type for the entire bookmark tree
            self.root_folder.set_browser(browser)
            return True
        except Exception as e:
            print(f"Error loading bookmarks: {e}")
            return False

    def save_bookmarks(self) -> bool:
        """Save current bookmarks back to the browser's file"""
        if not self.current_parser or not self.root_folder:
            return False
        
        try:
            bookmark_paths = self.path_manager.get_bookmark_paths(self.current_browser)
            if not bookmark_paths:
                return False
                
            # Save to the main bookmarks file
            self.current_parser.save(bookmark_paths[0])

            return True
        except Exception as e:
            print(f"Error saving bookmarks: {e}")
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
            return True
        return False

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

class BookmarkManager:
    """Manages bookmarks across multiple browsers"""
    
    def __init__(self):
        self._browser_instances: Dict[BrowserType, BrowserBookmarks] = {}
        self._path_manager = PathManager()
    
    def load_all_browsers(self) -> Dict[BrowserType, bool]:
        """Load bookmarks from all supported browsers"""
        results = {}
        supported_browsers = self._path_manager.get_supported_browsers()
        
        for browser, is_supported in supported_browsers.items():
            if is_supported:
                instance = BrowserBookmarks()
                success = instance.load_browser_bookmarks(browser)
                if success:
                    self._browser_instances[browser] = instance
                results[browser] = success
        
        return results
    
    def get_browser_instance(self, browser: BrowserType) -> Optional[BrowserBookmarks]:
        """Get the BrowserBookmarks instance for a specific browser"""
        return self._browser_instances.get(browser)
    
    def search_all_bookmarks(self, query: str) -> List[Bookmark]:
        """Search for bookmarks across all loaded browsers"""
        results = []
        for instance in self._browser_instances.values():
            results.extend(instance.search_bookmarks(query))
        return results
    
    def find_similar_bookmarks(self, url: str, threshold: float = 0.8) -> List[Bookmark]:
        """Find bookmarks with similar URLs across all browsers"""
        results = []
        for instance in self._browser_instances.values():
            if not instance.root_folder:
                continue
            
            def search_folder(folder: BookmarkFolder):
                for child in folder.children:
                    if isinstance(child, Bookmark):
                        similarity = url_similarity(url, child)
                        if similarity >= threshold:
                            results.append((similarity, child))
                    else:
                        search_folder(child)
            
            search_folder(instance.root_folder)
        
        # Sort results by similarity score in descending order
        results.sort(key=lambda x: x[0], reverse=True)
        return [bookmark for _, bookmark in results]
    
    def save_all_bookmarks(self) -> Dict[BrowserType, bool]:
        """Save bookmarks for all loaded browsers"""
        results = {}
        for browser, instance in self._browser_instances.items():
            results[browser] = instance.save_bookmarks()
        return results 