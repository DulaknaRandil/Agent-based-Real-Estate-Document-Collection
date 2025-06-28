"""
Browser automation manager for Charleston County TMS search with LangChain/LangSmith tracing
Using undetected-chromedriver for better real-site compatibility
"""
import logging
import os
import time
import base64
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import undetected_chromedriver as uc
from langsmith import traceable
from langchain_core.tools import tool
from src.config import BROWSER_HEADLESS, USER_AGENT, TIMEOUT_SECONDS, DOWNLOAD_PATH, DISABLE_SCREENSHOTS

logger = logging.getLogger(__name__)

class CharlestonBrowserManager:
    """Manages browser automation for Charleston County property search with LangSmith tracing using undetected Chrome"""
    
    def __init__(self):
        self.driver = None
        self.wait = None
    
    @property
    def page_source(self):
        """Return the current page source if available"""
        try:
            if self.driver:
                return self.driver.page_source
            return None
        except Exception as e:
            logger.error(f"Error getting page source: {e}")
            return None
        
    @traceable(name="start_browser")
    def start_browser(self):
        """Initialize undetected Chrome browser for real-site automation"""
        try:
            # Create Chrome options with minimal configuration
            options = uc.ChromeOptions()
            
            # Basic options for real-site compatibility
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--start-maximized')
            options.add_argument(f'--user-agent={USER_AGENT}')
            
            # Set download preferences
            prefs = {
                "download.default_directory": str(DOWNLOAD_PATH),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            }
            options.add_experimental_option("prefs", prefs)
            
            if BROWSER_HEADLESS:
                options.add_argument('--headless')
            
            # Initialize undetected Chrome with specific version
            # Force version 137 to match current Chrome
            self.driver = uc.Chrome(options=options, version_main=137)
            
            # Create WebDriverWait instance
            self.wait = WebDriverWait(self.driver, TIMEOUT_SECONDS)
            
            # Execute stealth script
            self.driver.execute_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
                
                window.chrome = {
                    runtime: {},
                };
            """)
            
            logger.info("Undetected Chrome browser started successfully")
            print("🔒 Undetected Chrome browser started!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            print(f"❌ Browser start failed: {e}")
            return False
    
    @traceable(name="navigate_to_charleston_workflow")
    def navigate_to_charleston_workflow(self):
        """Navigate to Charleston County Real Property Record Search using undetected Chrome"""
        try:
            from src.config import CHARLESTON_PROPERTY_SEARCH_URL
            
            logger.info(f"Step 1: Navigating to Charleston County Real Property Record Search")
            print(f"🌐 Opening: {CHARLESTON_PROPERTY_SEARCH_URL}")
            
            # Navigate to the property search page
            self.driver.get(CHARLESTON_PROPERTY_SEARCH_URL)
            
            # Wait for page to load
            time.sleep(5)
            
            # Wait for PIN field to be present
            logger.info("Step 2: Waiting for PIN field to be available...")
            print("🔍 Looking for PIN input field...")
            
            # Try multiple selectors for PIN field
            pin_selectors = [
                'input[title="PIN"]',
                'input[aria-label="PIN"]',
                'input[placeholder*="PIN"]',
                'input[name*="pin"]',
                'input[id*="pin"]'
            ]
            
            pin_field = None
            for selector in pin_selectors:
                try:
                    pin_field = self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    logger.info(f"Found PIN field with selector: {selector}")
                    print(f"✅ Found PIN field: {selector}")
                    break
                except:
                    continue
            
            if pin_field:
                logger.info("Successfully navigated to Charleston County Real Property Record Search page")
                print("✅ Page loaded and PIN field found!")
                return True
            else:
                # Take screenshot for debugging
                # Get TMS number if available
                tms = getattr(self, 'current_tms', 'unknown_tms')
                self.take_screenshot('navigation_debug.png', force=True, county="charleston", tms=tms)
                logger.warning("PIN field not found, screenshot saved")
                print("❌ PIN field not found, but page loaded")
                return False
            
        except Exception as e:
            logger.error(f"Failed to navigate to Charleston County property search: {e}")
            print(f"❌ Navigation failed: {e}")
            
            # Take error screenshot
            try:
                # Get TMS number if available
                tms = getattr(self, 'current_tms', 'unknown_tms')
                self.take_screenshot('navigation_error.png', force=True, county="charleston", tms=tms)
                print("📸 Error screenshot saved to screenshots directory")
            except Exception as screenshot_err:
                print(f"Failed to take error screenshot: {screenshot_err}")
            
            return False
    
    @traceable(name="find_and_fill_pin_field")
    def find_and_fill_pin_field(self, tms_number: str):
        """Find and fill the PIN field with TMS number using Selenium"""
        try:
            logger.info(f"Step 3: Looking for PIN field to fill with TMS: {tms_number}")
            print(f"📝 Filling PIN field with TMS: {tms_number}")
            
            # Try multiple selectors for PIN field
            pin_selectors = [
                'input[title="PIN"]',
                'input[aria-label="PIN"]',
                'input[placeholder*="PIN"]',
                'input[name*="pin"]',
                'input[id*="pin"]'
            ]
            
            pin_field = None
            for selector in pin_selectors:
                try:
                    pin_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    logger.info(f"Found PIN field with selector: {selector}")
                    break
                except:
                    continue
            
            if pin_field:
                # Clear any existing content and fill with TMS number
                pin_field.click()
                print(f"🖱️ Clicked on PIN field")
                time.sleep(1)
                
                pin_field.clear()
                print(f"🗑️ Cleared existing content")
                time.sleep(1)
                
                pin_field.send_keys(tms_number)
                print(f"⌨️ Typed TMS number: {tms_number}")
                time.sleep(2)
                
                logger.info(f"Successfully filled PIN field with TMS: {tms_number}")
                return True
            else:
                logger.warning("PIN field element not found")
                print("❌ PIN field element not found")
                return False
                
        except Exception as e:
            logger.error(f"Error filling PIN field: {e}")
            print(f"❌ Error filling PIN field: {e}")
            return False
    
    @traceable(name="click_charleston_search_button")
    def click_charleston_search_button(self):
        """Find and click the Charleston County search button using Selenium"""
        try:
            logger.info("Step 4: Looking for and clicking Charleston County search button")
            print("🔍 Looking for Search button...")
            
            # Try multiple selectors for search button
            search_button_selectors = [
                'button.btn.btn-primary.btn-icon.mr-2[title="Search"]',
                'button[title="Search"]',
                'input[type="submit"][value*="Search"]',
                'button:contains("Search")',
                '.search-button',
                '#search-button'
            ]
            
            search_button = None
            for selector in search_button_selectors:
                try:
                    if ':contains(' in selector:
                        # Use XPath for text-based search
                        search_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Search')]")
                    else:
                        search_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    logger.info(f"Found search button with selector: {selector}")
                    print(f"✅ Found search button: {selector}")
                    break
                except:
                    continue
            
            if search_button:
                # Check if button is enabled
                if search_button.is_enabled():
                    print("🖱️ Button is enabled, clicking...")
                    search_button.click()
                    time.sleep(3)
                    
                    logger.info("Successfully clicked Charleston County search button")
                    print("✅ Search button clicked!")
                    return True
                else:
                    print("⚠️ Button is disabled, waiting for it to become enabled...")
                    # Wait for button to become enabled with timeout
                    try:
                        WebDriverWait(self.driver, 15).until(
                            lambda driver: search_button.is_enabled()
                        )
                        print("🖱️ Button is now enabled, clicking...")
                        search_button.click()
                        time.sleep(3)
                        
                        logger.info("Successfully clicked Charleston County search button after waiting")
                        print("✅ Search button clicked after waiting!")
                        return True
                    except TimeoutException:
                        logger.error("Search button remained disabled after 15 seconds")
                        print("❌ Search button remained disabled after waiting")
                        
                        # Try alternative approach - force click with JavaScript
                        print("🔧 Attempting JavaScript click...")
                        try:
                            self.driver.execute_script("arguments[0].click();", search_button)
                            time.sleep(3)
                            logger.info("JavaScript click succeeded")
                            print("✅ JavaScript click succeeded!")
                            return True
                        except Exception as js_error:
                            logger.error(f"JavaScript click failed: {js_error}")
                            print(f"❌ JavaScript click failed: {js_error}")
                            return False
            else:
                logger.warning("Search button not found")
                print("❌ Search button not found")
                return False
                
        except Exception as e:
            logger.error(f"Search button click failed: {e}")
            print(f"❌ Search failed: {e}")
            return False
    
    @traceable(name="wait_for_charleston_results")
    def wait_for_charleston_results(self):
        """Wait for Charleston County search results to load"""
        try:
            logger.info("Step 5: Waiting for Charleston County search results")
            print("⏳ Waiting for search results...")
            
            # Wait for either property results or error/no results message
            result_selectors = [
                'a[title*="View Details"]',  # Property card links
                '.k-grid-content',           # Results grid
                '.alert',                    # Error messages
                '.no-results',              # No results message
                '.search-results',          # General results container
                '.property-card'            # Property cards
            ]
            
            # Wait for any of the result indicators
            for selector in result_selectors:
                try:
                    element = self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    logger.info(f"Found result element: {selector}")
                    print(f"✅ Found results with selector: {selector}")
                    return True
                except:
                    continue
            
            # If no specific selectors found, wait a bit longer for page to stabilize
            time.sleep(5)
            logger.info("Search completed (results may vary)")
            print("✅ Search completed!")
            return True
            
        except Exception as e:
            logger.error(f"Timeout waiting for Charleston County results: {e}")
            print(f"❌ Timeout waiting for results: {e}")
            return False
    
    @traceable(name="click_view_details_property_card")
    def click_view_details_property_card(self, tms_number: str):
        """Find and click the 'View Details' property card link for the specific TMS"""
        try:
            logger.info(f"Step 6: Looking for 'View Details' property card link for TMS: {tms_number}")
            print(f"🔍 Looking for 'View Details' link for TMS: {tms_number}")
            
            # Try multiple selectors for view details link
            view_details_selectors = [
                f'a[title="View Details {tms_number}"]',
                'a[title*="View Details"]',
                '.view-details',
                'a:contains("View Details")',
                'a:contains("Details")'
            ]
            
            view_details_link = None
            for selector in view_details_selectors:
                try:
                    if ':contains(' in selector:
                        # Use XPath for text-based search
                        view_details_link = self.driver.find_element(By.XPATH, "//a[contains(text(), 'View Details') or contains(text(), 'Details')]")
                    else:
                        view_details_link = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    logger.info(f"Found view details link with selector: {selector}")
                    print(f"✅ Found view details link: {selector}")
                    break
                except:
                    continue
            
            if view_details_link:
                # Click the "View Details" link
                print(f"🖱️ Clicking 'View Details' for TMS: {tms_number}")
                view_details_link.click()
                time.sleep(3)
                
                logger.info(f"Successfully clicked 'View Details' for TMS: {tms_number}")
                print("✅ Property details page loaded!")
                return True
            else:
                logger.warning("View Details link not found")
                print("❌ View Details link not found")
                return False
            
        except Exception as e:
            logger.error(f"Error clicking 'View Details' property card: {e}")
            print(f"❌ Error clicking 'View Details': {e}")
            return False
    
    @traceable(name="save_page_as_pdf")
    def save_page_as_pdf(self, label: str, filename: str, tms_number: str = None):
        """Save current page as PDF with specific label using Chrome's PDF printing"""
        try:
            logger.info(f"Saving page as PDF: {label}")
            
            # Use TMS-specific folder if provided
            if tms_number:
                from src.config import get_tms_folder_path
                downloads_dir = get_tms_folder_path(tms_number)
            else:
                # Create downloads directory if it doesn't exist
                downloads_dir = Path(DOWNLOAD_PATH) / "charleston"
                downloads_dir.mkdir(parents=True, exist_ok=True)
            
            # Create full PDF path
            pdf_path = downloads_dir / f"{filename}.pdf"
            
            # Use Chrome DevTools to generate PDF
            pdf_result = self.driver.execute_cdp_cmd('Page.printToPDF', {
                'landscape': False,
                'displayHeaderFooter': False,
                'printBackground': True,
                'preferCSSPageSize': True,
                'paperWidth': 8.5,
                'paperHeight': 11,
                'marginTop': 0.5,
                'marginBottom': 0.5,
                'marginLeft': 0.5,
                'marginRight': 0.5
            })
            
            # Decode and save PDF
            import base64
            with open(pdf_path, 'wb') as f:
                f.write(base64.b64decode(pdf_result['data']))
            
            logger.info(f"PDF saved: {label} -> {pdf_path}")
            print(f"📄 Saved PDF: {label}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save PDF {label}: {e}")
            # Fallback to screenshot if PDF fails
            try:
                screenshot_path = downloads_dir / f"{filename}_screenshot.png"
                self.driver.save_screenshot(str(screenshot_path))
                logger.info(f"Saved screenshot fallback: {screenshot_path}")
                print(f"📸 Saved screenshot: {label}")
                return True
            except Exception as fallback_error:
                logger.error(f"Even screenshot fallback failed: {fallback_error}")
                return False
    
    @traceable(name="navigate_to_tax_info")
    def navigate_to_tax_info(self, tms_number: str):
        """Navigate to tax info page for the property"""
        try:
            logger.info(f"Navigating to tax info for TMS: {tms_number}")
            
            # Look for tax info link at bottom of page
            tax_info_selectors = [
                'a[href*="tax"]',
                'a[href*="Tax"]',
                'a:contains("Tax Info")',
                'a:contains("tax info")',
                '.tax-info-link'
            ]
            
            tax_link = None
            for selector in tax_info_selectors:
                try:
                    if ':contains(' in selector:
                        tax_link = self.driver.find_element(By.XPATH, "//a[contains(text(), 'Tax') or contains(text(), 'tax')]")
                    else:
                        tax_link = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except:
                    continue
            
            if tax_link:
                tax_link.click()
                time.sleep(3)
                logger.info("Successfully navigated to tax info page")
                print("✅ Tax info page loaded")
                return True
            else:
                # Try direct URL navigation
                tax_url = f"https://sc-charleston.publicaccessnow.com/RealPropertyBillSearch/AccountSummary.aspx?p={tms_number}&a=1361283"
                self.driver.get(tax_url)
                time.sleep(3)
                logger.info("Navigated to tax info via direct URL")
                print("✅ Tax info page loaded via URL")
                return True
                
        except Exception as e:
            logger.error(f"Failed to navigate to tax info: {e}")
            return False
    
    @traceable(name="navigate_to_register_of_deeds")
    def navigate_to_register_of_deeds(self):
        """Navigate to Charleston County Register of Deeds website"""
        try:
            logger.info("Navigating to Register of Deeds Direct Book and Page Search")
            
            # ALWAYS use the direct Book and Page search URL to save tokens and time
            # This is the most efficient path to deed search
            direct_book_page_url = "https://www.charlestoncounty.org/departments/rod/ds-DMBookandPage.php"
            
            # Only use fallback URLs if the direct URL fails
            fallback_urls = [
                "https://www.charlestoncounty.org/departments/register-of-deeds/index.php",
                "https://rod.charlestoncounty.org/",
                "https://www.charlestoncounty.org/departments/rod/"
            ]
            
            # Try direct URL first
            logger.info(f"Navigating directly to Book & Page search: {direct_book_page_url}")
            self.driver.get(direct_book_page_url)
            time.sleep(3)
            
            # Check for book/page input fields to confirm we're on the direct search page
            try:
                book_fields = self.driver.find_elements(By.XPATH, "//input[contains(@id, 'Book') or contains(@name, 'Book') or contains(@placeholder, 'Book')]")
                if book_fields:
                    logger.info(f"Found book input field - direct URL works!")
                else:
                    logger.warning("Direct URL loaded but no book field found, checking page content")
            except Exception as e:
                logger.warning(f"Error checking for book fields: {e}")
                
                # Try fallback URLs if direct URL fails
                for url in fallback_urls:
                    try:
                        logger.info(f"Trying fallback URL: {url}")
                        self.driver.get(url)
                        time.sleep(3)
                        
                        # Check for book/page input fields on fallback URL
                        book_fields = self.driver.find_elements(By.XPATH, "//input[contains(@id, 'Book') or contains(@name, 'Book') or contains(@placeholder, 'Book')]")
                        if book_fields:
                            logger.info(f"Found book input field on fallback URL: {url}")
                            break
                    except:
                        continue
            
            # Take screenshot of the landing page for debugging
            self.take_screenshot("register_of_deeds_landing.png")
            logger.info("Landing page screenshot saved (if screenshots enabled)")
            
            # Check if we need to handle any disclaimer or legal notice
            try:
                disclaimer_checkbox = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="checkbox"]'))
                )
                if not disclaimer_checkbox.is_selected():
                    disclaimer_checkbox.click()
                    logger.info("Clicked disclaimer checkbox")
            except:
                logger.info("No disclaimer checkbox found on initial page")
            
            # Look for any "enter" or "submit" buttons that might need to be clicked to reach the search form
            try:
                enter_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Enter') or contains(text(), 'Search')] | //input[contains(@value, 'Enter') or contains(@value, 'Search')]")
                if enter_buttons:
                    enter_buttons[0].click()
                    logger.info("Clicked Enter button to proceed to search page")
                    time.sleep(3)
            except:
                pass
                
            logger.info("Successfully navigated to Register of Deeds")
            print("✅ Register of Deeds page loaded")
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate to Register of Deeds: {e}")
            return False
    
    @traceable(name="search_deed_by_book_page")
    def search_deed_by_book_page(self, book: str, page: str, max_retries: int = 2):
        """Search for deed by book and page number with validation and retry"""
        try:
            logger.info(f"Searching for deed: Book {book}, Page {page}")
            
            # Take screenshot of initial page state
            self.take_screenshot(f"deed_search_initial_{book}_{page}.png")
            logger.info(f"Initial state screenshot saved (if screenshots enabled)")
            
            # ALWAYS ensure we're on the direct book and page search URL
            current_url = self.driver.current_url
            target_url = "https://www.charlestoncounty.org/departments/rod/ds-DMBookandPage.php"
            
            if target_url.lower() not in current_url.lower():
                logger.info(f"Directly navigating to Book & Page search: {target_url}")
                self.driver.get(target_url)
                time.sleep(3)
            
            # If page has multiple forms or tabs, look for "Book and Page" search option
            try:
                book_page_tabs = self.driver.find_elements(By.XPATH, "//a[contains(text(), 'Book') and contains(text(), 'Page')]")
                if book_page_tabs:
                    logger.info("Found Book and Page search tab/option, clicking it")
                    book_page_tabs[0].click()
                    time.sleep(2)
            except Exception as tab_error:
                logger.warning(f"No Book and Page tab found or error clicking it: {tab_error}")
            
            for attempt in range(max_retries + 1):
                try:
                    # Format the book number - ensure 4 digits for numeric books
                    formatted_book = book.strip()
                    # If it's numeric, zero-pad to 4 digits
                    if formatted_book.isdigit():
                        formatted_book = formatted_book.zfill(4)
                    
                    # Format the page number - ensure 3 digits
                    formatted_page = page.strip()
                    if formatted_page.isdigit():
                        formatted_page = formatted_page.zfill(3)
                    
                    logger.info(f"Formatted deed reference: Book {formatted_book}, Page {formatted_page}")
                    
                    # COMPREHENSIVE FIELD SEARCH STRATEGY
                    # First, get all form input fields for examination
                    try:
                        input_fields = self.driver.find_elements(By.XPATH, "//input[@type='text']")
                        logger.info(f"Found {len(input_fields)} text input fields on page")
                        
                        # Print all field attributes for debugging
                        for i, field in enumerate(input_fields):
                            field_id = field.get_attribute('id') or 'no-id'
                            field_name = field.get_attribute('name') or 'no-name'
                            field_placeholder = field.get_attribute('placeholder') or 'no-placeholder'
                            logger.info(f"Field {i+1}: id='{field_id}', name='{field_name}', placeholder='{field_placeholder}'")
                    except Exception as field_scan_error:
                        logger.warning(f"Unable to scan input fields: {field_scan_error}")
                        
                    # FIELD DETECTION STRATEGY 1: Find book field by common attributes
                    book_field = None
                    book_field_found = False
                    
                    # Try all possible selectors for book field
                    book_selectors = [
                        "//input[@id='txtBook']",
                        "//input[contains(@id, 'Book')]",
                        "//input[contains(@name, 'Book')]", 
                        "//input[contains(@placeholder, 'Book')]",
                        "//input[contains(@id, 'book')]",
                        "//input[contains(@name, 'book')]",
                        "//input[contains(@placeholder, 'book')]",
                        "//input[contains(@label, 'Book')]",
                        "//input[contains(@aria-label, 'Book')]",
                        "//label[contains(text(), 'Book')]/following::input[1]",
                        "//label[contains(text(), 'book')]/following::input[1]"
                    ]
                    
                    for selector in book_selectors:
                        try:
                            book_field = WebDriverWait(self.driver, 5).until(
                                EC.presence_of_element_located((By.XPATH, selector))
                            )
                            book_field.clear()
                            book_field.send_keys(formatted_book)
                            logger.info(f"Entered book number '{formatted_book}' using selector: {selector}")
                            book_field_found = True
                            break
                        except:
                            continue
                    
                    # If we still can't find the book field, try the first input
                    if not book_field_found:
                        try:
                            # If we have exactly two text input fields, assume first is book
                            if len(input_fields) == 2:
                                book_field = input_fields[0]
                                book_field.clear()
                                book_field.send_keys(formatted_book)
                                logger.info(f"Entered book number '{formatted_book}' using first input field")
                                book_field_found = True
                            else:
                                # Use JavaScript to help find the right field if possible
                                self.driver.execute_script("""
                                    var inputs = document.querySelectorAll('input[type="text"]');
                                    for (var i = 0; i < inputs.length; i++) {
                                        var field = inputs[i];
                                        if (field.id.toLowerCase().indexOf('book') >= 0 || 
                                            field.name.toLowerCase().indexOf('book') >= 0 ||
                                            field.placeholder.toLowerCase().indexOf('book') >= 0) {
                                            field.style.border = '3px solid red';
                                            field.value = arguments[0];
                                            return true;
                                        }
                                    }
                                    return false;
                                """, formatted_book)
                        except Exception as js_error:
                            logger.warning(f"JavaScript field finder failed: {js_error}")
                    
                    # SIMILAR STRATEGY FOR PAGE FIELD
                    page_field = None
                    page_field_found = False
                    
                    page_selectors = [
                        "//input[@id='txtPage']",
                        "//input[contains(@id, 'Page')]",
                        "//input[contains(@name, 'Page')]", 
                        "//input[contains(@placeholder, 'Page')]",
                        "//input[contains(@id, 'page')]",
                        "//input[contains(@name, 'page')]",
                        "//input[contains(@placeholder, 'page')]",
                        "//input[contains(@label, 'Page')]",
                        "//input[contains(@aria-label, 'Page')]",
                        "//label[contains(text(), 'Page')]/following::input[1]",
                        "//label[contains(text(), 'page')]/following::input[1]"
                    ]
                    
                    for selector in page_selectors:
                        try:
                            page_field = WebDriverWait(self.driver, 5).until(
                                EC.presence_of_element_located((By.XPATH, selector))
                            )
                            page_field.clear()
                            page_field.send_keys(formatted_page)
                            logger.info(f"Entered page number '{formatted_page}' using selector: {selector}")
                            page_field_found = True
                            break
                        except:
                            continue
                    
                    # If we still can't find the page field, try the second input
                    if not page_field_found:
                        try:
                            # If we have exactly two text input fields, assume second is page
                            if len(input_fields) == 2:
                                page_field = input_fields[1]
                                page_field.clear()
                                page_field.send_keys(formatted_page)
                                logger.info(f"Entered page number '{formatted_page}' using second input field")
                                page_field_found = True
                            else:
                                # Use JavaScript to help find the right field if possible
                                self.driver.execute_script("""
                                    var inputs = document.querySelectorAll('input[type="text"]');
                                    for (var i = 0; i < inputs.length; i++) {
                                        var field = inputs[i];
                                        if (field.id.toLowerCase().indexOf('page') >= 0 || 
                                            field.name.toLowerCase().indexOf('page') >= 0 ||
                                            field.placeholder.toLowerCase().indexOf('page') >= 0) {
                                            field.style.border = '3px solid blue';
                                            field.value = arguments[0];
                                            return true;
                                        }
                                    }
                                    return false;
                                """, formatted_page)
                        except Exception as js_error:
                            logger.warning(f"JavaScript field finder failed: {js_error}")
                    
                    # Take screenshot after field entry for debugging
                    if not DISABLE_SCREENSHOTS:
                        self.driver.save_screenshot(f"deed_search_fields_filled_{book}_{page}.png")
                        logger.info(f"Saved fields filled screenshot")
                    
                    # Check for any legal disclaimer checkboxes
                    checkboxes = self.driver.find_elements(By.XPATH, "//input[@type='checkbox']")
                    for checkbox in checkboxes:
                        try:
                            if not checkbox.is_selected():
                                checkbox.click()
                                logger.info(f"Clicked checkbox: {checkbox.get_attribute('id') or 'unnamed'}")
                        except:
                            pass
                    
                    # COMPREHENSIVE SEARCH BUTTON DETECTION
                    search_button = None
                    search_button_found = False
                    
                    # Try all possible selectors for search button
                    search_button_selectors = [
                        "//button[@id='btnSearch']",
                        "//input[@id='btnSearch']",
                        "//button[contains(@id, 'Search') or contains(@id, 'search')]",
                        "//input[@type='submit' or @type='button' or @value='Search']", 
                        "//button[contains(text(), 'Search')]",
                        "//button[contains(text(), 'search')]",
                        "//input[contains(@value, 'Search')]",
                        "//input[contains(@value, 'search')]",
                        "//a[contains(text(), 'Search')]",
                        "//button[@type='submit']", 
                        "//input[@type='image' and contains(@src, 'search')]",
                        "//form//button", 
                        "//form//input[@type='submit']"
                    ]
                    
                    for selector in search_button_selectors:
                        try:
                            search_buttons = self.driver.find_elements(By.XPATH, selector)
                            if search_buttons:
                                # Try to pick the most relevant button if multiple found
                                for btn in search_buttons:
                                    if btn.is_displayed() and btn.is_enabled():
                                        search_button = btn
                                        search_button.click()
                                        logger.info(f"Clicked search button using selector: {selector}")
                                        search_button_found = True
                                        break
                            if search_button_found:
                                break
                        except:
                            continue
                    
                    # If we still can't find the search button, try JavaScript form submit as last resort
                    if not search_button_found:
                        try:
                            logger.info("Attempting form submit via JavaScript")
                            self.driver.execute_script("document.querySelector('form').submit();")
                            logger.info("Form submitted via JavaScript")
                        except Exception as js_submit_error:
                            logger.warning(f"JavaScript form submit failed: {js_submit_error}")
                            
                    # Wait for results or error message
                    time.sleep(5)
                    
                    # Check for CAPTCHA after form submission
                    if self.driver.page_source and ('captcha' in self.driver.page_source.lower() or 
                                                  'recaptcha' in self.driver.page_source.lower() or
                                                  'hcaptcha' in self.driver.page_source.lower()):
                        logger.info("CAPTCHA detected after search submission")
                        print("🔒 CAPTCHA detected after search submission")
                        
                        # Try to solve the captcha
                        captcha_result = self.detect_and_solve_captcha()
                        if captcha_result:
                            logger.info("CAPTCHA solved successfully, continuing workflow")
                            print("✅ CAPTCHA solved, continuing workflow")
                            time.sleep(3)  # Wait for page to process after CAPTCHA
                        else:
                            logger.warning("CAPTCHA solving failed or manual intervention required")
                            print("⚠️ CAPTCHA handling failed, may require manual intervention")
                    
                    # Take screenshot of search results for debugging
                    if not DISABLE_SCREENSHOTS:
                        self.driver.save_screenshot(f"deed_search_results_{book}_{page}.png")
                        logger.info(f"Saved search results screenshot")
                    
                    # IMPROVED RESULT DETECTION
                    # Check for various indicators that results are present
                    indicators_found = False
                    
                    # Possible result indicators
                    result_indicators = [
                        "//button[contains(text(), 'View')]", 
                        "//a[contains(text(), 'View')]", 
                        "//img[contains(@alt, 'view')]/parent::a", 
                        "//img[contains(@src, 'view')]/parent::a",
                        "//img[contains(@src, 'pdf')]/parent::a",
                        "//a[contains(@href, '.pdf')]",
                        "//table//tr[position() > 1]",  # Table with more than header row
                        "//td[contains(text(), '" + book + "')]",  # Cell containing book number
                        "//div[contains(text(), 'Result')]",  # Result header text
                        "//div[contains(@class, 'result')]"  # Result container
                    ]
                    
                    # Check for any result indicators
                    for indicator in result_indicators:
                        elements = self.driver.find_elements(By.XPATH, indicator)
                        if elements:
                            logger.info(f"Found {len(elements)} result indicator(s) using: {indicator}")
                            indicators_found = True
                            break
                    
                    # Check for "no results" messages
                    no_results = False
                    no_results_indicators = [
                        "//div[contains(text(), 'No results')]",
                        "//div[contains(text(), 'no records')]",
                        "//div[contains(text(), 'No matching')]",
                        "//p[contains(text(), 'No results')]",
                        "//span[contains(text(), 'no results')]"
                    ]
                    
                    for indicator in no_results_indicators:
                        elements = self.driver.find_elements(By.XPATH, indicator)
                        if elements:
                            logger.info(f"Found no results message using: {indicator}")
                            no_results = True
                            break
                    
                    # Evaluate search outcome
                    if no_results:
                        logger.warning(f"No deed found for Book {book}, Page {page}")
                        print(f"⚠️ No deed found for Book {book}, Page {page}")
                        return False
                    
                    if indicators_found:
                        # Success - found results
                        logger.info(f"✅ Deed found for Book {book}, Page {page}")
                        print(f"✅ Found deed: Book {book}, Page {page}")
                        return True
                    
                    # If we got here, check if we had form submit issues
                    if not search_button_found:
                        logger.warning(f"Search button not found/clicked for attempt {attempt+1}")
                        if attempt < max_retries:
                            continue
                    
                    # No clear indicators of success or failure
                    logger.warning(f"Unclear search results for Book {book}, Page {page}")
                    # Take screenshot of unclear results if screenshots are enabled
                    if not DISABLE_SCREENSHOTS:
                        self.driver.save_screenshot(f"deed_search_unclear_{book}_{page}.png")
                    
                    # Assume success and proceed - the download method will detect if there's a problem
                    logger.info(f"✓ Proceeding with deed: Book {book}, Page {page}")
                    print(f"✓ Proceeding with deed: Book {book}, Page {page}")
                    return True
                    
                except Exception as e:
                    if attempt < max_retries:
                        logger.warning(f"Deed search attempt {attempt+1} failed: {e}. Retrying...")
                        # Refresh the page to try again
                        self.navigate_to_register_of_deeds()
                        time.sleep(2)
                    else:
                        logger.error(f"All deed search attempts failed: {e}")
                        raise
            
        except Exception as e:
            logger.error(f"Failed to search deed {book} {page}: {e}")
            return False
    
    @traceable(name="download_deed_pdf")
    def download_deed_pdf(self, filename: str, tms_number: str = None, max_retries: int = 3):
        """Download deed PDF from view page with retry logic"""
        try:
            logger.info(f"Downloading deed PDF: {filename}")
            print(f"📥 Downloading deed PDF: {filename}")
            
            # Use TMS-specific folder if provided
            if tms_number:
                from src.config import get_tms_folder_path
                downloads_dir = get_tms_folder_path(tms_number)
            else:
                # Create downloads directory if it doesn't exist
                downloads_dir = Path(DOWNLOAD_PATH) / "charleston" / "deeds"
                downloads_dir.mkdir(parents=True, exist_ok=True)
            
            # Final PDF path
            pdf_path = downloads_dir / f"{filename}.pdf"
            
            # Take screenshot of results page before trying to click View button (if enabled)
            if not DISABLE_SCREENSHOTS:
                self.driver.save_screenshot(f"deed_download_start_{filename}.png")
                logger.info(f"Saved initial state screenshot")
            
            # Check for any captcha before trying to download
            if self.driver.page_source and ('captcha' in self.driver.page_source.lower() or 
                                          'recaptcha' in self.driver.page_source.lower() or
                                          'hcaptcha' in self.driver.page_source.lower()):
                logger.info("CAPTCHA detected before download")
                print("🔒 CAPTCHA detected before download")
                
                captcha_result = self.detect_and_solve_captcha()
                if captcha_result:
                    logger.info("CAPTCHA solved successfully, continuing download")
                    print("✅ CAPTCHA solved, continuing download")
                    time.sleep(3)
                else:
                    logger.warning("CAPTCHA solving failed, may affect download")
                    print("⚠️ CAPTCHA handling failed, attempting download anyway")
            
            # Log all page links for debugging
            try:
                links = self.driver.find_elements(By.TAG_NAME, 'a')
                logger.info(f"Found {len(links)} links on page")
                for i, link in enumerate(links[:10]):
                    href = link.get_attribute('href') or 'no-href'
                    text = link.text or 'no-text'
                    logger.info(f"Link {i+1}: text='{text}', href='{href}'")
            except Exception as link_error:
                logger.warning(f"Error listing page links: {link_error}")
            
            # Look for the record in search results - with retry
            for attempt in range(max_retries + 1):
                try:
                    # Look for download/view buttons - Try various selector patterns
                    view_pdf_selectors = [
                        "//a[contains(@href, '.pdf')]",
                        "//a[contains(text(), 'View') or contains(text(), 'PDF')]",
                        "//img[contains(@src, 'pdf') or contains(@alt, 'pdf')]/parent::a",
                        "//button[contains(text(), 'View') or contains(text(), 'Download')]",
                        "//a[contains(@title, 'View') or contains(@title, 'Download')]"
                    ]
                    
                    view_button = None
                    for selector in view_pdf_selectors:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        if elements:
                            view_button = elements[0]
                            logger.info(f"Found view/download button with selector: {selector}")
                            print(f"✅ Found view/download link: {selector}")
                            break
                    
                    if view_button:
                        # Click the view button to start download or open in new tab
                        logger.info("Clicking view/download button")
                        print("🖱️ Clicking view/download button...")
                        
                        # Try to handle target=_blank by saving the current handles
                        original_window = self.driver.current_window_handle
                        original_handles = self.driver.window_handles
                        
                        # Click the button - may open in new tab/window
                        view_button.click()
                        time.sleep(3)
                        
                        # Check if a new window/tab was opened
                        new_handles = self.driver.window_handles
                        if len(new_handles) > len(original_handles):
                            # Switch to new window
                            new_window = [x for x in new_handles if x != original_window][0]
                            self.driver.switch_to.window(new_window)
                            logger.info("Switched to new window/tab for PDF")
                            print("🔄 Switched to new window/tab for PDF")
                            
                            # Take screenshot in new window if enabled
                            if not DISABLE_SCREENSHOTS:
                                self.driver.save_screenshot(f"deed_new_window_{filename}.png")
                            
                            # Check for CAPTCHA in new window
                            if self.driver.page_source and ('captcha' in self.driver.page_source.lower() or 
                                                        'recaptcha' in self.driver.page_source.lower() or
                                                        'hcaptcha' in self.driver.page_source.lower()):
                                logger.info("CAPTCHA detected in PDF window")
                                print("🔒 CAPTCHA detected in PDF window")
                                
                                captcha_result = self.detect_and_solve_captcha()
                                if captcha_result:
                                    logger.info("CAPTCHA solved in PDF window")
                                    print("✅ CAPTCHA solved, continuing download")
                                    time.sleep(3)
                        
                        # Check for PDF content or download
                        if "application/pdf" in self.driver.page_source or ".pdf" in self.driver.current_url:
                            # Direct PDF in browser - save it
                            logger.info("Direct PDF detected in browser")
                            print("📄 PDF opened in browser, saving...")
                            
                            try:
                                # Get PDF content via DevTools Protocol
                                pdf_content = self.driver.execute_cdp_cmd('Page.printToPDF', {
                                    'landscape': False,
                                    'displayHeaderFooter': False,
                                    'printBackground': True,
                                })
                                
                                # Save PDF to file
                                with open(pdf_path, 'wb') as file:
                                    import base64
                                    file.write(base64.b64decode(pdf_content['data']))
                                
                                logger.info(f"Successfully saved PDF to: {pdf_path}")
                                print(f"✅ Successfully saved PDF: {filename}")
                                
                                # Close the new window and switch back if needed
                                if len(new_handles) > len(original_handles):
                                    self.driver.close()
                                    self.driver.switch_to.window(original_window)
                                
                                return True
                            except Exception as pdf_error:
                                logger.error(f"Error saving PDF: {pdf_error}")
                                
                                # Fallback - try to get PDF source directly
                                try:
                                    current_url = self.driver.current_url
                                    if current_url.endswith('.pdf'):
                                        import requests
                                        response = requests.get(current_url)
                                        with open(pdf_path, 'wb') as file:
                                            file.write(response.content)
                                        
                                        logger.info(f"Successfully saved PDF via direct URL: {pdf_path}")
                                        print(f"✅ Successfully saved PDF via URL: {filename}")
                                        return True
                                except Exception as fallback_error:
                                    logger.error(f"Fallback PDF download failed: {fallback_error}")
                        
                        # Wait for download to start (if not direct display)
                        time.sleep(5)
                        
                        # Look for the file in downloads directory
                        import glob
                        potential_files = list(downloads_dir.glob("*.pdf"))
                        
                        if potential_files:
                            newest_file = max(potential_files, key=lambda x: x.stat().st_mtime)
                            
                            # If file exists but doesn't match our expected filename, rename it
                            if newest_file.stem != filename:
                                target_path = downloads_dir / f"{filename}.pdf"
                                newest_file.rename(target_path)
                                logger.info(f"Renamed {newest_file} to {target_path}")
                            
                            logger.info(f"Successfully downloaded PDF: {newest_file}")
                            print(f"✅ Successfully downloaded PDF: {filename}")
                            

                            # Close the new window and switch back if needed
                            if len(new_handles) > len(original_handles):
                                self.driver.close()
                                self.driver.switch_to.window(original_window)
                                
                            return True
                        
                        # Try using browser back to get to search results and try again
                        if attempt < max_retries:
                            logger.info("PDF not found, navigating back to search results")
                            print("🔄 PDF not found, navigating back...")
                            
                            # Take screenshot before navigating back
                            self.driver.save_screenshot(f"before_navigate_back.png")
                            
                            self.driver.back()
                            time.sleep(3)
                            
                            # Take screenshot after navigating back
                            self.driver.save_screenshot(f"after_navigate_back.png")
                    else:
                        logger.warning("No view/download button found, attempting direct PDF extraction")
                        print("⚠️ No view/download button found")
                        
                        # Check if we're directly looking at a PDF object or iframe
                        pdf_objects = self.driver.find_elements(By.XPATH, "//object[contains(@type, 'pdf')] | //iframe[contains(@src, '.pdf')]")
                        
                        if pdf_objects:
                            pdf_src = pdf_objects[0].get_attribute('src') or pdf_objects[0].get_attribute('data')
                            
                            if pdf_src and '.pdf' in pdf_src:
                                # Download PDF directly
                                import requests
                                response = requests.get(pdf_src)
                                
                                with open(pdf_path, 'wb') as file:
                                    file.write(response.content)
                                
                                logger.info(f"Successfully downloaded PDF from object/iframe: {pdf_path}")
                                print(f"✅ Successfully saved PDF from viewer: {filename}")
                                return True
                        
                        if attempt < max_retries - 1:
                            # Retry after waiting
                            logger.info(f"Retry {attempt+1}/{max_retries} - waiting before next attempt")
                            print(f"🔄 Attempt {attempt+1}/{max_retries} failed, retrying...")
                            time.sleep(3)
                        else:
                            logger.error(f"Failed to find and click view button after {max_retries} attempts")
                            print(f"❌ Failed to download PDF: {filename}")
                            return False
                        
                except Exception as e:
                    logger.error(f"Error during attempt {attempt+1}: {e}")
                    
                    if attempt < max_retries:
                        # Take screenshot after error
                        self.driver.save_screenshot(f"download_error_{filename}_attempt{attempt+1}.png")
                        
                        # Check for CAPTCHA after error
                        if self.driver.page_source and ('captcha' in self.driver.page_source.lower() or 
                                                     'recaptcha' in self.driver.page_source.lower()):
                            logger.info("CAPTCHA detected after error")
                            print("🔒 CAPTCHA detected after error")
                            
                            captcha_result = self.detect_and_solve_captcha()
                            if captcha_result:
                                logger.info("CAPTCHA solved successfully, retrying download")
                                print("✅ CAPTCHA solved, retrying download")
                                time.sleep(3)
                        else:
                            # Wait before retry
                            logger.info(f"Retry {attempt+1}/{max_retries} - waiting 5 seconds")
                            print(f"🔄 Attempt {attempt+1}/{max_retries} failed, retrying...")
                            time.sleep(5)
                    else:
                        logger.error(f"Failed to download PDF after {max_retries} attempts: {e}")
                        print(f"❌ Failed to download PDF after {max_retries} attempts")
                        return False
            
            logger.error("All download attempts failed")
            print("❌ All download attempts failed")
            return False
            
        except Exception as e:
            logger.error(f"Error in download_deed_pdf: {e}")
            print(f"❌ Error downloading PDF: {e}")
            return False
    
    @traceable(name="navigate_back_to_deed_search")
    def navigate_back_to_deed_search(self):
        """Navigate back to deed search page for next search"""
        try:
            logger.info("Navigating back to deed search")
            
            # Take screenshot of current state
            self.driver.save_screenshot("before_navigate_back.png")
            
            # First check if we need to close any additional windows/tabs
            if len(self.driver.window_handles) > 1:
                logger.info(f"Multiple windows/tabs detected: {len(self.driver.window_handles)}")
                # Keep only the first window/tab
                main_window = self.driver.window_handles[0]
                current_handle = self.driver.current_window_handle
                
                # Close all but the main window
                for handle in self.driver.window_handles.copy():
                    if handle != main_window:
                        try:
                            self.driver.switch_to.window(handle)
                            self.driver.close()
                            logger.info(f"Closed extra window/tab: {handle}")
                        except Exception as close_error:
                            logger.warning(f"Error closing window/tab: {close_error}")
                
                # Switch back to main window
                try:
                    self.driver.switch_to.window(main_window)
                    logger.info("Switched back to main window")
                except Exception as switch_error:
                    logger.error(f"Error switching to main window: {switch_error}")
                    # If we can't switch back to main window, something's wrong - restart browser
                    self.navigate_to_register_of_deeds()
                    return True
            
            # Check if we're already on the deed search form
            try:
                # Quick check if we appear to be on a deed search form already
                book_fields = self.driver.find_elements(By.XPATH, "//input[contains(@id, 'Book') or contains(@name, 'Book') or contains(@placeholder, 'Book')]")
                if book_fields:
                    logger.info("Already on deed search form, no navigation needed")
                    return True
            except:
                pass
                
            # Try multiple approaches to navigate back
            
            # Approach 1: Try back button or navigation link
            try:
                back_selectors = [
                    "//button[contains(text(), 'Back')]", 
                    "//a[contains(text(), 'Back')]",
                    "//button[contains(text(), 'New Search')]",
                    "//a[contains(text(), 'New Search')]",
                    "//button[contains(@id, 'back') or contains(@class, 'back')]",
                    "//a[contains(@id, 'back') or contains(@class, 'back')]",
                    "//a[contains(@href, 'search')]",
                    "//a[contains(@href, 'index')]"
                ]
                
                back_button = None
                for selector in back_selectors:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements:
                        for element in elements:
                            if element.is_displayed() and element.is_enabled():
                                back_button = element
                                logger.info(f"Found back button/link using selector: {selector}")
                                break
                        if back_button:
                            break
                
                if back_button:
                    # Try both regular and JavaScript click
                    try:
                        back_button.click()
                        logger.info("Clicked back button with Selenium")
                    except Exception as click_error:
                        logger.warning(f"Regular click failed: {click_error}, trying JavaScript")
                        self.driver.execute_script("arguments[0].click();", back_button)
                        logger.info("Clicked back button with JavaScript")
                    
                    time.sleep(3)
                    
                    # Verify we're on the search form after clicking
                    book_fields = self.driver.find_elements(By.XPATH, "//input[contains(@id, 'Book') or contains(@name, 'Book') or contains(@placeholder, 'Book')]")
                    if book_fields:
                        logger.info("Successfully returned to deed search form using back button")
                        print("🔙 Back to deed search page")
                        return True
            except Exception as back_error:
                logger.warning(f"Back button approach failed: {back_error}")
            
            # Approach 2: Try browser navigation 
            try:
                logger.info("Trying browser back navigation")
                self.driver.back()
                time.sleep(3)
                
                # Verify we're on the search form after going back
                book_fields = self.driver.find_elements(By.XPATH, "//input[contains(@id, 'Book') or contains(@name, 'Book') or contains(@placeholder, 'Book')]")
                if book_fields:
                    logger.info("Successfully returned to deed search form using browser back")
                    print("🔙 Back to deed search page")
                    return True
            except Exception as browser_back_error:
                logger.warning(f"Browser back navigation failed: {browser_back_error}")
            
            # Approach 3: Navigate directly to deed search (most reliable)
            try:
                logger.info("Navigating directly to book and page search page")
                self.navigate_to_register_of_deeds()
                # This should handle any disclaimer checkbox
                time.sleep(3)
                
                # Verify we're on the search form
                book_fields = self.driver.find_elements(By.XPATH, "//input[contains(@id, 'Book') or contains(@name, 'Book') or contains(@placeholder, 'Book')]")
                if book_fields:
                    logger.info("Successfully returned to deed search form by direct navigation")
                    print("🔙 Back to deed search page")
                    return True
                else:
                    logger.warning("Direct navigation didn't lead to search form with book fields")
                    # Final attempt: direct navigation to old URL
                    self.driver.get("https://www.charlestoncounty.org/departments/rod/ds-DMBookandPage.php")
                    time.sleep(3)
            except Exception as nav_error:
                logger.error(f"Error with direct navigation approach: {nav_error}")
                # Last resort
                self.driver.get("https://www.charlestoncounty.org/departments/rod/")
                time.sleep(3)
                
            # Take a screenshot of where we ended up
            self.driver.save_screenshot("after_navigate_back.png")
            logger.info("Returned to deed search page (or attempted to)")
            print("🔙 Back to deed search page")
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate back to deed search: {e}")
            # Last resort - restart browser session
            try:
                self.navigate_to_register_of_deeds()
            except:
                pass
            return False

    @traceable(name="detect_and_solve_captcha")
    def detect_and_solve_captcha(self):
        """Detect and solve any CAPTCHA on the current page using 2captcha service"""
        try:
            from src.services.captcha_service import CaptchaSolver
            
            logger.info("Checking for CAPTCHA on current page")
            print("🔍 Checking for CAPTCHA...")
            
            # Initialize captcha solver
            captcha_solver = CaptchaSolver()
            
            # Check for reCAPTCHA v2
            recaptcha_elements = self.driver.find_elements(By.CSS_SELECTOR, '.g-recaptcha')
            if recaptcha_elements:
                print("🤖 reCAPTCHA v2 detected!")
                logger.info("reCAPTCHA v2 detected")
                
                # Get sitekey
                site_key = recaptcha_elements[0].get_attribute('data-sitekey')
                if not site_key:
                    logger.warning("Could not find data-sitekey attribute")
                    print("⚠️ Could not find data-sitekey attribute")
                    return False
                
                # Get page URL
                page_url = self.driver.current_url
                
                # Solve captcha synchronously using asyncio
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                captcha_solution = loop.run_until_complete(
                    captcha_solver.solve_recaptcha_v2(site_key, page_url)
                )
                loop.close()
                
                if not captcha_solution:
                    logger.error("Failed to solve reCAPTCHA")
                    print("❌ Failed to solve reCAPTCHA")
                    return False
                
                # Insert the solved captcha
                logger.info("Inserting captcha solution via JavaScript")
                print("✅ Captcha solution received, applying...")
                
                # Use JavaScript to insert the solution
                success = self.driver.execute_script(
                    f'if(typeof document.getElementById("g-recaptcha-response") !== "undefined" && '
                    f'document.getElementById("g-recaptcha-response") !== null) '
                    f'{{ document.getElementById("g-recaptcha-response").innerHTML = "{captcha_solution}"; return true; }} '
                    f'else {{ return false; }}'
                )
                
                if success:
                    # Also trigger the callback function if present
                    self.driver.execute_script(
                        'if(typeof ___grecaptcha_cfg !== "undefined") '
                        '{ setTimeout(function() {'
                        '  for(let f in ___grecaptcha_cfg.clients) {'
                        '    if(typeof ___grecaptcha_cfg.clients[f].callbacks !== "undefined" && '
                        '       ___grecaptcha_cfg.clients[f].callbacks.length > 0) {'
                        '      ___grecaptcha_cfg.clients[f].callbacks[0]();'
                        '    }'
                        '  }'
                        '}, 300); }'
                    )
                    
                    logger.info("Successfully solved and applied reCAPTCHA")
                    print("✅ CAPTCHA solved and applied!")
                    
                    # Wait a moment for any form submission to process
                    time.sleep(2)
                    
                    return True
                else:
                    logger.warning("Could not find g-recaptcha-response element")
                    print("⚠️ Could not insert CAPTCHA solution")
                    return False
            
            # Check for hCaptcha
            hcaptcha_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-hcaptcha-widget-id]')
            if hcaptcha_elements:
                print("🤖 hCaptcha detected!")
                logger.info("hCaptcha detected - manual intervention may be required")
                print("⚠️ hCaptcha support coming soon, manual intervention may be required")
                return False
            
            # Check for simple image captcha
            img_captcha_elements = self.driver.find_elements(
                By.XPATH, 
                "//img[contains(@src, 'captcha') or contains(@alt, 'captcha')]"
            )
            
            if img_captcha_elements:
                print("🤖 Image CAPTCHA detected!")
                logger.info("Image CAPTCHA detected")
                
                # Save the captcha image
                captcha_img = img_captcha_elements[0]
                img_src = captcha_img.get_attribute('src')
                
                # If it's a data URL or remote URL
                import tempfile
                import requests
                from PIL import Image
                from io import BytesIO
                
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                
                if img_src.startswith('data:image'):
                    # Data URL
                    import base64
                    image_data = img_src.split(',')[1]
                    with open(temp_file.name, 'wb') as f:
                        f.write(base64.b64decode(image_data))
                else:
                    # Remote URL
                    response = requests.get(img_src)
                    img = Image.open(BytesIO(response.content))
                    img.save(temp_file.name)
                
                # Solve the image captcha
                captcha_solution = loop.run_until_complete(
                    captcha_solver.solve_image_captcha(temp_file.name)
                )
                
                if not captcha_solution:
                    logger.error("Failed to solve image CAPTCHA")
                    print("❌ Failed to solve image CAPTCHA")
                    return False
                
                # Find the captcha input field
                captcha_input = self.driver.find_element(
                    By.XPATH,
                    "//input[contains(@id, 'captcha') or contains(@name, 'captcha') or contains(@placeholder, 'captcha')]"
                )
                
                if captcha_input:
                    # Enter the solution
                    captcha_input.clear()
                    captcha_input.send_keys(captcha_solution)
                    
                    logger.info("Successfully solved image CAPTCHA")
                    print("✅ Image CAPTCHA solved!")
                    
                    # Look for and click a submit button
                    submit_buttons = self.driver.find_elements(
                        By.XPATH,
                        "//button[@type='submit'] | //input[@type='submit']"
                    )
                    if submit_buttons:
                        submit_buttons[0].click()
                        time.sleep(2)
                    
                    return True
                else:
                    logger.warning("Could not find captcha input field")
                    print("⚠️ Could not find captcha input field")
                    return False
            
            logger.info("No CAPTCHA detected on current page")
            print("✅ No CAPTCHA detected")
            return True
            
        except Exception as e:
            logger.error(f"Error in CAPTCHA detection/solving: {e}")
            print(f"❌ CAPTCHA handling error: {e}")
            return False
    
    def close_browser(self):
        """Close the browser"""
        try:
            if self.driver:
                self.driver.quit()
                logger.info("Browser closed successfully")
                print("🔒 Browser closed")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
    
    def get_page_title(self):
        """Get the current page title for LLM analysis"""
        try:
            if self.driver:
                title = self.driver.title
                logger.info(f"Current page title: {title}")
                return title
            else:
                return "Browser not initialized"
        except Exception as e:
            logger.error(f"Error getting page title: {e}")
            return "Unknown"
            
    @property
    @property
    def page_source(self):
        """Get the current page source HTML for LLM analysis"""
        try:
            if self.driver:
                return self.driver.page_source
            else:
                return "Browser not initialized"
        except Exception as e:
            logger.error(f"Error getting page source: {e}")
            return "Error getting page source"
    
    def take_screenshot(self, filename="screenshot.png", force=False, county=None, tms=None):
        """
        Take a screenshot only if screenshots are not disabled or force is True
        
        Args:
            filename: The filename for the screenshot
            force: If True, take the screenshot even if DISABLE_SCREENSHOTS is True
            county: Optional county name to organize screenshots
            tms: Optional TMS number to organize screenshots
            
        Returns:
            str or None: Path to the screenshot if taken, None otherwise
        """
        from src.utils.screenshot_utils import save_screenshot
        
        # Use the unified screenshot utility
        if county and tms:
            # Save in the proper county/tms folder
            screenshot_dir = os.path.join("data", "screenshots", county, tms)
            os.makedirs(screenshot_dir, exist_ok=True)
            filepath = os.path.join(screenshot_dir, filename)
        else:
            # Fallback to temp folder
            filepath = f"data/temp/{filename}"
            
        return save_screenshot(self.driver, filename, filepath, force)

# LangChain Tools for Charleston County Browser Automation

@tool
def navigate_to_charleston_property_search() -> str:
    """Tool to navigate to Charleston County Real Property Record Search page."""
    browser_manager = CharlestonBrowserManager()
    browser_manager.start_browser()
    success = browser_manager.navigate_to_charleston_workflow()
    return f"Navigation {'successful' if success else 'failed'}"

@tool 
def fill_pin_field_with_tms(tms_number: str) -> str:
    """Tool to fill the PIN field with TMS number on Charleston County site."""
    
    # Try to find and click a submit button
    submit_buttons = self.driver.find_elements(By.XPATH, 
        "//button[@type='submit'] | //input[@type='submit'] | //button[contains(text(), 'Submit')] | //input[contains(@value, 'Submit')]")
    
    if submit_buttons:
        submit_buttons[0].click()
        logger.info("Clicked submit after solving image CAPTCHA")
        print("🖱️ Clicked submit button")
        time.sleep(2)
        
        return True
    else:
        logger.warning("Could not find CAPTCHA input field")
        print("⚠️ Could not find CAPTCHA input field")
        return False
            
    # Check for text challenge/question
    text_captcha_elements = self.driver.find_elements(
        By.XPATH,
        "//label[contains(text(), 'captcha') or contains(text(), 'challenge') or contains(text(), 'verification')]"
    )
            
    if text_captcha_elements:
                print("🤖 Text-based CAPTCHA/challenge detected!")