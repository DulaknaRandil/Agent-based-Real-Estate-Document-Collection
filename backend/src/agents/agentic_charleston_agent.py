# src/agents/agentic_charleston_agent.py
"""
Charleston County Property Document Collection Agent
Using Puppeteer for browser automation and Gemini for agentic reasoning
Implements the complete property search workflow with dynamic error handling
"""

import asyncio
import re
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict
import logging

from ..automation.puppeteer_browser_manager import PuppeteerBrowserManager
from ..models.property_record import PropertyRecord, PropertyDocument, BookPageReference, TaskStatus, County
from ..services.gemini_service import GeminiService
from ..services.knowledge_graph_service import CharlestonKnowledgeGraph
from ..services.langsmith_service import LangSmithService
from ..utils.logger import get_logger
from ..utils.config import Settings

class CharlestonWorkflowState(TypedDict):
    """State management for Charleston County workflow"""
    page: Any  # Page object
    browser_manager: Any  # Browser manager
    tms_number: str  # Property TMS number to search
    current_step: str  # Current workflow step
    selectors_tried: Dict[str, List[str]]  # Record of selectors tried
    retry_count: int  # Number of retries
    page_analysis: Dict[str, Any]  # LLM analysis of page
    page_screenshot: str  # Path to latest screenshot
    page_html: str  # Latest page HTML content
    search_successful: bool  # Whether search was successful
    error: Optional[str]  # Any error message
    documents_collected: List[str]  # Collected document paths
    book_page_references: List[Dict[str, str]]  # Extracted book/page references
    property_record: PropertyRecord  # Property record object

logger = get_logger(__name__)

class AgenticCharlestonAgent:
    """
    Charleston County Agent using Puppeteer and Gemini for intelligent automation
    Implements agentic property search workflow with dynamic error recovery
    """
    
    def __init__(self, browser_manager=None):
        """Initialize the Charleston Agent with required services"""
        self.gemini_service = GeminiService()
        self.knowledge_graph = CharlestonKnowledgeGraph()
        self.langsmith_service = LangSmithService()
        self.settings = Settings()
        self.browser_manager = browser_manager
        
        # Charleston County specific URLs
        self.base_url = "https://www.charlestoncounty.org/online-services.php"
        self.property_search_url = "https://sc-charleston.publicaccessnow.com/RealPropertyRecordSearch.aspx"
        self.deeds_search_url = "https://www.charlestoncounty.org/departments/rod/ds-DMBookandPage.php"
        
        # Create downloads directory if it doesn't exist
        self.downloads_dir = Path("data/downloads/charleston")
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize the workflow graph
        self.workflow = self._build_workflow()
        
    async def collect_property_documents(self, tms_number: str) -> PropertyRecord:
        """
        Execute complete Charleston County workflow for a TMS number
        
        Args:
            tms_number: The TMS number to search for
            
        Returns:
            PropertyRecord object with collected documents and metadata
        """
        logger.info(f"Starting Charleston property collection for TMS: {tms_number}")
        
        # Initialize property record
        property_record = PropertyRecord(
            tms_number=tms_number,
            county=County.CHARLESTON,
            status=TaskStatus.IN_PROGRESS,
            documents=[],
            errors=[],
            book_page_references=[]
        )
        
        try:
            # Create browser manager if not provided
            if self.browser_manager is None:
                self.browser_manager = PuppeteerBrowserManager(headless=self.settings.HEADLESS_MODE)
                await self.browser_manager.initialize()
                browser_created = True
            else:
                browser_created = False
                
            # Initialize workflow state
            initial_state = CharlestonWorkflowState(
                page=None,
                browser_manager=self.browser_manager,
                tms_number=tms_number,
                current_step="initialized",
                selectors_tried={},
                retry_count=0,
                page_analysis={},
                page_screenshot="",
                page_html="",
                search_successful=False,
                error=None,
                documents_collected=[],
                book_page_references=[],
                property_record=property_record
            )
            
            # Execute workflow
            final_state = await self.workflow.ainvoke(initial_state)
            
            # Update property record from final state
            property_record = final_state["property_record"]
            
            # Log completion
            logger.info(f"Charleston workflow for TMS {tms_number} completed with status: {property_record.status.value}")
            
            # Generate workflow summary with LLM
            summary = await self._generate_workflow_summary(final_state)
            if not property_record.metadata:
                property_record.metadata = {}
            property_record.metadata["execution_summary"] = summary
            
            # Clean up browser if we created it
            if browser_created and self.browser_manager:
                await self.browser_manager.cleanup()
            
        except Exception as e:
            logger.error(f"Charleston workflow failed: {e}")
            property_record.status = TaskStatus.FAILED
            property_record.errors.append(f"Workflow error: {str(e)}")
        
        return property_record
    
    async def _analyze_page(self, page) -> Dict[str, Any]:
        """Use LLM to analyze the page content and identify elements"""
        try:
            # Get page title
            title = await page.evaluate('() => document.title')
            
            # Get HTML content
            html_content = await page.content()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_path = f"data/temp/current_page_{timestamp}.html"
            Path("data/temp").mkdir(parents=True, exist_ok=True)
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            # Import the screenshot utility
            from src.utils.screenshot_utils import save_error_screenshot
            
            # Take screenshot and save to the proper location
            county = "charleston"
            tms = self.tms_number if hasattr(self, 'tms_number') else "unknown_tms"
            screenshot_path = save_error_screenshot(
                page,
                county=county,
                tms=tms,
                error_type=f"navigation_{timestamp}"
            )
            
            # Extract form elements
            form_elements = await page.evaluate('''
                () => {
                    const result = [];
                    const forms = document.querySelectorAll('form');
                    
                    forms.forEach(form => {
                        const inputs = Array.from(form.querySelectorAll('input, button, select, textarea')).map(el => {
                            return {
                                tag: el.tagName.toLowerCase(),
                                type: el.type || '',
                                id: el.id || '',
                                name: el.name || '',
                                value: el.value || '',
                                placeholder: el.placeholder || '',
                                class: el.className || '',
                                isVisible: (el.offsetParent !== null),
                                label: el.labels && el.labels.length > 0 ? 
                                    el.labels[0].textContent.trim() : ''
                            };
                        });
                        
                        result.push({
                            id: form.id || '',
                            action: form.action || '',
                            method: form.method || '',
                            inputs: inputs
                        });
                    });
                    
                    return result;
                }
            ''')
            
            # Get visible text content
            text_content = await page.evaluate('''
                () => {
                    const textNodes = [];
                    const walker = document.createTreeWalker(
                        document.body,
                        NodeFilter.SHOW_TEXT,
                        null,
                        false
                    );
                    
                    let node;
                    while (node = walker.nextNode()) {
                        if (node.textContent.trim()) {
                            const element = node.parentElement;
                            if (element.offsetParent !== null) {
                                textNodes.push(node.textContent.trim());
                            }
                        }
                    }
                    
                    return textNodes.slice(0, 50).join(' | ');
                }
            ''')
            
            return {
                "title": title,
                "screenshot_path": screenshot_path,
                "html_path": html_path,
                "form_elements": form_elements,
                "text_content": text_content
            }
            
        except Exception as e:
            logger.error(f"Page analysis error: {e}")
            return {
                "title": "Error",
                "error": str(e)
            }

    async def _ask_llm_to_identify_selectors(self, state: CharlestonWorkflowState) -> Dict[str, Any]:
        """Ask LLM to identify input field and search button selectors with knowledge graph fallback"""
        
        # Start LangSmith tracing
        trace_data = await self.langsmith_service.trace_workflow_execution(
            workflow_type="selector_identification",
            tms_numbers=[state["tms_number"]],
            county="charleston",
            current_step=state["current_step"],
            page_title=state["page_analysis"].get("title", "unknown")
        )
        
        # First try to get selectors from knowledge graph
        kg_selectors = self._get_knowledge_graph_selectors(state["current_step"])
        if kg_selectors:
            logger.info("Using knowledge graph selectors as primary strategy")
            
        page_analysis = state["page_analysis"]
        system_prompt = """You are an AI assistant specializing in web automation and element identification for Charleston County property searches.
        
        Your task is to identify the best selectors for PIN/TMS input field and search button on a property search page.
        
        Based on the Charleston County website structure, look specifically for:
        - TMS/PIN input: Usually has title="PIN" and aria-label="PIN" 
        - Search button: Usually has class="btn btn-primary" and title="Search"
        
        Analyze the form elements and provide multiple potential selectors for each element, ranked from most specific to most general.
        Look for inputs that might contain TMS, PIN, Property ID, or similar in their attributes.
        
        Return a JSON response with the following structure:
        {
          "pin_field_selectors": [
            {"selector": "css_selector_1", "confidence": 0.9, "reason": "explanation"},
            {"selector": "css_selector_2", "confidence": 0.7, "reason": "explanation"}
          ],
          "search_button_selectors": [
            {"selector": "css_selector_1", "confidence": 0.9, "reason": "explanation"},
            {"selector": "css_selector_2", "confidence": 0.7, "reason": "explanation"}
          ],
          "page_analysis": "brief analysis of what you see on this page",
          "recommendations": "any special handling recommendations"
        }
        
        For each selector, provide multiple options with different specificity levels.
        Consider using:
        1. ID-based selectors (most specific)
        2. Name-based selectors
        3. Class + type selectors
        4. Attribute selectors (title, aria-label)
        5. Positional selectors (least specific)
        """
        
        form_elements_str = json.dumps(page_analysis["form_elements"], indent=2)
        
        try:
            response = await self.gemini_service.generate_content(
                prompt=f"Page title: {page_analysis['title']}\n\nVisible text content sample: {page_analysis['text_content'][:500]}\n\nForm elements:\n{form_elements_str}",
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=2000,
                as_json=True
            )
            
            # If LLM succeeds, merge with knowledge graph data
            if "parsed_json" in response and kg_selectors:
                llm_result = response["parsed_json"]
                merged_result = self._merge_llm_and_kg_selectors(llm_result, kg_selectors)
                
                # Record successful LLM execution in knowledge graph
                if self.knowledge_graph.driver:
                    self.knowledge_graph.record_successful_execution(
                        step_id=state["current_step"],
                        selector_used="llm_generated",
                        execution_time=1.0
                    )
                
                return merged_result
            
            elif "parsed_json" in response:
                return response["parsed_json"]
                
        except Exception as e:
            logger.error(f"LLM selector identification failed: {e}")
            
            # Record failed LLM execution in knowledge graph
            if self.knowledge_graph.driver:
                self.knowledge_graph.record_failed_execution(
                    step_id=state["current_step"],
                    selector_used="llm_generated",
                    error_message=str(e)
                )
        
        # Fallback to knowledge graph if LLM fails
        if kg_selectors:
            logger.info("LLM failed, using knowledge graph fallback selectors")
            return self._format_kg_selectors_for_llm_response(kg_selectors)
        
        # Ultimate fallback with hardcoded Charleston County selectors
        logger.warning("Both LLM and knowledge graph failed, using hardcoded fallback selectors")
        return {
            "pin_field_selectors": [
                {"selector": 'input[title="PIN"][aria-label="PIN"]', "confidence": 0.9, "reason": "Charleston County specific selector"},
                {"selector": 'input[title="PIN"]', "confidence": 0.8, "reason": "Charleston County fallback"},
                {"selector": 'input[aria-label="PIN"]', "confidence": 0.7, "reason": "Charleston County fallback"},
                {"selector": 'input[class*="form-control"][title="PIN"]', "confidence": 0.6, "reason": "Charleston County fallback"},
                {"selector": "input[name='PIN']", "confidence": 0.5, "reason": "Generic fallback"},
                {"selector": "input[type='text']", "confidence": 0.3, "reason": "Last resort fallback"}
            ],
            "search_button_selectors": [
                {"selector": 'button.btn-primary[title="Search"]', "confidence": 0.9, "reason": "Charleston County specific selector"},
                {"selector": 'button[title="Search"]', "confidence": 0.8, "reason": "Charleston County fallback"},
                {"selector": 'button:contains("Search")', "confidence": 0.7, "reason": "Charleston County fallback"},
                {"selector": "input[type='submit']", "confidence": 0.5, "reason": "Generic fallback"},
                {"selector": "button[type='submit']", "confidence": 0.4, "reason": "Generic fallback"}
            ],
            "page_analysis": "Using hardcoded Charleston County selectors due to LLM failure",
            "recommendations": "Check page structure manually and update knowledge graph"
        }
        
        return {
            "pin_field_selectors": [
                {"selector": "input[name='PIN']", "confidence": 0.5, "reason": "Default fallback"},
                {"selector": "input[type='text']", "confidence": 0.3, "reason": "Default fallback"}
            ],
            "search_button_selectors": [
                {"selector": "input[type='submit']", "confidence": 0.5, "reason": "Default fallback"},
                {"selector": "button[type='submit']", "confidence": 0.4, "reason": "Default fallback"}
            ]
        }
    
    async def _analyze_search_results(self, state: CharlestonWorkflowState) -> Dict[str, Any]:
        """Ask LLM to analyze if the search was successful"""
        page_analysis = state["page_analysis"]
        system_prompt = """You are an AI assistant specializing in web automation.
        
        Your task is to determine if a property search was successful by analyzing the page content.
        Look for indicators of successful search results, such as:
        
        1. Property information displayed
        2. "View Details" or similar links
        3. Property IDs or other details matching the search
        4. Absence of error messages like "No records found"
        
        Return a JSON response with the following structure:
        {
          "success": true/false,
          "confidence": 0.0-1.0,
          "reasoning": "explanation of your analysis",
          "next_actions": [
            {"action": "click", "target": "selector", "description": "description of what to do next"}
          ]
        }
        """
        
        response = await self.gemini_service.generate_content(
            prompt=f"Page title: {page_analysis['title']}\n\nVisible text content sample: {page_analysis['text_content']}\n\nAnalyze if this page shows successful search results for property TMS {state['tms_number']}",
            system_prompt=system_prompt,
            temperature=0.2,
            max_tokens=1000,
            as_json=True
        )
        
        if "error" in response:
            logger.error(f"LLM search results analysis error: {response['error']}")
            return {
                "success": False,
                "confidence": 0.5,
                "reasoning": "Failed to analyze search results"
            }
        
        if "parsed_json" in response:
            return response["parsed_json"]
        
        return {
            "success": False,
            "confidence": 0.5,
            "reasoning": "Failed to analyze search results"
        }
    
    async def _get_error_recovery_strategy(self, state: CharlestonWorkflowState) -> Dict[str, Any]:
        """Ask LLM for error recovery strategies"""
        system_prompt = """You are an AI assistant specializing in web automation error recovery.
        
        Your task is to provide recovery strategies for errors encountered during property search automation.
        Analyze the error and current state, then suggest alternative approaches.
        
        Return a JSON response with recovery strategies:
        {
          "analysis": "explanation of what might have gone wrong",
          "alternative_selectors": ["selector1", "selector2"],
          "alternative_actions": [
            {"type": "click", "selector": "different_selector", "description": "try clicking this instead"},
            {"type": "javascript", "code": "document.querySelector('form').submit();", "description": "try submitting form via JS"}
          ],
          "recommendations": "general advice for recovery"
        }
        """
        
        response = await self.gemini_service.generate_content(
            prompt=f"Error: {state['error']}\nCurrent step: {state['current_step']}\n\nPage title: {state['page_analysis']['title']}\n\nSelectors already tried: {json.dumps(state.get('selectors_tried', {}))}\n\nProvide recovery strategies.",
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=1500,
            as_json=True
        )
        
        if "error" in response:
            logger.error(f"LLM error recovery error: {response['error']}")
            return {
                "alternative_selectors": ["input[type='text']", "input", "input[aria-label*='PIN']"],
                "alternative_actions": [
                    {"type": "click", "selector": "button", "description": "Try any button"},
                    {"type": "javascript", "code": "document.querySelector('form').submit();", "description": "Submit form via JS"}
                ]
            }
        
        if "parsed_json" in response:
            return response["parsed_json"]
        
        return {
            "alternative_selectors": ["input"],
            "alternative_actions": [
                {"type": "javascript", "code": "document.querySelector('form').submit();", "description": "Submit form via JS"}
            ]
        }
    
    async def _extract_book_page_references(self, page) -> List[Dict[str, str]]:
        """Extract book and page numbers from property details"""
        try:
            content = await page.content()
            
            # Multiple regex patterns for book/page extraction
            patterns = [
                r'Book\s+([A-Z]?\d+)\s+Page\s+(\d+)',
                r'DB\s+([A-Z]?\d+)\s+PG\s+(\d+)',
                r'Deed\s+Book\s+([A-Z]?\d+)\s+Page\s+(\d+)',
                r'(\d{4})\s+(\d{3})',  # 4-digit book, 3-digit page
                r'([A-Z]\d{3})\s+(\d{3})'  # Alpha-numeric book
            ]
            
            book_page_refs = []
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for book, page in matches:
                    # Filter for books starting with letter and 280+ (1997-present)
                    if self._is_valid_book_reference(book):
                        book_page_refs.append({
                            "book": book.strip(),
                            "page": page.strip(),
                            "formatted_book": book.strip().zfill(4),
                            "formatted_page": page.strip().zfill(3)
                        })
            
            # Remove duplicates
            unique_refs = []
            seen = set()
            for ref in book_page_refs:
                key = f"{ref['book']}-{ref['page']}"
                if key not in seen:
                    seen.add(key)
                    unique_refs.append(ref)
            
            return unique_refs
            
        except Exception as e:
            logger.error(f"Extract book/page error: {e}")
            return []
    
    def _is_valid_book_reference(self, book: str) -> bool:
        """Validate book reference according to requirements"""
        try:
            # Books starting with letter and 280+ (1997-present)
            if book.isalpha():
                return False
            
            if book[0].isalpha() and len(book) > 1:
                numeric_part = book[1:]
                if numeric_part.isdigit() and int(numeric_part) >= 280:
                    return True
            
            # All numeric books
            if book.isdigit() and int(book) >= 280:
                return True
            
            return False
            
        except:
            return False
    
    async def _generate_workflow_summary(self, state: CharlestonWorkflowState) -> str:
        """Generate a summary of the workflow execution"""
        property_record = state["property_record"]
        
        prompt = f"""
        Summarize the Charleston County property search workflow:
        
        TMS Number: {state['tms_number']}
        Final step: {state['current_step']}
        Status: {property_record.status.value}
        Documents collected: {len(property_record.documents)}
        Book/Page references: {len(state.get('book_page_references', []))}
        Errors: {property_record.errors}
        
        Provide a concise summary of what was accomplished and any issues encountered.
        """
        
        response = await self.gemini_service.generate_content(
            prompt=prompt,
            system_prompt="You are an AI assistant providing concise summaries of workflow execution.",
            temperature=0.1,
            max_tokens=300
        )
        
        if "error" in response:
            return "Workflow summary generation failed"
        
        return response.get("content", "Summary unavailable")
    
    # Workflow Node Functions
    
    async def initialize_workflow(self, state: CharlestonWorkflowState) -> CharlestonWorkflowState:
        """Initialize workflow with browser setup"""
        logger.info("Initializing Charleston workflow")
        
        try:
            browser_manager = state["browser_manager"]
            
            # Check if browser manager exists and is properly initialized
            if browser_manager is None:
                logger.warning("No browser manager provided, creating new one")
                browser_manager = PuppeteerBrowserManager(headless=False)
                await browser_manager.initialize()
                state["browser_manager"] = browser_manager
            
            # Check if browser is still alive, if not reinitialize
            if not await browser_manager.is_browser_alive():
                logger.warning("Browser connection lost, reinitializing")
                await browser_manager.initialize()
            
            # Create or get page
            page = await browser_manager.get_page("charleston")
            
            # Test the page connection by getting the title
            try:
                test_title = await page.evaluate('() => document.title')
                logger.info(f"Page connection test successful: {test_title}")
            except Exception as e:
                logger.warning(f"Page connection test failed: {e}, creating new page")
                page = await browser_manager.create_page("charleston_new")
            
            # Update state with page
            state["page"] = page
            state["current_step"] = "initialized"
            state["selectors_tried"] = {}
            
            logger.info("Browser initialized successfully")
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            state["error"] = f"Initialization error: {str(e)}"
            state["current_step"] = "error"
            state["property_record"].errors.append(f"Initialization error: {str(e)}")
            state["property_record"].status = TaskStatus.FAILED
        
        return state
    
    async def navigate_to_search_page(self, state: CharlestonWorkflowState) -> CharlestonWorkflowState:
        """Navigate to Charleston County property search page"""
        logger.info("Navigating to Charleston County property search page")
        
        try:
            page = state["page"]
            browser_manager = state["browser_manager"]
            
            # Navigate to search page
            search_url = "https://sc-charleston.publicaccessnow.com/RealPropertyRecordSearch.aspx"
            success = await browser_manager.navigate_to(search_url, page)
            
            if not success:
                state["error"] = "Failed to navigate to search page"
                state["current_step"] = "navigation_error"
                state["property_record"].errors.append("Failed to navigate to search page")
                return state
            
            # Wait for page to load
            await asyncio.sleep(3)
            
            # Analyze page
            state["page_analysis"] = await self._analyze_page(page)
            state["current_step"] = "on_search_page"
            
            logger.info("Successfully navigated to search page")
            
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            state["error"] = f"Navigation error: {str(e)}"
            state["current_step"] = "error"
            state["property_record"].errors.append(f"Navigation error: {str(e)}")
        
        return state
    
    async def identify_and_fill_form(self, state: CharlestonWorkflowState) -> CharlestonWorkflowState:
        """Identify form elements using LLM and fill in TMS number"""
        logger.info("Identifying form elements and filling TMS")
        
        try:
            page = state["page"]
            browser_manager = state["browser_manager"]
            tms_number = state["tms_number"]
            
            # Ask LLM to identify selectors
            selector_suggestions = await self._ask_llm_to_identify_selectors(state)
            state["selector_suggestions"] = selector_suggestions
            
            # Try each PIN field selector in order of confidence
            pin_filled = False
            
            for selector_info in selector_suggestions.get("pin_field_selectors", []):
                selector = selector_info["selector"]
                logger.info(f"Trying PIN field selector: {selector}")
                
                try:
                    # Check if element exists
                    element_exists = await page.evaluate(f'() => !!document.querySelector("{selector}")')
                    if element_exists:
                        success = await browser_manager.input_text(page, selector, tms_number)
                        if success:
                            logger.info(f"Successfully filled TMS {tms_number} using selector {selector}")
                            pin_filled = True
                            if "selectors_tried" not in state:
                                state["selectors_tried"] = {}
                            state["selectors_tried"]["pin_field"] = selector
                            break
                        else:
                            logger.warning(f"Failed to fill TMS with selector {selector}")
                    else:
                        logger.warning(f"PIN field selector not found: {selector}")
                except Exception as e:
                    logger.warning(f"Error trying selector {selector}: {e}")
            
            if not pin_filled:
                state["error"] = "Failed to identify and fill PIN field"
                state["current_step"] = "pin_field_error"
                state["property_record"].errors.append("Failed to identify and fill PIN field")
                return state
            
            state["current_step"] = "form_filled"
            logger.info("Successfully filled form")
            
        except Exception as e:
            logger.error(f"Form filling failed: {e}")
            state["error"] = f"Form filling error: {str(e)}"
            state["current_step"] = "error"
            state["property_record"].errors.append(f"Form filling error: {str(e)}")
        
        return state
    
    async def submit_search(self, state: CharlestonWorkflowState) -> CharlestonWorkflowState:
        """Submit the search form"""
        logger.info("Submitting search form")
        
        try:
            page = state["page"]
            browser_manager = state["browser_manager"]
            
            # Make sure we have selector suggestions
            if "selector_suggestions" not in state or not state["selector_suggestions"]:
                # Get suggestions using LLM
                selector_suggestions = await self._ask_llm_to_identify_selectors(state)
                state["selector_suggestions"] = selector_suggestions
            
            # Try each search button selector in order of confidence
            search_submitted = False
            
            # Get the search button selectors
            search_button_selectors = state["selector_suggestions"].get("search_button_selectors", [
                {"selector": "input[type='submit']", "confidence": 0.8},
                {"selector": "button[type='submit']", "confidence": 0.7},
                {"selector": ".searchButton", "confidence": 0.6},
                {"selector": "button:contains('Search')", "confidence": 0.5},
                {"selector": "input.btn", "confidence": 0.4}
            ])
            
            for selector_info in search_button_selectors:
                selector = selector_info["selector"]
                logger.info(f"Trying search button selector: {selector}")
                
                try:
                    # Check if element exists
                    element_exists = await page.evaluate(f'() => !!document.querySelector("{selector}")')
                    if element_exists:
                        success = await browser_manager.click_element(page, selector)
                        if success:
                            logger.info(f"Successfully clicked search button using selector {selector}")
                            search_submitted = True
                            if "selectors_tried" not in state:
                                state["selectors_tried"] = {}
                            state["selectors_tried"]["search_button"] = selector
                            break
                        else:
                            logger.warning(f"Failed to click search button with selector {selector}")
                    else:
                        logger.warning(f"Search button selector not found: {selector}")
                except Exception as e:
                    logger.warning(f"Error trying selector {selector}: {e}")
            
            # Try the Enter key as fallback
            if not search_submitted:
                try:
                    logger.info("Trying to press Enter key as fallback")
                    await page.keyboard.press('Enter')
                    search_submitted = True
                except Exception as e:
                    logger.warning(f"Enter key press failed: {e}")
            
            if not search_submitted:
                state["error"] = "Failed to identify and click search button"
                state["current_step"] = "search_button_error"
                state["property_record"].errors.append("Failed to identify and click search button")
                return state
            
            # Wait for results to load
            await asyncio.sleep(5)
            
            # Take screenshot and analyze page to verify search results
            state["page_analysis"] = await self._analyze_page(page)
            state["current_step"] = "search_submitted"
            
            # Check if search was successful (look for results or next step indicators)
            page_text = state["page_analysis"]["text_content"].lower()
            if "no records found" in page_text:
                state["error"] = "No property records found for the TMS number"
                state["search_successful"] = False
                state["current_step"] = "no_results"
                state["property_record"].errors.append("No property records found for the TMS number")
            elif "view details" in page_text or "property" in page_text:
                state["search_successful"] = True
                state["current_step"] = "search_successful"
            else:
                # Ask LLM to analyze if search was successful
                search_success_analysis = await self._analyze_search_results(state)
                state["search_successful"] = search_success_analysis.get("success", False)
                state["current_step"] = "search_results_analyzed"
                
                if not state["search_successful"]:
                    state["property_record"].errors.append("Search results not found or could not be analyzed")
            
            logger.info(f"Search submission complete. Success: {state['search_successful']}")
            
        except Exception as e:
            logger.error(f"Search submission failed: {e}")
            state["error"] = f"Search submission error: {str(e)}"
            state["current_step"] = "error"
            state["property_record"].errors.append(f"Search submission error: {str(e)}")
        
        return state
    
    async def process_search_results(self, state: CharlestonWorkflowState) -> CharlestonWorkflowState:
        """Process search results and download property information"""
        logger.info("Processing search results")
        
        try:
            page = state["page"]
            browser_manager = state["browser_manager"]
            tms_number = state["tms_number"]
            
            # First find and click "View Details" link
            view_details_selectors = [
                'a:has-text("View Details")',
                'a[title="View Details"]',
                'a.details-link',
                'a.ViewDetails',
                'a:has-text("Details")'
            ]
            
            view_details_clicked = False
            for selector in view_details_selectors:
                try:
                    element_exists = await page.evaluate(f'() => !!document.querySelector("{selector}")')
                    if element_exists:
                        success = await browser_manager.click_element(page, selector)
                        if success:
                            logger.info(f"Clicked View Details using selector {selector}")
                            view_details_clicked = True
                            break
                except Exception as e:
                    logger.warning(f"Error clicking View Details with selector {selector}: {e}")
            
            if not view_details_clicked:
                state["error"] = "Failed to click View Details link"
                state["current_step"] = "view_details_error"
                state["property_record"].errors.append("Failed to click View Details link")
                return state
            
            # Wait for details page to load
            await asyncio.sleep(3)
            
            # Save Property Card as PDF
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"Property_Card_{tms_number}_{timestamp}.pdf"
            property_card_path = str(self.downloads_dir / filename)
            
            # Save PDF using Puppeteer's built-in PDF functionality
            pdf_options = {
                'path': property_card_path,
                'format': 'Letter',
                'printBackground': True
            }
            await page.pdf(pdf_options)
            
            if os.path.exists(property_card_path):
                logger.info(f"Saved property card to {property_card_path}")
                state["property_record"].documents.append(PropertyDocument(
                    file_path=property_card_path,
                    document_type="property_card",
                    file_size=os.path.getsize(property_card_path),
                    metadata={"tms_number": tms_number}
                ))
                state["documents_collected"].append(property_card_path)
            else:
                logger.warning("Failed to save property card PDF")
                state["property_record"].errors.append("Failed to save property card PDF")
            
            # Extract book and page references
            book_page_refs = await self._extract_book_page_references(page)
            if book_page_refs:
                logger.info(f"Extracted {len(book_page_refs)} book/page references")
                state["book_page_references"] = book_page_refs
                
                # Convert to BookPageReference objects for property record
                for ref in book_page_refs:
                    state["property_record"].book_page_references.append(BookPageReference(
                        book=ref["book"],
                        page=ref["page"],
                        formatted_book=ref["formatted_book"],
                        formatted_page=ref["formatted_page"]
                    ))
            
            # Click Tax Info link if available
            tax_info_selectors = [
                'a[title="Tax Info"]',
                'a:has-text("Tax Info")',
                'a.tax-info',
                '#taxInfoLink'
            ]
            
            tax_info_clicked = False
            for selector in tax_info_selectors:
                try:
                    element_exists = await page.evaluate(f'() => !!document.querySelector("{selector}")')
                    if element_exists:
                        success = await browser_manager.click_element(page, selector)
                        if success:
                            logger.info(f"Clicked Tax Info using selector {selector}")
                            tax_info_clicked = True
                            
                            # Wait for tax info page to load
                            await asyncio.sleep(3)
                            
                            # Save Tax Info as PDF
                            tax_filename = f"Tax_Info_{tms_number}_{timestamp}.pdf"
                            tax_info_path = str(self.downloads_dir / tax_filename)
                            
                            await page.pdf({
                                'path': tax_info_path,
                                'format': 'Letter',
                                'printBackground': True
                            })
                            
                            if os.path.exists(tax_info_path):
                                logger.info(f"Saved tax info to {tax_info_path}")
                                state["property_record"].documents.append(PropertyDocument(
                                    file_path=tax_info_path,
                                    document_type="tax_info",
                                    file_size=os.path.getsize(tax_info_path),
                                    metadata={"tms_number": tms_number}
                                ))
                                state["documents_collected"].append(tax_info_path)
                            
                            break
                except Exception as e:
                    logger.warning(f"Error clicking Tax Info with selector {selector}: {e}")
            
            if not tax_info_clicked:
                logger.warning("Could not find Tax Info link")
                state["property_record"].errors.append("Could not find Tax Info link")
            
            state["current_step"] = "property_info_collected"
            
        except Exception as e:
            logger.error(f"Processing search results failed: {e}")
            state["error"] = f"Processing results error: {str(e)}"
            state["current_step"] = "error"
            state["property_record"].errors.append(f"Processing results error: {str(e)}")
        
        return state
    
    async def collect_deed_documents(self, state: CharlestonWorkflowState) -> CharlestonWorkflowState:
        """Collect deed documents for each book/page reference"""
        logger.info("Collecting deed documents")
        
        try:
            page = state["page"]
            browser_manager = state["browser_manager"]
            tms_number = state["tms_number"]
            book_page_refs = state["book_page_references"]
            
            if not book_page_refs:
                logger.warning("No book/page references to collect deeds for")
                state["current_step"] = "no_deed_references"
                return state
            
            for ref in book_page_refs:
                try:
                    # Navigate to Register of Deeds search
                    logger.info(f"Searching for deed with Book {ref['book']}, Page {ref['page']}")
                    
                    success = await browser_manager.navigate_to(self.deeds_search_url, page)
                    if not success:
                        logger.warning("Failed to navigate to deeds search page")
                        continue
                    
                    # Wait for page to load
                    await asyncio.sleep(3)
                    
                    # Enter book number
                    book_input_selectors = ['input[name*="book"]', '#book', 'input[placeholder*="book"]']
                    for selector in book_input_selectors:
                        try:
                            element_exists = await page.evaluate(f'() => !!document.querySelector("{selector}")')
                            if element_exists:
                                await browser_manager.input_text(page, selector, ref["formatted_book"])
                                break
                        except Exception as e:
                            logger.warning(f"Error with book input selector {selector}: {e}")
                    
                    # Enter page number
                    page_input_selectors = ['input[name*="page"]', '#page', 'input[placeholder*="page"]']
                    for selector in page_input_selectors:
                        try:
                            element_exists = await page.evaluate(f'() => !!document.querySelector("{selector}")')
                            if element_exists:
                                await browser_manager.input_text(page, selector, ref["formatted_page"])
                                break
                        except Exception as e:
                            logger.warning(f"Error with page input selector {selector}: {e}")
                    
                    # Click legal disclaimer checkbox if present
                    disclaimer_selectors = ['input[name="agreelegal"]', '#agreelegal', 'input[type="checkbox"]']
                    for selector in disclaimer_selectors:
                        try:
                            element_exists = await page.evaluate(f'() => !!document.querySelector("{selector}")')
                            if element_exists:
                                await browser_manager.click_element(page, selector)
                                break
                        except Exception:
                            pass
                    
                    # Click search button
                    search_button_selectors = [
                        'input[name="send_button"]', 
                        'input[type="submit"]', 
                        'button[type="submit"]'
                    ]
                    
                    search_clicked = False
                    for selector in search_button_selectors:
                        try:
                            element_exists = await page.evaluate(f'() => !!document.querySelector("{selector}")')
                            if element_exists:
                                success = await browser_manager.click_element(page, selector)
                                if success:
                                    search_clicked = True
                                    break
                        except Exception:
                            pass
                    
                    if not search_clicked:
                        logger.warning(f"Could not click search button for Book {ref['book']}, Page {ref['page']}")
                        continue
                    
                    # Wait for results
                    await asyncio.sleep(3)
                    
                    # Find and click View button if present
                    view_selectors = ['a:has-text("View")', 'a.view-link', 'a[title*="View"]']
                    view_clicked = False
                    
                    for selector in view_selectors:
                        try:
                            element_exists = await page.evaluate(f'() => !!document.querySelector("{selector}")')
                            if element_exists:
                                success = await browser_manager.click_element(page, selector)
                                if success:
                                    view_clicked = True
                                    # Wait for document to load
                                    await asyncio.sleep(3)
                                    break
                        except Exception:
                            pass
                    
                    if not view_clicked:
                        logger.warning(f"Could not view document for Book {ref['book']}, Page {ref['page']}")
                        continue
                    
                    # Save deed document
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"Deed_B{ref['formatted_book']}_P{ref['formatted_page']}_{tms_number}_{timestamp}.pdf"
                    deed_path = str(self.downloads_dir / filename)
                    
                    # Download PDF
                    await page.pdf({
                        'path': deed_path,
                        'format': 'Letter',
                        'printBackground': True
                    })
                    
                    if os.path.exists(deed_path):
                        logger.info(f"Saved deed document to {deed_path}")
                        state["property_record"].documents.append(PropertyDocument(
                            file_path=deed_path,
                            document_type="deed",
                            file_size=os.path.getsize(deed_path),
                            metadata={
                                "tms_number": tms_number,
                                "book": ref["book"],
                                "page": ref["page"]
                            }
                        ))
                        state["documents_collected"].append(deed_path)
                    
                except Exception as e:
                    logger.error(f"Error collecting deed for Book {ref['book']}, Page {ref['page']}: {e}")
                    state["property_record"].errors.append(
                        f"Error collecting deed for Book {ref['book']}, Page {ref['page']}: {str(e)}"
                    )
            
            state["current_step"] = "deeds_collected"
            
        except Exception as e:
            logger.error(f"Collecting deeds failed: {e}")
            state["error"] = f"Deed collection error: {str(e)}"
            state["current_step"] = "error"
            state["property_record"].errors.append(f"Deed collection error: {str(e)}")
        
        return state
    
    async def handle_error(self, state: CharlestonWorkflowState) -> CharlestonWorkflowState:
        """Handle errors using LLM-driven recovery strategies"""
        error_message = state["error"]
        current_step = state["current_step"]
        
        logger.info(f"Handling error in step '{current_step}': {error_message}")
        
        # Increment retry count
        state["retry_count"] = state.get("retry_count", 0) + 1
        
        if state["retry_count"] > 3:
            logger.error("Maximum retry count exceeded")
            state["current_step"] = "max_retries_exceeded"
            state["property_record"].errors.append("Maximum retry count exceeded")
            state["property_record"].status = TaskStatus.FAILED
            return state
        
        try:
            # Ask LLM for recovery strategy
            recovery_strategy = await self._get_error_recovery_strategy(state)
            state["recovery_strategy"] = recovery_strategy
            
            # Implement recovery strategy
            if "pin_field_error" in current_step:
                # Try alternative PIN field selectors
                alternative_selectors = recovery_strategy.get("alternative_selectors", [])
                for selector in alternative_selectors:
                    try:
                        success = await state["browser_manager"].input_text(
                            state["page"], 
                            selector, 
                            state["tms_number"]
                        )
                        if success:
                            logger.info(f"Recovery successful: filled PIN field with alternative selector {selector}")
                            if "selectors_tried" not in state:
                                state["selectors_tried"] = {}
                            state["selectors_tried"]["pin_field"] = selector
                            state["current_step"] = "form_filled"
                            state["error"] = None
                            return state
                    except Exception as e:
                        logger.warning(f"Recovery attempt failed with selector {selector}: {e}")
            
            elif "search_button_error" in current_step:
                # Try alternative search button strategies
                alternative_actions = recovery_strategy.get("alternative_actions", [])
                for action in alternative_actions:
                    try:
                        if action["type"] == "click":
                            success = await state["browser_manager"].click_element(
                                state["page"], 
                                action["selector"]
                            )
                            if success:
                                logger.info(f"Recovery successful: clicked search button with alternative selector {action['selector']}")
                                if "selectors_tried" not in state:
                                    state["selectors_tried"] = {}
                                state["selectors_tried"]["search_button"] = action["selector"]
                                state["current_step"] = "search_submitted"
                                state["error"] = None
                                await asyncio.sleep(3)  # Wait for results to load
                                state["page_analysis"] = await self._analyze_page(state["page"])
                                return state
                        elif action["type"] == "javascript":
                            # Execute JavaScript as a fallback
                            await state["page"].evaluate(action["code"])
                            logger.info(f"Recovery successful: executed JavaScript action")
                            state["current_step"] = "search_submitted"
                            state["error"] = None
                            await asyncio.sleep(3)  # Wait for results to load
                            state["page_analysis"] = await self._analyze_page(state["page"])
                            return state
                    except Exception as e:
                        logger.warning(f"Recovery action failed: {e}")
            
            # If we reach here, recovery failed
            logger.warning("All recovery strategies failed")
            state["current_step"] = f"{current_step}_recovery_failed"
            
        except Exception as e:
            logger.error(f"Error recovery handling failed: {e}")
            state["error"] = f"Recovery error: {str(e)}"
            state["property_record"].errors.append(f"Recovery error: {str(e)}")
        
        return state
    
    async def cleanup_workflow(self, state: CharlestonWorkflowState) -> CharlestonWorkflowState:
        """Cleanup workflow resources and generate summary"""
        logger.info("Cleaning up workflow resources")
        
        try:
            # Update property record status
            if state.get("documents_collected"):
                state["property_record"].status = TaskStatus.COMPLETED
            else:
                state["property_record"].status = TaskStatus.FAILED
                if not state["property_record"].errors:
                    state["property_record"].errors.append("No documents were collected")
            
            # Generate workflow summary with LLM
            summary = await self._generate_workflow_summary(state)
            if not state["property_record"].metadata:
                state["property_record"].metadata = {}
            state["property_record"].metadata["execution_summary"] = summary
            
            state["current_step"] = "completed"
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            state["error"] = f"Cleanup error: {str(e)}"
            state["current_step"] = "error"
            state["property_record"].errors.append(f"Cleanup error: {str(e)}")
        
        return state
    
    def _decide_next_step(self, state: CharlestonWorkflowState) -> str:
        """Determine the next step in the workflow"""
        current_step = state["current_step"]
        
        if "error" in current_step:
            return "handle_error"
        
        step_transitions = {
            "initialized": "navigate_to_search_page",
            "on_search_page": "identify_and_fill_form",
            "form_filled": "submit_search",
            "search_successful": "process_search_results",
            "search_results_analyzed": "process_search_results",
            "property_info_collected": "collect_deed_documents",
            "deeds_collected": "cleanup_workflow",
            "no_results": "cleanup_workflow",
            "no_deed_references": "cleanup_workflow",
            "max_retries_exceeded": "cleanup_workflow"
        }
        
        return step_transitions.get(current_step, "cleanup_workflow")
    
    def _build_workflow(self) -> Any:
        """Build the LangGraph workflow for Charleston County property search"""
        workflow = StateGraph(CharlestonWorkflowState)
        
        # Add nodes
        workflow.add_node("initialize_workflow", self.initialize_workflow)
        workflow.add_node("navigate_to_search_page", self.navigate_to_search_page)
        workflow.add_node("identify_and_fill_form", self.identify_and_fill_form)
        workflow.add_node("submit_search", self.submit_search)
        workflow.add_node("process_search_results", self.process_search_results)
        workflow.add_node("collect_deed_documents", self.collect_deed_documents)
        workflow.add_node("handle_error", self.handle_error)
        workflow.add_node("cleanup_workflow", self.cleanup_workflow)
        
        # Set entry point
        workflow.set_entry_point("initialize_workflow")
        
        # Add edges with conditional routing
        workflow.add_conditional_edges(
            "initialize_workflow",
            self._decide_next_step,
            {
                "navigate_to_search_page": "navigate_to_search_page",
                "handle_error": "handle_error",
                "cleanup_workflow": "cleanup_workflow"
            }
        )
        
        workflow.add_conditional_edges(
            "navigate_to_search_page",
            self._decide_next_step,
            {
                "identify_and_fill_form": "identify_and_fill_form",
                "handle_error": "handle_error",
                "cleanup_workflow": "cleanup_workflow"
            }
        )
        
        workflow.add_conditional_edges(
            "identify_and_fill_form",
            self._decide_next_step,
            {
                "submit_search": "submit_search",
                "handle_error": "handle_error",
                "cleanup_workflow": "cleanup_workflow"
            }
        )
        
        workflow.add_conditional_edges(
            "submit_search",
            self._decide_next_step,
            {
                "process_search_results": "process_search_results",
                "handle_error": "handle_error",
                "cleanup_workflow": "cleanup_workflow"
            }
        )
        
        workflow.add_conditional_edges(
            "process_search_results",
            self._decide_next_step,
            {
                "collect_deed_documents": "collect_deed_documents",
                "handle_error": "handle_error",
                "cleanup_workflow": "cleanup_workflow"
            }
        )
        
        workflow.add_conditional_edges(
            "collect_deed_documents",
            self._decide_next_step,
            {
                "cleanup_workflow": "cleanup_workflow",
                "handle_error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "handle_error",
            self._decide_next_step,
            {
                "navigate_to_search_page": "navigate_to_search_page",
                "identify_and_fill_form": "identify_and_fill_form",
                "submit_search": "submit_search",
                "process_search_results": "process_search_results",
                "collect_deed_documents": "collect_deed_documents",
                "cleanup_workflow": "cleanup_workflow",
                "handle_error": "handle_error"  # Allow retry loop but will be limited by max_retries
            }
        )
        
        # End state
        workflow.add_edge("cleanup_workflow", END)
        
        return workflow.compile()
    
    def _get_knowledge_graph_selectors(self, current_step: str) -> Dict[str, Any]:
        """Get selectors from knowledge graph for current step"""
        if not self.knowledge_graph.driver:
            return {}
        
        try:
            # Map current step to element types
            element_type_mapping = {
                "enter_tms": "tms_input",
                "click_search": "search_button", 
                "click_view_details": "view_details",
                "navigate_property_search": "property_search",
                "click_tax_info": "tax_info"
            }
            
            element_type = element_type_mapping.get(current_step)
            if not element_type:
                return {}
                
            return self.knowledge_graph.get_element_selectors(element_type)
            
        except Exception as e:
            logger.error(f"Failed to get knowledge graph selectors: {e}")
            return {}
    
    def _merge_llm_and_kg_selectors(self, llm_result: Dict[str, Any], kg_selectors: Dict[str, Any]) -> Dict[str, Any]:
        """Merge LLM results with knowledge graph selectors"""
        # Start with LLM results
        merged = llm_result.copy()
        
        # Add knowledge graph selectors as high-confidence options
        if kg_selectors.get("primary_selector"):
            # Add KG primary selector as top option for PIN field
            kg_pin_selector = {
                "selector": kg_selectors["primary_selector"],
                "confidence": 0.95,
                "reason": "Knowledge graph primary selector"
            }
            merged["pin_field_selectors"].insert(0, kg_pin_selector)
            
            # Add fallback selectors
            for i, fallback in enumerate(kg_selectors.get("fallback_selectors", [])):
                fallback_selector = {
                    "selector": fallback,
                    "confidence": 0.8 - (i * 0.1),
                    "reason": f"Knowledge graph fallback {i+1}"
                }
                merged["pin_field_selectors"].insert(i+1, fallback_selector)
        
        return merged
    
    def _format_kg_selectors_for_llm_response(self, kg_selectors: Dict[str, Any]) -> Dict[str, Any]:
        """Format knowledge graph selectors to match LLM response format"""
        pin_selectors = []
        search_selectors = []
        
        # Add primary selector
        if kg_selectors.get("primary_selector"):
            pin_selectors.append({
                "selector": kg_selectors["primary_selector"],
                "confidence": 0.9,
                "reason": "Knowledge graph primary selector"
            })
        
        # Add fallback selectors
        for i, fallback in enumerate(kg_selectors.get("fallback_selectors", [])):
            pin_selectors.append({
                "selector": fallback,
                "confidence": 0.8 - (i * 0.1),
                "reason": f"Knowledge graph fallback {i+1}"
            })
        
        # Default search button selectors
        search_selectors = [
            {"selector": 'button.btn-primary[title="Search"]', "confidence": 0.9, "reason": "Charleston County search button"},
            {"selector": 'button[title="Search"]', "confidence": 0.8, "reason": "Generic search button"},
            {"selector": "input[type='submit']", "confidence": 0.7, "reason": "Submit button fallback"}
        ]
        
        return {
            "pin_field_selectors": pin_selectors,
            "search_button_selectors": search_selectors,
            "page_analysis": f"Using knowledge graph selectors: {kg_selectors.get('description', 'No description')}",
            "recommendations": "Knowledge graph fallback strategy active"
        }

    async def _trace_step_execution(self, step_name: str, state: CharlestonWorkflowState, success: bool, details: Dict[str, Any] = None):
        """Trace individual step execution with LangSmith"""
        try:
            await self.langsmith_service.trace_step_execution(
                step_name=step_name,
                tms_number=state["tms_number"],
                county="charleston",
                success=success,
                retry_count=state.get("retry_count", 0),
                page_url=details.get("page_url", "unknown") if details else "unknown",
                execution_time=details.get("execution_time", 0) if details else 0,
                error_message=details.get("error_message") if details else None,
                **details if details else {}
            )
        except Exception as e:
            logger.error(f"Failed to trace step execution: {e}")
