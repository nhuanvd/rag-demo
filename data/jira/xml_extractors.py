"""
JIRA XML Data Extractor

This module extracts data from JIRA XML exports instead of web scraping.
XML exports are more reliable and provide cleaner structured data.
"""

import logging
from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Any


class JIRAXMLDataExtractor:
    """Extract data from JIRA XML exports."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def extract_ticket_data(self, xml_content: str) -> Dict[str, Any]:
        """
        Extract all ticket data from JIRA XML export.

        Args:
            xml_content: Raw XML content from JIRA export

        Returns:
            Dictionary containing all extracted ticket data
        """
        soup = BeautifulSoup(xml_content, "xml")
        issue = soup.find("item")

        if not issue:
            self.logger.warning("No issue found in XML content")
            return {}

        data = {}

        # Extract basic information
        data["id"] = self._extract_text(issue, "key")
        data["title"] = self._extract_text(issue, "summary")
        data["type"] = self._extract_text(issue, "type")
        data["status"] = self._extract_text(issue, "status")
        data["priority"] = self._extract_text(issue, "priority")
        data["assignee"] = self._extract_text(issue, "assignee")
        data["reporter"] = self._extract_text(issue, "reporter")
        data["created"] = self._extract_date(issue, "created")
        data["updated"] = self._extract_date(issue, "updated")
        data["resolution"] = self._extract_text(issue, "resolution")
        data["description"] = self._extract_text(issue, "description")
        data["environment"] = self._extract_text(issue, "environment")

        # Extract parent information
        parent = issue.find("parent")
        if parent:
            data["parent"] = parent.get_text(strip=True)

        # Extract labels
        data["labels"] = self._extract_labels(issue)

        # Extract components
        data["components"] = self._extract_components(issue)

        # Extract fix versions
        data["fix_versions"] = self._extract_fix_versions(issue)

        # Extract issue links (relationships)
        data["related_tickets"] = self._extract_issue_links(issue)

        # Extract subtasks
        data["subtasks"] = self._extract_subtasks(issue)

        # Extract comments
        data["comments"] = self._extract_comments(issue)

        return data

    def _extract_text(self, element, tag_name: str) -> str:
        """Extract text content from a specific tag."""
        tag = element.find(tag_name)
        if tag:
            # Clean HTML for better RAG/AI compatibility
            return self._clean_html_for_rag(tag.get_text(strip=True))
        return ""

    def _extract_date(self, element, tag_name: str) -> str:
        """Extract date and convert to ISO 8601 format."""
        tag = element.find(tag_name)
        if tag:
            date_text = tag.get_text(strip=True)
            if date_text:
                return self._convert_to_iso8601(date_text)
        return ""

    def _convert_to_iso8601(self, date_text: str) -> str:
        """Convert JIRA date format to ISO 8601."""
        if not date_text:
            return ""

        try:
            from datetime import datetime
            import re

            # JIRA typically uses formats like:
            # "Thu, 19 Jun 2025 15:01:03 +0700"
            # "2025-06-19T15:01:03.000+0700"
            # "2025-06-19 15:01:03"

            # Try parsing common JIRA date formats
            formats_to_try = [
                "%a, %d %b %Y %H:%M:%S %z",  # Thu, 19 Jun 2025 15:01:03 +0700
                "%Y-%m-%dT%H:%M:%S.%f%z",  # 2025-06-19T15:01:03.000+0700
                "%Y-%m-%dT%H:%M:%S%z",  # 2025-06-19T15:01:03+0700
                "%Y-%m-%d %H:%M:%S",  # 2025-06-19 15:01:03
                "%Y-%m-%dT%H:%M:%S",  # 2025-06-19T15:01:03
            ]

            for fmt in formats_to_try:
                try:
                    dt = datetime.strptime(date_text, fmt)
                    return dt.isoformat()
                except ValueError:
                    continue

            # If no format matches, try to extract date components manually
            # Look for patterns like "Thu, 19 Jun 2025 15:01:03 +0700"
            pattern = r"(\w+), (\d+) (\w+) (\d+) (\d+):(\d+):(\d+) ([+-]\d{4})"
            match = re.match(pattern, date_text)
            if match:
                day_name, day, month_name, year, hour, minute, second, tz = (
                    match.groups()
                )

                # Convert month name to number
                month_map = {
                    "Jan": "01",
                    "Feb": "02",
                    "Mar": "03",
                    "Apr": "04",
                    "May": "05",
                    "Jun": "06",
                    "Jul": "07",
                    "Aug": "08",
                    "Sep": "09",
                    "Oct": "10",
                    "Nov": "11",
                    "Dec": "12",
                }
                month = month_map.get(month_name, "01")

                # Format as ISO 8601
                iso_date = f"{year}-{month}-{day.zfill(2)}T{hour.zfill(2)}:{minute.zfill(2)}:{second.zfill(2)}{tz}"
                return iso_date

            # If all else fails, return the original text
            return date_text

        except Exception as e:
            # If conversion fails, return the original text
            return date_text

    def _clean_html_for_rag(self, text: str) -> str:
        """Clean HTML content to be more RAG/AI friendly while preserving structure."""
        if not text:
            return ""

        import re
        from bs4 import BeautifulSoup

        # Parse HTML
        soup = BeautifulSoup(text, "html.parser")

        # Convert to markdown-like format
        # Headers
        for i, tag in enumerate(["h1", "h2", "h3", "h4", "h5", "h6"], 1):
            for header in soup.find_all(tag):
                header_text = header.get_text(strip=True)
                if header_text:
                    header.replace_with(f"\n{'#' * i} {header_text}\n")

        # Code blocks - handle these first before lists
        for pre in soup.find_all("pre"):
            code_text = pre.get_text()
            # Ensure code block starts on new line
            pre.replace_with(f"\n\n```\n{code_text}\n```\n\n")

        # Inline code
        for code in soup.find_all("code"):
            code_text = code.get_text()
            code.replace_with(f"`{code_text}`")

        # Bold text
        for bold in soup.find_all(["strong", "b"]):
            bold_text = bold.get_text()
            bold.replace_with(f"**{bold_text}**")

        # Italic text
        for italic in soup.find_all(["em", "i"]):
            italic_text = italic.get_text()
            italic.replace_with(f"*{italic_text}*")

        # Links
        for link in soup.find_all("a"):
            link_text = link.get_text(strip=True)
            href = link.get("href", "")
            if href and link_text:
                link.replace_with(f"[{link_text}]({href})")
            elif link_text:
                link.replace_with(link_text)

        # Line breaks
        for br in soup.find_all("br"):
            br.replace_with("\n")

        # Paragraphs
        for p in soup.find_all("p"):
            p_text = p.get_text(strip=True)
            if p_text:
                p.replace_with(f"{p_text}\n\n")

        # Lists - handle these last to avoid conflicts with code blocks
        for ul in soup.find_all("ul"):
            list_items = []
            for li in ul.find_all("li"):
                # Get text content, preserving any code blocks that were already processed
                li_text = li.get_text(strip=True)
                if li_text:
                    # Check if this list item contains code blocks and format accordingly
                    if "```" in li_text:
                        # Split by code blocks and format properly
                        parts = li_text.split("```")
                        formatted_parts = []
                        for i, part in enumerate(parts):
                            part = part.strip()
                            if part and i % 2 == 0:  # Text parts
                                formatted_parts.append(f"- {part}")
                            elif part and i % 2 == 1:  # Code parts
                                formatted_parts.append(f"\n```\n{part}\n```\n")
                        list_items.append("\n".join(formatted_parts))
                    else:
                        list_items.append(f"- {li_text}")
            if list_items:
                ul.replace_with(f"\n{chr(10).join(list_items)}\n")

        # Get final text and clean up
        result = soup.get_text()

        # Clean up excessive whitespace
        result = re.sub(r"\n\s*\n\s*\n", "\n\n", result)  # Multiple newlines to double
        result = re.sub(r"[ \t]+", " ", result)  # Multiple spaces to single
        result = re.sub(r"\n ", "\n", result)  # Remove leading spaces from lines

        return result.strip()

    def _process_list_item(self, li_element) -> str:
        """Process a list item, handling nested code blocks properly."""
        # Create a copy to work with
        li_copy = BeautifulSoup(str(li_element), "html.parser").find("li")

        # First, handle any code blocks within the list item
        for pre in li_copy.find_all("pre"):
            code_text = pre.get_text()
            pre.replace_with(f"\n\n```\n{code_text}\n```\n\n")

        # Get the text content
        text = li_copy.get_text(strip=True)
        if text:
            return f"- {text}"
        return ""

    def _extract_labels(self, issue) -> List[str]:
        """Extract labels from the issue."""
        labels = []
        labels_elem = issue.find("labels")
        if labels_elem:
            label_items = labels_elem.find_all("label")
            labels = [label.get_text(strip=True) for label in label_items]
        return labels

    def _extract_components(self, issue) -> List[str]:
        """Extract components from the issue."""
        components = []
        components_elem = issue.find("components")
        if components_elem:
            component_items = components_elem.find_all("component")
            components = [comp.get_text(strip=True) for comp in component_items]
        return components

    def _extract_fix_versions(self, issue) -> List[str]:
        """Extract fix versions from the issue."""
        fix_versions = []
        fix_versions_elem = issue.find("fixVersions")
        if fix_versions_elem:
            version_items = fix_versions_elem.find_all("fixVersion")
            fix_versions = [version.get_text(strip=True) for version in version_items]
        return fix_versions

    def _extract_issue_links(self, issue) -> List[Dict[str, str]]:
        """Extract issue links (relationships) from the issue."""
        related_tickets = []

        issuelinks = issue.find("issuelinks")
        if not issuelinks:
            return related_tickets

        # Extract inward links (other issues that link to this one)
        inwardlinks = issuelinks.find("inwardlinks")
        if inwardlinks:
            # Get the relationship type from the description attribute
            relationship = inwardlinks.get("description", "relates to")
            # Get the section name from the issuelinktype
            section_name = self._get_section_name(issuelinks, "inward")
            inward_links = inwardlinks.find_all("issuelink")
            for link in inward_links:
                issue_key = link.get_text(strip=True)
                if issue_key:
                    related_tickets.append(
                        {
                            "id": issue_key,
                            "title": "",  # XML doesn't include titles, would need separate call
                            "type": "",
                            "priority": "",
                            "status": "",
                            "relationship": relationship,
                            "section_name": section_name,
                        }
                    )

        # Extract outward links (this issue links to others)
        outwardlinks = issuelinks.find("outwardlinks")
        if outwardlinks:
            # Get the relationship type from the description attribute
            relationship = outwardlinks.get("description", "relates to")
            # Get the section name from the issuelinktype
            section_name = self._get_section_name(issuelinks, "outward")
            outward_links = outwardlinks.find_all("issuelink")
            for link in outward_links:
                issue_key = link.get_text(strip=True)
                if issue_key:
                    related_tickets.append(
                        {
                            "id": issue_key,
                            "title": "",  # XML doesn't include titles, would need separate call
                            "type": "",
                            "priority": "",
                            "status": "",
                            "relationship": relationship,
                            "section_name": section_name,
                        }
                    )

        return related_tickets

    def _get_section_name(self, issuelinks, direction: str) -> str:
        """Get the section name from issuelinktype for the given direction."""
        # Look for issuelinktype elements
        link_types = issuelinks.find_all("issuelinktype")
        for link_type in link_types:
            if direction == "inward":
                inwardlinks = link_type.find("inwardlinks")
                if inwardlinks:
                    # Get the name from the issuelinktype
                    name_elem = link_type.find("name")
                    if name_elem:
                        return name_elem.get_text(strip=True)
            else:
                outwardlinks = link_type.find("outwardlinks")
                if outwardlinks:
                    # Get the name from the issuelinktype
                    name_elem = link_type.find("name")
                    if name_elem:
                        return name_elem.get_text(strip=True)

        return "Related Issues"  # Default fallback

    def _get_link_type(self, issuelinks, direction: str) -> str:
        """Get the relationship type for inward or outward links."""
        # Look for issuelinktype elements
        link_types = issuelinks.find_all("issuelinktype")
        for link_type in link_types:
            if direction == "inward":
                inward_desc = link_type.find("inwarddescription")
                if inward_desc:
                    return inward_desc.get_text(strip=True)
            else:
                outward_desc = link_type.find("outwarddescription")
                if outward_desc:
                    return outward_desc.get_text(strip=True)

        # If no specific link type found, try to get from the issuelinks structure
        # Look for text that might indicate the relationship type
        if direction == "inward":
            # Check if there's a "Cloners" text in the inward links
            inwardlinks = issuelinks.find("inwardlinks")
            if inwardlinks:
                inward_text = inwardlinks.get_text()
                if "cloners" in inward_text.lower():
                    return "is cloned by"

        return "relates to"  # Default fallback

    def _extract_subtasks(self, issue) -> List[Dict[str, str]]:
        """Extract subtasks from the issue."""
        subtasks = []
        subtask_items = issue.find_all("subtask")

        for subtask in subtask_items:
            subtask_id = subtask.get("key", "")
            subtask_title = subtask.get_text(strip=True)
            if subtask_id:
                subtasks.append({"id": subtask_id, "title": subtask_title})

        return subtasks

    def _extract_comments(self, issue) -> List[Dict[str, str]]:
        """Extract comments from the issue."""
        comments = []
        comments_elem = issue.find("comments")

        if comments_elem:
            comment_items = comments_elem.find_all("comment")
            for comment in comment_items:
                author = comment.get("author", "Unknown")
                created = self._convert_to_iso8601(comment.get("created", ""))
                # Clean HTML for comments too
                body = self._clean_html_for_rag(comment.get_text(strip=True))

                comments.append({"author": author, "created": created, "body": body})

        return comments
