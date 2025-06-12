import logging
import sys
import shutil
from datetime import datetime
from pathlib import Path
from appdirs import user_data_dir

# Configure logging
def setup_logging():
    """Configure logging for the application"""
    # Get the appropriate app data directory
    app_name = "BookmarkManager"
    log_dir = Path(user_data_dir(app_name)) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
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
    logger.info(f"Application started - Log file created at {current_log}")

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