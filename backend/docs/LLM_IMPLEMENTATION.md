# LLM Implementation Details

This document provides an in-depth explanation of how Large Language Models (LLMs) are implemented in the Real Estate Document Collection System.

## Architecture Overview

The system implements a multi-model LLM approach with intelligent fallback mechanisms to ensure high availability, reliability, and performance for all AI-powered features.

## GeminiService Class

The core of the LLM implementation is the `GeminiService` class located in `src/services/gemini_service.py`. This service:

1. Provides a unified interface for all LLM operations
2. Implements an intelligent cascading fallback pattern
3. Handles errors gracefully with fallback mechanisms

### Initialization

```python
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
```

## LLM Models Used

### Primary Model: Google Gemini 2.0

- **Model ID**: `gemini-2.0-flash-exp`
- **Features**:
  - Fast response times
  - Good understanding of property-related concepts
  - Structuring output according to expected JSON formats
- **Used For**: All primary LLM tasks including page analysis, query parsing, and strategy generation

### First Fallback: Groq with DeepSeek

- **Model ID**: `deepseek-r1-distill-llama-70b`
- **Features**:
  - High reliability
  - Different infrastructure than Google for fault tolerance
- **Used For**: All tasks when Gemini is unavailable

### Second Fallback: DeepSeek via Groq

- **Model ID**: `deepseek-r1-distill-llama-70b`
- **Used For**: Last resort when both Gemini and Groq fail

## Cascading Fallback Pattern

The system employs an intelligent cascading fallback pattern:

```python
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
```

## Key LLM Tasks

### 1. Property Search Query Parsing

```python
def parse_property_search_query(self, user_query: str) -> Dict:
    """Parse user query to extract TMS number and search intent"""
```

- Extracts TMS numbers, addresses, and owner names from user queries
- Formats TMS numbers according to county requirements
- Returns structured JSON with confidence scores

### 2. Search Strategy Generation

```python
def generate_search_strategy(self, tms_number: str, context: Dict = None) -> Dict:
    """Generate search strategy for Charleston County automation"""
```

- Creates step-by-step search plans customized for each county
- Anticipates potential challenges and provides fallback strategies
- Optimizes for expected document types

### 3. Page Content Analysis

```python
def analyze_page_content(self, page_html: str, search_goal: str) -> Dict:
    """Analyze webpage content to determine next actions"""
```

- Identifies important page elements like forms, buttons, and links
- Detects errors and validation messages
- Recommends specific next actions

### 4. Error Recovery Planning

```python
def generate_error_recovery_plan(self, error_context: Dict) -> Dict:
    """Generate error recovery plan based on current state"""
```

- Analyzes error conditions and context
- Provides specific recovery steps
- Suggests preventative measures for future runs

### 5. Deed Reference Extraction

```python
def extract_deed_references(self, extraction_prompt: str) -> List[Dict]:
    """Extract deed book and page references from property page content"""
```

- Extracts book/page references for deed documents
- Parses HTML tables for structured data
- Provides fallback extraction using regex patterns

## Integration with LangGraph

The LLM service is tightly integrated with LangGraph for workflow orchestration:

```python
@traceable(name="initialize_search")
async def initialize_search(self, state: WorkflowState) -> WorkflowState:
    """Initialize the search workflow using LLM query parsing and TMS formatting"""
    
    llm_instructions = f"""
    Parse and prepare this TMS number for Charleston County property search: {state['tms_number']}
    
    Requirements:
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
```

## Performance Considerations

- **Caching**: Common LLM responses are cached to reduce API calls
- **Token Optimization**: Prompts are designed to minimize token usage
- **Error Handling**: Comprehensive error handling with automatic retries
- **Fallback Responses**: Predefined fallback responses ensure the system remains operational even if all LLM services fail

## Configuration and API Keys

LLM services require API keys configured in the `.env` file:

```
# AI Service Configuration
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key
```
