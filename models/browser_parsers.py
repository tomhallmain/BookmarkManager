import json
import plistlib
import sqlite3
import glob
from pathlib import Path
from typing import Dict, Any, Union, List
from .bookmark import Bookmark, BookmarkFolder, BookmarkType
from datetime import datetime

class BrowserParser:
    """Base class for browser-specific bookmark parsers"""
    def __init__(self):
        self.root_folder = None

    def parse(self, file_path: Union[str, Path]) -> BookmarkFolder:
        """Parse bookmarks from the given file path"""
        raise NotImplementedError

    def save(self, file_path: Union[str, Path]) -> None:
        """Save bookmarks to the given file path"""
        raise NotImplementedError

class SafariParser(BrowserParser):
    """Parser for Safari bookmarks (plist format)"""
    def parse(self, file_path: Union[str, Path]) -> BookmarkFolder:
        with open(file_path, 'rb') as f:
            plist_data = plistlib.load(f)
        
        self.root_folder = self._parse_folder(plist_data)
        return self.root_folder

    def _parse_folder(self, data: Dict[str, Any]) -> BookmarkFolder:
        folder = BookmarkFolder(title=data.get('Title', 'Untitled'))
        
        if 'Children' in data:
            for child in data['Children']:
                if child.get('WebBookmarkType') == 'WebBookmarkTypeList':
                    folder.add_child(self._parse_folder(child))
                elif child.get('WebBookmarkType') == 'WebBookmarkTypeLeaf':
                    uri_dict = child.get('URIDictionary', {})
                    bookmark = Bookmark(
                        title=uri_dict.get('title', 'Untitled'),
                        url=child.get('URLString', ''),
                        description=child.get('ReadingList', {}).get('PreviewText')
                    )
                    folder.add_child(bookmark)
        
        return folder

    def save(self, file_path: Union[str, Path]) -> None:
        if not self.root_folder:
            raise ValueError("No bookmarks to save")
        
        plist_data = self._convert_to_plist(self.root_folder)
        with open(file_path, 'wb') as f:
            plistlib.dump(plist_data, f)

    def _convert_to_plist(self, folder: BookmarkFolder) -> Dict[str, Any]:
        plist_data = {
            'WebBookmarkType': 'WebBookmarkTypeList',
            'Title': folder.title,
            'Children': []
        }
        
        for child in folder.children:
            if isinstance(child, BookmarkFolder):
                plist_data['Children'].append(self._convert_to_plist(child))
            else:
                bookmark_data = {
                    'WebBookmarkType': 'WebBookmarkTypeLeaf',
                    'URIDictionary': {'title': child.title},
                    'URLString': child.url
                }
                if child.description:
                    bookmark_data['ReadingList'] = {'PreviewText': child.description}
                plist_data['Children'].append(bookmark_data)
        
        return plist_data

class ChromeParser(BrowserParser):
    """Parser for Chrome/Edge bookmarks (JSON format)"""
    def parse(self, file_path: Union[str, Path]) -> BookmarkFolder:
        with open(file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # Create a root folder to hold all special folders
        self.root_folder = BookmarkFolder(title="Bookmarks")
        
        # Parse each special folder
        for folder_key, folder_data in json_data['roots'].items():
            if folder_key == 'bookmark_bar':
                folder = self._parse_folder(folder_data)
                folder.title = "Bookmarks Bar"
                self.root_folder.add_child(folder)
            elif folder_key == 'other':
                folder = self._parse_folder(folder_data)
                folder.title = "Other Bookmarks"
                self.root_folder.add_child(folder)
            elif folder_key == 'synced':
                folder = self._parse_folder(folder_data)
                folder.title = "Mobile Bookmarks"
                self.root_folder.add_child(folder)
        
        return self.root_folder

    def _parse_folder(self, data: Dict[str, Any]) -> BookmarkFolder:
        folder = BookmarkFolder(title=data.get('name', 'Untitled'))
        
        if 'children' in data:
            for child in data['children']:
                if child.get('type') == 'folder':
                    folder.add_child(self._parse_folder(child))
                else:
                    bookmark = Bookmark(
                        title=child.get('name', 'Untitled'),
                        url=child.get('url', '')
                    )
                    folder.add_child(bookmark)
        
        return folder

    def save(self, file_path: Union[str, Path]) -> None:
        if not self.root_folder:
            raise ValueError("No bookmarks to save")
        
        # Convert the root folder structure back to Chrome's format
        json_data = {
            'roots': {
                'bookmark_bar': self._convert_to_json(self.root_folder.find_child("Bookmarks Bar")),
                'other': self._convert_to_json(self.root_folder.find_child("Other Bookmarks")),
                'synced': self._convert_to_json(self.root_folder.find_child("Mobile Bookmarks"))
            }
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2)

    def _convert_to_json(self, folder: BookmarkFolder) -> Dict[str, Any]:
        json_data = {
            'name': folder.title,
            'type': 'folder',
            'children': []
        }
        
        for child in folder.children:
            if isinstance(child, BookmarkFolder):
                json_data['children'].append(self._convert_to_json(child))
            else:
                bookmark_data = {
                    'name': child.title,
                    'type': 'url',
                    'url': child.url
                }
                json_data['children'].append(bookmark_data)
        
        return json_data

class EdgeParser(ChromeParser):
    """Parser for Microsoft Edge bookmarks (JSON format)"""
    def parse(self, file_path: Union[str, Path]) -> BookmarkFolder:
        with open(file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # Edge's bookmark structure is similar to Chrome's but might have additional metadata
        self.root_folder = self._parse_folder(json_data['roots']['bookmark_bar'])
        return self.root_folder

    def save(self, file_path: Union[str, Path]) -> None:
        if not self.root_folder:
            raise ValueError("No bookmarks to save")
        
        json_data = {
            'roots': {
                'bookmark_bar': self._convert_to_json(self.root_folder)
            }
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2)

class FirefoxParser(BrowserParser):
    """Parser for Firefox bookmarks (SQLite database format)"""
    
    def _get_profile_path(self) -> Path:
        """Get the path to the Firefox profile directory"""
        firefox_path = Path.home() / 'Library/Application Support/Firefox/Profiles'
        profiles = list(firefox_path.glob('*.default*'))
        if not profiles:
            raise FileNotFoundError("No Firefox profile found")
        return profiles[0]

    def parse(self, file_path: Union[str, Path]) -> BookmarkFolder:
        """Parse bookmarks from Firefox's SQLite database"""
        profile_path = self._get_profile_path()
        db_path = profile_path / 'places.sqlite'
        
        # Create a temporary copy of the database to avoid locking issues
        temp_db = db_path.with_suffix('.sqlite.tmp')
        with open(db_path, 'rb') as src, open(temp_db, 'wb') as dst:
            dst.write(src.read())
        
        try:
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            
            # Create root folder
            self.root_folder = BookmarkFolder(title="Firefox Bookmarks")
            
            # Get all bookmarks and folders
            cursor.execute("""
                SELECT b.id, b.parent, b.title, b.type, b.position,
                       p.url, b.lastModified
                FROM moz_bookmarks b
                LEFT JOIN moz_places p ON b.fk = p.id
                ORDER BY b.parent, b.position
            """)
            
            # Create a dictionary to store all items
            items = {}
            
            for row in cursor.fetchall():
                item_id, parent_id, title, item_type, position, url, last_modified = row
                
                if item_type == 1:  # Folder
                    folder = BookmarkFolder(
                        title=title or "Untitled",
                        modified_at=datetime.fromtimestamp(last_modified / 1000000)
                    )
                    items[item_id] = folder
                else:  # Bookmark
                    bookmark = Bookmark(
                        title=title or "Untitled",
                        url=url or "",
                        modified_at=datetime.fromtimestamp(last_modified / 1000000)
                    )
                    items[item_id] = bookmark
                
                # Add to parent folder
                if parent_id == 0:  # Root level
                    self.root_folder.add_child(items[item_id])
                elif parent_id in items:
                    items[parent_id].add_child(items[item_id])
            
            return self.root_folder
            
        finally:
            conn.close()
            temp_db.unlink()  # Clean up temporary file

    def save(self, file_path: Union[str, Path]) -> None:
        """Save bookmarks back to Firefox's SQLite database"""
        if not self.root_folder:
            raise ValueError("No bookmarks to save")
        
        profile_path = self._get_profile_path()
        db_path = profile_path / 'places.sqlite'
        
        # Create a temporary copy of the database
        temp_db = db_path.with_suffix('.sqlite.tmp')
        with open(db_path, 'rb') as src, open(temp_db, 'wb') as dst:
            dst.write(src.read())
        
        try:
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            
            # Start transaction
            cursor.execute("BEGIN TRANSACTION")
            
            # Clear existing bookmarks
            cursor.execute("DELETE FROM moz_bookmarks WHERE parent > 0")
            
            # Helper function to insert items
            def insert_items(folder: BookmarkFolder, parent_id: int, position: int = 0):
                for child in folder.children:
                    if isinstance(child, BookmarkFolder):
                        cursor.execute("""
                            INSERT INTO moz_bookmarks (parent, title, type, position, lastModified)
                            VALUES (?, ?, 1, ?, ?)
                        """, (parent_id, child.title, position, int(child.modified_at.timestamp() * 1000000)))
                        new_parent_id = cursor.lastrowid
                        insert_items(child, new_parent_id)
                    else:
                        # Insert URL into moz_places if it doesn't exist
                        cursor.execute("""
                            INSERT OR IGNORE INTO moz_places (url)
                            VALUES (?)
                        """, (child.url,))
                        
                        # Get the place ID
                        cursor.execute("SELECT id FROM moz_places WHERE url = ?", (child.url,))
                        place_id = cursor.fetchone()[0]
                        
                        # Insert bookmark
                        cursor.execute("""
                            INSERT INTO moz_bookmarks (parent, fk, title, type, position, lastModified)
                            VALUES (?, ?, ?, 2, ?, ?)
                        """, (parent_id, place_id, child.title, position, 
                              int(child.modified_at.timestamp() * 1000000)))
                    
                    position += 1
            
            # Insert root folder if it doesn't exist
            cursor.execute("""
                INSERT OR IGNORE INTO moz_bookmarks (id, parent, title, type)
                VALUES (1, 0, 'Firefox Bookmarks', 1)
            """)
            
            # Insert all bookmarks and folders
            insert_items(self.root_folder, 1)
            
            # Commit transaction
            conn.commit()
            
        finally:
            conn.close()
            # Replace original database with updated one
            temp_db.replace(db_path) 