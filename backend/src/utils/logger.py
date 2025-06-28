"""
Logging configuration for Charleston County TMS search
"""
import logging
import sys
from pathlib import Path
from src.config import LOGS_PATH, LOG_LEVEL

def setup_logger():
    """Set up logging configuration with Windows Unicode support"""
    
    # Create logs directory if it doesn't exist
    LOGS_PATH.mkdir(parents=True, exist_ok=True)
    
    # Configure logging with UTF-8 encoding for Windows compatibility
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper()),
        format=log_format,
        handlers=[
            # Console handler with UTF-8 encoding
            logging.StreamHandler(sys.stdout),
            # File handler with UTF-8 encoding for Windows compatibility
            logging.FileHandler(
                LOGS_PATH / 'charleston_workflow.log', 
                encoding='utf-8',
                errors='replace'
            )
        ]
    )
    
    # Set specific loggers to reduce noise
    logging.getLogger('pyppeteer').setLevel(logging.WARNING)
    logging.getLogger('websockets').setLevel(logging.WARNING)
    logging.getLogger('google').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('groq').setLevel(logging.INFO)
    
    logger = logging.getLogger(__name__)
    logger.info("Logger initialized successfully with Unicode support")
