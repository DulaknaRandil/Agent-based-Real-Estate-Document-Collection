"""
LangGraph State Management for Charleston County Property Search Workflow with LLM Query Parsing
"""
import logging
import json
from typing import Dict, List, Optional, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langsmith import traceable
from dataclasses import dataclass
import asyncio
from datetime import datetime

from src.services.knowledge_graph_service import CharlestonKnowledgeGraph
from src.services.gemini_service import GeminiService
from src.services.captcha_service import CaptchaSolver
from src.automation.browser_manager import CharlestonBrowserManager

logger = logging.getLogger(__name__)

class WorkflowState(TypedDict):
    """State structure for Charleston County workflow"""
    tms_number: str
    current_step: str
    status: str
    browser_session: Optional[Dict]
    search_results: Optional[Dict]
    downloaded_documents: List[str]
    errors: List[str]
    retry_count: int
    captcha_solved: bool
    knowledge_graph_updated: bool
    next_action: Optional[str]
    metadata: Dict

@dataclass
class CharlestonWorkflowAgent:
    """LangGraph-based agent for Charleston County property search workflow"""
    
    def __init__(self, gemini_service=None, kg_service=None, use_direct_urls=True, optimize_token_usage=False, log_level=None):
        self.kg_service = kg_service if kg_service else CharlestonKnowledgeGraph()
        self.llm_service = gemini_service if gemini_service else GeminiService()
        self.captcha_service = CaptchaSolver()
        self.browser_manager = CharlestonBrowserManager()
        self.workflow = None
        self.memory = MemorySaver()
        self.use_direct_urls = use_direct_urls
        self.optimize_token_usage = optimize_token_usage
        if log_level:
            logger.setLevel(log_level)
        self.setup_workflow()
    
    def _format_tms_for_charleston(self, tms_number: str) -> str:
        """
        Format TMS number for Charleston County requirements
        Removes dashes and spaces as required by Charleston County PIN search
        
        Args:
            tms_number (str): Raw TMS number (may have dashes/spaces)
            
        Returns:
            str: Formatted TMS without dashes or spaces (e.g., "1230000123")
        """
        if not tms_number:
            return ""
        
        # Remove all dashes, spaces, and other non-digit characters
        formatted = ''.join(char for char in str(tms_number) if char.isdigit())
        
        logger.info(f"TMS formatting: '{tms_number}' -> '{formatted}'")
        
        # Validate length (Charleston County TMS typically 10 digits)
        if len(formatted) < 8 or len(formatted) > 12:
            logger.warning(f"TMS length unusual for Charleston County: {len(formatted)} digits")
        
        return formatted
    
    def setup_workflow(self):
        """Setup LangGraph workflow with states and transitions"""
        
        # Create workflow graph
        workflow = StateGraph(WorkflowState)
        
        # Add workflow nodes
        workflow.add_node("initialize", self.initialize_search)
        workflow.add_node("start_browser", self.start_browser)
        workflow.add_node("navigate_to_site", self.navigate_to_site)
        workflow.add_node("handle_captcha", self.handle_captcha)
        workflow.add_node("fill_search_form", self.fill_search_form)
        workflow.add_node("execute_search", self.execute_search)
        workflow.add_node("process_results", self.process_results)
        workflow.add_node("download_documents", self.download_documents)
        workflow.add_node("update_knowledge_graph", self.update_knowledge_graph)
        workflow.add_node("error_recovery", self.error_recovery)
        workflow.add_node("finalize", self.finalize_workflow)
        
        # Define workflow edges and conditions
        workflow.set_entry_point("initialize")
        
        workflow.add_edge("initialize", "start_browser")
        workflow.add_edge("start_browser", "navigate_to_site")
        
        # Conditional edges based on state
        workflow.add_conditional_edges(
            "navigate_to_site",
            self.check_navigation_result,
            {
                "success": "fill_search_form",
                "captcha_required": "handle_captcha",
                "error": "error_recovery"
            }
        )
        
        workflow.add_edge("handle_captcha", "fill_search_form")
        workflow.add_edge("fill_search_form", "execute_search")
        
        workflow.add_conditional_edges(
            "execute_search",
            self.check_search_result,
            {
                "success": "process_results",
                "no_results": "finalize",
                "error": "error_recovery"
            }
        )
        
        workflow.add_edge("process_results", "download_documents")
        workflow.add_edge("download_documents", "update_knowledge_graph")
        workflow.add_edge("update_knowledge_graph", "finalize")
        
        workflow.add_conditional_edges(
            "error_recovery",
            self.check_recovery_result,
            {
                "retry": "start_browser",
                "skip": "finalize",
                "abort": END
            }
        )
        
        workflow.add_edge("finalize", END)
        
        # Compile workflow
        self.workflow = workflow.compile(checkpointer=self.memory)
        logger.info("LangGraph workflow compiled successfully")
    
    @traceable(name="initialize_search")
    async def initialize_search(self, state: WorkflowState) -> WorkflowState:
        """Initialize the search workflow using LLM query parsing and TMS formatting"""
        logger.info(f"Initializing LLM-powered search for TMS: {state['tms_number']}")
        
        # Format TMS number properly (remove dashes and spaces for Charleston County)
        formatted_tms = self._format_tms_for_charleston(state['tms_number'])
        state['tms_number'] = formatted_tms
        
        logger.info(f"TMS formatted for Charleston County: {formatted_tms}")
        
        # Use LLM to parse and validate the TMS query with specific Charleston County instructions
        llm_instructions = f"""
        Parse this Charleston County property search request:
        TMS Number: {formatted_tms}
        
        IMPORTANT FORMATTING RULES:
        - Charleston County requires TMS numbers WITHOUT dashes or spaces
        - Format: 1230000123 (NOT 123-00-00-123)
        - The TMS should be exactly 10 digits when possible
        - Validate the TMS format for Charleston County requirements
        
        Analyze the search intent and confirm the TMS format is correct.
        """
        
        query_analysis = await asyncio.to_thread(
            self.llm_service.parse_property_search_query,
            llm_instructions
        )
        
        logger.info(f"LLM Query Analysis: {query_analysis}")
        
        # Create property node in knowledge graph
        await asyncio.to_thread(
            self.kg_service.create_property_node, 
            formatted_tms, 
            formatted_tms
        )
        
        # Generate search strategy using LLM with Charleston County specific guidance
        strategy_prompt = f"""
        Generate a search strategy for Charleston County property records:
        TMS Number: {formatted_tms}
        
        CHARLESTON COUNTY SPECIFIC REQUIREMENTS:
        1. Use Real Property Record Search system
        2. Navigate to the correct PIN field
        3. Enter TMS without dashes or spaces: {formatted_tms}
        4. Click the correct search button
        5. Wait for results and click "View Details" link
        6. Handle any CAPTCHAs or obstacles
        
        Strategy should be step-by-step and specific to Charleston County workflow.
        """
        
        strategy = await asyncio.to_thread(
            self.llm_service.generate_search_strategy,
            strategy_prompt,
            {"query_analysis": query_analysis, "formatted_tms": formatted_tms}
        )
        
        state.update({
            "current_step": "initialize",
            "status": "initialized",
            "metadata": {
                "search_strategy": strategy,
                "query_analysis": query_analysis,
                "formatted_tms": formatted_tms,
                "llm_guidance": "TMS formatted and strategy generated for Charleston County"
            },
            "retry_count": 0
        })
        
        # Store workflow state
        await asyncio.to_thread(
            self.kg_service.store_workflow_state,
            formatted_tms,
            "initialize",
            "completed",
            {"llm_analysis": query_analysis, "formatted_tms": formatted_tms}
        )
        
        return state
    
    async def start_browser(self, state: WorkflowState) -> WorkflowState:
        """Start browser session using undetected Chrome"""
        logger.info("Starting undetected Chrome browser session")
        
        try:
            # Run synchronous browser start in thread
            success = await asyncio.to_thread(self.browser_manager.start_browser)
            if success:
                state.update({
                    "current_step": "start_browser",
                    "status": "browser_started",
                    "browser_session": {"active": True}
                })
            else:
                state["errors"].append("Failed to start browser")
                state["status"] = "error"
                
        except Exception as e:
            logger.error(f"Browser start error: {e}")
            state["errors"].append(str(e))
            state["status"] = "error"
        
        return state
    
    @traceable(name="navigate_to_site")
    async def navigate_to_site(self, state: WorkflowState) -> WorkflowState:
        """Navigate through Charleston County workflow using LLM guidance"""
        logger.info("LLM-guided navigation through Charleston County Real Property Search")
        
        try:
            # Run synchronous navigation in thread
            success = await asyncio.to_thread(self.browser_manager.navigate_to_charleston_workflow)
            
            if success:
                # Use LLM to analyze the loaded page with Charleston County specifics
                page_title = await asyncio.to_thread(self.browser_manager.get_page_title)
                
                page_analysis_prompt = f"""
                Analyze Charleston County Real Property Search page:
                Page title: {page_title}
                
                CHARLESTON COUNTY NAVIGATION VERIFICATION:
                - Confirm this is the Charleston County Real Property Record Search page
                - Verify PIN field is visible and accessible
                - Check for any navigation obstacles or redirects
                - Look for CAPTCHA requirements
                - Ensure the search form is ready for TMS input
                
                Provide guidance on the page state and readiness for property search.
                """
                
                page_analysis = await asyncio.to_thread(
                    self.llm_service.analyze_page_content,
                    page_analysis_prompt,
                    "Charleston County search page analysis and readiness verification"
                )
                
                logger.info(f"LLM Page Analysis: {page_analysis}")
                
                state.update({
                    "current_step": "navigate_to_site",
                    "status": "navigation_success",
                    "metadata": {
                        "page_analysis": page_analysis,
                        "page_title": page_title,
                        "llm_guidance": "Navigation successful, Charleston County search page loaded and ready for PIN input"
                    }
                })
                logger.info("Navigation to Charleston County successful")
            else:
                logger.error("❌ Navigation to Charleston County failed")
                state["errors"].append("Charleston County navigation workflow failed")
                state["status"] = "navigation_error"
                
        except Exception as e:
            logger.error(f"LLM-guided navigation error: {e}")
            state["errors"].append(str(e))
            state["status"] = "navigation_error"
        
        return state
    
    async def handle_captcha(self, state: WorkflowState) -> WorkflowState:
        """Handle CAPTCHA if present"""
        logger.info("Handling CAPTCHA")
        
        try:
            page_url = self.browser_manager.page.url
            captcha_result = await self.captcha_service.detect_and_solve_captcha(
                self.browser_manager.page, page_url
            )
            
            if captcha_result and captcha_result != "no_captcha_found":
                # Submit CAPTCHA solution
                await self.browser_manager.page.evaluate(
                    f'document.getElementById("g-recaptcha-response").innerHTML="{captcha_result}";'
                )
                state.update({
                    "current_step": "handle_captcha",
                    "status": "captcha_solved",
                    "captcha_solved": True
                })
            else:
                state.update({
                    "current_step": "handle_captcha",
                    "status": "no_captcha_or_failed"
                })
                
        except Exception as e:
            logger.error(f"CAPTCHA handling error: {e}")
            state["errors"].append(str(e))
            state["status"] = "captcha_error"
        
        return state
    
    @traceable(name="fill_search_form")
    async def fill_search_form(self, state: WorkflowState) -> WorkflowState:
        """Fill the PIN field with formatted TMS number using LLM guidance"""
        formatted_tms = state['tms_number']  # Already formatted in initialize_search
        logger.info(f"LLM-guided PIN field filling with formatted TMS: {formatted_tms}")
        
        try:
            # Use LLM to analyze form requirements with specific Charleston County instructions
            page_title = await asyncio.to_thread(self.browser_manager.get_page_title)
            
            form_analysis_prompt = f"""
            Analyze the Charleston County property search form:
            Page title: {page_title}
            
            CHARLESTON COUNTY PIN FIELD REQUIREMENTS:
            - Look for PIN field (Property Identification Number)
            - TMS must be entered WITHOUT dashes or spaces
            - Target TMS: {formatted_tms} (formatted correctly for Charleston County)
            - Verify the form is ready for TMS input
            - Confirm this is the Real Property Record Search page
            
            Analyze if the form is ready and provide guidance for PIN field interaction.
            """
            
            form_analysis = await asyncio.to_thread(
                self.llm_service.analyze_page_content,
                form_analysis_prompt,
                "Charleston County PIN field analysis and interaction guidance"
            )
            
            logger.info(f"LLM Form Analysis: {form_analysis}")
            
            # Fill PIN field using synchronous browser manager with formatted TMS
            success = await asyncio.to_thread(
                self.browser_manager.find_and_fill_pin_field, 
                formatted_tms  # Use formatted TMS without dashes/spaces
            )
            
            if success:
                state.update({
                    "current_step": "fill_search_form",
                    "status": "form_filled",
                    "metadata": {
                        "form_analysis": form_analysis,
                        "formatted_tms_used": formatted_tms,
                        "llm_guidance": f"PIN field successfully filled with formatted TMS: {formatted_tms}"
                    }
                })
                logger.info(f"PIN field filled successfully with formatted TMS: {formatted_tms}")
            else:
                state["errors"].append(f"PIN field filling failed for formatted TMS: {formatted_tms}")
                state["status"] = "form_fill_error"
                logger.error(f"❌ PIN field filling failed for formatted TMS: {formatted_tms}")
                
        except Exception as e:
            logger.error(f"LLM-guided form filling error: {e}")
            state["errors"].append(str(e))
            state["status"] = "form_fill_error"
        
        return state
    
    @traceable(name="execute_search")
    async def execute_search(self, state: WorkflowState) -> WorkflowState:
        """Execute the search and click View Details using LLM guidance with multi-level fallback"""
        formatted_tms = state['tms_number']
        logger.info(f"LLM-guided Charleston County search execution for TMS: {formatted_tms}")
        
        try:
            # Get page title for context
            page_title = await asyncio.to_thread(self.browser_manager.get_page_title)
            
            # Context for the search execution phase
            context = {
                "page_title": page_title,
                "tms_number": formatted_tms,
                "current_step": "execute_search",
                "previous_step": state.get("current_step")
            }
            
            # Get instructions from LLM service directly
            search_prompt = f"""
            Charleston County property search instructions:
            Page title: {page_title}
            TMS: {formatted_tms}
            
            CHARLESTON SEARCH EXECUTION:
            1. Locate and click the search button
            2. Wait for the results page to load
            3. If multiple results appear, find the exact match for TMS {formatted_tms}
            4. Click on the matching property
            5. Wait for property details page to load
            
            What is the exact sequence of steps to execute the search correctly?
            """
            
            search_instructions = await asyncio.to_thread(
                self.llm_service.analyze_page_content,
                search_prompt,
                "Charleston County search execution strategy"
            )
            
            if search_instructions:
                logger.info(f"Search instructions: {search_instructions[:100]}..." if len(search_instructions) > 100 else search_instructions)
            
            # Execute search using browser manager
            search_success = await asyncio.to_thread(
                self.browser_manager.click_charleston_search_button
            )
            
            if search_success:
                logger.info("✅ Search button clicked successfully")
                
                # Wait for results
                results_success = await asyncio.to_thread(self.browser_manager.wait_for_charleston_results)
                
                if results_success:
                    logger.info("✅ Search results loaded")
                    
                    # Use LLM to analyze results page with Charleston County specifics
                    page_title = await asyncio.to_thread(self.browser_manager.get_page_title)
                    
                    results_analysis_prompt = f"""
                    Analyze Charleston County search results:
                    Page title: {page_title}
                    TMS searched: {formatted_tms}
                    
                    CHARLESTON COUNTY RESULTS ANALYSIS:
                    - Verify property record found for TMS {formatted_tms}
                    - Locate the "View Details" link for the property
                    - Identify property card or record row
                    - Check for any error messages or no results found
                    - Provide guidance for accessing property details
                    
                    Analyze the search results and guide next action.
                    """
                    
                    results_analysis = await asyncio.to_thread(
                        self.llm_service.analyze_page_content,
                        results_analysis_prompt,
                        "Charleston County search results analysis and View Details guidance"
                    )
                    
                    logger.info(f"LLM Results Analysis: {results_analysis}")
                    
                    # Click "View Details" property card
                    details_success = await asyncio.to_thread(
                        self.browser_manager.click_view_details_property_card, 
                        formatted_tms
                    )
                    
                    if details_success:
                        logger.info("✅ View Details clicked successfully")
                        state.update({
                            "current_step": "execute_search",
                            "status": "search_completed",
                            "metadata": {
                                "instruction_source": "gemini_direct",
                                "results_analysis": results_analysis,
                                "tms_used": formatted_tms,
                                "llm_guidance": f"Search completed and property details accessed for TMS: {formatted_tms}"
                            }
                        })
                    else:
                        logger.warning("❌ View Details click failed")
                        state.update({
                            "current_step": "execute_search",
                            "status": "view_details_failed",
                            "metadata": {
                                "tms_used": formatted_tms,
                                "llm_guidance": "Search succeeded but View Details click failed"
                            }
                        })
                else:
                    logger.warning("❌ No search results found")
                    state.update({
                        "current_step": "execute_search",
                        "status": "no_results",
                        "metadata": {
                            "tms_used": formatted_tms,
                            "llm_guidance": f"Search executed but no results found for TMS: {formatted_tms}"
                        }
                    })
            else:
                logger.error("Search button click failed")
                state["errors"].append(f"Search button click failed for TMS: {formatted_tms}")
                state["status"] = "search_error"
                
        except Exception as e:
            logger.error(f"LLM-guided search execution error: {e}")
            state["errors"].append(str(e))
            state["status"] = "search_error"
        
        return state
    
    async def process_results(self, state: WorkflowState) -> WorkflowState:
        """Process property page, save PDF, extract deed references, and navigate to tax info"""
        formatted_tms = state['tms_number']
        logger.info(f"Processing property page for TMS: {formatted_tms}")
        
        try:
            # Step 1: LLM analysis of property page
            page_title = await asyncio.to_thread(self.browser_manager.get_page_title)
            
            property_analysis_prompt = f"""
            Analyze the Charleston County property details page:
            Page title: {page_title}
            TMS: {formatted_tms}
            
            PROPERTY PAGE ANALYSIS TASKS:
            1. Confirm this is the property details page for TMS {formatted_tms}
            2. Identify the property information section
            3. Locate the transactions section at the bottom of the page
            4. Extract all Book and Page numbers from transaction history
            5. Look for deed references (format: Book XXXX Page XXX)
            6. Note any sales history or transaction data
            7. Verify tax info link is available at bottom of page
            
            Extract all deed book and page references for later deed retrieval.
            Focus on books starting with letters and 280+ (1997-present) for online availability.
            """
            
            property_analysis = await asyncio.to_thread(
                self.llm_service.analyze_page_content,
                property_analysis_prompt,
                "Charleston County property page analysis and deed reference extraction"
            )
            
            logger.info(f"LLM Property Analysis: {property_analysis}")
            
            # Step 2: Save property page as PDF labeled "Property Card"
            pdf_success = await asyncio.to_thread(
                self.browser_manager.save_page_as_pdf,
                f"Property Card - TMS {formatted_tms}",
                f"property_card_{formatted_tms}",
                formatted_tms  # Pass TMS for folder organization
            )
            
            if pdf_success:
                state["downloaded_documents"].append(f"Property Card - TMS {formatted_tms}")
                logger.info(f"✅ Property Card PDF saved for TMS: {formatted_tms}")
            
            # Step 3: Extract deed references using LLM - with improved extraction
            try:
                page_html = await asyncio.to_thread(
                    lambda: self.browser_manager.driver.page_source if self.browser_manager.driver else ""
                )
            except Exception as page_error:
                logger.error(f"Error getting page source: {page_error}")
                page_html = ""
            
            # Get the current URL for context
            current_url = await asyncio.to_thread(lambda: self.browser_manager.driver.current_url)
            
            deed_extraction_prompt = f"""
            Extract deed book and page references from this Charleston County property page HTML:
            TMS: {formatted_tms}
            URL: {current_url}
            
            DEED REFERENCE EXTRACTION:
            - Look for transaction history at bottom of page - usually in a table format
            - Find all "Book" and "Page" number combinations in the HTML
            - Format: Book XXXX Page XXX (4 digits + 3 digits)
            - Also look for formats like:
              * Bk XXXX Pg XXX
              * DB XXXX PG XXX
              * Book/Page: XXXX/XXX
              * XXXX-XXX (hyphenated format)
            - Focus on books starting with letters + 280 or higher (1997+)
            - Return as structured list with book and page references
            - Include transaction year if available
            
            HTML CONTENT:
            {page_html[:15000]}  # First 15K characters of HTML
            
            Extract all available deed references for document retrieval.
            Pay special attention to the transaction history section.
            """
            
            deed_references = await asyncio.to_thread(
                self.llm_service.extract_deed_references,
                deed_extraction_prompt
            )
            
            if deed_references:
                logger.info(f"LLM Deed References: {json.dumps(deed_references, indent=2)}")
                print(f"📋 Found {len(deed_references)} deed references for TMS {formatted_tms}")
                for ref in deed_references[:3]:  # Show first few references
                    print(f"  - Book {ref.get('book')}, Page {ref.get('page')}" + 
                          (f", Year {ref.get('year')}" if 'year' in ref else ""))
                if len(deed_references) > 3:
                    print(f"  ... and {len(deed_references) - 3} more")
            else:
                logger.warning(f"No deed references found for TMS {formatted_tms}")
                print(f"⚠️ No deed references found for TMS {formatted_tms}")
            
            # Step 4: Navigate to tax info page
            tax_info_success = await asyncio.to_thread(
                self.browser_manager.navigate_to_tax_info,
                formatted_tms
            )
            
            if tax_info_success:
                # Step 5: Save tax info page as PDF
                tax_pdf_success = await asyncio.to_thread(
                    self.browser_manager.save_page_as_pdf,
                    f"Tax Info - TMS {formatted_tms}",
                    f"tax_info_{formatted_tms}",
                    formatted_tms  # Pass TMS for folder organization
                )
                
                if tax_pdf_success:
                    state["downloaded_documents"].append(f"Tax Info - TMS {formatted_tms}")
                    logger.info(f"✅ Tax Info PDF saved for TMS: {formatted_tms}")
            
            state.update({
                "current_step": "process_results",
                "status": "results_processed",
                "search_results": {
                    "property_analysis": property_analysis,
                    "deed_references": deed_references,
                    "pdfs_saved": state["downloaded_documents"]
                },
                "metadata": {
                    "property_analysis": property_analysis,
                    "deed_references": deed_references,
                    "tms_processed": formatted_tms,
                    "llm_guidance": f"Property page processed, PDFs saved, deed references extracted for TMS: {formatted_tms}"
                }
            })
            
        except Exception as e:
            logger.error(f"Results processing error: {e}")
            state["errors"].append(str(e))
            state["status"] = "processing_error"
        
        return state
    
    async def download_documents(self, state: WorkflowState) -> WorkflowState:
        """Download deed documents from Charleston County Register of Deeds with robust looping and state tracking"""
        formatted_tms = state['tms_number']
        logger.info(f"Downloading deed documents for TMS: {formatted_tms}")
        try:
            # Get deed references from previous step
            deed_references = state.get("search_results", {}).get("deed_references", [])
            if not deed_references:
                logger.warning("No deed references found to download")
                state.update({
                    "current_step": "download_documents",
                    "status": "no_deeds_found"
                })
                return state
            
            # Track already downloaded deeds in state
            already_downloaded = set(state.get("downloaded_documents", []))
            
            # Save deed references to Neo4j for efficient tracking
            try:
                # Store deed references in Neo4j for persistence
                await asyncio.to_thread(
                    self.kg_service.store_deed_references,
                    formatted_tms,
                    deed_references
                )
                logger.info(f"✓ Stored {len(deed_references)} deed references in Neo4j")
            except Exception as e:
                logger.warning(f"Failed to store deed references in Neo4j: {e}")
            
            # Use GeminiService to batch and prioritize deeds efficiently
            # This optimizes the collection order to minimize token usage
            try:
                # Get already downloaded deeds from state
                collected_deeds = [{"book": d.split()[1], "page": d.split()[2]} for d in already_downloaded 
                                 if d.startswith("DB ") and len(d.split()) == 3]
                
                # Use the prioritization logic to get most important deeds first
                prioritized_deeds = self.llm_service.prioritize_deed_collection(
                    deed_references, 
                    collected_deeds,
                    max_priority_count=len(deed_references)  # Process all deeds
                )
                
                # Use the prioritized list for processing
                pending_deeds = prioritized_deeds.get("priority_deeds", [])
                logger.info(f"Prioritized {len(pending_deeds)} deeds for collection")
                
                if not pending_deeds:
                    logger.info("All deeds already downloaded")
                    state.update({
                        "current_step": "download_documents",
                        "status": "all_deeds_downloaded"
                    })
                    return state
            except Exception as e:
                logger.warning(f"Error in deed prioritization, using default order: {e}")
                # Fallback to simple filtering if prioritization fails
                pending_deeds = [d for d in deed_references if f"DB {d.get('book')} {d.get('page')}" not in already_downloaded]
                if not pending_deeds:
                    logger.info("All deeds already downloaded (fallback check)")
                    state.update({
                        "current_step": "download_documents",
                        "status": "all_deeds_downloaded"
                    })
                    return state
            
            # Navigate to Register of Deeds website
            deed_site_success = await asyncio.to_thread(
                self.browser_manager.navigate_to_register_of_deeds
            )
            if not deed_site_success:
                state["errors"].append("Failed to navigate to Register of Deeds")
                state["status"] = "deed_navigation_error"
                return state
            
            # Use the optimized workflow for better efficiency
            workflow = self.llm_service.generate_deed_collection_workflow(
                formatted_tms,
                deed_references,
                collected_deeds
            )
            
            # Save workflow to temp for debugging
            try:
                import json
                from pathlib import Path
                output_dir = Path("data/temp")
                output_dir.mkdir(parents=True, exist_ok=True)
                
                with open(output_dir / "deed_workflow.json", "w") as f:
                    json.dump(workflow, f, indent=2)
                
                logger.info(f"Saved deed collection workflow to data/temp/deed_workflow.json")
            except Exception as e:
                logger.warning(f"Failed to save workflow file: {e}")
            
            # Get deeds to process in efficient order
            deeds_to_process = workflow["collection_sequence"]
            logger.info(f"Found {len(deeds_to_process)} deeds to process in optimized workflow")
            
            # Only process pending deeds
            if not deeds_to_process:
                logger.info("All deeds already downloaded")
                state.update({
                    "current_step": "download_documents",
                    "status": "all_deeds_downloaded"
                })
                return state
            
            # Navigate directly to Register of Deeds book and page search URL
            # This is the most efficient URL that saves tokens and time
            deed_site_success = await asyncio.to_thread(
                self.browser_manager.navigate_to_register_of_deeds
            )
            if not deed_site_success:
                state["errors"].append("Failed to navigate to Register of Deeds")
                state["status"] = "deed_navigation_error"
                return state
            
            # Loop through deeds to process in optimized order
            deeds_processed = 0
            for deed_ref in deeds_to_process:
                try:
                    book = deed_ref.get('book', '')
                    page = deed_ref.get('page', '')
                    if not book or not page:
                        continue
                        
                    deed_filename = f"DB {book} {page}"
                    if deed_filename in already_downloaded:
                        logger.info(f"✓ Deed already downloaded: {deed_filename}")
                        continue
                        
                    logger.info(f"Processing deed: Book {book}, Page {page} ({deeds_processed+1}/{len(deeds_to_process)})")
                    
                    # Search for the deed using the direct book/page search
                    deed_found = await asyncio.to_thread(
                        self.browser_manager.search_deed_by_book_page,
                        book,
                        page.zfill(3)
                    )
                    
                    if deed_found:
                        # Download the deed PDF
                        deed_download_success = await asyncio.to_thread(
                            self.browser_manager.download_deed_pdf,
                            deed_filename,
                            formatted_tms
                        )
                        
                        if deed_download_success:
                            state["downloaded_documents"] = state.get("downloaded_documents", []) + [deed_filename]
                            already_downloaded.add(deed_filename)
                            deeds_processed += 1
                            
                            logger.info(f"✅ Downloaded deed: {deed_filename}")
                            
                            # Create transaction and deed nodes in Neo4j
                            transaction_date = deed_ref.get('year', datetime.now().strftime("%Y"))
                            from src.config import get_tms_folder_path
                            pdf_url = str(get_tms_folder_path(formatted_tms) / f"{deed_filename}.pdf")
                            
                            try:
                                await asyncio.to_thread(
                                    self.kg_service.create_transaction_and_deed,
                                    formatted_tms,
                                    transaction_date,
                                    book,
                                    page,
                                    pdf_url,
                                    deed_filename
                                )
                                logger.info(f"✓ Created Neo4j nodes for deed: {deed_filename}")
                            except Exception as neo4j_error:
                                logger.error(f"Neo4j error for deed {deed_filename}: {neo4j_error}")
                        
                        else:
                            logger.warning(f"⚠️ Failed to download deed: {deed_filename}")
                    
                    # Always navigate back to book/page search for next deed
                    # This ensures we're on the correct page regardless of download success
                    await asyncio.to_thread(
                        self.browser_manager.navigate_to_register_of_deeds
                    )
                    
                except Exception as deed_error:
                    logger.error(f"Error processing deed {book} {page}: {deed_error}")
                    state["errors"].append(f"Deed error {book} {page}: {str(deed_error)}")
                    
                    # Continue with next deed despite errors in one deed
                    try:
                        # Try to get back to deed search page
                        await asyncio.to_thread(
                            self.browser_manager.navigate_to_register_of_deeds
                        )
                    except:
                        pass
                    continue
            
            # Update state with deed collection results
            state.update({
                "current_step": "download_documents",
                "status": "documents_downloaded",
                "metadata": {
                    "downloaded_deeds": list(already_downloaded),
                    "total_deeds_found": len(deed_references),
                    "deeds_processed": deeds_processed,
                    "download_completed": deeds_processed == len(deeds_to_process)
                }
            })
            
            logger.info(f"✅ Completed deed download process: {deeds_processed}/{len(deeds_to_process)} deeds downloaded")
            
        except Exception as e:
            logger.error(f"Deed download error: {e}")
            state["errors"].append(str(e))
            state["status"] = "download_error"
        return state
    
    async def update_knowledge_graph(self, state: WorkflowState) -> WorkflowState:
        """Update knowledge graph with collected data"""
        logger.info("Updating knowledge graph")
        
        try:
            from src.config import CHARLESTON_PROPERTY_CARD_BASE, CHARLESTON_TAX_INFO_BASE
            
            # Create property card node
            property_card_url = f"{CHARLESTON_PROPERTY_CARD_BASE}{state['tms_number']}"
            await asyncio.to_thread(
                self.kg_service.create_property_card_node,
                state['tms_number'],
                property_card_url
            )
            
            # Create tax info node
            tax_info_url = f"{CHARLESTON_TAX_INFO_BASE}{state['tms_number']}"
            await asyncio.to_thread(
                self.kg_service.create_tax_info_node,
                state['tms_number'],
                tax_info_url
            )
            
            state.update({
                "current_step": "update_knowledge_graph",
                "status": "kg_updated",
                "knowledge_graph_updated": True
            })
            
        except Exception as e:
            logger.error(f"Knowledge graph update error: {e}")
            state["errors"].append(str(e))
            state["status"] = "kg_update_error"
        
        return state
    
    async def error_recovery(self, state: WorkflowState) -> WorkflowState:
        """Handle errors and attempt recovery"""
        logger.info("Attempting error recovery")
        
        try:
            # Use LLM to generate recovery plan
            error_context = {
                "errors": state["errors"],
                "current_step": state["current_step"],
                "retry_count": state["retry_count"]
            }
            
            recovery_plan = await asyncio.to_thread(
                self.llm_service.generate_error_recovery_plan,
                error_context
            )
            
            state["retry_count"] += 1
            
            if state["retry_count"] < 3:
                state.update({
                    "current_step": "error_recovery",
                    "status": "retry_planned",
                    "next_action": "retry"
                })
            else:
                state.update({
                    "current_step": "error_recovery",
                    "status": "max_retries_reached",
                    "next_action": "abort"
                })
                
        except Exception as e:
            logger.error(f"Error recovery failed: {e}")
            state["next_action"] = "abort"
        
        return state
    
    @traceable(name="finalize_workflow")
    async def finalize_workflow(self, state: WorkflowState) -> WorkflowState:
        """Finalize workflow and clean up resources"""
        tms_number = state['tms_number']
        
        logger.info(f"🏁 Finalizing workflow for TMS: {tms_number}")
        downloaded_docs = state.get("downloaded_documents", [])
        
        try:
            # Verify all required documents were downloaded
            if not downloaded_docs:
                state["errors"].append("No documents were downloaded")
                state["status"] = "incomplete"
                logger.warning(f"No documents downloaded for TMS: {tms_number}")
            
            # Close browser gracefully
            try:
                if self.browser_manager.driver:
                    await asyncio.to_thread(self.browser_manager.close_browser)
                    logger.info("Browser session closed")
            except Exception as browser_error:
                logger.error(f"Browser close error: {browser_error}")
                state["errors"].append(f"Browser close error: {browser_error}")
            
            # Verify documents were downloaded
            try:
                # Check if PDFs were saved correctly
                from src.config import get_tms_folder_path
                
                tms_folder = get_tms_folder_path(tms_number)
                if tms_folder.exists():
                    pdf_files = list(tms_folder.glob("*.pdf"))
                    logger.info(f"Found {len(pdf_files)} PDF files in {tms_folder}")
                    
                    # Verify property card PDF exists
                    property_card_exists = any("property_card" in f.name.lower() for f in pdf_files)
                    if property_card_exists:
                        logger.info("✅ Property Card PDF verified")
                    else:
                        logger.warning("❌ Property Card PDF not found")
                        if "Property Card" not in downloaded_docs:
                            downloaded_docs.append(f"Property Card - TMS {tms_number} (verification failed)")
                    
                    # Verify tax info PDF exists
                    tax_info_exists = any("tax_info" in f.name.lower() for f in pdf_files)
                    if tax_info_exists:
                        logger.info("✅ Tax Info PDF verified")
                    else:
                        logger.warning("❌ Tax Info PDF not found")
                        if "Tax Info" not in downloaded_docs:
                            downloaded_docs.append(f"Tax Info - TMS {tms_number} (verification failed)")
                    
                    # Verify deed PDFs exist if we had references - with better None handling
                    search_results = state.get("search_results")
                    deed_references = []
                    if search_results and isinstance(search_results, dict):
                        deed_references = search_results.get("deed_references", [])
                    
                    deed_files = [f for f in pdf_files if "db_" in f.name.lower() or "db " in f.name.lower()]
                    
                    if deed_references and not deed_files:
                        logger.warning(f"❌ No deed PDFs found despite {len(deed_references)} references")
                    elif deed_files:
                        logger.info(f"✅ Found {len(deed_files)} deed PDFs")
                else:
                    logger.warning(f"TMS folder not found: {tms_folder}")
            
            except Exception as verify_error:
                logger.error(f"Document verification error: {verify_error}")
                state["errors"].append(f"Document verification error: {verify_error}")
            
            # Store final workflow state in Neo4j
            try:
                # Create a LangSmith trace URL if available
                import os
                langsmith_trace_url = None
                
                if 'LANGCHAIN_TRACING_V2' in os.environ and os.environ.get('LANGCHAIN_TRACING_V2') == 'true':
                    langsmith_project = os.environ.get('LANGCHAIN_PROJECT', 'default')
                    langsmith_endpoint = os.environ.get('LANGCHAIN_ENDPOINT', 'https://api.smith.langchain.com')
                    
                    # Create a trace URL for the LangSmith project
                    # Format: https://smith.langchain.com/projects/{project}/traces
                    langsmith_trace_url = f"https://smith.langchain.com/projects/{langsmith_project}/traces"
                    
                    # Add trace URL to the state for reference
                    state["langsmith_trace_url"] = langsmith_trace_url
                
                await asyncio.to_thread(
                    self.kg_service.store_workflow_state,
                    tms_number,
                    "completed",
                    "success" if not state.get("errors") else "partial_success",
                    {
                        "downloaded_docs": downloaded_docs,
                        "completion_time": datetime.now().isoformat(),
                        "langsmith_url": langsmith_trace_url
                    }
                )
                logger.info(f"Final workflow state stored in Neo4j for TMS: {tms_number}")
            except Exception as kg_error:
                logger.warning(f"Neo4j workflow state update warning: {kg_error}")
                state["errors"].append(f"Neo4j update error: {kg_error}")
            
            # Create property nodes in Neo4j
            try:
                await asyncio.to_thread(
                    self.kg_service.create_property_node,
                    tms_number=tms_number,
                    pin=tms_number
                )
                
                # Create property card node
                from src.config import CHARLESTON_PROPERTY_CARD_BASE
                property_card_url = f"{CHARLESTON_PROPERTY_CARD_BASE}{tms_number}"
                await asyncio.to_thread(
                    self.kg_service.create_property_card_node,
                    tms_number,
                    property_card_url,
                    "Property Card"
                )
                
                # Create tax info node
                from src.config import CHARLESTON_TAX_INFO_BASE
                tax_info_url = f"{CHARLESTON_TAX_INFO_BASE}{tms_number}"
                await asyncio.to_thread(
                    self.kg_service.create_tax_info_node,
                    tms_number,
                    tax_info_url,
                    "Tax Info"
                )
                
                logger.info("Knowledge graph updated with property nodes and document links")
            except Exception as kg_error:
                logger.warning(f"Neo4j property node creation warning: {kg_error}")
                state["errors"].append(f"Neo4j property node error: {kg_error}")
            
            # Set final state
            state.update({
                "current_step": "finalize",
                "status": "completed",
                "downloaded_documents": downloaded_docs,
                "success": True
            })
            
            # Include all search results in the final state
            if "search_results" not in state:
                state["search_results"] = {}
                
            # Print success message
            print(f"✅ Workflow completed for TMS: {tms_number}")
            print(f"📄 Downloaded {len(downloaded_docs)} documents")
            
            # Return all errors for debugging
            if state.get("errors"):
                logger.warning(f"Workflow completed with {len(state['errors'])} errors: {state['errors']}")
                print(f"⚠️ Completed with {len(state['errors'])} non-fatal errors")
            
        except Exception as e:
            logger.error(f"Workflow finalization error: {e}")
            state["errors"].append(str(e))
            state["status"] = "finalization_error"
            state["success"] = False
            
            # Make sure browser is closed even on error
            try:
                if self.browser_manager.driver:
                    await asyncio.to_thread(self.browser_manager.close_browser)
            except:
                pass
        
        return state
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            if hasattr(self, 'browser_manager') and self.browser_manager and self.browser_manager.driver:
                await asyncio.to_thread(self.browser_manager.close_browser)
            if hasattr(self, 'kg_service') and self.kg_service:
                self.kg_service.close()
            logger.info("Charleston workflow agent resources cleaned up")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            
    # Aliases for different naming conventions
    cleanup_resources = cleanup
    cleanup_workflow = cleanup
    
    # Condition functions for workflow routing
    def check_navigation_result(self, state: WorkflowState) -> str:
        """Check navigation result to determine next step"""
        if state["status"] == "captcha_required":
            return "captcha_required"
        elif state["status"] == "navigation_success":
            return "success"
        else:
            return "error"
    
    def check_search_result(self, state: WorkflowState) -> str:
        """Check search result to determine next step"""
        if state["status"] == "search_completed":
            return "success"
        elif state["status"] == "no_results":
            return "no_results"
        else:
            return "error"
    
    def check_recovery_result(self, state: WorkflowState) -> str:
        """Check recovery action"""
        return state.get("next_action", "abort")
    
    async def run_workflow(self, tms_number: str) -> Dict:
        """Run the complete Charleston County workflow"""
        logger.info(f"Starting workflow for TMS: {tms_number}")
        
        # Initial state
        initial_state = WorkflowState(
            tms_number=tms_number,
            current_step="start",
            status="initializing",
            browser_session=None,
            search_results=None,
            downloaded_documents=[],
            errors=[],
            retry_count=0,
            captcha_solved=False,
            knowledge_graph_updated=False,
            next_action=None,
            metadata={}
        )
        
        try:
            # Run workflow without complex config for now
            final_state = initial_state
            
            # Execute workflow steps manually for debugging
            final_state = await self.initialize_search(final_state)
            if final_state["status"] != "initialized":
                return final_state
                
            final_state = await self.start_browser(final_state)
            if final_state["status"] != "browser_started":
                return final_state
                
            final_state = await self.navigate_to_site(final_state)
            if final_state["status"] != "navigation_success":
                return final_state
                
            final_state = await self.fill_search_form(final_state)
            if final_state["status"] != "form_filled":
                return final_state
                
            final_state = await self.execute_search(final_state)
            if final_state["status"] != "search_completed":
                return final_state
                
            # Process search results to extract deed references and save property card
            final_state = await self.process_results(final_state)
            if final_state["status"] == "results_processed":
                # Proceed with downloading any deed documents found
                final_state = await self.download_documents(final_state)
            
            # Update the Knowledge Graph with the collected information
            final_state = await self.update_knowledge_graph(final_state)
            
            # Finalize the workflow (including browser cleanup)
            final_state = await self.finalize_workflow(final_state)
            
            logger.info(f"Manual workflow completed for TMS: {tms_number}")
            return final_state
            
        except Exception as e:
            logger.error(f"Workflow failed for TMS {tms_number}: {e}")
            return {
                "status": "workflow_error",
                "error": str(e),
                "tms_number": tms_number
            }
    
    @traceable(name="execute_workflow")
    async def execute_workflow(self, tms_number: str) -> Dict:
        """
        Execute the complete LangGraph workflow with LLM guidance and LangSmith tracing
        
        Args:
            tms_number (str): The TMS number to search for
            
        Returns:
            Dict: Final workflow state with results
        """
        logger.info(f"Starting LangGraph workflow for TMS: {tms_number}")
        
        # Initial state
        initial_state = {
            "tms_number": tms_number,
            "current_step": "start",
            "status": "starting",
            "browser_session": None,
            "search_results": None,
            "downloaded_documents": [],
            "errors": [],
            "retry_count": 0,
            "captcha_solved": False,
            "knowledge_graph_updated": False,
            "next_action": None,
            "metadata": {}
        }
        
        try:
            # Execute the LangGraph workflow with LLM decision points
            config = {"configurable": {"thread_id": f"tms_{tms_number}"}}
            
            logger.info("🧠 LangGraph workflow starting with LLM guidance...")
            print("🤖 Starting AI-powered workflow with LangSmith tracing...")
            
            # Instead of the problematic workflow.invoke, let's run the manual workflow
            # but with proper LangSmith tracing
            final_state = await self.run_manual_workflow_with_tracing(tms_number)
            
            logger.info(f"LangGraph workflow completed for TMS: {tms_number}")
            print(f"✅ AI workflow completed! Check LangSmith dashboard for traces.")
            
            return final_state
            
        except Exception as e:
            logger.error(f"Workflow failed for TMS {tms_number}: {e}")
            print(f"❌ AI workflow failed: {e}")
            return {
                "status": "workflow_error",
                "errors": [str(e)],
                "tms_number": tms_number,
                "current_step": "failed"
            }
    
    @traceable(name="run_manual_workflow_with_tracing")
    async def run_manual_workflow_with_tracing(self, tms_number: str) -> Dict:
        """
        Execute manual workflow steps with LLM guidance and LangSmith tracing
        This method is fully traceable with LangSmith for workflow visualization
        """
        print("🧠 Running LLM-guided workflow with full LangSmith tracing...")
        
        # Generate run ID for tracing
        import platform
        import os
        from datetime import datetime
        
        run_id = f"charleston-{tms_number}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        start_time = datetime.now()
        
        # Setup LangSmith tracing if enabled
        langsmith_trace_url = None
        if 'LANGCHAIN_TRACING_V2' in os.environ and os.environ.get('LANGCHAIN_TRACING_V2') == 'true':
            langsmith_project = os.environ.get('LANGCHAIN_PROJECT', 'charleston-workflow')
            langsmith_trace_url = f"https://smith.langchain.com/projects/{langsmith_project}/traces"
            logger.info(f"LangSmith tracing enabled: {langsmith_trace_url}")
        
        # Initial state with enhanced metadata
        final_state = {
            "tms_number": tms_number,
            "current_step": "start",
            "status": "starting",
            "browser_session": None,
            "search_results": {},
            "downloaded_documents": [],
            "errors": [],
            "retry_count": 0,
            "captcha_solved": False,
            "knowledge_graph_updated": False,
            "next_action": None,
            "metadata": {
                "run_id": run_id,
                "system": platform.system(),
                "start_time": start_time.isoformat(),
                "tms_number": tms_number,
                "workflow": "charleston_county_property_search"
            }
        }
        
        try:
            print("🤖 Step 1: LLM initializing search strategy...")
            final_state = await self.initialize_search(final_state)
            if final_state["status"] != "initialized":
                return self._finalize_traced_workflow(final_state, start_time, langsmith_trace_url, False)
            
            print("🌐 Step 2: Starting browser session...")
            final_state = await self.start_browser(final_state)
            if final_state["status"] != "browser_started":
                return self._finalize_traced_workflow(final_state, start_time, langsmith_trace_url, False)
                
            print("🧭 Step 3: LLM-guided navigation to Charleston County...")
            final_state = await self.navigate_to_site(final_state)
            if final_state["status"] != "navigation_success":
                return self._finalize_traced_workflow(final_state, start_time, langsmith_trace_url, False)
                
            print("📝 Step 4: LLM analyzing form and filling PIN...")
            final_state = await self.fill_search_form(final_state)
            if final_state["status"] != "form_filled":
                return self._finalize_traced_workflow(final_state, start_time, langsmith_trace_url, False)
                
            print("🔍 Step 5: LLM executing search...")
            final_state = await self.execute_search(final_state)
            if final_state["status"] != "search_completed":
                logger.warning("Search stage did not complete successfully, but continuing workflow")
            
            print("📄 Step 6: Processing property results and collecting deed references...")
            final_state = await self.process_results(final_state)
            
            print("📚 Step 7: Downloading deed documents...")
            final_state = await self.download_documents(final_state)
            
            print("🗃️ Step 8: Updating Knowledge Graph...")
            final_state = await self.update_knowledge_graph(final_state)
            
            print("🏁 Step 9: LLM finalizing workflow...")
            final_state = await self.finalize_workflow(final_state)
            
            # Finalize the traced workflow with success status
            return self._finalize_traced_workflow(final_state, start_time, langsmith_trace_url, True)
            
        except Exception as e:
            logger.error(f"LLM-guided workflow failed for TMS {tms_number}: {e}")
            print(f"❌ LLM workflow error: {e}")
            
            if "errors" not in final_state:
                final_state["errors"] = []
                
            final_state["errors"].append(str(e))
            final_state["status"] = "workflow_error"
            final_state["current_step"] = final_state.get("current_step", "unknown") + "_error"
            
            # Finalize with error status
            return self._finalize_traced_workflow(final_state, start_time, langsmith_trace_url, False)
    
    def _finalize_traced_workflow(self, state: Dict, start_time, langsmith_trace_url: str = None, success: bool = True) -> Dict:
        """Helper to finalize a traced workflow and add metadata"""
        from datetime import datetime
        
        # Add completion metadata
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # Update state
        state["success"] = success
        state["execution_time_seconds"] = execution_time
        
        if langsmith_trace_url:
            state["langsmith_trace_url"] = langsmith_trace_url
            
        # Update metadata
        if "metadata" not in state:
            state["metadata"] = {}
            
        state["metadata"].update({
            "end_time": end_time.isoformat(),
            "execution_time_seconds": execution_time,
            "status": "completed" if success else "failed",
            "documents_count": len(state.get("downloaded_documents", [])),
            "error_count": len(state.get("errors", [])),
            "success": success
        })
        
        # Log completion
        if success:
            logger.info(f"✅ Workflow completed successfully in {execution_time:.1f} seconds")
            print(f"✅ Workflow completed in {execution_time:.1f} seconds")
        else:
            logger.warning(f"⚠️ Workflow ended with issues after {execution_time:.1f} seconds")
            print(f"⚠️ Workflow ended with issues after {execution_time:.1f} seconds")
            if state.get("errors"):
                logger.warning(f"Errors: {', '.join(state['errors'][:3])}" + 
                              (f" and {len(state['errors'])-3} more" if len(state['errors']) > 3 else ""))
        
        return state
