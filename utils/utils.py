import logging
import sys
import shutil
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlparse, urlunparse

# Configure logging
def setup_logging():
    """Configure logging for the application"""
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Define log file paths
    current_log = log_dir / "bookmark_manager.log"
    backup_log = log_dir / f"bookmark_manager_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Rotate logs if current log exists
    if current_log.exists():
        # Get existing backup files
        backup_files = sorted(log_dir.glob("bookmark_manager_*.log"), reverse=True)
        
        # If we have 2 or more backups, remove the oldest one
        while len(backup_files) >= 2:
            backup_files[-1].unlink()
            backup_files.pop()
        
        # Rename current log to backup
        shutil.move(str(current_log), str(backup_log))
    
    # Create a more detailed formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Remove any existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create and configure handlers
    file_handler = logging.FileHandler(
        current_log,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Set up specific loggers with appropriate levels
    main_logger = logging.getLogger("BookmarkManager")
    main_logger.setLevel(logging.INFO)
    
    # Set up debug logging for specific modules
    debug_modules = [
        "BookmarkManager.browser",
        "BookmarkManager.parser",
        "BookmarkManager.url"
    ]
    for module in debug_modules:
        logging.getLogger(module).setLevel(logging.DEBUG)
    
    # Log startup message
    logger = logging.getLogger("BookmarkManager")
    logger.info("Application started - New log file created")

# Create logger instance with context
class ContextLogger(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        # Add browser context if available
        browser = kwargs.pop('browser', None)
        if browser:
            msg = f"[{browser}] {msg}"
        return msg, kwargs

# Initialize logging when module is imported
setup_logging()

# Create the main logger
logger = ContextLogger(logging.getLogger("BookmarkManager"), {})

def normalize_url(url: str) -> str:
    """
    Normalize a URL for comparison by:
    1. Removing protocol (http/https)
    2. Removing www.
    3. Removing trailing slashes
    4. Converting to lowercase
    5. Removing query parameters and fragments
    """
    try:
        # Parse the URL
        parsed = urlparse(url.lower())
        
        # Remove www. from netloc if present
        netloc = parsed.netloc
        if netloc.startswith('www.'):
            netloc = netloc[4:]
        
        # Reconstruct URL without protocol, query, and fragment
        normalized = urlunparse(('', netloc, parsed.path.rstrip('/'), '', '', ''))
        return normalized
    except Exception as e:
        logger.warning(f"URL normalization failed | URL: {url} | Error: {e}")
        # If URL parsing fails, return the original URL in lowercase
        return url.lower()

def url_similarity(url1: str, url2: str) -> float:
    """
    Calculate similarity between two URLs.
    Returns a float between 0 and 1, where 1 means identical and 0 means completely different.
    
    The similarity score is calculated in tiers:
    1.0: Exact match after normalization
    0.9: Match at start or after URL word boundary (/, -, _)
    0.8: One URL is a substring of the other
    0.0-0.7: String similarity ratio
    """
    # Use normalized URLs for comparison
    norm1 = url1 if isinstance(url1, str) else url1.normalized_url
    norm2 = url2 if isinstance(url2, str) else url2.normalized_url
    
    # Tier 1: Exact match
    if norm1 == norm2:
        logger.debug(f"URL exact match | URL1: {norm1} | URL2: {norm2}")
        return 1.0
    
    # Tier 2: Word boundary match
    # Check both directions for word boundary matches
    for (test_str, target_str) in [(norm1, norm2), (norm2, norm1)]:
        if test_str in target_str:
            idx = target_str.find(test_str)
            # Check if it's at the start
            if idx == 0:
                logger.debug(f"URL word boundary match at start | Test: {test_str} | Target: {target_str}")
                return 0.9
            # Check if it's after a word boundary
            if idx > 0 and target_str[idx-1] in ['/', '-', '_']:
                logger.debug(f"URL word boundary match after separator | Test: {test_str} | Target: {target_str}")
                return 0.9
    # Tier 3: General substring match
            else:
                logger.debug(f"URL substring match | Test: {test_str} | Target: {target_str}")
                return 0.8 # No need to check further
    
    # Tier 4: String similarity
    # Use SequenceMatcher for string distance
    ratio = SequenceMatcher(None, norm1, norm2).ratio()
    logger.debug(f"URL similarity ratio | URL1: {norm1} | URL2: {norm2} | Ratio: {ratio:.3f}")
    return 0.7 * ratio  # Cap at 0.7 to maintain tier separation

def are_urls_similar(url1: str, url2: str, threshold: float = 0.8) -> bool:
    """
    Determine if two URLs are similar enough to be considered the same resource.
    Args:
        url1: First URL to compare (str or Bookmark)
        url2: Second URL to compare (str or Bookmark)
        threshold: Similarity threshold (0.0 to 1.0) above which URLs are considered similar
    Returns:
        bool: True if URLs are similar enough, False otherwise
    """
    similarity = url_similarity(url1, url2)
    logger.debug(f"URL similarity check | URL1: {url1} | URL2: {url2} | Similarity: {similarity:.3f} | Threshold: {threshold}")
    return similarity >= threshold 