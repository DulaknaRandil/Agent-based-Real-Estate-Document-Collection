"""
Gemini LLM Service for Charleston County Property Search with Fallback Options
"""
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
import google.generativeai as genai
from groq import Groq
from src.config import GEMINI_API_KEY, GROQ_API_KEY, DEEPSEEK_API_KEY
from datetime import datetime

logger = logging.getLogger(__name__)

class GeminiService:
    """Google Gemini LLM service with multiple fallback options for query parsing and instruction generation"""
    
    def __init__(self):
        self.gemini_model = None
        self.groq_client = None
        self.deepseek_client = None
        self.initialize()
    
    def initialize(self):
        """Initialize Gemini API and fallback LLM options"""
        try:
            # Initialize Gemini 2.0
            if GEMINI_API_KEY:
                genai.configure(api_key=GEMINI_API_KEY)
                self.gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')
                logger.info("Gemini 2.0 LLM service initialized")
            else:
                logger.warning("GEMINI_API_KEY not found")
            
            # Initialize Groq fallback
            if GROQ_API_KEY:
                self.groq_client = Groq(api_key=GROQ_API_KEY)
                logger.info("Groq LLM service initialized as fallback")
            else:
                logger.warning("GROQ_API_KEY not found")
            
            # Initialize DeepSeek fallback
            if DEEPSEEK_API_KEY:
                self.deepseek_client = Groq(api_key=DEEPSEEK_API_KEY)
                logger.info("DeepSeek LLM service initialized as additional fallback")
            else:
                logger.warning("DEEPSEEK_API_KEY not found")
                
        except Exception as e:
            logger.error(f"Failed to initialize LLM services: {e}")
    
    def _call_gemini(self, prompt: str, system_instruction: str = None) -> str:
        """Call Gemini 2.0 API"""
        try:
            if not self.gemini_model:
                raise ValueError("Gemini model not initialized")
            
            # Create model with system instruction if provided
            if system_instruction:
                model = genai.GenerativeModel(
                    'gemini-2.0-flash-exp',
                    system_instruction=system_instruction
                )
                response = model.generate_content(prompt)
            else:
                response = self.gemini_model.generate_content(prompt)
            
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise
    
    def _call_groq(self, prompt: str, system_message: str = None) -> str:
        """Call Groq API as fallback"""
        try:
            if not self.groq_client:
                raise ValueError("Groq client not initialized")
            
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt})
            
            # Using deepseek-r1-distill-llama-70b which is available in Groq
            completion = self.groq_client.chat.completions.create(
                model="deepseek-r1-distill-llama-70b",
                messages=messages,
                temperature=0.3,
                max_tokens=2048
            )
            
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            raise
    
    def _call_deepseek(self, prompt: str, system_message: str = None) -> str:
        """Call DeepSeek API as another fallback option"""
        try:
            if not self.deepseek_client:
                raise ValueError("DeepSeek client not initialized")
            
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt})
            
            # Using DeepSeek's distilled LLaMa model
            completion = self.deepseek_client.chat.completions.create(
                model="deepseek-r1-distill-llama-70b",
                messages=messages,
                temperature=0.3,
                max_tokens=2048
            )
            
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"DeepSeek API error: {e}")
            raise
    
    def _call_llm_with_fallback(self, prompt: str, system_instruction: str = None) -> str:
        """Call LLM with fallback pattern: Gemini first, then Groq, then DeepSeek"""
        # Try Gemini first
        try:
            if self.gemini_model:
                logger.debug("Attempting Gemini 2.0 call")
                return self._call_gemini(prompt, system_instruction)
        except Exception as e:
            logger.warning(f"Gemini failed, trying Groq fallback: {e}")
        
        # Fallback to Groq
        try:
            if self.groq_client:
                logger.info("Using Groq fallback")
                return self._call_groq(prompt, system_instruction)
        except Exception as e:
            logger.warning(f"Groq failed, trying DeepSeek fallback: {e}")
        
        # Fallback to DeepSeek
        try:
            if self.deepseek_client:
                logger.info("Using DeepSeek fallback")
                return self._call_deepseek(prompt, system_instruction)
        except Exception as e:
            logger.error(f"All LLM services failed: {e}")
            raise
        
        raise ValueError("No LLM service available")
    
    def parse_property_search_query(self, user_query: str) -> Dict:
        """Parse user query to extract TMS number and search intent"""
        try:
            system_instruction = """
            You are a property search query parser for Charleston County, SC. 
            Parse user queries to extract TMS numbers, addresses, owner names, and search intent.
            Always return valid JSON.
            """
            
            prompt = f"""
            Parse this Charleston County property search query and extract information:
            
            User Query: "{user_query}"
            
            Return JSON with these exact keys:
            {{
                "tms_number": "string or null if not found",
                "address": "string or null if not found", 
                "owner_name": "string or null if not found",
                "search_intent": "property_search",
                "confidence_score": 0.8,
                "reasoning": "brief explanation of parsing decisions"
            }}
            
            TMS numbers are typically 10 digits, may have dashes or spaces.
            """
            
            response_text = self._call_llm_with_fallback(prompt, system_instruction)
            
            # Try to parse JSON response
            try:
                result = json.loads(response_text)
                logger.info(f"Successfully parsed query: {user_query}")
                return result
            except json.JSONDecodeError:
                logger.warning("LLM response was not valid JSON, using fallback")
                return {
                    "tms_number": None,
                    "address": None,
                    "owner_name": None,
                    "search_intent": "property_search",
                    "confidence_score": 0.5,
                    "reasoning": "JSON parsing failed",
                    "raw_response": response_text
                }
            
        except Exception as e:
            logger.error(f"Failed to parse query: {e}")
            return {
                "tms_number": None,
                "address": None,
                "owner_name": None,
                "search_intent": "property_search",
                "confidence_score": 0.0,
                "error": str(e)
            }
    
    
    def generate_search_strategy(self, tms_number: str, context: Dict = None) -> Dict:
        """Generate search strategy for Charleston County automation"""
        try:
            system_instruction = """
            You are an expert in Charleston County property search automation.
            Generate comprehensive search strategies that account for potential challenges.
            Always return valid JSON.
            """
            
            prompt = f"""
            Generate a detailed search strategy for Charleston County property with TMS: {tms_number}
            
            Context: {context or {}}
            
            Return JSON with these exact keys:
            {{
                "strategy": "strategy_name",
                "steps": ["step1", "step2", "step3"],
                "expected_documents": ["doc1", "doc2"],
                "potential_challenges": ["challenge1", "challenge2"],
                "fallback_strategies": ["fallback1", "fallback2"],
                "estimated_time": "10-15 minutes",
                "priority_documents": ["most_important_doc"]
            }}
            
            Consider: TMS formatting, captcha handling, PDF downloads, deed searches.
            """
            
            response_text = self._call_llm_with_fallback(prompt, system_instruction)
            
            try:
                result = json.loads(response_text)
                logger.info(f"Generated search strategy for TMS: {tms_number}")
                return result
            except json.JSONDecodeError:
                logger.warning("LLM response was not valid JSON, using fallback strategy")
                return self._get_fallback_strategy()
                
        except Exception as e:
            logger.error(f"Failed to generate search strategy: {e}")
            return self._get_fallback_strategy(error=str(e))
    
    def _get_fallback_strategy(self, error: str = None) -> Dict:
        """Return fallback search strategy when LLM fails"""
        return {
            "strategy": "comprehensive_property_search",
            "steps": [
                "navigate_to_property_search",
                "fill_tms_field", 
                "execute_search",
                "download_property_card",
                "get_tax_information",
                "search_deed_records"
            ],
            "expected_documents": ["property_card", "tax_info", "deeds"],
            "potential_challenges": ["captcha", "network_issues", "element_not_found"],
            "fallback_strategies": ["retry_with_delay", "use_alternative_selectors"],
            "estimated_time": "15-20 minutes",
            "priority_documents": ["property_card"],
            "fallback": True,
            "error": error
        }
    
    def analyze_page_content(self, page_html: str, search_goal: str) -> Dict:
        """Analyze webpage content to determine next actions"""
        try:
            # Truncate HTML for API limits
            truncated_html = page_html[:3000] if len(page_html) > 3000 else page_html
            
            system_instruction = """
            You are a web automation expert analyzing Charleston County government websites.
            Identify page elements, forms, buttons, and recommend next actions.
            Always return valid JSON.
            """
            
            prompt = f"""
            Analyze this Charleston County webpage HTML to achieve goal: {search_goal}
            
            HTML snippet:
            {truncated_html}
            
            Return JSON with these exact keys:
            {{
                "page_type": "search_page|results_page|property_card|deed_page|error_page",
                "available_actions": ["action1", "action2"],
                "recommended_action": "specific_next_step",
                "form_fields": ["field1", "field2"],
                "buttons": ["button1", "button2"],
                "links": ["link1", "link2"],
                "issues": ["issue1", "issue2"],
                "confidence": 0.8
            }}
            
            Look for: TMS input fields, search buttons, property cards, deed links, error messages.
            """
            
            response_text = self._call_llm_with_fallback(prompt, system_instruction)
            
            try:
                result = json.loads(response_text)
                logger.info(f"Analyzed page content for goal: {search_goal}")
                return result
            except json.JSONDecodeError:
                logger.warning("LLM response was not valid JSON, using fallback analysis")
                return self._get_fallback_page_analysis()
                
        except Exception as e:
            logger.error(f"Failed to analyze page content: {e}")
            return self._get_fallback_page_analysis(error=str(e))
    
    def _get_fallback_page_analysis(self, error: str = None) -> Dict:
        """Return fallback page analysis when LLM fails"""
        return {
            "page_type": "unknown",
            "available_actions": ["continue_with_automation"],
            "recommended_action": "proceed_with_fallback",
            "form_fields": [],
            "buttons": [],
            "links": [],
            "issues": ["llm_unavailable"],
            "confidence": 0.3,
            "fallback": True,
            "error": error
        }
    
    def generate_error_recovery_plan(self, error_context: Dict) -> Dict:
        """Generate error recovery plan based on current state"""
        try:
            system_instruction = """
            You are an expert in web automation error recovery.
            Analyze errors and provide actionable recovery plans for Charleston County automation.
            Always return valid JSON.
            """
            
            prompt = f"""
            Generate error recovery plan for Charleston County automation error:
            
            Error Context: {json.dumps(error_context, indent=2)}
            
            Return JSON with these exact keys:
            {{
                "root_cause": "likely_cause_of_error",
                "recovery_plan": "plan_name",
                "immediate_steps": ["step1", "step2"],
                "alternative_approaches": ["approach1", "approach2"],
                "prevention_strategies": ["strategy1", "strategy2"],
                "retry_recommended": true,
                "max_retries": 3,
                "escalation_needed": false
            }}
            
            Consider: network issues, element not found, captcha, rate limiting, server errors.
            """
            
            response_text = self._call_llm_with_fallback(prompt, system_instruction)
            
            try:
                result = json.loads(response_text)
                logger.info("Generated error recovery plan")
                return result
            except json.JSONDecodeError:
                logger.warning("LLM response was not valid JSON, using fallback recovery")
                return self._get_fallback_recovery_plan()
                
        except Exception as e:
            logger.error(f"Failed to generate recovery plan: {e}")
            return self._get_fallback_recovery_plan(error=str(e))
    
    def _get_fallback_recovery_plan(self, error: str = None) -> Dict:
        """Return fallback recovery plan when LLM fails"""
        return {
            "root_cause": "unknown_error",
            "recovery_plan": "generic_retry",
            "immediate_steps": ["refresh_page", "retry_element_detection", "use_alternative_selectors"],
            "alternative_approaches": ["manual_intervention", "skip_step"],
            "prevention_strategies": ["add_longer_waits", "improve_element_detection"],
            "retry_recommended": True,
            "max_retries": 3,
            "escalation_needed": False,
            "fallback": True,
            "error": error
        }
    
    
    def extract_deed_references(self, extraction_prompt: str) -> List[Dict]:
        """Extract deed book and page references from property page content"""
        try:
            logger.info("Extracting deed references from property page")
            
            # First, check for Sales History table format
            if "<table" in extraction_prompt and "Sales History" in extraction_prompt:
                logger.info("Detected Sales History table format")
                sales_history_refs = self.extract_sales_history_table(extraction_prompt)
                if sales_history_refs:
                    logger.info(f"Successfully extracted {len(sales_history_refs)} deed references from Sales History table")
                    return sales_history_refs
                    
            # Then try other table formats
            elif "<table" in extraction_prompt and "ui-table" in extraction_prompt:
                logger.info("Detected HTML table format, attempting table-based extraction")
                table_refs = self.extract_deed_references_from_table(extraction_prompt)
                if table_refs:
                    logger.info(f"Successfully extracted {len(table_refs)} deed references from table")
                    return table_refs
                else:
                    logger.info("Table extraction failed or found no references, falling back to LLM extraction")
            
            # If table extraction failed or wasn't applicable, use LLM extraction
            system_instruction = """
            You are an expert in extracting deed references from Charleston County property records.
            Look for deed book and page numbers in various formats.
            Always return valid JSON array with properly formatted book and page numbers.
            """
            
            prompt = f"""
            Extract all deed book and page references from this property information:
            
            {extraction_prompt[:15000]}  # Limit prompt size for API limits
            
            Return JSON array with this exact format:
            [
                {{"book": "book_number", "page": "page_number", "confidence": 0.9, "year": "year if available"}},
                {{"book": "book_number", "page": "page_number", "confidence": 0.8, "year": "year if available"}}
            ]
            
            SPECIFIC REQUIREMENTS:
            1. Focus on books starting with letters (like A280) or 280+ (1997-present)
            2. Format page numbers as 3 digits (e.g., "013" for page 13)
            3. Look for patterns like:
               - Book 1234 Page 567
               - Bk 1234 Pg 567  
               - DB 1234 PG 567
               - 1234/567
               - Book A285 Page 123
            4. Include transaction year if available
            5. Sort by highest confidence first
            6. Assign confidence scores based on pattern clarity:
               - Full "Book X Page Y" pattern: 0.95
               - Other clear patterns: 0.85
               - Partial/ambiguous matches: 0.7
            7. Filter out unlikely references (below 0.6 confidence)
            8. Look especially for HTML table cells with book and page numbers
            
            Return empty array if no deed references found.
            """
            
            response_text = self._call_llm_with_fallback(prompt, system_instruction)
            
            try:
                deed_refs = json.loads(response_text)
                if isinstance(deed_refs, list):
                    # Apply additional filtering and validation
                    validated_refs = []
                    for ref in deed_refs:
                        if not ref.get("book") or not ref.get("page"):
                            continue
                        
                        # Ensure page is properly formatted as 3 digits
                        ref["page"] = ref["page"].zfill(3) if ref["page"].isdigit() else ref["page"]
                        
                        # Add extraction source
                        ref["extracted_by"] = "gemini_llm"
                        
                        validated_refs.append(ref)
                    
                    logger.info(f"Extracted {len(validated_refs)} deed references")
                    return validated_refs
                else:
                    logger.warning("LLM response was not a JSON array")
                    return []
            except json.JSONDecodeError:
                logger.warning("LLM response was not valid JSON, using fallback deed extraction")
                return self._extract_deed_references_fallback(extraction_prompt)
                
        except Exception as e:
            logger.error(f"Failed to extract deed references: {e}")
            return []
    
    def _extract_deed_references_fallback(self, content: str) -> List[Dict]:
        """Fallback deed reference extraction using regex patterns"""
        import re
        
        deed_refs = []
        
        # Common deed reference patterns
        patterns = [
            # Standard format
            r'Book\s+([A-Z]?\d+)\s+Page\s+(\d+)(?:.*?(\d{4}))?',
            # Abbreviated format
            r'Bk\.?\s+([A-Z]?\d+)\s+Pg\.?\s+(\d+)(?:.*?(\d{4}))?',
            # DB format
            r'DB\s+([A-Z]?\d+)\s+PG\s+(\d+)(?:.*?(\d{4}))?',
            # Slash format
            r'(\d+)/(\d+)(?:.*?(\d{4}))?',
            # Alpha-numeric book format
            r'Book\s+([A-Z]\d+)\s+Page\s+(\d+)(?:.*?(\d{4}))?',
            # Simple number pattern near transaction text
            r'(?:transaction|sale|deed|conveyance).*?(\d{3,4}).*?(\d{1,3})(?:.*?(\d{4}))?',
            # Table cell format (common in Charleston records)
            r'<td[^>]*>([A-Z]?\d{3,4})</td>.*?<td[^>]*>(\d{1,3})</td>(?:.*?<td[^>]*>(\d{4})</td>)?'
        ]
        
        confidence_scores = {
            0: 0.9,  # Standard format
            1: 0.85, # Abbreviated format
            2: 0.85, # DB format
            3: 0.7,  # Slash format
            4: 0.9,  # Alpha-numeric book format
            5: 0.6,  # Simple number pattern
            6: 0.8   # Table cell format
        }
        
        for i, pattern in enumerate(patterns):
            matches = re.finditer(pattern, content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                book = match.group(1)
                page = match.group(2).zfill(3)  # Ensure 3-digit page format
                year = match.group(3) if len(match.groups()) > 2 and match.group(3) else None
                
                # Skip implausible page numbers
                if len(page) > 5 or (page.isdigit() and int(page) > 999):
                    continue
                    
                # Check if book is relevant (starts with letter or ≥ 280)
                is_relevant = False
                if book and (book[0].isalpha() or (book.isdigit() and int(book) >= 280)):
                    is_relevant = True
                
                if is_relevant:
                    deed_ref = {
                        "book": book,
                        "page": page,
                        "confidence": confidence_scores.get(i, 0.7),
                        "extracted_by": "regex_fallback"
                    }
                    
                    if year and 1900 <= int(year) <= 2100:
                        deed_ref["year"] = year
                        
                    deed_refs.append(deed_ref)
        
        # Remove duplicates
        unique_refs = []
        seen = set()
        for ref in deed_refs:
            key = (ref["book"], ref["page"])
            if key not in seen:
                seen.add(key)
                unique_refs.append(ref)
        
        # Sort by confidence (highest first)
        unique_refs.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        
        logger.info(f"Fallback extraction found {len(unique_refs)} deed references")
        return unique_refs
    
    def extract_deed_references_from_table(self, html_content: str) -> List[Dict]:
        """
        Extract deed book and page references from HTML table format
        
        This is specialized for the table format seen on the Charleston County property search results
        where deed information is presented in a structured table with Book, Page, Date, Grantor, Grantee columns
        """
        import re
        from bs4 import BeautifulSoup
        
        logger.info("Extracting deed references from property page table format")
        
        try:
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find tables with the specific class for deed references
            tables = soup.find_all('table', class_='ui-widget-content ui-table')
            
            if not tables:
                logger.warning("No tables found with class 'ui-widget-content ui-table'")
                # Try alternative approach - find any table with Book and Page columns
                tables = []
                all_tables = soup.find_all('table')
                for table in all_tables:
                    headers = table.find_all('th')
                    header_texts = [h.text.strip() for h in headers]
                    if 'Book' in header_texts and 'Page' in header_texts:
                        tables.append(table)
                
                if not tables:
                    logger.warning("No tables found with Book and Page columns")
                    return []
            
            deed_references = []
            
            for table in tables:
                rows = table.find_all('tr')
                
                # Skip header row
                for row in rows[1:]:
                    cells = row.find_all('td')
                    if len(cells) >= 8:  # Expecting at least Book, Page, Date, Grantor, Grantee columns
                        # Extract book number (cell 0)
                        book = cells[0].text.strip()
                        # Extract page number (cell 1)
                        page = cells[1].text.strip()
                        # Extract date if available (cell 2)
                        date_text = cells[2].text.strip() if len(cells) > 2 else ""
                        # Extract grantor if available (cell 3)
                        grantor = cells[3].text.strip() if len(cells) > 3 else ""
                        # Extract grantee if available (cell 4)
                        grantee = cells[4].text.strip() if len(cells) > 4 else ""
                        # Extract deed price if available (cell 7)
                        price_text = cells[7].text.strip() if len(cells) > 7 else ""
                        
                        # Clean up book and page numbers
                        book = re.sub(r'\s+', '', book)  # Remove all whitespace
                        page = re.sub(r'\s+', '', page)  # Remove all whitespace
                        
                        # Format page as 3 digits
                        if page.isdigit():
                            page = page.zfill(3)
                        
                        # Extract year from date if available
                        year = None
                        if date_text:
                            date_match = re.search(r'(\d{4})', date_text)
                            if date_match:
                                year = date_match.group(1)
                        
                        # Extract price if available
                        price = None
                        if price_text:
                            price_match = re.search(r'[\$]?([0-9,]+)', price_text)
                            if price_match:
                                price = price_match.group(1).replace(',', '')
                        
                        # Add to references if both book and page are valid
                        if book and page:
                            deed_reference = {
                                "book": book,
                                "page": page,
                                "confidence": 0.99,  # High confidence for structured table data
                                "extracted_by": "table_parser",
                            }
                            
                            if year:
                                deed_reference["year"] = year
                            
                            if grantor:
                                deed_reference["grantor"] = grantor
                            
                            if grantee:
                                deed_reference["grantee"] = grantee
                            
                            if price:
                                deed_reference["price"] = price
                                
                            deed_references.append(deed_reference)
            
            logger.info(f"Extracted {len(deed_references)} deed references from table format")
            return deed_references
            
        except Exception as e:
            logger.error(f"Failed to extract deed references from table: {e}")
            return []
    
    def extract_sales_history_table(self, html_content: str) -> List[Dict]:
        """
        Extract deed information specifically from Sales History tables
        
        This is specialized for the Sales History tables that have the format:
        Book | Page | Date | Grantor | Grantee | Type | Deed | Deed Price
        
        Args:
            html_content: HTML string containing the Sales History table
            
        Returns:
            List of deed reference dictionaries
        """
        import re
        from bs4 import BeautifulSoup
        
        logger.info("Extracting Sales History table data")
        
        try:
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find tables with the specific class or structure
            tables = soup.find_all('table', class_='ui-widget-content ui-table')
            
            if not tables:
                logger.warning("No Sales History tables found with expected class")
                # Try to find by header content instead
                all_tables = soup.find_all('table')
                for table in all_tables:
                    headers = table.find_all('th')
                    header_texts = [h.text.strip() for h in headers]
                    if 'Book' in header_texts and 'Page' in header_texts and 'Date' in header_texts:
                        tables.append(table)
                        logger.info("Found Sales History table by header content")
            
            if not tables:
                logger.warning("No Sales History tables found")
                return []
            
            deed_references = []
            processed_rows = 0
            
            for table in tables:
                rows = table.find_all('tr')
                
                # Skip header row
                data_rows = rows[1:] if len(rows) > 0 else []
                
                for row in data_rows:
                    cells = row.find_all('td')
                    if len(cells) >= 8:  # Complete row with all expected columns
                        # Extract all relevant data
                        book = cells[0].text.strip()
                        page = cells[1].text.strip()
                        date_text = cells[2].text.strip()
                        grantor = cells[3].text.strip()
                        grantee = cells[4].text.strip()
                        deed_type_cell = cells[6].text.strip() if len(cells) > 6 else ""
                        price_text = cells[7].text.strip() if len(cells) > 7 else ""
                        
                        # Clean and format data
                        book = re.sub(r'\s+', '', book)
                        page = re.sub(r'\s+', '', page)
                        
                        # Format page as 3 digits
                        if page.isdigit():
                            page = page.zfill(3)
                        
                        # Extract year from date
                        year = None
                        if date_text:
                            date_match = re.search(r'(\d{1,2}/\d{1,2}/)?(\d{4})', date_text)
                            if date_match:
                                year = date_match.group(2)
                        
                        # Extract price
                        price = None
                        if price_text:
                            price_match = re.search(r'[\$]?([0-9,]+)', price_text)
                            if price_match:
                                price = price_match.group(1).replace(',', '')
                        
                        # Extract deed type
                        deed_type = None
                        if deed_type_cell:
                            # Common abbreviations in Charleston County
                            deed_types = {
                                "Ge": "General Warranty Deed",
                                "Sp": "Special Warranty Deed", 
                                "Qu": "Quitclaim Deed",
                                "Ta": "Tax Deed",
                                "Fo": "Foreclosure Deed",
                                "Pr": "Probate Deed"
                            }
                            for abbr, full_type in deed_types.items():
                                if abbr in deed_type_cell:
                                    deed_type = full_type
                                    break
                        
                        # Create reference if both book and page are valid
                        if book and page:
                            deed_reference = {
                                "book": book,
                                "page": page,
                                "confidence": 0.99,  # High confidence for table data
                                "extracted_by": "sales_history_parser",
                                "source": "sales_history_table",
                            }
                            
                            if year:
                                deed_reference["year"] = year
                            
                            if date_text:
                                deed_reference["date"] = date_text
                                
                            if grantor:
                                deed_reference["grantor"] = grantor
                            
                            if grantee:
                                deed_reference["grantee"] = grantee
                            
                            if price:
                                deed_reference["price"] = price
                                
                            if deed_type:
                                deed_reference["deed_type"] = deed_type
                                
                            deed_references.append(deed_reference)
                            processed_rows += 1
            
            logger.info(f"Extracted {len(deed_references)} deed references from Sales History table ({processed_rows} rows processed)")
            return deed_references
            
        except Exception as e:
            logger.error(f"Failed to extract Sales History table data: {e}")
            return []
    
    def process_deed_batches(self, html_content: str, collected_deeds: List[Dict] = None) -> Dict:
        """
        Process deed references from HTML table into batches and track collection status
        
        This method extracts deed references from a Sales History table, compares with
        already collected deeds, and organizes the remaining deeds into batches for
        efficient collection with proper state tracking.
        
        Args:
            html_content: HTML content containing the deed table
            collected_deeds: List of deeds already collected (book/page pairs)
            
        Returns:
            Dict with keys:
                - deed_references: All extracted deed references
                - pending_deeds: Deeds not yet collected
                - collection_status: Status of each deed (collected/pending)
                - total_count: Total number of deeds found
                - collected_count: Number of deeds already collected
                - pending_count: Number of deeds still pending collection
        """
        logger.info("Processing deed batches from HTML table")
        
        # Extract all deed references from the table
        all_deed_refs = self.extract_deed_references_from_table(html_content)
        
        # Initialize tracking collections
        collected_set = set()
        if collected_deeds:
            for deed in collected_deeds:
                key = (deed.get('book', ''), deed.get('page', ''))
                collected_set.add(key)
        
        # Separate deeds into collected vs pending
        pending_deeds = []
        collection_status = {}
        
        for ref in all_deed_refs:
            book = ref.get('book', '')
            page = ref.get('page', '')
            key = (book, page)
            
            # Track status of each deed
            if key in collected_set:
                collection_status[f"DB {book} {page}"] = "collected"
            else:
                collection_status[f"DB {book} {page}"] = "pending"
                pending_deeds.append(ref)
        
        result = {
            "deed_references": all_deed_refs,
            "pending_deeds": pending_deeds,
            "collection_status": collection_status,
            "total_count": len(all_deed_refs),
            "collected_count": len(all_deed_refs) - len(pending_deeds),
            "pending_count": len(pending_deeds)
        }
        
        logger.info(f"Found {result['total_count']} total deeds, {result['collected_count']} already collected, {result['pending_count']} pending collection")
        return result
    
    def create_deed_collection_plan(self, deed_references: List[Dict], batch_size: int = 5) -> Dict:
        """
        Create a structured collection plan for deed references
        
        Args:
            deed_references: List of deed reference dictionaries with book/page
            batch_size: Number of deeds to process in each batch
            
        Returns:
            Dict with collection plan information
        """
        # Organize references into batches
        batches = []
        current_batch = []
        
        for i, ref in enumerate(deed_references):
            current_batch.append(ref)
            if len(current_batch) >= batch_size or i == len(deed_references) - 1:
                batches.append(current_batch)
                current_batch = []
        
        # Create collection plan
        collection_plan = {
            "total_deeds": len(deed_references),
            "total_batches": len(batches),
            "batch_size": batch_size,
            "batches": batches,
            "estimated_time_minutes": len(deed_references) * 2,  # Estimate 2 minutes per deed
            "created_at": datetime.now().isoformat()
        }
        
        logger.info(f"Created deed collection plan with {collection_plan['total_batches']} batches for {collection_plan['total_deeds']} deeds")
        return collection_plan
    
    def prioritize_deed_collection(self, deed_references: List[Dict], 
                             collected_deeds: List[Dict] = None,
                             max_priority_count: int = 5) -> Dict:
        """
        Prioritize deed references for collection based on various factors
        
        This method helps determine which deeds should be collected next based on:
        - Already collected deeds (to avoid duplication)
        - Recent deeds (newer dates/higher book numbers)
        - Complete deed information (with grantor, grantee, price)
        
        Args:
            deed_references: List of all deed references
            collected_deeds: List of already collected deed references
            max_priority_count: Maximum number of priority deeds to return
            
        Returns:
            Dict with prioritized collection information
        """
        if not deed_references:
            return {
                "priority_deeds": [],
                "remaining_deeds": [],
                "already_collected": [],
                "total_deeds": 0,
                "priority_count": 0,
                "remaining_count": 0,
                "collected_count": 0
            }
        
        # Create a set of already collected book/page combinations
        collected_keys = set()
        if collected_deeds:
            for deed in collected_deeds:
                key = (deed.get('book', ''), deed.get('page', ''))
                collected_keys.add(key)
        
        # Separate uncollected deeds
        uncollected_deeds = []
        already_collected = []
        
        for deed in deed_references:
            key = (deed.get('book', ''), deed.get('page', ''))
            if key in collected_keys:
                already_collected.append(deed)
            else:
                uncollected_deeds.append(deed)
        
        # Sort uncollected deeds by priority factors:
        # 1. More recent deeds first (higher year)
        # 2. Otherwise, higher book number first
        
        def get_sort_key(deed):
            # Try to get year first
            year = deed.get('year', '0000')
            
            # Get numeric book value for sorting
            book = deed.get('book', '')
            numeric_book = 0
            if book:
                if book[0].isalpha():
                    # For alpha-numeric books like F226, sort alphabetically first
                    alpha = book[0].upper()
                    numeric_part = ''.join(c for c in book[1:] if c.isdigit())
                    numeric_book = ord(alpha) * 10000 + (int(numeric_part) if numeric_part.isdigit() else 0)
                else:
                    numeric_book = int(book) if book.isdigit() else 0
                    
            return (year, numeric_book)
                
        # Sort deeds by priority
        uncollected_deeds.sort(key=get_sort_key, reverse=True)
        
        # Select priority deeds
        priority_deeds = uncollected_deeds[:max_priority_count]
        remaining_deeds = uncollected_deeds[max_priority_count:]
        
        result = {
            "priority_deeds": priority_deeds,
            "remaining_deeds": remaining_deeds,
            "already_collected": already_collected,
            "total_deeds": len(deed_references),
            "priority_count": len(priority_deeds),
            "remaining_count": len(remaining_deeds),
            "collected_count": len(already_collected)
        }
        
        logger.info(f"Prioritized {result['priority_count']} deeds for immediate collection, " 
                   f"{result['remaining_count']} remaining, {result['collected_count']} already collected")
        
        return result
    
    def get_phase_instructions(self, phase: str, context: Dict = None) -> Dict:
        """
        Get workflow phase instructions from Gemini 2.0
        
        Args:
            phase: Workflow phase name (e.g., "search_form", "extract_deed")
            context: Optional context for improved instructions
            
        Returns:
            Dict: Instructions for the workflow phase
        """
        try:
            system_instruction = """You are an AI assistant specialized in Charleston County property records workflow.
            Provide detailed instructions for each workflow phase. Be clear, concise, and specific."""
            
            prompt = f"""
            Generate detailed instructions for the Charleston County workflow phase: '{phase}'
            
            Context about this phase: {json.dumps(context) if context else "No additional context"}
            
            Return structured JSON with:
            1. step_by_step_instructions: Array of action steps
            2. expected_selectors: HTML/CSS selectors to target
            3. error_handling: How to handle common issues
            4. success_criteria: How to determine if the phase completed successfully
            """
            
            response = self._call_gemini(prompt, system_instruction)
            
            # Parse the response and extract JSON
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                try:
                    return json.loads(json_str)
                except:
                    # If JSON parsing fails, return the text
                    return {
                        "step_by_step_instructions": [response],
                        "raw_response": response
                    }
            else:
                return {
                    "step_by_step_instructions": [response],
                    "raw_response": response
                }
            
        except Exception as e:
            logger.error(f"Failed to get phase instructions from Gemini: {e}")
            return {"error": str(e)}
    
    def get_phase_instructions_groq(self, phase: str, context: Dict = None) -> Dict:
        """
        Get workflow phase instructions from Groq LLM (fallback)
        
        Args:
            phase: Workflow phase name (e.g., "search_form", "extract_deed")
            context: Optional context for improved instructions
            
        Returns:
            Dict: Instructions for the workflow phase
        """
        try:
            if not self.groq_client:
                raise ValueError("Groq client not initialized")
            
            system_message = """You are an AI assistant specialized in Charleston County property records workflow.
            Provide detailed instructions for each workflow phase. Be clear, concise, and specific."""
            
            user_message = f"""
            Generate detailed instructions for the Charleston County workflow phase: '{phase}'
            
            Context about this phase: {json.dumps(context) if context else "No additional context"}
            
            Include:
            - Direct instructions for this specific phase
            - Common challenges and solutions
            - Best practices for this phase
            - URLs to use (if applicable)
            - Next steps after this phase
            
            Return your instructions in clear, action-oriented steps.
            """
            
            # Call Groq API
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]
            
            completion = self.groq_client.chat.completions.create(
                model="deepseek-r1-distill-llama-70b",
                messages=messages,
                temperature=0.3,
                max_tokens=1024
            )
            
            response_text = completion.choices[0].message.content
            
            # Package the response
            result = {
                "phase": phase,
                "instructions": response_text,
                "generated_by": "groq",
                "generated_at": datetime.now().isoformat()
            }
            
            logger.info(f"Generated phase instructions via Groq fallback: {phase}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get phase instructions from Groq: {e}")
            
            # Return basic fallback instructions
            return {
                "phase": phase,
                "instructions": f"Navigate to https://www.charlestoncounty.org/departments/rod/ds-DMBookandPage.php to search for deeds by book and page number. For phase '{phase}', follow the standard workflow steps.",
                "generated_by": "fallback",
                "generated_at": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def generate_deed_collection_workflow(self, tms_number: str, 
                                    deed_references: List[Dict], 
                                    collected_deeds: List[Dict] = None) -> Dict:
        """
        Generate structured deed collection workflow guidance
        
        This method creates a comprehensive workflow plan for collecting all deeds
        from a Sales History table, including tracking of collection state and full
        looping process to navigate back and continue after each deed download.
        
        Args:
            tms_number: Property TMS number
            deed_references: List of all deed references to collect
            collected_deeds: List of already collected deeds
            
        Returns:
            Dict with full workflow guidance
        """
        try:
            # Prioritize deeds for collection
            prioritized = self.prioritize_deed_collection(deed_references, collected_deeds)
            
            # Create collection batches
            collection_plan = self.create_deed_collection_plan(
                prioritized.get("priority_deeds", []) + prioritized.get("remaining_deeds", [])
            )
            
            # Generate collection workflow
            workflow = {
                "tms_number": tms_number,
                "workflow_name": "deed_collection_workflow",
                "deed_references": deed_references,
                "collection_plan": collection_plan,
                "prioritized_deeds": prioritized,
                "steps": [
                    {
                        "name": "navigate_to_register_of_deeds",
                        "description": "Navigate to Charleston County Register of Deeds",
                        "url": "https://www.charlestoncounty.org/departments/rod/ds-DMBookandPage.php",
                        "success_criteria": "Book and Page search form is visible",
                        "retry_attempts": 3
                    },
                    {
                        "name": "deed_collection_loop",
                        "description": "Collect each deed in sequence",
                        "deeds_to_collect": collection_plan["total_deeds"],
                        "success_criteria": "All deeds downloaded",
                        "looping_strategy": "process_each_deed_then_return_to_search"
                    },
                    {
                        "name": "verify_collection",
                        "description": "Verify all deeds were collected successfully",
                        "success_criteria": "All deed files exist in folder",
                        "verification_method": "check_files_and_database"
                    }
                ],
                "collection_instructions": [
                    "For each deed, navigate to Register of Deeds Book & Page search",
                    "Enter book number (e.g., '1247') in the Book field",
                    "Enter page number (e.g., '453') in the Page field",
                    "Check the legal disclaimer checkbox",
                    "Click the Search button",
                    "On results page, click View button to open/download deed",
                    "Save PDF as 'DB {book} {page}.pdf' in the correct folder",
                    "Navigate BACK to the search form",
                    "Repeat for next deed until all collected"
                ],
                "navigation_back_strategies": [
                    "Close any new tabs/windows that opened during deed view",
                    "Use browser back button to return to search form",
                    "If needed, navigate directly to https://www.charlestoncounty.org/departments/rod/ds-DMBookandPage.php",
                    "Verify search form is visible before proceeding to next deed"
                ],
                "error_handling": [
                    "If deed is not found, log the issue and continue to next deed",
                    "If search form can't be reached, try direct URL navigation",
                    "If PDF can't be downloaded, try print-to-PDF as alternative",
                    "Track all attempted and successful downloads to avoid duplication"
                ]
            }
            
            # Generate collection sequence with field values for each deed
            collection_sequence = []
            
            # Combine priority and remaining deeds
            all_uncollected = (prioritized.get("priority_deeds", []) + 
                              prioritized.get("remaining_deeds", []))
            
            # Create sequence for each deed
            for i, deed in enumerate(all_uncollected):
                book = deed.get("book", "")
                page = deed.get("page", "")
                filename = f"DB {book} {page}"
                
                sequence_item = {
                    "sequence_number": i + 1,
                    "book": book,
                    "page": page,
                    "filename": filename,
                    "search_values": {
                        "book_field": book,
                        "page_field": page.lstrip("0") if page.isdigit() else page
                    },
                    "year": deed.get("year", "Unknown"),
                    "priority": i < len(prioritized.get("priority_deeds", [])),
                    "grantor": deed.get("grantor", ""),
                    "grantee": deed.get("grantee", ""),
                }
                
                collection_sequence.append(sequence_item)
                
            workflow["collection_sequence"] = collection_sequence
                
            logger.info(f"Generated deed collection workflow for {len(collection_sequence)} deeds")
            return workflow
            
        except Exception as e:
            logger.error(f"Failed to generate deed collection workflow: {e}")
            return {
                "error": str(e),
                "tms_number": tms_number,
                "deed_count": len(deed_references) if deed_references else 0,
                "fallback_instructions": [
                    "Navigate to Register of Deeds Book & Page search",
                    "Process each deed individually",
                    "Return to search form after each deed"
                ]
            }
    
    def generate_deed_collection_workflow(self, tms_number: str, deed_references: List[Dict], 
                                     collected_deeds: List[Dict] = None) -> Dict:
        """
        Generate an optimized workflow for collecting deed documents
        
        Args:
            tms_number: Property TMS number
            deed_references: List of all deed references to collect
            collected_deeds: List of already collected deeds
            
        Returns:
            Dict with optimized workflow plan
        """
        import time
        
        # First prioritize the deeds based on importance
        prioritized = self.prioritize_deed_collection(deed_references, collected_deeds)
        
        # Combine priority and remaining deeds for the full collection sequence
        all_deeds_to_collect = prioritized["priority_deeds"] + prioritized["remaining_deeds"]
        
        # Create the workflow plan
        workflow = {
            "tms_number": tms_number,
            "total_deeds": len(deed_references),
            "deeds_to_collect": len(all_deeds_to_collect),
            "deeds_already_collected": prioritized["collected_count"],
            "collection_sequence": all_deeds_to_collect,
            "estimated_time_minutes": len(all_deeds_to_collect) * 2,  # Estimate 2 min per deed
            "direct_url": "https://www.charlestoncounty.org/departments/rod/ds-DMBookandPage.php",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "workflow_steps": []
        }
        
        # Generate optimized workflow steps for each deed
        for i, deed in enumerate(all_deeds_to_collect):
            book = deed.get('book', '')
            page = deed.get('page', '')
            
            # Format book and page numbers according to Charleston County rules
            formatted_book = book
            if book.isdigit():
                formatted_book = book.zfill(4)  # Ensure 4 digits for numeric books
                
            formatted_page = page
            if page.isdigit():
                formatted_page = page.zfill(3)  # Ensure 3 digits
                
            step = {
                "step_number": i + 1,
                "deed_reference": f"Book {formatted_book} Page {formatted_page}",
                "book": formatted_book,
                "page": formatted_page,
                "actions": [
                    {
                        "name": "navigate_to_register_of_deeds",
                        "url": workflow["direct_url"],
                        "params": {}
                    },
                    {
                        "name": "search_deed_by_book_page",
                        "params": {
                            "book": formatted_book,
                            "page": formatted_page
                        }
                    },
                    {
                        "name": "download_deed_pdf",
                        "params": {
                            "filename": f"DB {book} {page}",
                            "tms": tms_number
                        }
                    }
                ],
                "fallbacks": [
                    {
                        "condition": "element_not_found",
                        "action": "retry_with_alternate_selectors"
                    },
                    {
                        "condition": "download_failed",
                        "action": "refresh_and_retry"
                    }
                ]
            }
            
            workflow["workflow_steps"].append(step)
            
        logger.info(f"Generated optimized workflow for {len(workflow['workflow_steps'])} deeds")
        return workflow
