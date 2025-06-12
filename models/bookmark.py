from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union, TYPE_CHECKING
import platform
import uuid

from utils.utils import normalize_url

if TYPE_CHECKING:
    from .bookmark import Bookmark, BookmarkFolder

class BookmarkType(Enum):
    FOLDER = "folder"
    BOOKMARK = "bookmark"

class BrowserType(Enum):
    """Enum for supported browser types"""
    SAFARI = "Safari"
    CHROME = "Chrome"
    FIREFOX = "Firefox"
    EDGE = "Edge"
    BRAVE = "Brave"
    OPERA = "Opera"
    VIVALDI = "Vivaldi"
    DUCKDUCKGO = "DuckDuckGo"
    YANDEX = "Yandex"
    UNKNOWN = "Unknown"

    def is_chromium_based(self) -> bool:
        """Check if the browser is Chromium-based"""
        return self in {
            BrowserType.CHROME,
            BrowserType.EDGE,
            BrowserType.BRAVE,
            BrowserType.OPERA,
            BrowserType.VIVALDI,
            BrowserType.DUCKDUCKGO,
            BrowserType.YANDEX
        }

@dataclass
class Bookmark:
    """Represents a single bookmark entry"""
    title: str
    url: str
    type: BookmarkType = BookmarkType.BOOKMARK
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    parent_id: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    browser: Optional[BrowserType] = None  # Inherited from parent folder
    host: Optional[str] = None  # Inherited from parent folder
    normalized_url: str = field(init=False)  # Computed from url
    
    def __post_init__(self):
        """Initialize computed fields after instance creation"""
        self.normalized_url = normalize_url(self.url)

    def to_dict(self) -> Dict:
        """Convert a Bookmark object to a dictionary for network transmission."""
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url,
            'description': self.description,
            'parent_id': self.parent_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_modified': self.modified_at.isoformat() if self.modified_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Bookmark':
        """Convert a dictionary to a Bookmark object."""
        return cls(
            id=data.get('id'),
            title=data['title'],
            url=data['url'],
            description=data.get('description'),
            parent_id=data.get('parent_id'),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            modified_at=datetime.fromisoformat(data['last_modified']) if data.get('last_modified') else None
        )

@dataclass
class BookmarkFolder:
    """Represents a folder containing bookmarks and other folders"""
    title: str
    type: BookmarkType = BookmarkType.FOLDER
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    description: Optional[str] = None
    parent_id: Optional[str] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    children: List[Union['Bookmark', 'BookmarkFolder']] = field(default_factory=list)
    browser: BrowserType = BrowserType.UNKNOWN
    host: str = field(default_factory=lambda: platform.node())

    def add_child(self, child: Union['Bookmark', 'BookmarkFolder']) -> None:
        """Add a child bookmark or folder to this folder"""
        child.parent_id = self.id
        # Inherit browser and host information
        child.browser = self.browser
        child.host = self.host
        self.children.append(child)
        self.modified_at = datetime.now()

    def remove_child(self, child_id: str) -> None:
        """Remove a child bookmark or folder by its ID"""
        self.children = [c for c in self.children if c.id != child_id]
        self.modified_at = datetime.now()

    def find_child(self, child_id: str) -> Optional[Union['Bookmark', 'BookmarkFolder']]:
        """Find a child bookmark or folder by its ID"""
        for child in self.children:
            if child.id == child_id:
                return child
            if isinstance(child, BookmarkFolder):
                found = child.find_child(child_id)
                if found:
                    return found
        return None

    def set_browser(self, browser: BrowserType) -> None:
        """Set the browser type for this folder and all its children"""
        self.browser = browser
        for child in self.children:
            child.browser = browser
            if isinstance(child, BookmarkFolder):
                child.set_browser(browser)

    def set_host(self, host: str) -> None:
        """Set the host name for this folder and all its children"""
        self.host = host
        for child in self.children:
            child.host = host
            if isinstance(child, BookmarkFolder):
                child.set_host(host)

    def to_dict(self) -> Dict:
        """Serialize the BookmarkFolder object to a dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'type': self.type.value,
            'description': self.description,
            'parent_id': self.parent_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_modified': self.modified_at.isoformat() if self.modified_at else None,
            'browser': self.browser.value if self.browser else None,
            'host': self.host,
            'children': [child.to_dict() for child in self.children]
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'BookmarkFolder':
        """Convert a dictionary to a BookmarkFolder object."""
        folder = cls(
            id=data.get('id'),
            title=data['title'],
            description=data.get('description'),
            parent_id=data.get('parent_id'),
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else None,
            modified_at=datetime.fromisoformat(data['last_modified']) if data.get('last_modified') else None,
            browser=BrowserType(data['browser']) if data.get('browser') else BrowserType.UNKNOWN,
            host=data.get('host', platform.node())
        )
        
        # Recursively create children
        for child_data in data.get('children', []):
            if child_data['type'] == BookmarkType.FOLDER.value:
                child = BookmarkFolder.from_dict(child_data)
            else:
                child = Bookmark.from_dict(child_data)
            folder.add_child(child)
            
        return folder 