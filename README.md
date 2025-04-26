# BookmarkManager

A cross-browser bookmark management tool that helps you organize and find bookmarks across different browsers.

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

## Requirements
- Python 3.6+
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

The application will automatically detect and load bookmarks from supported browsers installed on your system. Use the tabs to:
1. Search across all browsers
2. Find similar URLs to detect duplicates or related bookmarks
3. Share bookmarks with other computers

## Network Sharing
To share bookmarks with other computers:
1. Run BookmarkManager on each computer
2. In the Network tab:
   - For computers on the same network:
     - Click "Refresh" to see available instances
     - Select an instance and click "Connect"
   - For computers on different networks:
     - Enter the remote computer's IP address or hostname
     - Enter the port (default: 8765)
     - Click "Connect"
3. Once connected, select bookmarks to share
4. Click "Share Bookmarks" to send them

## Note
Some browsers may require the application to be closed before changes to bookmarks can be saved.

