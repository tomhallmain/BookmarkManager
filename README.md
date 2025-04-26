# BookmarkManager

A cross-browser bookmark manager that allows you to view, organize, and manage bookmarks across different browsers. It also supports sharing and syncing bookmarks between computers on the same network.

## Features
- Load and manage bookmarks from multiple browsers:
  - Safari (macOS only)
  - Chrome
  - Firefox
  - Brave
  - Edge (untested)
  - Opera (untested)
  - Vivaldi (untested)
  - DuckDuckGo (untested)
  - Yandex (untested)
- Search bookmarks across all browsers simultaneously
- Find similar URLs using intelligent matching:
  - Exact matches
  - Word boundary matches (URLs that match at the start or after /, -, _)
  - Substring matches
  - Fuzzy matches based on similarity
- Modern Qt-based user interface with:
  - Search across all browsers
  - Similar URL finder
  - Adjustable similarity threshold
  - Context menu for quick bookmark actions
  - Resizable columns for better visibility
- Network sharing with end-to-end encryption and automatic discovery
  - Includes protection against DDoS, message tampering, and session hijacking
- Share bookmarks between computers on the same network
- Automatic discovery of other BookmarkManager instances
- Two-way sync of bookmarks between machines
- End-to-end encryption for secure sharing
- Protection against DDoS attacks and other security threats

## Network Sharing Features

### Automatic Discovery
- Automatically finds other BookmarkManager instances on the same network
- Shows available instances in the Network tab
- Displays connection status and details

### Bookmark Sharing
- Share all bookmarks or selected bookmarks with other instances
- Default setting to share all bookmarks for easy setup
- Secure end-to-end encryption for all shared data
- Automatic duplicate detection and handling

### Two-Way Sync
- Enable/disable two-way sync between machines
- Automatic merging of bookmarks from different sources
- Preserves folder structure during sync
- Handles conflicts and duplicates intelligently

### Security Features
- End-to-end encryption using NaCl
- Message signing and verification
- Rate limiting and connection limits
- IP blacklisting for suspicious activity
- Session token management
- Protection against DDoS attacks

## Requirements
- Python 3.8 or higher
- PySide6 (Qt for Python)
- Access to browser bookmark files

## Installation
```bash
pip install -r requirements.txt
```

## Browser Support
The application supports both Chromium-based browsers (using a common JSON format) and browser-specific formats like Safari's plist and Firefox's SQLite database. While not every browser has been tested, the application is designed to be easily extensible.

If you encounter issues with a specific browser:
1. Check the browser's bookmark file location in the `PathManager` class
2. Verify the bookmark file format in the `BrowserParsers` class
3. Add or modify the appropriate paths and parsers as needed

## Usage
Run the application:
```bash
python main.py
```

2. Select a browser from the dropdown menu to view its bookmarks.

3. Use the Network tab to:
   - Connect to other BookmarkManager instances
   - Share bookmarks with other computers
   - Enable two-way sync
   - View connection status and details

4. To share bookmarks:
   - Connect to another instance using either manual connection or auto-discovery
   - Use "Share Bookmarks" to share all bookmarks (default) or selected bookmarks
   - Use "Sync Bookmarks" to perform a two-way sync between machines

5. To manage bookmarks:
   - Right-click on bookmarks or folders to access context menu
   - Add, edit, or delete bookmarks and folders
   - Drag and drop to organize bookmarks
   - Use the search bar to find specific bookmarks

## Security

The application implements several security measures to protect your bookmarks:

- End-to-end encryption for all network communication
- Secure key exchange using NaCl
- Message signing with HMAC
- Rate limiting and connection limits
- IP blacklisting for suspicious activity
- Automatic cleanup of stale connections
- Protection against common attacks (DDoS, replay, etc.)

