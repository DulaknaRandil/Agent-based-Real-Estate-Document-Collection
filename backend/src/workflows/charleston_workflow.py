"""
Charleston County TMS search workflow using LLM-powered LangGraph agent
"""
import asyncio
import logging
import os
from src.agents.charleston.charleston_langgraph_agent import CharlestonWorkflowAgent
from src.config import DEFAULT_TMS
from src.utils.logger import setup_logger
from src.utils.screenshot_utils import get_screenshot_url

logger = logging.getLogger(__name__)

class CharlestonWorkflow:
    """Main workflow for Charleston County TMS property search using LangGraph agent"""
    
    def __init__(self):
        self.agent = CharlestonWorkflowAgent()
        
    async def search_property_by_tms(self, tms_number: str = None):
        """
        Complete LLM-powered workflow to search for a property by TMS number using LangGraph
        
        Args:
            tms_number (str): The TMS number to search for
        """
        if not tms_number:
            tms_number = DEFAULT_TMS
            
        logger.info(f"Starting LLM-powered Charleston County search for TMS: {tms_number}")
        
        try:
            # Execute the LangGraph workflow with LLM guidance and LangSmith tracing
            result = await self.agent.execute_workflow(tms_number)
            
            # Process error screenshots if any
            error_screenshots = []
            if hasattr(result, 'get') and result.get("error_screenshots"):
                for screenshot in result.get("error_screenshots"):
                    # Create screenshot URL
                    screenshot_url = get_screenshot_url(
                        county="charleston",
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
                    "llm_traces": "Check LangSmith dashboard for detailed traces"
                }
            
        except Exception as e:
            logger.error(f"LangGraph workflow execution error: {e}")
            return {
                "success": False,
                "tms_number": tms_number,
                "status": "workflow_error",
                "errors": [str(e)],
                "llm_traces": "Check LangSmith dashboard for error traces"
            }
            
        finally:
            # Clean up the agent
            await self.agent.cleanup()
    
    async def run(self, tms: str = None, include_property_card: bool = True, include_tax_info: bool = True, include_deeds: bool = True, progress_callback=None):
        """Run the complete LangGraph-powered Charleston County workflow
        
        Args:
            tms (str): TMS number to search for
            include_property_card (bool): Whether to include property card 
            include_tax_info (bool): Whether to include tax info
            include_deeds (bool): Whether to include deeds
            progress_callback (callable): Callback for progress updates
        """
        # Update progress if callback provided
        if progress_callback:
            progress_callback(10, "Starting Charleston workflow")
        
        setup_logger()
        
        # Execute the workflow
        result = await self.search_property_by_tms(tms)
        
        # Update final progress
        if progress_callback:
            if result.get("success"):
                progress_callback(100, "Workflow completed successfully", result.get("documents"))
            else:
                progress_callback(0, f"Workflow failed: {result.get('errors', ['Unknown error'])}", None)
                
        return result
