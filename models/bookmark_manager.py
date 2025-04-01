from typing import List, Optional, Union, Dict
from pathlib import Path
from .bookmark import Bookmark, BookmarkFolder, BookmarkType, BrowserType
from .browser_parsers import BrowserParser, SafariParser, ChromeParser, EdgeParser, FirefoxParser
from .path_manager import PathManager

class BookmarkManager:
    """Manages bookmark operations and coordinates between UI and data models"""
    
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
            BrowserType.BRAVE: ChromeParser()  # Brave uses Chrome's bookmark format
        }

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
            if browser in [BrowserType.CHROME, BrowserType.EDGE, BrowserType.BRAVE]:
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
            
            # For Chromium-based browsers, we might want to handle saving to Other Bookmarks
            # This would require separating bookmarks into the appropriate files
            # For now, we'll just save to the main file
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