"""
Test suite for testing the browser automation manager for Charleston County
"""
import pytest
import os
import time
from pathlib import Path
from src.automation.browser_manager import CharlestonBrowserManager

@pytest.fixture
def browser_manager():
    """Create browser manager instance for tests"""
    manager = CharlestonBrowserManager()
    # Start the browser before test
    success = manager.start_browser()
    assert success, "Browser failed to start"
    
    # Return the manager for test use
    yield manager
    
    # Cleanup after test
    if manager.driver:
        manager.driver.quit()

def test_browser_start():
    """Test that the browser starts correctly"""
    manager = CharlestonBrowserManager()
    success = manager.start_browser()
    assert success, "Browser failed to start"
    
    # Verify driver is initialized
    assert manager.driver is not None, "Driver was not initialized"
    assert manager.wait is not None, "WebDriverWait was not initialized"
    
    # Cleanup
    if manager.driver:
        manager.driver.quit()

def test_navigate_to_charleston():
    """Test navigation to Charleston County property search"""
    manager = CharlestonBrowserManager()
    success = manager.start_browser()
    assert success, "Browser failed to start"
    
    # Navigate to property search
    success = manager.navigate_to_charleston_workflow()
    assert success, "Failed to navigate to Charleston property search"
    
    # Verify we're on the right page (has PIN field)
    pin_field = manager.driver.find_elements_by_css_selector('input[title="PIN"]')
    assert len(pin_field) > 0 or "PIN" in manager.driver.page_source, "PIN field not found on page"
    
    # Cleanup
    if manager.driver:
        manager.driver.quit()

def test_search_property(browser_manager):
    """Test property search with a valid TMS number"""
    # Define test TMS number (use a real but anonymized TMS)
    tms_number = "5590200072"
    
    # Start the workflow
    success = browser_manager.navigate_to_charleston_workflow()
    assert success, "Failed to navigate to Charleston property search"
    
    # Fill the PIN field with TMS number
    success = browser_manager.find_and_fill_pin_field(tms_number)
    assert success, "Failed to fill PIN field"
    
    # Click search button
    success = browser_manager.click_charleston_search_button()
    assert success, "Failed to click search button"
    
    # Wait for results
    success = browser_manager.wait_for_charleston_results()
    assert success, "Failed to get search results"
    
    # Verify we found the property (either property details visible or PIN in results)
    assert "Details" in browser_manager.driver.page_source or tms_number in browser_manager.driver.page_source, "Property search results not found"

def main():
    # This allows the file to be run directly
    import sys
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Test browser manager with different scenarios")
    parser.add_argument("--batch", help="Run batch search for multiple deeds", action="store_true")
    parser.add_argument("--book", help="Deed book number", type=str)
    parser.add_argument("--page", help="Deed page number", type=str)
    parser.add_argument("--tms", help="TMS number for property search", type=str)
    
    args = parser.parse_args()
    
    # Create browser manager
    manager = CharlestonBrowserManager()
    success = manager.start_browser()
    
    if not success:
        print("❌ Failed to start browser, exiting")
        sys.exit(1)
    
    try:
        # Initialize workflow
        print("🔍 Initializing workflow...")
        success = manager.navigate_to_charleston_workflow()
        
        if not success:
            print("❌ Failed to navigate to Charleston workflow, exiting")
            sys.exit(1)
        
        # Handle batch or single deed search
        if args.batch:
            if args.tms:
                print(f"📊 Running batch search for TMS: {args.tms}")
                # Search property first
                manager.find_and_fill_pin_field(args.tms)
                manager.click_charleston_search_button()
                manager.wait_for_charleston_results()
                manager.navigate_to_property_details()
                
                # Extract data
                details = manager.extract_property_details()
                owner = manager.extract_owner_info()
                print(f"📋 Property details: {details}")
                print(f"👤 Owner: {owner}")
                
                # Get deed history
                manager.navigate_to_register_of_deeds()
                manager.search_deeds_by_tms(args.tms)
                deed_history = manager.extract_deed_history()
                print(f"📜 Found {len(deed_history)} deeds")
                
                # Download first 3 deeds
                for idx, deed in enumerate(deed_history[:3]):
                    print(f"📄 Downloading deed {idx+1}/{min(3, len(deed_history))}: Book {deed['book']}, Page {deed['page']}")
                    manager.search_deed_by_book_page(deed["book"], deed["page"])
                    manager.download_deed_document()
            else:
                print("❌ TMS number required for batch search")
                sys.exit(1)
        elif args.book and args.page:
            # Single deed search
            print(f"🔍 Searching for deed: Book {args.book}, Page {args.page}")
            
            # Navigate to register of deeds
            manager.navigate_to_register_of_deeds()
            
            # Search for specific deed
            success = manager.search_deed_by_book_page(args.book, args.page)
            
            if success:
                # Download deed
                success = manager.download_deed_document()
                
                if success:
                    print(f"✅ Successfully downloaded deed: Book {args.book}, Page {args.page}")
                else:
                    print(f"❌ Failed to download deed")
            else:
                print(f"❌ Failed to search for deed")
        else:
            if args.tms:
                # Basic property search
                print(f"🔍 Searching for property with TMS: {args.tms}")
                manager.find_and_fill_pin_field(args.tms)
                manager.click_charleston_search_button()
                success = manager.wait_for_charleston_results()
                
                if success:
                    print(f"✅ Successfully found property")
                    manager.navigate_to_property_details()
                    details = manager.extract_property_details()
                    print(f"📋 Property details: {details}")
                else:
                    print(f"❌ Failed to find property")
            else:
                print("❌ Missing required arguments. Use --batch with --tms, or --book with --page, or just --tms")
                sys.exit(1)
    
    finally:
        # Cleanup
        if manager.driver:
            manager.driver.quit()

if __name__ == "__main__":
    main()
