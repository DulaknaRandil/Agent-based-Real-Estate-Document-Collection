"""
Complete end-to-end test for the Charleston County deed search workflow
- Validates browser automation
- Tests direct URL navigation to deed search
- Verifies deed search and download
- Validates Neo4j knowledge graph integration
- Measures performance metrics
"""
import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from datetime import datetime

from src.agents.charleston_langgraph_agent import CharlestonWorkflowAgent
from src.services.gemini_service import GeminiService
from src.services.knowledge_graph_service import CharlestonKnowledgeGraph
from src.automation.browser_manager import CharlestonBrowserManager
from src.utils.logger import setup_logger
from src.config import get_tms_folder_path

# Set up logging
setup_logger()
logger = logging.getLogger(__name__)

class WorkflowTestResult:
    """Track workflow test results and metrics"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.end_time = None
        self.browser_init_success = False
        self.navigation_success = False
        self.deed_search_success = False
        self.deed_download_success = False
        self.neo4j_success = False
        self.llm_success = False
        self.workflow_stats = {
            "deed_references_found": 0,
            "deeds_downloaded": 0,
            "nodes_created": 0,
            "relationships_created": 0,
            "tokens_used": 0,
            "errors": []
        }
        self.timing = {
            "browser_init_time": 0,
            "navigation_time": 0,
            "search_time": 0,
            "download_time": 0,
            "llm_processing_time": 0,
            "neo4j_time": 0,
            "total_time": 0
        }
    
    def finish(self):
        """Complete the test and calculate total time"""
        self.end_time = datetime.now()
        self.timing["total_time"] = (self.end_time - self.start_time).total_seconds()
        return self
    
    def add_error(self, error_message):
        """Add an error message to the test results"""
        self.workflow_stats["errors"].append(error_message)
    
    def get_summary(self):
        """Generate a summary of the test results"""
        success = all([
            self.browser_init_success,
            self.navigation_success,
            self.deed_search_success, 
            self.deed_download_success,
            self.neo4j_success,
            self.llm_success
        ])
        
        return {
            "success": success,
            "success_rate": self.calculate_success_rate(),
            "test_duration_seconds": round(self.timing["total_time"], 2),
            "test_duration_minutes": round(self.timing["total_time"] / 60, 2),
            "steps": {
                "browser_initialization": self.browser_init_success,
                "site_navigation": self.navigation_success,
                "deed_search": self.deed_search_success,
                "deed_download": self.deed_download_success,
                "neo4j_integration": self.neo4j_success,
                "llm_processing": self.llm_success
            },
            "timing": {
                k: round(v, 2) for k, v in self.timing.items()
            },
            "workflow_stats": self.workflow_stats,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None
        }
    
    def calculate_success_rate(self):
        """Calculate overall success rate as percentage"""
        successful_steps = sum([
            self.browser_init_success,
            self.navigation_success,
            self.deed_search_success,
            self.deed_download_success,
            self.neo4j_success,
            self.llm_success
        ])
        return round((successful_steps / 6) * 100, 1)
    
    def save_results(self, output_file="data/temp/end_to_end_results.json"):
        """Save test results to JSON file"""
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(self.get_summary(), f, indent=2)
        logger.info(f"Test results saved to {output_file}")
        print(f"\n💾 Test results saved to {output_file}")

async def test_browser_functionality(tms_number, test_result):
    """Test the basic browser functionality"""
    try:
        print(f"\n{'='*80}")
        print(f"🔍 TESTING BROWSER FUNCTIONALITY")
        print(f"{'='*80}")
        
        # Initialize browser
        browser_start = time.time()
        browser = CharlestonBrowserManager()
        success = browser.start_browser()
        browser_time = time.time() - browser_start
        test_result.timing["browser_init_time"] = browser_time
        
        if success:
            test_result.browser_init_success = True
            logger.info(f"✓ Browser initialized successfully in {browser_time:.2f} seconds")
            print(f"✓ Browser initialized successfully in {browser_time:.2f} seconds")
        else:
            logger.error("❌ Browser initialization failed")
            print("❌ Browser initialization failed")
            test_result.add_error("Browser initialization failed")
            return False, None
        
        # Test navigation to deed search
        nav_start = time.time()
        success = browser.navigate_to_register_of_deeds()
        nav_time = time.time() - nav_start
        test_result.timing["navigation_time"] = nav_time
        
        if success:
            test_result.navigation_success = True
            logger.info(f"✓ Navigated to deed search in {nav_time:.2f} seconds")
            print(f"✓ Navigated to deed search in {nav_time:.2f} seconds")
        else:
            logger.error("❌ Navigation to deed search failed")
            print("❌ Navigation to deed search failed")
            test_result.add_error("Navigation to deed search failed")
            return False, browser
            
        return True, browser
        
    except Exception as e:
        logger.error(f"Browser test error: {e}")
        print(f"❌ Browser test error: {e}")
        test_result.add_error(f"Browser test error: {str(e)}")
        return False, None

async def test_deed_search_download(browser, book, page, tms_number, test_result):
    """Test deed search and download functionality"""
    try:
        print(f"\n{'='*80}")
        print(f"📄 TESTING DEED SEARCH & DOWNLOAD: Book {book}, Page {page}")
        print(f"{'='*80}")
        
        # Test deed search
        search_start = time.time()
        search_success = browser.search_deed_by_book_page(book, page)
        search_time = time.time() - search_start
        test_result.timing["search_time"] += search_time
        
        if search_success:
            test_result.deed_search_success = True
            logger.info(f"✓ Deed search successful (Book {book}, Page {page}) in {search_time:.2f} seconds")
            print(f"✓ Deed search successful (Book {book}, Page {page}) in {search_time:.2f} seconds")
        else:
            logger.error(f"❌ Deed search failed (Book {book}, Page {page})")
            print(f"❌ Deed search failed (Book {book}, Page {page})")
            test_result.add_error(f"Deed search failed for Book {book}, Page {page}")
            return False
        
        # Test deed download
        filename = f"Deed_Book{book}_Page{page}"
        download_start = time.time()
        download_success = browser.download_deed_pdf(filename, tms_number)
        download_time = time.time() - download_start
        test_result.timing["download_time"] += download_time
        
        if download_success:
            test_result.deed_download_success = True
            test_result.workflow_stats["deeds_downloaded"] += 1
            logger.info(f"✓ Deed download successful ({filename}) in {download_time:.2f} seconds")
            print(f"✓ Deed download successful ({filename}) in {download_time:.2f} seconds")
        else:
            logger.error(f"❌ Deed download failed ({filename})")
            print(f"❌ Deed download failed ({filename})")
            test_result.add_error(f"Deed download failed for {filename}")
            return False
            
        # Verify downloaded file
        try:
            downloads_dir = get_tms_folder_path(tms_number)
            pdf_path = downloads_dir / f"{filename}.pdf"
            
            if pdf_path.exists():
                size_kb = pdf_path.stat().st_size / 1024
                logger.info(f"✓ Verified downloaded file: {pdf_path.name} ({size_kb:.1f} KB)")
                print(f"✓ Verified downloaded file: {pdf_path.name} ({size_kb:.1f} KB)")
            else:
                logger.warning(f"⚠️ File not found at expected path: {pdf_path}")
                print(f"⚠️ File not found at expected path: {pdf_path}")
        except Exception as e:
            logger.error(f"Error verifying downloaded file: {e}")
            print(f"⚠️ Error verifying downloaded file: {e}")
        
        return download_success
        
    except Exception as e:
        logger.error(f"Deed search/download error: {e}")
        print(f"❌ Deed search/download error: {e}")
        test_result.add_error(f"Deed search/download error: {str(e)}")
        return False

async def test_full_workflow(tms_number, test_result):
    """Test the complete LangGraph workflow with Neo4j integration"""
    try:
        print(f"\n{'='*80}")
        print(f"🔄 TESTING FULL WORKFLOW INTEGRATION FOR TMS: {tms_number}")
        print(f"{'='*80}")
        
        # Initialize services
        llm_start = time.time()
        gemini_service = GeminiService()
        llm_time = time.time() - llm_start
        test_result.timing["llm_processing_time"] += llm_time
        
        logger.info(f"✓ LLM service initialized in {llm_time:.2f} seconds")
        print(f"✓ LLM service initialized in {llm_time:.2f} seconds")
        
        neo4j_start = time.time()
        kg_service = CharlestonKnowledgeGraph()
        neo4j_time = time.time() - neo4j_start
        test_result.timing["neo4j_time"] += neo4j_time
        
        logger.info(f"✓ Neo4j service initialized in {neo4j_time:.2f} seconds")
        print(f"✓ Neo4j service initialized in {neo4j_time:.2f} seconds")
        
        # Create and initialize LangGraph agent
        agent = CharlestonWorkflowAgent(
            gemini_service,
            kg_service,
            use_direct_urls=True,
            optimize_token_usage=True
        )
        
        # Run the workflow
        print("\n🚀 Executing full workflow...")
        workflow_start = time.time()
        result = await agent.run_workflow(tms_number)
        workflow_time = time.time() - workflow_start
        
        # Log token usage if available
        if hasattr(agent, 'token_usage') and agent.token_usage:
            test_result.workflow_stats["tokens_used"] = agent.token_usage
            logger.info(f"Token usage: {agent.token_usage}")
            print(f"Token usage: {agent.token_usage}")
        
        # Process workflow results
        if result:
            # Check for downloaded documents
            docs = result.get("downloaded_documents", [])
            test_result.workflow_stats["deeds_downloaded"] = len(docs)
            
            # Check for errors
            errors = result.get("errors", [])
            for error in errors:
                test_result.add_error(f"Workflow error: {error}")
            
            logger.info(f"✓ Workflow completed in {workflow_time:.2f} seconds")
            print(f"✓ Workflow completed in {workflow_time:.2f} seconds")
            print(f"  - Documents downloaded: {len(docs)}")
            print(f"  - Errors: {len(errors)}")
            
            # Check for LLM success (deed references extracted)
            deed_refs_file = Path("data/temp/deed_references.json")
            if deed_refs_file.exists():
                try:
                    with open(deed_refs_file) as f:
                        deed_data = json.load(f)
                        ref_count = len(deed_data.get("references", []))
                        test_result.workflow_stats["deed_references_found"] = ref_count
                        test_result.llm_success = ref_count > 0
                        logger.info(f"✓ LLM extracted {ref_count} deed references")
                        print(f"✓ LLM extracted {ref_count} deed references")
                except:
                    logger.error("Error reading deed references file")
            
            # Query Neo4j to verify nodes were created
            try:
                neo4j_start = time.time()
                deed_nodes = kg_service.get_all_deeds_for_property(tms_number)
                neo4j_time = time.time() - neo4j_start
                test_result.timing["neo4j_time"] += neo4j_time
                
                node_count = len(deed_nodes)
                test_result.workflow_stats["nodes_created"] = node_count
                test_result.neo4j_success = node_count > 0
                
                logger.info(f"✓ Neo4j integration verified: {node_count} nodes found")
                print(f"✓ Neo4j integration verified: {node_count} nodes found")
                
            except Exception as neo4j_error:
                logger.error(f"Neo4j verification failed: {neo4j_error}")
                print(f"❌ Neo4j verification failed: {neo4j_error}")
                test_result.add_error(f"Neo4j verification failed: {str(neo4j_error)}")
            
            return True
        else:
            logger.error("❌ Workflow execution failed")
            print("❌ Workflow execution failed")
            test_result.add_error("Workflow execution failed with no results")
            return False
        
    except Exception as e:
        logger.error(f"Full workflow test error: {e}")
        print(f"❌ Full workflow test error: {e}")
        test_result.add_error(f"Full workflow test error: {str(e)}")
        return False
    finally:
        # Clean up resources if needed
        if 'agent' in locals():
            await agent.cleanup()

async def manual_deed_workflow_test(tms_number):
    """Execute manual deed workflow test for a specific TMS number"""
    test_result = WorkflowTestResult()
    success = False
    
    try:
        print(f"\n{'='*80}")
        print(f"🧪 RUNNING END-TO-END WORKFLOW TEST FOR TMS: {tms_number}")
        print(f"{'='*80}\n")
        
        # Step 1: Test browser functionality
        browser_success, browser = await test_browser_functionality(tms_number, test_result)
        if not browser_success:
            print("❌ Browser functionality test failed, aborting")
            return False
            
        # Step 2: Test deed search & download with sample deed references
        # Using fixed deed references for consistent testing
        sample_deeds = [
            ("5590", "200"),  # Format: (book, page)
            ("0280", "199")
        ]
        
        for book, page in sample_deeds:
            deed_success = await test_deed_search_download(browser, book, page, tms_number, test_result)
            if not deed_success:
                print(f"⚠️ Deed search/download test failed for Book {book}, Page {page}")
            
        # Step 3: Test full workflow integration
        workflow_success = await test_full_workflow(tms_number, test_result)
        
        # Close browser from manual testing
        if browser and hasattr(browser, 'driver'):
            browser.driver.quit()
            logger.info("Browser closed")
        
        # Calculate final success and generate report
        test_result.finish()
        summary = test_result.get_summary()
        success = summary["success"]
        
        # Print test results
        print(f"\n{'='*80}")
        print(f"📊 END-TO-END TEST RESULTS:")
        print(f"{'='*80}")
        print(f"  Overall success: {'✅ PASS' if success else '❌ FAIL'}")
        print(f"  Success rate: {summary['success_rate']}%")
        print(f"  Total duration: {summary['test_duration_seconds']:.2f} seconds ({summary['test_duration_minutes']:.2f} minutes)")
        
        print("\n🧩 TEST STEPS:")
        for step, result in summary["steps"].items():
            status = "✅" if result else "❌"
            print(f"  {status} {step.replace('_', ' ').title()}")
        
        print("\n⏱️ TIMING:")
        for operation, seconds in summary["timing"].items():
            if seconds > 0:
                print(f"  - {operation.replace('_', ' ').title()}: {seconds:.2f} seconds")
        
        print("\n📈 WORKFLOW STATS:")
        print(f"  - Deed references found: {summary['workflow_stats']['deed_references_found']}")
        print(f"  - Deeds downloaded: {summary['workflow_stats']['deeds_downloaded']}")
        print(f"  - Neo4j nodes created: {summary['workflow_stats']['nodes_created']}")
        print(f"  - Tokens used: {summary['workflow_stats']['tokens_used']}")
        
        if summary['workflow_stats']['errors']:
            print("\n⚠️ ERRORS:")
            for error in summary['workflow_stats']['errors'][:5]:  # Show only first 5 errors
                print(f"  - {error}")
            if len(summary['workflow_stats']['errors']) > 5:
                print(f"  ...and {len(summary['workflow_stats']['errors']) - 5} more errors")
        
        # Save test results
        test_result.save_results()
        
        print(f"\n{'='*80}")
        print(f"{'✅ TEST COMPLETED SUCCESSFULLY!' if success else '❌ TEST FAILED!'}")
        print(f"{'='*80}")
        
        return success
        
    except Exception as e:
        logger.error(f"End-to-end test execution error: {e}")
        print(f"\n❌ TEST EXECUTION ERROR: {e}")
        test_result.add_error(f"Test execution error: {str(e)}")
        test_result.finish()
        test_result.save_results()
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run end-to-end test for Charleston workflow")
    parser.add_argument("--tms", required=True, help="TMS number to use for testing")
    args = parser.parse_args()
    
    # Run the test
    if asyncio.run(manual_deed_workflow_test(args.tms)):
        sys.exit(0)
    else:
        sys.exit(1)
