# Agent-based Real Estate Document Collection

![Property Document Collection System](https://img.shields.io/badge/Status-Complete-brightgreen)

This project demonstrates an AI agent that automates the collection of property documents from county websites, specifically targeting Charleston County and Berkeley County in South Carolina. The system uses advanced browser automation and AI techniques to navigate complex websites, extract data, and organize documents - all based on simple TMS/parcel number inputs.

- **Frontend**: User interface for entering TMS numbers and viewing collected documents
- **Backend**: AI agent powering the browser automation and document collection processes

## 📋 Project Overview

The goal is to automate the tedious manual process of collecting property documents from county websites:

- **Property Cards**: Detailed property information and characteristics
- **Tax Information**: Tax bills and receipts 
- **Deed Records**: Historical ownership transfers and deed documents

The system breaks down complex human instructions into automated steps that can be executed by an AI agent, significantly reducing the time required to collect these documents.

## 📼 Demo Video

[Watch the system in action](workflow_demo.mp4)

This demo video shows the system successfully collecting documents from both Charleston and Berkeley County websites, navigating through multiple pages, handling forms, and organizing the results.

## 🧠 LLM Integration

This project leverages multiple LLMs (Large Language Models) with a robust fallback system to ensure reliable operation:

### Primary Model:
- **Google Gemini 2.0**: Used as the primary LLM with the `gemini-2.0-flash-exp` model for all core AI functions, including:
  - Natural language query parsing
  - Website analysis and element identification
  - Search strategy generation
  - Error recovery planning
  - Deed reference extraction and optimization

### Fallback Models:
- **Groq API**: Serves as the first fallback option when Gemini is unavailable, using `deepseek-r1-distill-llama-70b`
- **DeepSeek API**: Acts as a secondary fallback option, also using the `deepseek-r1-distill-llama-70b` model

### Integration Framework:
- **LangGraph**: Used for sophisticated AI workflow orchestration and state management
- **LangSmith**: Provides tracing and observability for the AI workflows

The system implements an intelligent cascading fallback pattern where if the primary LLM fails, it automatically tries the next available model, ensuring robust operation even if one LLM service is experiencing issues.

## 🚀 Features

### AI-Powered Automation
- **Natural Language Instruction Parsing**: Processes step-by-step human instructions
- **Browser Automation**: Navigates websites, fills forms, and downloads documents
- **CAPTCHA Handling**: Solves CAPTCHAs that may appear during navigation
- **Error Recovery**: Adapts to website changes and error conditions

### Document Organization
- **TMS-Based Storage**: All documents organized by TMS/parcel number
- **Structured Naming**: Consistent naming conventions for all document types
- **Deed Reference Extraction**: Automatically extracts and follows deed book/page references

### User Interface
- **Simple Search**: Easy input of TMS numbers by county
- **Real-time Progress**: Live updates of collection progress
- **Document Viewer**: View and download collected documents directly in the interface
- **Deed Book/Page Display**: Organized presentation of deed references and documents

## 📊 Supported Counties

### Charleston County
- Property card collection from Public Access website
- Tax information extraction
- Deed document collection from Register of Deeds
- Book and page reference extraction and following

### Berkeley County
- Property card collection from Berkeley County Property Search
- Tax bill and receipt collection
- Previous owner history extraction
- Deed document collection from Register of Deeds

## 🔧 Technical Architecture

### Frontend
- **HTML/CSS/JavaScript**: Modern, responsive web interface
- **Bootstrap**: UI framework for responsive design
- **Document Viewer**: Built-in PDF preview functionality
- **Real-time Updates**: Asynchronous communication with backend API

### Browser Automation
- **Selenium**: Core browser automation framework
- **undetected-chromedriver**: Enhanced Chrome driver to bypass anti-bot measures
- **Custom stealth techniques**: JavaScript injections to evade detection
- **Screenshot capture**: Automated debugging and error diagnosis
- **Dynamic element locators**: Multiple selector strategies for resilience

### Backend
- **Python**: Core language for backend implementation
- **LangChain/LangGraph**: Agent framework for orchestrating workflows
- **Selenium + undetected-chromedriver**: Browser automation for navigating county websites
- **FastAPI**: REST API for communication with frontend
- **Neo4j**: Knowledge graph for property relationships (optional)

## 💻 Setup and Usage

### Prerequisites
1. Python 3.10+ installed
2. Node.js and npm (for frontend development only)
3. 2CAPTCHA API key (for CAPTCHA solving)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/real-estate-document-collection.git
cd real-estate-document-collection
```

2. Install backend dependencies:
```bash
cd backend
pip install -r requirements.txt
```

3. Configure environment variables in a `.env` file:
```
TWOCAPTCHA_API_KEY=your_api_key
NEO4J_URI=bolt://localhost:7687 (optional)
NEO4J_USER=neo4j (optional)
NEO4J_PASSWORD=password (optional)
```

### Running the Application

1. Start the backend server:
```bash
cd backend
python run_server.py
```

2. Serve the frontend:
```bash
cd frontend
python -m http.server 5000
```

3. Access the application at [http://localhost:5000/](http://localhost:5000/)

## 🧪 Testing

### Test TMS Numbers

#### Charleston County
- 5590200072
- 5321500185
- 5321500197
- 4211400056

#### Berkeley County
- 2340601038
- 1950000124
- 3881300334
- 4631102012
- 3091300118
- 2590502005

## 🎬 Demo Video

[Watch the workflow demo](workflow_demo.mp4) - A detailed walkthrough showing the system in action. The video demonstrates:

1. Property card collection from Charleston County
2. Tax information retrieval
3. Deed document collection with book/page references
4. Berkeley County workflow execution
5. Error handling and screenshot capture
6. Results organization by TMS number

## 📋 Implementation Details

### Charleston County Workflow
1. Navigate to Charleston County online services
2. Access real property record search
3. Enter TMS number and search
4. Access property details page
5. Save property card as PDF
6. Extract deed book and page references
7. Access tax information
8. Save tax information as PDF
9. Navigate to Register of Deeds page
10. Search for each deed by book/page
11. Download and save all deed documents

### Berkeley County Workflow
1. Navigate to Berkeley County Property Search
2. Enter TMS number and retrieve property card
3. Save property card as PDF
4. Extract previous owner history references
5. Navigate to Berkeley County Assessor
6. Search for tax information
7. Save tax bill and tax receipt as PDFs
8. Navigate to Register of Deeds
9. Search for each deed using appropriate book type based on filing date
10. Download and save all deed documents

## 👨‍💻 Development Process

The development of this system involved:

1. **Website Analysis**: Detailed study of county websites and document retrieval processes
2. **Instruction Parsing**: Converting human instructions into actionable steps
3. **Agent Development**: Implementing the AI agent using LangChain/LangGraph
4. **Browser Automation**: Setting up reliable browser automation with Playwright
5. **Error Handling**: Adding recovery mechanisms for various error conditions
6. **Testing & Refinement**: Extensive testing with real TMS numbers

## �️ How It Works

The system utilizes a layered architecture that combines several technologies:

### Architecture
1. **Frontend Layer**: HTML/CSS/JavaScript UI for user interaction
   - Modern, responsive interface using Bootstrap
   - Real-time status updates via API polling
   - Document viewer with PDF and error screenshot display
   
2. **API Layer**: FastAPI backend server
   - RESTful endpoints for workflow management
   - Async task processing for non-blocking operation
   - Document serving and organization
   
3. **Agent Layer**: LangChain/LangGraph orchestration
   - AI agent workflows for decision making
   - Error handling and recovery mechanisms
   - Progress tracking and reporting
   
4. **Automation Layer**: Browser automation with Playwright/Selenium
   - Parallel browser session management
   - State persistence between navigation steps
   - Screenshot capturing for error diagnosis

### Data Flow
1. User enters TMS number and county in the frontend
2. Request is sent to API, which initiates a background workflow
3. AI agent orchestrates browser automation steps
4. Documents are downloaded and organized into county/TMS folders
5. Frontend polls for status updates and displays results
6. Error screenshots are saved when issues occur

## 🤖 Steps Automated

The system automates numerous steps that would normally require manual work:

### 1. Charleston County Workflow
- **Property Search Navigation**
  - Navigate to Charleston County's online services
  - Access property search page
  - Enter TMS/PIN number in search field
  - Submit search and handle any CAPTCHAs
  
- **Property Card Collection**
  - Identify property listing in search results
  - Navigate to property details page
  - Extract property information
  - Save property card as PDF
  
- **Tax Information Collection**
  - Navigate to tax information page
  - Extract tax amounts and payment history
  - Download tax receipts if available
  
- **Deed Collection**
  - Extract deed book/page references from property data
  - Navigate to Register of Deeds website
  - Enter book and page numbers in search form
  - Download deed documents as PDFs
  - Follow reference chains to older deeds if needed

### 2. Berkeley County Workflow
- **Property Search Navigation**
  - Access Berkeley County property search portal
  - Handle any login requirements
  - Enter TMS number in search
  - Process search results page
  
- **Property Data Collection**
  - Navigate through property details tabs
  - Extract ownership history
  - Capture assessment data
  - Download property card
  
- **Deed Reference Collection**
  - Extract deed book/page references
  - Access document search system
  - Request and download deed PDFs

### 3. Error Handling
- **Screenshot Capture**: Automatic saving of screenshots when errors occur
- **Error Classification**: Categorization of error types for reporting
- **Recovery Attempts**: Multiple retry strategies with increasing backoff
- **User Notification**: Clear error reporting in the UI

## 🔜 Improvements and Future Work

The current system works successfully but could benefit from several enhancements:

1. **Enhanced Browser Automation**: Implement more robust browser control with better element selection strategies and waiting mechanisms
2. **Advanced CAPTCHA Handling**: Integrate more sophisticated CAPTCHA solving services with higher success rates
3. **Dynamic Error Recovery**: Add more intelligent error recovery with context-aware retry strategies
4. **Latency Reduction**: Optimize browser automation and parallel processing to reduce overall collection time
5. **Additional Counties**: Expand to support more SC counties and eventually other states
6. **Document OCR**: Extract text from collected PDFs to enable searching
7. **Automated Data Extraction**: Pull key information from documents into structured database
8. **Mobile Support**: Optimize frontend for mobile devices
9. **User Accounts**: Add user authentication and saved searches

## ⏱️ Time Spent

Total development time: **4 days**

- Day 1: Architecture design, backend setup, and initial API implementation
- Day 2: Browser automation development and Charleston County workflow implementation
- Day 3: Berkeley County workflow implementation and error handling
- Day 4: Frontend development, integration testing, and bug fixes

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
