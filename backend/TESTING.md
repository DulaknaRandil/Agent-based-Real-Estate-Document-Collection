# Testing the Real Estate Document Collection System

This guide provides instructions for testing the document collection system for both Charleston County and Berkeley County.

## Prerequisites

1. Ensure all dependencies are installed:
   ```
   pip install -r requirements.txt
   ```

2. Make sure your `.env` file is properly configured with API keys:
   - `TWOCAPTCHA_API_KEY` - Required for solving CAPTCHAs
   - Other API keys as specified in the `.env` file

## Running the Backend Server

1. Start the backend API server:
   ```
   python server.py
   ```

2. The server will be available at http://localhost:8000

## Testing the Frontend

1. Open the frontend in a web browser:
   - Directly open `frontend/index.html` in a browser
   - Or set up a simple HTTP server: `python -m http.server 8080 -d frontend`

2. In the frontend interface:
   - Select a county (Charleston or Berkeley)
   - Enter a valid TMS number from the test table
   - Click "Start Document Collection"
   - Monitor the progress and view collected documents

## Test TMS Numbers

### Charleston County
- 5590200072
- 5321500185
- 5321500197
- 4211400056

### Berkeley County
- 2340601038
- 1950000124
- 3881300334
- 4631102012
- 3091300118
- 2590502005

## API Endpoints

You can test the API endpoints directly using tools like curl, Postman, or directly in the browser:

1. Start a workflow:
   ```
   curl -X POST http://localhost:8000/start-workflow \
     -H "Content-Type: application/json" \
     -d '{"county":"charleston","tms":"5590200072"}'
   ```

2. Check workflow status:
   ```
   curl http://localhost:8000/workflow-status/{task_id}
   ```

3. List available documents:
   ```
   curl http://localhost:8000/documents/charleston/5590200072
   ```

## Troubleshooting

### CAPTCHA Issues
- If CAPTCHA solving fails, ensure your 2captcha API key is valid and has sufficient balance
- Check the logs in `data/logs/` for detailed error information

### Browser Automation Issues
- Ensure Chrome/Chromium is installed on your system
- Check if the sites are accessible from your network (you may need VPN as mentioned in requirements)
- Look for screenshots saved in the data directory when errors occur

### Database Issues
- Ensure you have permission to write to the filesystem
- Check that data directories exist and are writable

## Automated Tests

You can run the automated test suite to verify system functionality:

```bash
# Run all pytest tests
python -m pytest tests/

# Run browser manager test with a single deed
python test_browser_manager.py --book 5590 --page 200 --tms 5590200072

# Run browser manager test in batch mode
python test_browser_manager.py --batch --tms 5590200072

# Run workflow integration test
python test_workflow_integration.py --tms 5590200072

# Run the optimized workflow test
python test_optimized_workflow.py --tms 5590200072
```

## 📊 Test Results

All tests generate detailed logs and results:

- **Logs**: Find detailed logs in `data/logs/` directory
- **Test Reports**: JSON format benchmark and test results in `data/temp/`
- **Downloaded Files**: PDF documents saved in TMS-specific folders under `data/downloads/charleston/`

## 🔍 What the Tests Validate

### Browser Manager Test

- Direct URL navigation to deed search page
- Book/Page field detection and input
- Search button detection and interaction
- Results detection and validation
- View button detection and PDF download

### Workflow Integration Test

- End-to-end workflow from TMS lookup to deed collection
- Neo4j knowledge graph integration
- LLM processing for deed reference extraction
- Document download and storage
- Workflow state tracking

### Optimized Workflow Test

- Comprehensive end-to-end testing of the entire system
- Performance benchmarking for all components
- Streamlined browser automation with improved robustness
- Efficient deed reference extraction and document downloading
- Knowledge graph integration and validation
- Detailed metrics collection and reporting
- Error handling with graceful degradation
- JSON report generation for CI/CD integration

## 📝 Interpreting Benchmark Results

The benchmark results JSON files contain detailed metrics on:

- **Navigation Time**: Time spent on page navigation
- **Deed Search Time**: Time spent searching for deeds
- **Download Time**: Time spent downloading documents
- **Processing Time**: Time spent on AI processing
- **Success Rate**: Percentage of successful operations
- **Token Usage**: LLM token consumption metrics

## 🛠️ Troubleshooting

If tests fail, check:

1. Browser display settings (tests work best with browser visible)
2. Internet connectivity and website availability
3. Neo4j database connection (for integration tests)
4. API keys for Gemini LLM service
5. Detailed error messages in log files
