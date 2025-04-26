from pathlib import Path
import platform
from typing import Dict, Optional, List

from .bookmark import BrowserType

class PathManager:
    """Manages platform-specific paths for browser bookmarks"""
    
    def __init__(self):
        self._system = platform.system().lower()
        self._home = Path.home()
        
        # Define base paths for different browsers on different platforms
        self._base_paths = {
            'darwin': {  # macOS
                BrowserType.SAFARI: self._home / 'Library/Safari',
                BrowserType.CHROME: self._home / 'Library/Application Support/Google/Chrome',
                BrowserType.FIREFOX: self._home / 'Library/Application Support/Firefox/Profiles',
                BrowserType.EDGE: self._home / 'Library/Application Support/Microsoft Edge',
                BrowserType.BRAVE: self._home / 'Library/Application Support/BraveSoftware/Brave-Browser',
                BrowserType.OPERA: self._home / 'Library/Application Support/com.operasoftware.Opera',
                BrowserType.VIVALDI: self._home / 'Library/Application Support/Vivaldi',
                BrowserType.DUCKDUCKGO: self._home / 'Library/Application Support/DuckDuckGo',
                BrowserType.YANDEX: self._home / 'Library/Application Support/Yandex/YandexBrowser'
            },
            'windows': {
                BrowserType.SAFARI: None,  # Safari is not available on Windows
                BrowserType.CHROME: self._home / 'AppData/Local/Google/Chrome/User Data',
                BrowserType.FIREFOX: self._home / 'AppData/Roaming/Mozilla/Firefox/Profiles',
                BrowserType.EDGE: self._home / 'AppData/Local/Microsoft/Edge/User Data',
                BrowserType.BRAVE: self._home / 'AppData/Local/BraveSoftware/Brave-Browser/User Data',
                BrowserType.OPERA: self._home / 'AppData/Roaming/Opera Software/Opera Stable',
                BrowserType.VIVALDI: self._home / 'AppData/Local/Vivaldi/User Data',
                BrowserType.DUCKDUCKGO: self._home / 'AppData/Local/DuckDuckGo/User Data',
                BrowserType.YANDEX: self._home / 'AppData/Local/Yandex/YandexBrowser/User Data'
            },
            'linux': {
                BrowserType.SAFARI: None,  # Safari is not available on Linux
                BrowserType.CHROME: self._home / '.config/google-chrome',
                BrowserType.FIREFOX: self._home / '.mozilla/firefox',
                BrowserType.EDGE: self._home / '.config/microsoft-edge',
                BrowserType.BRAVE: self._home / '.config/BraveSoftware/Brave-Browser',
                BrowserType.OPERA: self._home / '.config/opera',
                BrowserType.VIVALDI: self._home / '.config/vivaldi',
                BrowserType.DUCKDUCKGO: self._home / '.config/duckduckgo',
                BrowserType.YANDEX: self._home / '.config/yandex-browser'
            }
        }
        
        # Define profile names for different browsers
        self._profile_names = {
            BrowserType.CHROME: 'Default',
            BrowserType.EDGE: 'Default',
            BrowserType.BRAVE: 'Default',
            BrowserType.OPERA: 'Default',
            BrowserType.VIVALDI: 'Default',
            BrowserType.DUCKDUCKGO: 'Default',
            BrowserType.YANDEX: 'Default',
            BrowserType.FIREFOX: '*.default*'  # Firefox uses wildcards for profile names
        }
        
        # Define bookmark file names
        self._bookmark_files = {
            BrowserType.SAFARI: 'Bookmarks.plist',
            BrowserType.CHROME: 'Bookmarks',
            BrowserType.EDGE: 'Bookmarks',
            BrowserType.BRAVE: 'Bookmarks',
            BrowserType.OPERA: 'Bookmarks',
            BrowserType.VIVALDI: 'Bookmarks',
            BrowserType.DUCKDUCKGO: 'Bookmarks',
            BrowserType.YANDEX: 'Bookmarks',
            BrowserType.FIREFOX: 'places.sqlite'
        }

    def get_bookmark_paths(self, browser: BrowserType) -> List[Path]:
        """Get the full paths to all bookmark files for the specified browser"""
        if browser not in self._bookmark_files:
            raise ValueError(f"Unsupported browser: {browser}")
        
        base_path = self._base_paths.get(self._system, {}).get(browser)
        if base_path is None:
            raise ValueError(f"Browser {browser} is not supported on {self._system}")
        
        paths = []
        
        if browser == BrowserType.FIREFOX:
            # Firefox requires special handling for profile paths
            profiles = list(base_path.glob(self._profile_names[browser]))
            if not profiles:
                raise FileNotFoundError(f"No Firefox profile found in {base_path}")
            paths.append(profiles[0] / self._bookmark_files[browser])
        elif browser == BrowserType.SAFARI:
            # Safari bookmarks are directly in the Safari folder
            paths.append(base_path / self._bookmark_files[browser])
        else:
            # For Chromium-based browsers, use the Default profile
            profile_name = self._profile_names.get(browser, 'Default')
            profile_path = base_path / profile_name
            paths.append(profile_path / self._bookmark_files[browser])
        
        return paths

    def get_supported_browsers(self) -> Dict[BrowserType, bool]:
        """Get a dictionary of supported browsers for the current platform"""
        return {
            browser: base_path is not None
            for browser, base_path in self._base_paths.get(self._system, {}).items()
        }

    @property
    def system(self) -> str:
        """Get the current operating system name"""
        return self._system

    @property
    def home(self) -> Path:
        """Get the user's home directory"""
        return self._home 