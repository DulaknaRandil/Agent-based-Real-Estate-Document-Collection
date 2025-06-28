"""
Browser automation manager for Berkeley County property search with LangChain/LangSmith tracing
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
from src.config import BROWSER_HEADLESS, USER_AGENT, TIMEOUT_SECONDS, DOWNLOAD_PATH

logger = logging.getLogger(__name__)

class BerkeleyBrowserManager:
    """Manages browser automation for Berkeley County property search with LangSmith tracing"""
    
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
            self.driver = uc.Chrome(options=options, version_main=137)
            
            # Create WebDriverWait instance
            self.wait = WebDriverWait(self.driver, TIMEOUT_SECONDS)
            
            # Execute stealth script
            self.driver.execute_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
            """)
            
            logger.info("Undetected Chrome browser started successfully")
            print("🔒 Undetected Chrome browser started!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            print(f"❌ Browser start failed: {e}")
            return False
    
    @traceable(name="navigate_to_berkeley_property_search")
    def navigate_to_berkeley_property_search(self):
        """Navigate to Berkeley County Property Search"""
        try:
            logger.info("Navigating to Berkeley County Property Search")
            print("🌐 Opening Berkeley County Property Search...")
            
            # Navigate to the Berkeley County Property Search
            self.driver.get("https://berkeleycountysc.gov/Property-Search/")
            
            # Wait for page to load
            time.sleep(5)
            
            logger.info("Successfully navigated to Berkeley County Property Search")
            print("✅ Berkeley County Property Search page loaded!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate to Berkeley County property search: {e}")
            print(f"❌ Navigation failed: {e}")
            return False
    
    @traceable(name="search_property_by_tms")
    def search_property_by_tms(self, tms_number: str):
        """Search for property by TMS number in Berkeley County"""
        try:
            logger.info(f"Searching for property with TMS: {tms_number}")
            print(f"🔍 Searching for property with TMS: {tms_number}")
            
            # Find the TMS input field and button
            input_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "tms"))
            )
            
            # Clear existing content and fill with TMS number
            input_field.clear()
            input_field.send_keys(tms_number)
            
            # Find and click the submit button
            submit_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'retrieve property card')]"))
            )
            submit_button.click()
            
            # Wait for results page to load
            time.sleep(5)
            
            logger.info("Property search completed")
            print("✅ Property search completed!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to search property by TMS: {e}")
            print(f"❌ Property search failed: {e}")
            return False
    
    @traceable(name="save_property_card")
    def save_property_card(self, tms_number: str):
        """Save property card as PDF"""
        try:
            logger.info(f"Saving property card for TMS: {tms_number}")
            print(f"📄 Saving property card for TMS: {tms_number}")
            
            # Get the property card content
            property_card = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'property-card')]"))
            )
            
            # Create berkeley downloads directory if it doesn't exist
            downloads_dir = Path(DOWNLOAD_PATH) / "berkeley" / tms_number
            downloads_dir.mkdir(parents=True, exist_ok=True)
            
            # Save as PDF using Chrome's PDF printing
            pdf_path = downloads_dir / f"Property_Card_{tms_number}.pdf"
            
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
            with open(pdf_path, 'wb') as f:
                f.write(base64.b64decode(pdf_result['data']))
            
            logger.info(f"Property card saved to: {pdf_path}")
            print(f"✅ Property card saved to: {pdf_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save property card: {e}")
            print(f"❌ Failed to save property card: {e}")
            
            # Fallback to screenshot
            try:
                from src.utils.screenshot_utils import save_screenshot
                
                downloads_dir = Path(DOWNLOAD_PATH) / "berkeley" / tms_number
                downloads_dir.mkdir(parents=True, exist_ok=True)
                screenshot_path = downloads_dir / f"Property_Card_{tms_number}_screenshot.png"
                save_screenshot(self.driver, f"Property_Card_{tms_number}_screenshot.png", str(screenshot_path), force=True)
                logger.info(f"Saved screenshot instead: {screenshot_path}")
                print(f"📸 Saved screenshot instead: {screenshot_path}")
                return True
            except Exception as fallback_error:
                logger.error(f"Even screenshot fallback failed: {fallback_error}")
                return False
    
    @traceable(name="extract_deed_references")
    def extract_deed_references(self):
        """Extract deed book and page references from property card"""
        try:
            logger.info("Extracting deed references")
            print("📚 Extracting deed book and page references...")
            
            # Look for previous owner history table
            owner_history = self.driver.find_elements(By.XPATH, "//table[contains(.//th, 'Previous Owner History')]//tr")
            
            deed_references = []
            
            # Skip header row
            for row in owner_history[1:]:
                try:
                    columns = row.find_elements(By.TAG_NAME, "td")
                    if len(columns) >= 4:  # Make sure there are enough columns
                        book_page = columns[3].text.strip()
                        year = columns[2].text.strip()
                        
                        if book_page:
                            # Parse book and page
                            if "/" in book_page:
                                book, page = book_page.split("/", 1)
                            else:
                                # Try to split by space or other common separators
                                import re
                                match = re.search(r'([A-Z0-9]+)[- ]?([0-9]+)', book_page)
                                if match:
                                    book, page = match.groups()
                                else:
                                    logger.warning(f"Could not parse book/page format: {book_page}")
                                    continue
                            
                            deed_references.append({
                                "book": book.strip(),
                                "page": page.strip(),
                                "year": year
                            })
                except Exception as row_error:
                    logger.warning(f"Error parsing row: {row_error}")
                    continue
            
            logger.info(f"Found {len(deed_references)} deed references")
            print(f"✅ Found {len(deed_references)} deed references")
            return deed_references
            
        except Exception as e:
            logger.error(f"Failed to extract deed references: {e}")
            print(f"❌ Failed to extract deed references: {e}")
            return []
    
    @traceable(name="navigate_to_berkeley_tax_search")
    def navigate_to_berkeley_tax_search(self):
        """Navigate to Berkeley County Tax Search"""
        try:
            logger.info("Navigating to Berkeley County Tax Search")
            print("🌐 Opening Berkeley County Tax Search...")
            
            # Navigate to the Berkeley County Tax Search
            self.driver.get("https://berkeleycountysc.gov/Tax-Information/")
            
            # Wait for page to load
            time.sleep(5)
            
            logger.info("Successfully navigated to Berkeley County Tax Search")
            print("✅ Berkeley County Tax Search page loaded!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate to Berkeley County tax search: {e}")
            print(f"❌ Navigation failed: {e}")
            return False
    
    @traceable(name="search_tax_by_tms")
    def search_tax_by_tms(self, tms_number: str):
        """Search for tax information by TMS number"""
        try:
            logger.info(f"Searching for tax info with TMS: {tms_number}")
            print(f"🔍 Searching for tax info with TMS: {tms_number}")
            
            # Find the TMS input field and search button
            input_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "search-input"))
            )
            
            # Clear existing content and fill with TMS number
            input_field.clear()
            input_field.send_keys(tms_number)
            
            # Find and click the search button
            search_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Search')]"))
            )
            search_button.click()
            
            # Wait for results to load
            time.sleep(3)
            
            # Click on the view button
            view_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'View')]"))
            )
            view_button.click()
            
            # Wait for details page to load
            time.sleep(5)
            
            logger.info("Tax search completed")
            print("✅ Tax search completed!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to search tax by TMS: {e}")
            print(f"❌ Tax search failed: {e}")
            return False
    
    @traceable(name="save_tax_bill")
    def save_tax_bill(self, tms_number: str):
        """Save tax bill as PDF"""
        try:
            logger.info(f"Saving tax bill for TMS: {tms_number}")
            print(f"📄 Saving tax bill for TMS: {tms_number}")
            
            # Click on View & Print Bill tab
            bill_tab = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'View & Print Bill')]"))
            )
            bill_tab.click()
            
            # Wait for bill to load
            time.sleep(3)
            
            # Create berkeley downloads directory if it doesn't exist
            downloads_dir = Path(DOWNLOAD_PATH) / "berkeley" / tms_number
            downloads_dir.mkdir(parents=True, exist_ok=True)
            
            # Save as PDF using Chrome's PDF printing
            pdf_path = downloads_dir / f"Tax_Bill_{tms_number}.pdf"
            
            # Use Chrome DevTools to generate PDF
            pdf_result = self.driver.execute_cdp_cmd('Page.printToPDF', {
                'landscape': False,
                'displayHeaderFooter': False,
                'printBackground': True
            })
            
            # Decode and save PDF
            with open(pdf_path, 'wb') as f:
                f.write(base64.b64decode(pdf_result['data']))
            
            logger.info(f"Tax bill saved to: {pdf_path}")
            print(f"✅ Tax bill saved to: {pdf_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save tax bill: {e}")
            print(f"❌ Failed to save tax bill: {e}")
            return self._save_screen_as_fallback(tms_number, "Tax_Bill")
    
    @traceable(name="save_tax_receipt")
    def save_tax_receipt(self, tms_number: str):
        """Save tax receipt as PDF if available"""
        try:
            logger.info(f"Saving tax receipt for TMS: {tms_number}")
            print(f"📄 Saving tax receipt for TMS: {tms_number}")
            
            # Try to find and click View & Print Receipt tab
            receipt_tabs = self.driver.find_elements(By.XPATH, "//a[contains(text(), 'View & Print Receipt')]")
            
            if not receipt_tabs:
                logger.info("No tax receipt tab available")
                print("ℹ️ No tax receipt available for this property")
                return False
            
            # Click on the tab
            receipt_tabs[0].click()
            
            # Wait for receipt to load
            time.sleep(3)
            
            # Create berkeley downloads directory if it doesn't exist
            downloads_dir = Path(DOWNLOAD_PATH) / "berkeley" / tms_number
            downloads_dir.mkdir(parents=True, exist_ok=True)
            
            # Save as PDF
            pdf_path = downloads_dir / f"Tax_Receipt_{tms_number}.pdf"
            
            # Use Chrome DevTools to generate PDF
            pdf_result = self.driver.execute_cdp_cmd('Page.printToPDF', {
                'landscape': False,
                'displayHeaderFooter': False,
                'printBackground': True
            })
            
            # Decode and save PDF
            with open(pdf_path, 'wb') as f:
                f.write(base64.b64decode(pdf_result['data']))
            
            logger.info(f"Tax receipt saved to: {pdf_path}")
            print(f"✅ Tax receipt saved to: {pdf_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save tax receipt: {e}")
            print(f"❌ Failed to save tax receipt: {e}")
            return self._save_screen_as_fallback(tms_number, "Tax_Receipt")
    
    @traceable(name="navigate_to_berkeley_deeds")
    def navigate_to_berkeley_deeds(self):
        """Navigate to Berkeley County register of deeds website"""
        try:
            logger.info("Navigating to Berkeley County register of deeds")
            print("🌐 Opening Berkeley County register of deeds...")
            
            # Navigate to the Berkeley County register of deeds
            self.driver.get("https://search.berkeleydeeds.com/NameSearch.php?Accept=Accept")
            
            # Wait for page to load
            time.sleep(5)
            
            logger.info("Successfully navigated to Berkeley County register of deeds")
            print("✅ Berkeley County register of deeds page loaded!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate to Berkeley County deeds: {e}")
            print(f"❌ Navigation failed: {e}")
            return False
    
    @traceable(name="search_deed_by_book_page")
    def search_deed_by_book_page(self, book: str, page: str, year_filed: str = None):
        """Search for deed by book and page number"""
        try:
            logger.info(f"Searching for deed: Book {book}, Page {page}")
            print(f"🔍 Searching for deed: Book {book}, Page {page}")
            
            # Determine book type based on filing date
            # For deeds filed BEFORE 9/14/2015, use OLD REAL PROPERTY
            # Otherwise use RECORD BOOK (default)
            book_type = "OLD REAL PROPERTY" if self._is_before_sept_2015(year_filed) else "RECORD BOOK"
            
            # Select book type from dropdown
            book_type_select = self.wait.until(
                EC.presence_of_element_located((By.NAME, "book[bookcode]"))
            )
            
            # Use Select class to select by visible text
            from selenium.webdriver.support.select import Select
            select = Select(book_type_select)
            select.select_by_visible_text(book_type)
            
            # Format the page number - ensure 3 digits
            formatted_page = page.strip()
            if formatted_page.isdigit():
                formatted_page = formatted_page.zfill(3)
            
            # Enter book number
            book_field = self.wait.until(
                EC.presence_of_element_located((By.NAME, "book[booknum]"))
            )
            book_field.clear()
            book_field.send_keys(book.strip())
            
            # Enter page number
            page_field = self.wait.until(
                EC.presence_of_element_located((By.NAME, "book[pagenum]"))
            )
            page_field.clear()
            page_field.send_keys(formatted_page)
            
            # Click search button
            search_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='submit' and @value='Search']"))
            )
            search_button.click()
            
            # Wait for results
            time.sleep(5)
            
            logger.info("Deed search completed")
            print("✅ Deed search completed!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to search deed {book} {page}: {e}")
            print(f"❌ Deed search failed: {e}")
            return False
    
    @traceable(name="download_deed_pdf")
    def download_deed_pdf(self, book: str, page: str, tms_number: str):
        """Download deed PDF"""
        try:
            logger.info(f"Downloading deed: Book {book}, Page {page}")
            print(f"📥 Downloading deed: Book {book}, Page {page}")
            
            # Find the hyperlink to the PDF
            pdf_link = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'ViewDocument')]"))
            )
            
            # Get original window handle before clicking
            original_window = self.driver.current_window_handle
            
            # Click the link (may open in new window)
            pdf_link.click()
            time.sleep(5)
            
            # Switch to new window if opened
            all_windows = self.driver.window_handles
            for window in all_windows:
                if window != original_window:
                    self.driver.switch_to.window(window)
                    break
            
            # Create berkeley downloads directory if it doesn't exist
            downloads_dir = Path(DOWNLOAD_PATH) / "berkeley" / tms_number
            downloads_dir.mkdir(parents=True, exist_ok=True)
            
            # Save as PDF
            pdf_path = downloads_dir / f"DB_{book}_{page}.pdf"
            
            # Check if we're looking at a PDF in browser
            if "pdf" in self.driver.current_url.lower() or "document" in self.driver.current_url.lower():
                # Try to use Chrome's PDF saving
                try:
                    pdf_content = self.driver.execute_cdp_cmd('Page.printToPDF', {
                        'landscape': False,
                        'displayHeaderFooter': False,
                        'printBackground': True
                    })
                    
                    with open(pdf_path, 'wb') as f:
                        f.write(base64.b64decode(pdf_content['data']))
                    
                    logger.info(f"Deed saved to: {pdf_path}")
                    print(f"✅ Deed saved to: {pdf_path}")
                    
                    # Close new window and switch back
                    if len(all_windows) > 1:
                        self.driver.close()
                        self.driver.switch_to.window(original_window)
                    
                    return True
                except Exception as pdf_error:
                    logger.error(f"Error saving PDF directly: {pdf_error}")
                    
                    # Try to download via requests
                    try:
                        import requests
                        pdf_url = self.driver.current_url
                        response = requests.get(pdf_url)
                        
                        with open(pdf_path, 'wb') as f:
                            f.write(response.content)
                        
                        logger.info(f"Deed saved via requests to: {pdf_path}")
                        print(f"✅ Deed saved via direct download: {pdf_path}")
                        
                        # Close new window and switch back
                        if len(all_windows) > 1:
                            self.driver.close()
                            self.driver.switch_to.window(original_window)
                        
                        return True
                    except Exception as req_error:
                        logger.error(f"Error downloading PDF via requests: {req_error}")
            
            # Take screenshot as fallback
            from src.utils.screenshot_utils import save_screenshot
            save_screenshot(self.driver, os.path.basename(str(pdf_path).replace(".pdf", ".png")), 
                           str(pdf_path).replace(".pdf", ".png"), force=True)
            logger.info(f"Saved deed as screenshot: {pdf_path}")
            print(f"📸 Saved deed as screenshot")
            
            # Close new window and switch back
            if len(all_windows) > 1:
                self.driver.close()
                self.driver.switch_to.window(original_window)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to download deed: {e}")
            print(f"❌ Failed to download deed: {e}")
            return False
    
    def _is_before_sept_2015(self, year_filed: str = None):
        """Determine if the deed was filed before September 14, 2015"""
        if not year_filed:
            return False
            
        try:
            # Parse year_filed - could be just year or full date
            import re
            import datetime
            
            # Try to extract year
            year_match = re.search(r'(\d{4})', year_filed)
            if year_match:
                year = int(year_match.group(1))
                if year < 2015:
                    return True
                elif year > 2015:
                    return False
                else:
                    # If it's 2015, we need to check month and day
                    # Try to extract month and day if present
                    date_match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', year_filed)
                    if date_match:
                        month, day, year = map(int, date_match.groups())
                        date = datetime.date(year, month, day)
                        cutoff = datetime.date(2015, 9, 14)
                        return date < cutoff
            
            return False
        except Exception:
            # Default to newer format if we can't determine
            return False
    
    def _save_screen_as_fallback(self, tms_number: str, prefix: str):
        """Helper method to save screenshot as fallback"""
        try:
            downloads_dir = Path(DOWNLOAD_PATH) / "berkeley" / tms_number
            downloads_dir.mkdir(parents=True, exist_ok=True)
            screenshot_path = downloads_dir / f"{prefix}_{tms_number}_screenshot.png"
            from src.utils.screenshot_utils import save_screenshot
            save_screenshot(self.driver, os.path.basename(str(screenshot_path)), str(screenshot_path), force=True)
            logger.info(f"Saved screenshot as fallback: {screenshot_path}")
            print(f"📸 Saved screenshot: {screenshot_path}")
            return True
        except Exception as fallback_error:
            logger.error(f"Screenshot fallback failed: {fallback_error}")
            return False
    
    def check_for_captcha(self):
        """Check for and solve any captcha on the current page"""
        try:
            from src.services.captcha_service import CaptchaSolver
            
            if self.driver and self.driver.page_source:
                if ('captcha' in self.driver.page_source.lower() or 
                    'recaptcha' in self.driver.page_source.lower() or
                    'hcaptcha' in self.driver.page_source.lower()):
                    
                    logger.info("Captcha detected, attempting to solve")
                    print("🔒 CAPTCHA detected, attempting to solve...")
                    
                    captcha_solver = CaptchaSolver()
                    
                    # Handle reCAPTCHA v2
                    recaptcha_elements = self.driver.find_elements(By.CSS_SELECTOR, '.g-recaptcha')
                    if recaptcha_elements:
                        print("🤖 reCAPTCHA v2 detected!")
                        
                        # Get sitekey
                        site_key = recaptcha_elements[0].get_attribute('data-sitekey')
                        if not site_key:
                            return False
                        
                        # Get page URL
                        page_url = self.driver.current_url
                        
                        # Solve captcha synchronously
                        import asyncio
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        captcha_solution = loop.run_until_complete(
                            captcha_solver.solve_recaptcha_v2(site_key, page_url)
                        )
                        loop.close()
                        
                        if captcha_solution:
                            # Insert the solved captcha
                            self.driver.execute_script(
                                f'document.getElementById("g-recaptcha-response").innerHTML="{captcha_solution}";'
                            )
                            print("✅ CAPTCHA solved and applied!")
                            return True
                    
                    # If we get here, no supported captcha found or solving failed
                    return False
            
            return False
        except Exception as e:
            logger.error(f"Error in captcha detection/solving: {e}")
            return False
    
    def close_browser(self):
        """Close the browser"""
        try:
            if self.driver:
                self.driver.quit()
                logger.info("Browser closed successfully")
                return True
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
            return False
