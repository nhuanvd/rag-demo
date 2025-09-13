"""
Authentication module for JIRA scraper
Handles login, cookie management, and session authentication
"""

import os
import pickle
import logging
from typing import Dict, Optional

import requests
from bs4 import BeautifulSoup

from config import JIRA_SERVER_URL


class JIRAAuthenticator:
    """Handles JIRA authentication and session management"""

    def __init__(
        self, server_url: str = None, username: str = None, password: str = None
    ):
        """
        Initialize JIRA authenticator

        Args:
            server_url: JIRA server URL (optional, uses config default)
            username: JIRA username (optional, will be prompted if not provided)
            password: JIRA password (optional, will be prompted if not provided)
        """
        self.server_url = (server_url or JIRA_SERVER_URL).rstrip("/")
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)

        # Set custom user agent
        self.set_user_agent(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # Cookie management - use single cookie file
        self.cookie_file = os.path.join(os.path.dirname(__file__), ".cookies.pkl")

    def set_user_agent(self, user_agent: str) -> None:
        """
        Set custom user agent for requests

        Args:
            user_agent: User agent string to use for requests
        """
        self.session.headers.update({"User-Agent": user_agent})

    def set_user_agent_preset(self, preset: str) -> None:
        """
        Set user agent from predefined presets

        Args:
            preset: Preset name (chrome_mac, chrome_windows, firefox_mac, etc.)
        """
        presets = self.get_user_agent_presets()
        if preset in presets:
            self.set_user_agent(presets[preset])
        else:
            self.logger.warning(f"Unknown user agent preset: {preset}")

    def get_user_agent_presets(self) -> Dict[str, str]:
        """
        Get available user agent presets

        Returns:
            Dictionary of preset names to user agent strings
        """
        return {
            "chrome_mac": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "chrome_windows": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "firefox_mac": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Gecko/20100101 Firefox/121.0",
            "firefox_windows": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "safari_mac": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            "edge_windows": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            "mobile_chrome": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/120.0.6099.71 Mobile/15E148 Safari/604.1",
            "mobile_safari": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        }

    def get_user_agent(self) -> str:
        """
        Get current user agent

        Returns:
            Current user agent string
        """
        return self.session.headers.get("User-Agent", "")

    def save_cookies(self) -> None:
        """Save session cookies to file"""
        try:
            with open(self.cookie_file, "wb") as f:
                pickle.dump(self.session.cookies, f)
            self.logger.info(f"Cookies saved to {self.cookie_file}")
        except Exception as e:
            self.logger.error(f"Failed to save cookies: {e}")

    def load_cookies(self) -> bool:
        """
        Load session cookies from file

        Returns:
            True if cookies were loaded successfully, False otherwise
        """
        try:
            if os.path.exists(self.cookie_file):
                with open(self.cookie_file, "rb") as f:
                    self.session.cookies.update(pickle.load(f))
                self.logger.info(f"Cookies loaded from {self.cookie_file}")
                return True
            else:
                self.logger.info("No cookie file found")
                return False
        except Exception as e:
            self.logger.error(f"Failed to load cookies: {e}")
            return False

    def clear_cookies(self) -> None:
        """Clear saved cookies and session cookies"""
        try:
            if os.path.exists(self.cookie_file):
                os.remove(self.cookie_file)
                self.logger.info("Cookies cleared")
        except Exception as e:
            self.logger.error(f"Failed to clear cookies: {e}")

        self.session.cookies.clear()

    def test_authentication(self) -> bool:
        """
        Test if current session is authenticated

        Returns:
            True if authenticated, False otherwise
        """
        try:
            # Try to access a protected JIRA page
            test_url = f"{self.server_url}/secure/Dashboard.jspa"
            response = self.session.get(test_url, timeout=10)

            # Check if we're redirected to login page
            if "login" in response.url.lower() or response.status_code == 401:
                return False

            # Check for JIRA-specific content
            if "jira" in response.text.lower() or "dashboard" in response.text.lower():
                return True

            return False
        except Exception as e:
            self.logger.debug(f"Authentication test failed: {e}")
            return False

    def get_login_page(self) -> Optional[Dict[str, str]]:
        """
        Get login page and extract form data

        Returns:
            Dictionary with form data or None if failed
        """
        try:
            login_url = f"{self.server_url}/login.jsp"
            response = self.session.get(login_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Look for login form
            form = soup.find("form", {"id": "login-form"}) or soup.find(
                "form", {"class": "login-form"}
            )

            if not form:
                # Try to find any form with username/password fields
                forms = soup.find_all("form")
                for f in forms:
                    if f.find("input", {"name": "os_username"}) or f.find(
                        "input", {"name": "username"}
                    ):
                        form = f
                        break

            if not form:
                self.logger.error("Could not find login form")
                return None

            # Extract form action and method
            action = form.get("action", "")
            method = form.get("method", "post").lower()

            # Make action URL absolute
            if action.startswith("/"):
                action = f"{self.server_url}{action}"
            elif not action.startswith("http"):
                action = f"{self.server_url}/{action}"

            # Extract hidden fields
            hidden_fields = {}
            for hidden in form.find_all("input", {"type": "hidden"}):
                name = hidden.get("name")
                value = hidden.get("value", "")
                if name:
                    hidden_fields[name] = value

            return {
                "action": action,
                "method": method,
                "hidden_fields": hidden_fields,
            }
        except Exception as e:
            self.logger.error(f"Failed to get login page: {e}")
            return None

    def login_with_credentials(self, username: str, password: str) -> bool:
        """
        Login with username and password

        Args:
            username: JIRA username
            password: JIRA password

        Returns:
            True if login successful, False otherwise
        """
        try:
            # Get login page data
            form_data = self.get_login_page()
            if not form_data:
                return False

            # Prepare login data
            login_data = {
                "os_username": username,
                "os_password": password,
                "os_destination": "",
                "os_cookie": "true",
                "login": "Log In",
            }

            # Add hidden fields
            login_data.update(form_data["hidden_fields"])

            # Submit login form
            response = self.session.post(
                form_data["action"],
                data=login_data,
                allow_redirects=True,
                timeout=30,
            )

            # Check if login was successful
            if self.test_authentication():
                self.save_cookies()
                self.logger.info("Login successful")
                return True
            else:
                self.logger.error(
                    "Login failed - invalid credentials or CAPTCHA required"
                )
                return False

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    def login_with_cookies(self, cookies: Dict[str, str]) -> bool:
        """
        Login using provided cookies

        Args:
            cookies: Dictionary of cookie name-value pairs

        Returns:
            True if login successful, False otherwise
        """
        try:
            # Clear existing cookies
            self.session.cookies.clear()

            # Set provided cookies
            for name, value in cookies.items():
                self.session.cookies.set(
                    name,
                    value,
                    domain=self.server_url.replace("https://", "").replace(
                        "http://", ""
                    ),
                )

            # Test authentication
            if self.test_authentication():
                self.save_cookies()
                self.logger.info("Cookie authentication successful")
                return True
            else:
                self.logger.error("Cookie authentication failed")
                return False

        except Exception as e:
            self.logger.error(f"Cookie authentication failed: {e}")
            return False

    def ensure_authenticated(self) -> bool:
        """
        Ensure user is authenticated, prompting for credentials if needed

        Returns:
            True if authenticated, False otherwise
        """
        # First try to load existing cookies
        if self.load_cookies() and self.test_authentication():
            self.logger.info("Using existing authentication")
            return True

        # If no cookies or authentication failed, prompt user
        print("\n🔐 JIRA Authentication Required")
        print("=" * 40)

        # Check if cookies file exists
        if not os.path.exists(self.cookie_file):
            print("No existing cookies found.")
            print("\nChoose authentication method:")
            print("1. Use cookies (recommended for CAPTCHA-protected instances)")
            print("2. Use username/password")

            while True:
                choice = input("\nEnter your choice (1 or 2): ").strip()
                if choice in ["1", "2"]:
                    break
                print("Please enter 1 or 2")
        else:
            print("Existing cookies found but authentication failed.")
            print("\nChoose authentication method:")
            print("1. Use cookies (recommended for CAPTCHA-protected instances)")
            print("2. Use username/password")

            while True:
                choice = input("\nEnter your choice (1 or 2): ").strip()
                if choice in ["1", "2"]:
                    break
                print("Please enter 1 or 2")

        if choice == "1":
            # Cookie authentication
            print("\n🍪 Cookie Authentication")
            print("Please provide the following cookies from your browser:")
            print(
                "(You can find these in your browser's Developer Tools > Application > Cookies)"
            )

            cookies = {}
            cookie_names = [
                "JSESSIONID",
                "atlassian.xsrf.token",
                "seraph.rememberme.cookie",
            ]

            for cookie_name in cookie_names:
                while True:
                    value = input(f"Enter {cookie_name}: ").strip()
                    if value:
                        cookies[cookie_name] = value
                        break
                    print(f"{cookie_name} is required")

            return self.login_with_cookies(cookies)

        else:
            # Username/password authentication
            print("\n👤 Username/Password Authentication")

            if not self.username:
                self.username = input("Enter JIRA username: ").strip()
                if not self.username:
                    print("Username is required")
                    return False

            if not self.password:
                import getpass

                self.password = getpass.getpass("Enter JIRA password: ").strip()
                if not self.password:
                    print("Password is required")
                    return False

            return self.login_with_credentials(self.username, self.password)

    @classmethod
    def create_interactive(cls) -> "JIRAAuthenticator":
        """
        Create authenticator with interactive setup

        Returns:
            JIRAAuthenticator instance
        """
        return cls()
