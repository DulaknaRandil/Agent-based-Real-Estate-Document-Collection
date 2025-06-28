"""
Berkeley County workflow for document collection
"""
import logging
import os
import asyncio
from typing import Callable, Optional, List, Dict, Any
from src.automation.berkeley_browser_manager import BerkeleyBrowserManager

logger = logging.getLogger(__name__)

class BerkeleyWorkflow:
    """Manages the Berkeley County document collection workflow"""
    
    def __init__(self):
        self.browser_manager = None
        self.documents = []
    
    async def run(
        self,
        tms: str,
        include_property_card: bool = True,
        include_tax_info: bool = True,
        include_deeds: bool = True,
        progress_callback: Optional[Callable[[int, str, Optional[List[Dict[str, str]]]], None]] = None
    ):
        """
        Run the Berkeley County document collection workflow
        
        Args:
            tms: The TMS number to search for
            include_property_card: Whether to include property card
            include_tax_info: Whether to include tax information
            include_deeds: Whether to include deeds
            progress_callback: Callback for progress updates
        """
        try:
            # Initialize browser manager
            self.browser_manager = BerkeleyBrowserManager()
            await self._update_progress(10, "Initializing browser", progress_callback)
            
            # Start browser session
            self.browser_manager.start_browser()
            await self._update_progress(20, "Browser started", progress_callback)
            
            # Create download directory
            download_dir = f"data/downloads/berkeley/{tms}"
            os.makedirs(download_dir, exist_ok=True)
            
            # Collect property card if requested
            if include_property_card:
                await self._update_progress(30, "Collecting property card", progress_callback)
                property_card_path = await self._collect_property_card(tms, download_dir)
                if property_card_path:
                    self.documents.append({
                        "type": "property_card",
                        "filename": os.path.basename(property_card_path),
                        "path": property_card_path
                    })
            
            # Collect tax information if requested
            if include_tax_info:
                await self._update_progress(50, "Collecting tax information", progress_callback)
                tax_docs = await self._collect_tax_info(tms, download_dir)
                self.documents.extend(tax_docs)
            
            # Collect deeds if requested
            if include_deeds:
                await self._update_progress(70, "Collecting deed documents", progress_callback)
                deed_docs = await self._collect_deeds(tms, download_dir)
                self.documents.extend(deed_docs)
            
            # Close browser
            await self._update_progress(95, "Closing browser", progress_callback)
            self.browser_manager.close_browser()
            
            # Complete workflow
            await self._update_progress(
                100, 
                "Berkeley County workflow completed", 
                progress_callback,
                self.documents
            )
            
            return self.documents
            
        except Exception as e:
            logger.exception(f"Error in Berkeley workflow: {str(e)}")
            if self.browser_manager:
                self.browser_manager.close_browser()
            raise
    
    async def _collect_property_card(self, tms, download_dir):
        """Collect property card for a TMS number"""
        try:
            property_card_path = self.browser_manager.navigate_to_property_card(tms, download_dir)
            return property_card_path
        except Exception as e:
            logger.exception(f"Error collecting property card: {str(e)}")
            return None
    
    async def _collect_tax_info(self, tms, download_dir):
        """Collect tax information for a TMS number"""
        try:
            tax_docs = []
            
            # Get tax bill
            tax_bill_path = self.browser_manager.navigate_to_tax_bill(tms, download_dir)
            if tax_bill_path:
                tax_docs.append({
                    "type": "tax_bill",
                    "filename": os.path.basename(tax_bill_path),
                    "path": tax_bill_path
                })
            
            # Get tax receipt if available
            tax_receipt_path = self.browser_manager.navigate_to_tax_receipt(tms, download_dir)
            if tax_receipt_path:
                tax_docs.append({
                    "type": "tax_receipt",
                    "filename": os.path.basename(tax_receipt_path),
                    "path": tax_receipt_path
                })
            
            return tax_docs
        except Exception as e:
            logger.exception(f"Error collecting tax information: {str(e)}")
            return []
    
    async def _collect_deeds(self, tms, download_dir):
        """Collect deeds for a TMS number"""
        try:
            deed_docs = []
            
            # Get conveyance book and page references from property card
            book_page_refs = self.browser_manager.extract_deed_references(tms)
            
            # Navigate to Register of Deeds and download each deed
            for book_type, book, page, year in book_page_refs:
                deed_path = self.browser_manager.navigate_to_deed(book_type, book, page, year, download_dir)
                if deed_path:
                    deed_docs.append({
                        "type": "deed",
                        "book": book,
                        "page": page,
                        "filename": os.path.basename(deed_path),
                        "path": deed_path
                    })
            
            return deed_docs
        except Exception as e:
            logger.exception(f"Error collecting deeds: {str(e)}")
            return []
    
    async def _update_progress(self, progress, message, callback, documents=None):
        """Update workflow progress via callback"""
        if callback:
            callback(progress, message, documents)
        logger.info(f"Berkeley workflow progress: {progress}% - {message}")
        # Small delay to allow for UI updates
        await asyncio.sleep(0.1)
    
    async def search_property_by_tms(self, tms_number: str = None):
        """
        Complete LLM-powered workflow to search for a property by TMS number using LangGraph
        
        Args:
            tms_number (str): The TMS number to search for
        """
        if not tms_number:
            tms_number = DEFAULT_TMS
            
        logger.info(f"Starting LLM-powered Berkeley County search for TMS: {tms_number}")
        
        try:
            # Execute the LangGraph workflow with LLM guidance and LangSmith tracing
            result = await self.agent.execute_workflow(tms_number)
            
            # Process error screenshots if any
            error_screenshots = []
            if hasattr(result, 'get') and result.get("error_screenshots"):
                for screenshot in result.get("error_screenshots"):
                    # Create screenshot URL
                    from src.utils.screenshot_utils import get_screenshot_url
                    screenshot_url = get_screenshot_url(
                        county="berkeley",
                        tms=tms_number,
                        filename=os.path.basename(screenshot["path"])
                    )
                    error_screenshots.append({
                        "filename": os.path.basename(screenshot["path"]),
                        "url": screenshot_url,
                        "metadata": screenshot.get("metadata")
                    })
            
            if hasattr(result, 'get') and result.get("status") == "completed":
                logger.info(f"✅ LangGraph workflow completed successfully for TMS: {tms_number}")
                return {
                    "success": True,
                    "tms_number": tms_number,
                    "status": result.get("status"),
                    "documents": result.get("downloaded_documents", []),
                    "error_screenshots": error_screenshots,
                    "knowledge_graph_updated": result.get("knowledge_graph_updated", False),
                    "llm_traces": "Available in LangSmith dashboard"
                }
            else:
                logger.error(f"❌ LangGraph workflow failed for TMS: {tms_number}")
                return {
                    "success": False,
                    "tms_number": tms_number,
                    "status": result.get("status", "failed"),
                    "error_screenshots": error_screenshots,
                    "errors": result.get("errors", []),
                }
        except Exception as e:
            logger.exception(f"Error in LLM-powered search for TMS {tms_number}: {str(e)}")
            return {
                "success": False,
                "tms_number": tms_number,
                "status": "error",
                "error_message": str(e)
            }
