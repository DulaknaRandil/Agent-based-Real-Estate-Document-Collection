"""
Unified wrapper for handling all screenshot operations in the browser managers
This ensures consistent screenshot behavior across the application
"""
import logging
import os
from pathlib import Path
from src.config import DISABLE_SCREENSHOTS
from datetime import datetime
from typing import Optional
import base64

logger = logging.getLogger(__name__)

def save_screenshot(driver, filename, filepath=None, force=False):
    """
    Unified function to save screenshots that respects the DISABLE_SCREENSHOTS setting
    
    Args:
        driver: Selenium WebDriver instance
        filename: Screenshot filename
        filepath: Optional full path to save the screenshot
        force: Whether to force taking screenshot even if disabled
        
    Returns:
        str or None: Path to the screenshot if taken, None otherwise
    """
    # Skip screenshot if disabled and not forced
    if DISABLE_SCREENSHOTS and not force:
        logger.debug(f"Screenshot disabled: {filename}")
        return None
        
    # Take screenshot if enabled or forced
    try:
        if driver:
            # Determine the full path
            if filepath:
                full_path = filepath
            else:
                # Default to data/screenshots directory
                screenshots_dir = Path("data") / "screenshots"
                screenshots_dir.mkdir(parents=True, exist_ok=True)
                full_path = str(screenshots_dir / filename)
                
            # Save the screenshot
            driver.save_screenshot(full_path)
            logger.info(f"📸 Screenshot saved: {full_path}")
            return full_path
        else:
            logger.warning("Cannot take screenshot, driver is None")
            return None
    except Exception as e:
        logger.error(f"Failed to take screenshot: {e}")
        return None

"""
Utility functions for capturing and saving screenshots during document collection
"""

def save_error_screenshot(
    page,  # Playwright page object
    county: str,
    tms: str,
    error_type: str,
    book: Optional[str] = None,
    page_num: Optional[str] = None,
    attempt: int = 1
) -> str:
    """
    Capture a screenshot of the current page when an error occurs
    
    Args:
        page: The Playwright page object
        county: County name
        tms: TMS number
        error_type: Type of error (e.g., 'deed', 'property_card')
        book: Deed book number (optional)
        page_num: Deed page number (optional)
        attempt: Attempt number
    
    Returns:
        str: Path to the saved screenshot
    """
    try:
        # Create screenshot filename
        if book and page_num:
            filename = f"download_error_DB {book} {page_num}_attempt{attempt}.png"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"download_error_{error_type}_{timestamp}_attempt{attempt}.png"
        
        # Ensure directory exists
        screenshot_dir = os.path.join("data", "screenshots", county, tms)
        os.makedirs(screenshot_dir, exist_ok=True)
        
        # Full path for screenshot
        screenshot_path = os.path.join(screenshot_dir, filename)
        
        # Take screenshot with Playwright
        page.screenshot(path=screenshot_path, full_page=True)
        
        logger.info(f"Saved error screenshot: {screenshot_path}")
        
        return screenshot_path
        
    except Exception as e:
        logger.exception(f"Failed to save screenshot: {e}")
        return None

def get_screenshot_url(county: str, tms: str, filename: str) -> str:
    """
    Get the URL for accessing a screenshot
    
    Args:
        county: County name
        tms: TMS number
        filename: Screenshot filename
    
    Returns:
        str: API URL for accessing the screenshot
    """
    return f"/api/screenshots/{county}/{tms}/{filename}"

def encode_screenshot_to_base64(screenshot_path: str) -> Optional[str]:
    """
    Convert a screenshot to base64 encoding for embedding in HTML
    
    Args:
        screenshot_path: Path to the screenshot file
    
    Returns:
        str: Base64 encoded screenshot
    """
    try:
        if not os.path.exists(screenshot_path):
            logger.error(f"Screenshot file not found: {screenshot_path}")
            return None
            
        with open(screenshot_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            return f"data:image/png;base64,{base64_image}"
            
    except Exception as e:
        logger.exception(f"Failed to encode screenshot to base64: {e}")
        return None
