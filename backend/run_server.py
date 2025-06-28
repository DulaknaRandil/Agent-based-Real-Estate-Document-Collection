# Server entry point for running the FastAPI server in development mode
# This allows easy testing of the backend API

import os
import sys

# Ensure correct working directory
if sys.argv[0]:
    os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))

# Import and run the server
from src.api.server import main

if __name__ == "__main__":
    # Pass any command line arguments to the server
    # You can use --no-reload to disable auto-reloading
    main()
