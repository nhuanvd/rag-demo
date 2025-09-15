# JIRA Scraper for RAG Training

Scrapes JIRA tickets and saves them in RAG-optimized text format using XML export.

## Features

- **Reliable**: Uses JIRA's XML export instead of web scraping
- **Auto-Auth**: Saves and reuses session cookies
- **Complete Data**: Extracts all ticket fields including relationships
- **Clean Output**: Converts HTML to Markdown for better AI compatibility

## Quick Start

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Run scraper:**
```bash
python jira_runner.py
```

3. **Choose authentication method when prompted:**
   - **Cookies** (recommended for CAPTCHA-protected instances)
   - **Username/Password**

## Authentication

The scraper will prompt you for authentication once at the start:
- **Cookies**: Enter JSESSIONID, atlassian.xsrf.token, and seraph.rememberme.cookie
- **Username/Password**: Enter your JIRA credentials
- Cookies are automatically saved and reused for all subsequent requests

## What it extracts

- **Basic Info**: Ticket ID, title, type, status, priority
- **People**: Assignee, reporter, created/updated dates
- **Content**: Description, comments, labels, components
- **Relationships**: Related tickets, subtasks, parent tasks
- **Attachments**: File names and sizes

## Output

Each ticket saved as `SL-XXXX.txt` with clean Markdown formatting perfect for RAG training:
- **ISO 8601 Dates**: All dates converted to standard ISO 8601 format (e.g., `2025-06-19T15:01:03+07:00`)
- **Clean Markdown**: HTML content converted to readable Markdown

## Files

- `scraper.py` - Main scraper class
- `auth.py` - Interactive authentication and cookies
- `xml_extractors.py` - XML data extraction
- `runner.py` - Command-line interface
- `config.py` - Configuration settings

## Usage

```python
from jira import JIRARequestsScraper

# Create scraper (auto-loads credentials from .env)
scraper = JIRARequestsScraper()

# Get ticket data (auto-authenticates)
ticket_data = scraper.get_ticket_data("SL-7")
```