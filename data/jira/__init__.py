"""
JIRA Scraper Package
Modular JIRA scraping tool for RAG training data
"""

from scraper import JIRARequestsScraper
from auth import JIRAAuthenticator
from xml_extractors import JIRAXMLDataExtractor

__version__ = "2.0.0"
__all__ = ["JIRARequestsScraper", "JIRAAuthenticator", "JIRAXMLDataExtractor"]
