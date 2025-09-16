"""
Main JIRA scraper class
Uses modular components for authentication and data extraction
"""

import os
import time
from typing import Dict, List, Optional, Any
import logging
import yaml

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from auth import JIRAAuthenticator
from xml_extractors import JIRAXMLDataExtractor


class JIRARequestsScraper:
    """Main JIRA scraper class with modular components"""

    def __init__(self):
        """
        Initialize JIRA requests scraper
        Uses interactive authentication flow
        """
        # Initialize authenticator with interactive setup
        self.authenticator = JIRAAuthenticator.create_interactive()

        # Initialize data extractor
        self.extractor = JIRAXMLDataExtractor()

        # Set up logger
        self.logger = logging.getLogger(__name__)

        # Expose session for backward compatibility
        self.session = self.authenticator.session

        # Authentication status tracking
        self._authenticated = False

    def login(self) -> bool:
        """Login to JIRA using requests session"""
        return self.authenticator.login()

    def set_session_cookies(self, cookies: Dict[str, str]) -> bool:
        """Set session cookies from browser (alternative to login)"""
        return self.authenticator.set_session_cookies(cookies)

    def test_authentication(self) -> bool:
        """Test if current session is authenticated"""
        return self.authenticator.test_authentication()

    def save_cookies(self) -> bool:
        """Save current session cookies to file"""
        return self.authenticator.save_cookies()

    def load_cookies(self) -> bool:
        """Load session cookies from file"""
        return self.authenticator.load_cookies()

    def clear_cookies(self) -> bool:
        """Clear saved cookies"""
        return self.authenticator.clear_cookies()

    def ensure_authenticated(self) -> bool:
        """Ensure session is authenticated (only authenticates once)"""
        if self._authenticated:
            return True

        # Authenticate only once
        if self.authenticator.ensure_authenticated():
            self._authenticated = True
            return True
        else:
            return False

    def reset_authentication(self) -> None:
        """Reset authentication status to force re-authentication"""
        self._authenticated = False

    def set_user_agent(self, user_agent: str) -> None:
        """Set custom user agent for requests"""
        self.authenticator.set_user_agent(user_agent)

    def get_user_agent(self) -> str:
        """Get current user agent"""
        return self.authenticator.get_user_agent()

    def get_user_agent_presets(self) -> Dict[str, str]:
        """Get common user agent presets"""
        return self.authenticator.get_user_agent_presets()

    def set_user_agent_preset(self, preset_name: str) -> bool:
        """Set user agent using a preset"""
        return self.authenticator.set_user_agent_preset(preset_name)

    def get_ticket_data(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """
        Get ticket data using XML export (more reliable than web scraping)

        Args:
            ticket_id: JIRA ticket ID (e.g., 'SL-1234')

        Returns:
            Dictionary containing ticket data or None if ticket doesn't exist
        """
        try:
            # Construct the URL for the XML export
            xml_url = f"{self.authenticator.server_url}/si/jira.issueviews:issue-xml/{ticket_id}/{ticket_id}.xml"

            # Make the request
            response = self.session.get(xml_url)

            if response.status_code == 404:
                self.logger.warning(f"Ticket {ticket_id} not found (404)")
                return None

            response.raise_for_status()

            # Extract data using the XML extractor
            ticket_data = self.extractor.extract_ticket_data(response.text)

            # Add the ticket ID to the data if not already present
            if not ticket_data.get("id"):
                ticket_data["id"] = ticket_id

            return ticket_data

        except Exception as e:
            self.logger.warning(f"Failed to get ticket data for {ticket_id}: {str(e)}")
            return None

    def format_for_rag(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format ticket data for RAG training as structured data"""
        if not ticket_data:
            return {}

        # Create structured RAG data
        rag_data = {}
        for key in [
            "id",
            "title",
            "type",
            "status",
            "priority",
            "assignee",
            "reporter",
            "created",
            "updated",
            "resolution",
        ]:
            value = ticket_data.get(key)
            if value is not None:
                rag_data[key] = value

        # Always include lists, defaulting to empty if missing
        for list_key in ["labels", "components", "fix_versions"]:
            value = ticket_data.get(list_key)
            if value:
                rag_data[list_key] = value

        # Add related tickets grouped by section name
        if ticket_data.get("related_tickets"):
            sections = {}
            for related in ticket_data["related_tickets"]:
                section_name = related.get("section_name", "Related Issues")
                if section_name not in sections:
                    sections[section_name.lower()] = []
                sections[section_name.lower()].append(related)

            rag_data["related_tickets"] = sections

        # Add subtasks
        if ticket_data.get("subtasks"):
            rag_data["subtasks"] = ticket_data["subtasks"]

        # Add parent task
        if ticket_data.get("parent"):
            rag_data["parent_task"] = ticket_data["parent"]

        # Add description
        if ticket_data.get("description"):
            rag_data["description"] = ticket_data["description"]

        # Add comments
        if ticket_data.get("comments"):
            rag_data["comments"] = ticket_data["comments"]

        # Add attachments
        if ticket_data.get("attachments"):
            rag_data["attachments"] = ticket_data["attachments"]

        return rag_data

    def save_ticket(self, ticket_data: Dict[str, Any], output_dir: str) -> bool:
        """Save ticket data to YAML file"""
        if not ticket_data:
            return False

        try:
            # Format data for RAG as structured data
            rag_data = self.format_for_rag(ticket_data)

            # Create filename with .yml extension
            filename = f"{ticket_data['id']}.yml"
            filepath = os.path.join(output_dir, filename)

            # Save to YAML file
            with open(filepath, "w", encoding="utf-8") as f:
                yaml.dump(
                    rag_data,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )

            self.logger.info(f"Saved ticket {ticket_data['id']} to {filepath}")
            return True

        except Exception as e:
            self.logger.error(
                f"Failed to save ticket {ticket_data.get('id', 'unknown')}: {str(e)}"
            )
            return False

    def crawl_tickets(
        self,
        project_key: str,
        start_id: int,
        end_id: int,
        output_dir: str,
        delay: float = 1.0,
        max_retries: int = 3,
    ) -> Dict[str, int]:
        """Crawl tickets in a range"""
        # Authenticate once at the start
        if not self.ensure_authenticated():
            self.logger.error("Authentication required to crawl tickets")
            return {"total_attempted": 0, "successful": 0, "failed": 0, "not_found": 0}

        stats = {"total_attempted": 0, "successful": 0, "failed": 0, "not_found": 0}

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        self.logger.info(
            f"Starting to crawl tickets {project_key}-{start_id} to {project_key}-{end_id}"
        )

        for ticket_num in tqdm(range(start_id, end_id + 1), desc="Crawling tickets"):
            ticket_id = f"{project_key}-{ticket_num}"
            stats["total_attempted"] += 1

            # Try to get ticket data with retries
            ticket_data = None
            for attempt in range(max_retries):
                try:
                    ticket_data = self.get_ticket_data(ticket_id)
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        self.logger.warning(
                            f"Attempt {attempt + 1} failed for {ticket_id}, retrying..."
                        )
                        time.sleep(delay * (attempt + 1))
                    else:
                        self.logger.error(
                            f"All attempts failed for {ticket_id}: {str(e)}"
                        )

            if ticket_data:
                if self.save_ticket(ticket_data, output_dir):
                    stats["successful"] += 1
                else:
                    stats["failed"] += 1
            else:
                stats["not_found"] += 1

            # Add delay between requests to be respectful to the server
            time.sleep(delay)

        self.logger.info(f"Crawling completed. Stats: {stats}")
        return stats
