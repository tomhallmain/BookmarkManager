from typing import List, Dict, Optional
from models.bookmark import Bookmark, BookmarkFolder
from models.browser_bookmarks import BrowserBookmarks
from models.bookmark import BrowserType
from models.path_manager import PathManager
from utils.utils import url_similarity, logger

class BookmarkManager:
    """Manages bookmarks across multiple browsers"""
    
    def __init__(self):
        self._browser_instances: Dict[BrowserType, BrowserBookmarks] = {}
        self._path_manager = PathManager()
        self.is_modified = False  # Track if any changes have been made
        self._available_browsers: Optional[List[BrowserType]] = None  # Cache for available browsers
        self._current_browser: Optional[BrowserType] = None  # Currently selected browser
    
    @property
    def current_browser(self) -> Optional[BrowserType]:
        """Get the currently selected browser"""
        return self._current_browser
    
    @current_browser.setter
    def current_browser(self, browser: BrowserType):
        """Set the currently selected browser"""
        if browser not in self._browser_instances:
            self._browser_instances[browser] = BrowserBookmarks(browser, self._path_manager)
        self._current_browser = browser
    
    def get_current_browser_instance(self) -> Optional[BrowserBookmarks]:
        """Get the BrowserBookmarks instance for the current browser"""
        if not self._current_browser:
            return None
        return self._browser_instances.get(self._current_browser)
    
    def load_supported_browsers(self) -> List[BrowserType]:
        """Load supported browsers, only returning those with valid paths.
        Results are cached to avoid rechecking paths."""
        if self._available_browsers is not None:
            return self._available_browsers
            
        logger.info("Loading supported browsers")
        supported_browsers = self._path_manager.get_supported_browsers()
        available_browsers = []
        
        for browser, is_supported in supported_browsers.items():
            if is_supported:
                # Get or create BrowserBookmarks instance for this browser
                if browser not in self._browser_instances:
                    self._browser_instances[browser] = BrowserBookmarks(browser, self._path_manager)
                
                # Check if it has valid bookmarks
                browser_instance = self._browser_instances[browser]
                if browser_instance.has_valid_bookmark_path():
                    available_browsers.append(browser)
        
        if not available_browsers:
            logger.error("No available browsers found")
            self._available_browsers = []
            return []
        
        self._available_browsers = available_browsers
        return available_browsers
    
    def load_all_browsers(self) -> Dict[BrowserType, bool]:
        """Load bookmarks from all supported browsers"""
        results = {}
        available_browsers = self.load_supported_browsers()  # Use cached results
        
        for browser in available_browsers:
            # Get existing instance or create new one if needed
            if browser not in self._browser_instances:
                self._browser_instances[browser] = BrowserBookmarks(browser, self._path_manager)
            
            instance = self._browser_instances[browser]
            success = instance.load_browser_bookmarks()
            results[browser] = success
        
        self.is_modified = False  # Reset modified flag after loading
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
        
        if any(results.values()):  # If any save was successful
            self.is_modified = False  # Reset modified flag after saving
        return results 