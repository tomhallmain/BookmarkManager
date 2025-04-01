# BookmarkManager

A cross-browser bookmark management tool that helps you organize and find bookmarks across different browsers.

## Features
- Load and manage bookmarks from multiple browsers:
  - Safari
  - Chrome
  - Firefox
  - Edge
  - Brave
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

## Requirements
- Python 3.6+
- PySide6 (Qt for Python)
- Access to browser bookmark files

## Installation
```bash
pip install -r requirements.txt
```

## Usage
Run the application:
```bash
python main.py
```

The application will automatically detect and load bookmarks from supported browsers installed on your system. Use the tabs to:
1. Search across all browsers
2. Find similar URLs to detect duplicates or related bookmarks

## Note
Some browsers may require the application to be closed before changes to bookmarks can be saved.

