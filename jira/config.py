"""
Configuration file for JIRA crawler
"""

import os

current_dir = os.path.dirname(os.path.abspath(__file__))

# JIRA Server Configuration
JIRA_SERVER_URL = "https://issues.goodjourney.io"

# Crawling Configuration
CRAWL_CONFIG = {
    "project_key": "SL",
    "start_id": 35000,
    "end_id": 35044,
    "output_dir": os.path.join(current_dir, "data"),
    "delay": 1.0,  # seconds between requests (increased for web scraping)
    "max_retries": 3,
    "headless": True,  # Run browser in headless mode
    "batch_size": 100,  # Process tickets in batches
}
