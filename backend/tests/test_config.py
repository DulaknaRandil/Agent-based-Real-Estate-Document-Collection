#!/usr/bin/env python3
"""
Test script to debug BROWSER_HEADLESS configuration
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

raw_value = os.getenv("BROWSER_HEADLESS")
print(f"Raw BROWSER_HEADLESS: {repr(raw_value)}")
print(f"Lower: {repr(raw_value.lower()) if raw_value else 'None'}")

# Test old logic
old_result = os.getenv("BROWSER_HEADLESS", "true").lower() == "true"
print(f"Old logic result: {old_result}")

# Test new logic
new_result = os.getenv("BROWSER_HEADLESS", "true").lower() in ("true", "1", "yes", "on")
print(f"New logic result: {new_result}")

# Test what we want
correct_result = os.getenv("BROWSER_HEADLESS", "true").lower() in ("false", "0", "no", "off")
print(f"Correct logic result (inverted): {not correct_result}")
