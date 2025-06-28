"""
Berkeley County AI Agent for document collection
"""
import logging
import os
from langchain_core.tools import tool
from langsmith import traceable
from src.automation.berkeley_browser_manager import BerkeleyBrowserManager

logger = logging.getLogger(__name__)

class BerkeleyAgent:
    """
    Agent for Berkeley County property document collection
    Using LangSmith for tracing and monitoring
    """
    
    def __init__(self):
        """Initialize Berkeley County agent"""
        self.browser_manager = BerkeleyBrowserManager()
        self.documents_collected = []
    
    @traceable(run_type="chain")
    def setup(self):
        """Set up the browser for automation"""
        self.browser_manager.start_browser()
        return {"status": "success", "message": "Browser initialized successfully"}
    
    @traceable(run_type="chain")
    def collect_property_card(self, tms: str) -> dict:
        """
        Collect property card for a TMS number
        
        Args:
            tms: TMS number to search for
            
        Returns:
            Dict with status and file path
        """
        try:
            # Create download directory
            download_dir = os.path.join("data", "downloads", "berkeley", tms)
            os.makedirs(download_dir, exist_ok=True)
            
            # Navigate to property card
            property_card_path = self.browser_manager.navigate_to_property_card(tms, download_dir)
            
            if property_card_path:
                self.documents_collected.append({
                    "type": "property_card",
                    "path": property_card_path
                })
                return {"status": "success", "file_path": property_card_path}
            else:
                return {"status": "error", "message": "Failed to collect property card"}
                
        except Exception as e:
            logger.exception(f"Error collecting property card: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    @traceable(run_type="chain")
    def collect_tax_info(self, tms: str) -> dict:
        """
        Collect tax information for a TMS number
        
        Args:
            tms: TMS number to search for
            
        Returns:
            Dict with status and file paths
        """
        try:
            # Create download directory
            download_dir = os.path.join("data", "downloads", "berkeley", tms)
            os.makedirs(download_dir, exist_ok=True)
            
            # Navigate to tax bill
            tax_bill_path = self.browser_manager.navigate_to_tax_bill(tms, download_dir)
            
            # Navigate to tax receipt if available
            tax_receipt_path = self.browser_manager.navigate_to_tax_receipt(tms, download_dir)
            
            documents = []
            
            if tax_bill_path:
                self.documents_collected.append({
                    "type": "tax_bill",
                    "path": tax_bill_path
                })
                documents.append({"type": "tax_bill", "path": tax_bill_path})
            
            if tax_receipt_path:
                self.documents_collected.append({
                    "type": "tax_receipt",
                    "path": tax_receipt_path
                })
                documents.append({"type": "tax_receipt", "path": tax_receipt_path})
            
            if documents:
                return {"status": "success", "documents": documents}
            else:
                return {"status": "error", "message": "Failed to collect tax information"}
                
        except Exception as e:
            logger.exception(f"Error collecting tax information: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    @traceable(run_type="chain")
    def collect_deeds(self, tms: str) -> dict:
        """
        Collect deed documents for a TMS number
        
        Args:
            tms: TMS number to search for
            
        Returns:
            Dict with status and file paths
        """
        try:
            # Create download directory
            download_dir = os.path.join("data", "downloads", "berkeley", tms)
            os.makedirs(download_dir, exist_ok=True)
            
            # Extract deed references from property card
            deed_references = self.browser_manager.extract_deed_references(tms)
            
            if not deed_references:
                return {"status": "error", "message": "No deed references found"}
            
            # Navigate to each deed and download
            documents = []
            
            for book_type, book, page, year in deed_references:
                deed_path = self.browser_manager.navigate_to_deed(
                    book_type, book, page, year, download_dir
                )
                
                if deed_path:
                    deed_doc = {
                        "type": "deed",
                        "book": book,
                        "page": page,
                        "path": deed_path
                    }
                    self.documents_collected.append(deed_doc)
                    documents.append(deed_doc)
            
            if documents:
                return {"status": "success", "documents": documents}
            else:
                return {"status": "error", "message": "Failed to collect deed documents"}
                
        except Exception as e:
            logger.exception(f"Error collecting deed documents: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    @traceable(run_type="chain")
    def cleanup(self) -> dict:
        """Close browser and clean up resources"""
        try:
            self.browser_manager.close_browser()
            return {"status": "success", "message": "Browser closed successfully"}
        except Exception as e:
            logger.exception(f"Error closing browser: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    @tool
    def collect_berkeley_documents(self, tms: str) -> dict:
        """
        Collect all documents for a Berkeley County TMS number
        
        Args:
            tms: TMS number to search for
            
        Returns:
            Dict with status and collected documents
        """
        try:
            # Reset documents collected
            self.documents_collected = []
            
            # Set up browser
            setup_result = self.setup()
            if setup_result["status"] != "success":
                return {"status": "error", "message": setup_result["message"]}
            
            # Collect property card
            property_result = self.collect_property_card(tms)
            if property_result["status"] != "success":
                self.cleanup()
                return {"status": "error", "message": property_result["message"]}
            
            # Collect tax information
            tax_result = self.collect_tax_info(tms)
            if tax_result["status"] != "success":
                logger.warning(f"Tax information collection failed: {tax_result['message']}")
                # Continue with deeds even if tax info fails
            
            # Collect deed documents
            deeds_result = self.collect_deeds(tms)
            if deeds_result["status"] != "success":
                logger.warning(f"Deed collection failed: {deeds_result['message']}")
                # Continue with cleanup
            
            # Clean up
            self.cleanup()
            
            return {
                "status": "success", 
                "tms": tms,
                "documents": self.documents_collected
            }
            
        except Exception as e:
            logger.exception(f"Error collecting Berkeley County documents: {str(e)}")
            try:
                self.cleanup()
            except:
                pass
            return {"status": "error", "message": str(e)}
