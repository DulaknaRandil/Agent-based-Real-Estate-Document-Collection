"""
Server entry point for the Real Estate Document Collection API
"""
import uvicorn
import os
import logging
import sys
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/logs/api_server.log")
    ]
)

def main():
    """Run the API server"""
    # Ensure log directory exists
    os.makedirs("data/logs", exist_ok=True)
    
    # Parse command line arguments
    use_reload = "--no-reload" not in sys.argv
    
    # Get the root directory of the project
    root_dir = Path(__file__).parent.parent.parent
    
    # Configure server options
    server_options = {
        "host": "0.0.0.0",
        "port": 8000,
        "log_level": "info"
    }
    
    # Add reload options if enabled
    if use_reload:
        server_options.update({
            "reload": True,
            "reload_dirs": [
                str(root_dir / "src"),
                str(root_dir / "tests")
            ],
            "reload_excludes": [
                "*.pyc", "*.pyo", "*.pyd", "__pycache__",
                "data/**/*",  # Explicitly exclude all data subdirectories
                "data/downloads/**/*",
                "data/logs/**/*",
                "data/screenshots/**/*",
                "data/temp/**/*",
                "*.log"
            ]
        })
    
    # Start the server with the configured options
    uvicorn.run("src.api.main:app", **server_options)

if __name__ == "__main__":
    main()
