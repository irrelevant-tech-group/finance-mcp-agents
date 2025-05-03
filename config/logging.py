import os
import logging
from logging.handlers import RotatingFileHandler
from config.settings import settings

def setup_logger(name="finance-ai", log_file="app.log"):
    """Set up logger with appropriate configuration"""
    # Create logs directory if it doesn't exist
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_path = os.path.join(log_dir, log_file)
    
    # Create logger
    logger = logging.getLogger(name)
    
    # Set log level based on environment
    log_level = getattr(logging, settings.LOG_LEVEL)
    logger.setLevel(log_level)
    
    # Create handlers
    console_handler = logging.StreamHandler()
    file_handler = RotatingFileHandler(
        log_path, maxBytes=10485760, backupCount=5
    )  # 10MB per file, max 5 files
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Set formatter for handlers
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# Create default logger
logger = setup_logger()

# For testing
if __name__ == "__main__":
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")