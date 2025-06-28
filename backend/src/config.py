"""
Configuration settings for Charleston County TMS search automation with AI and Knowledge Graph
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Screenshot behavior
DISABLE_SCREENSHOTS = os.getenv("DISABLE_SCREENSHOTS", "true").lower() not in ("false", "0", "no", "off")

# Charleston County specific settings
CHARLESTON_ONLINE_SERVICES_URL = "https://www.charlestoncounty.org/online-services.php"
CHARLESTON_PUBLIC_ACCESS_URL = "https://sc-charleston.publicaccessnow.com/"
CHARLESTON_PROPERTY_SEARCH_URL = "https://sc-charleston.publicaccessnow.com/RealPropertyRecordSearch.aspx"
CHARLESTON_PROPERTY_CARD_BASE = "https://sc-charleston.publicaccessnow.com/RealPropertyRecordSearch/RealPropertyInfo.aspx?p="
CHARLESTON_TAX_INFO_BASE = "https://sc-charleston...BillSearch/AccountSummary.aspx?p="
CHARLESTON_DEED_VIEWER_BASE = "https://docviewer.charlestoncounty.org/ROD/ViewDocument"
CHARLESTON_DEED_SEARCH_URL = "https://www.charlestoncounty.org/departments/rod/ds-DMBookandPage.php"
DEFAULT_TMS = "5590200072"  # Example TMS number from the guide

# AI/LLM Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "charleston-county-agent")

# CAPTCHA Configuration
TWOCAPTCHA_API_KEY = os.getenv("TWOCAPTCHA_API_KEY")

# Neo4j Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://f9893d6b.databases.neo4j.io")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# Browser settings
BROWSER_HEADLESS = os.getenv("BROWSER_HEADLESS", "true").lower() not in ("false", "0", "no", "off")
TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", "60"))
USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

# Directory paths
DOWNLOAD_PATH = PROJECT_ROOT / "data" / "downloads" / "charleston"
LOGS_PATH = PROJECT_ROOT / "data" / "logs"
TEMP_PATH = PROJECT_ROOT / "data" / "temp"

# Create directories if they don't exist
for path in [DOWNLOAD_PATH, LOGS_PATH, TEMP_PATH]:
    path.mkdir(parents=True, exist_ok=True)
    
def get_tms_folder_path(tms_number: str) -> Path:
    """
    Get the path to the TMS-specific folder for document storage
    
    Args:
        tms_number: The TMS number
        
    Returns:
        Path: Path to the TMS-specific download folder
    """
    tms_folder = DOWNLOAD_PATH / f"folder-{tms_number}"
    tms_folder.mkdir(parents=True, exist_ok=True)
    return tms_folder

# Retry settings
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
