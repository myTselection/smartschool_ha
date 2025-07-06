from __future__ import annotations

import contextlib
import json
import re
from dataclasses import dataclass, field
from functools import cached_property
from http.cookiejar import LoadError, LWPCookieJar
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlencode, urljoin, urlparse

import yaml
# from logprise import logger
import logging
from requests import Session

from .common import bs4_html, fill_form
from .exceptions import SmartSchoolAuthenticationError

try:
    import pyotp
except ImportError:
    pyotp = None

if TYPE_CHECKING:
    from requests import Response

    from .credentials import Credentials


logger = logging.getLogger(__name__) # Use a logger instance
__all__ = ["Smartschool"]


@dataclass
class Smartschool(Session):
    creds: Credentials | None = None
    useCookies: bool = field(init=False, default=False)
    _login_attempts: int = field(init=False, default=0)
    _max_login_attempts: int = field(init=False, default=3)
    _authenticated_user: dict | None = field(init=False, default=None)

    def __post_init__(self):
        super().__init__()

        if self.creds:
            self.creds.validate()

        self._initialize_session()

        if self.useCookies and self._authenticated_user_file and self._authenticated_user_file.exists():
            self._authenticated_user = yaml.safe_load(self._authenticated_user_file.read_text(encoding="utf8"))

    @property
    def authenticated_user(self) -> dict | None:
        if self._authenticated_user is None:
            raise ValueError("We couldn't retrieve the authenticated user somehow!")
        return self._authenticated_user

    @authenticated_user.setter
    def authenticated_user(self, new_user: dict | None) -> None:
        self._authenticated_user = new_user
        if self.useCookies:
            if not self._authenticated_user_file:
                return

            if new_user:
                with self._authenticated_user_file.open(mode="w", encoding="utf8") as fp:
                    yaml.dump(new_user, fp)
            else:
                self._authenticated_user_file.unlink(missing_ok=True)

    @property
    def _authenticated_user_file(self) -> Path | None:
        if self.creds:
            return self.cache_path / "authenticated_user.yml"
        return None

    def _handle_auth_redirect(self, response: Response) -> Response | None:
        """Handle authentication redirects with chain support."""
        if not self._is_auth_url(response.url):
            return None

        if self._login_attempts >= self._max_login_attempts:
            raise SmartSchoolAuthenticationError(f"Max login attempts ({self._max_login_attempts}) reached")

        logger.debug(f"Auth redirect detected: {response.url}")
        self._login_attempts += 1

        if response.url.endswith("/login"):
            response = self._do_login(response)
        if response.url.endswith("/account-verification"):
            self._parse_login_information(response)
            response = self._do_login_verification(response)
        if response.url.endswith("/2fa"):
            response = self._complete_verification_2fa()
        return response

    def _reset_login_attempts(self):
        """Reset login attempt counter on successful request."""
        if self._login_attempts > 0:
            logger.debug("Resetting login attempts after successful request")
            self._login_attempts = 0

    @property
    def cache_path(self) -> Path:
        p = Path.home() / ".cache/smartschool"
        if self.creds:
            p /= self.creds.username

        p.mkdir(parents=True, exist_ok=True)

        return p

    @property
    def cookie_file(self) -> Path:
        return self.cache_path / "cookies.txt"

    def _initialize_session(self):
        self.headers["User-Agent"] = "unofficial Smartschool API interface"
        if self.useCookies:
            cookie_jar = LWPCookieJar(self.cookie_file)
            with contextlib.suppress(FileNotFoundError, LoadError):
                cookie_jar.load(ignore_discard=True)

            self.cookies = cookie_jar

    def create_url(self, url: str) -> str:
        return urljoin(self._url, url)

    def _is_auth_url(self, url: str | Response) -> bool:
        """Check if the URL contains authentication-related path segments."""
        auth_segments = {"login", "account-verification", "2fa"}
        path_segments = set(urlparse(url).path.split("/"))

        return bool(auth_segments & path_segments)

    def request(self, method, url, **kwargs) -> Response:
        """Override Session.request to handle auth and cookies transparently."""
        if self.creds is None:
            raise RuntimeError("Smartschool instance must have valid credentials.")

        # Convert relative URLs to absolute
        full_url = self.create_url(url) if not url.startswith("http") else url

        # Make the request
        response = super().request(method, full_url, **kwargs)

        # Handle auth redirects
        response = self._handle_auth_redirect(response)
        if not self._is_auth_url(full_url):  # The original URL was NOT a login-url
            response = super().request(method, full_url, **kwargs)
            self._reset_login_attempts()
        elif not self._is_auth_url(response.url):  # Original was login, and this is not anymore
            self._reset_login_attempts()

        # Save cookies
        if self.useCookies:
            self.cookies.save(ignore_discard=True)

        return response

    def json(self, url, method: str = "get", **kwargs) -> dict:
        """Handle JSON responses with potential double encoding."""
        if method.lower() == "post":
            r = self.request("POST", url, **kwargs)
        else:
            if "data" in kwargs:
                data = urlencode(kwargs.pop("data"))
                url += ("&" if "?" in url else "?") + data
            r = self.request("GET", url, **kwargs)

        json_ = r.text
        while isinstance(json_, str):
            if not json_:
                return {}
            json_ = json.loads(json_)
        return json_

    def _do_login(self, response: Response) -> Response:
        """Handle login form submission."""
        logger.info(f"Logging in with {self.creds.username}")
        data = fill_form(
            response,
            'form[name="login_form"]',
            {
                "username": self.creds.username,
                "password": self.creds.password,
            },
        )
        return super().request("POST", response.url, data=data, allow_redirects=True)

    def _do_login_verification(self, response: Response) -> Response:
        """Handle account verification (birthday)."""
        logger.info(f"Account verification for {self.creds.username}")
        data = fill_form(
            response,
            'form[name="account_verification_form"]',
            {
                "security_question_answer": self.creds.mfa,
            },
        )
        return super().request("POST", response.url, data=data, allow_redirects=True)

    def _complete_verification_2fa(self) -> Response:
        """Handle 2FA verification using TOTP."""
        if pyotp is None:
            raise SmartSchoolAuthenticationError("2FA verification requires 'pyotp' package. Install with: pip install pyotp")

        logger.info(f"2FA verification for {self.creds.username}")

        # Check 2FA config
        config_resp = super().request("GET", self.create_url("/2fa/api/v1/config"), allow_redirects=True)
        config_resp.raise_for_status()

        if config_resp.status_code != 200:
            raise SmartSchoolAuthenticationError("Could not access 2FA API endpoint")

        config_data = json.loads(config_resp.text)
        if "googleAuthenticator" not in config_data.get("possibleAuthenticationMechanisms", []):
            raise SmartSchoolAuthenticationError("Only googleAuthenticator 2FA is supported")

        # Generate TOTP code and submit
        totp = pyotp.TOTP(self.creds.mfa)
        data = f'{{"google2fa":"{totp.now()}"}}'

        return super().request("POST", self.create_url("/2fa/api/v1/google-authenticator"), data=data, allow_redirects=True)

    def _parse_login_information(self, response: Response) -> None:
        """Parse authenticated user information from response."""
        html = bs4_html(response)
        for script in html.select("script"):
            if script.get("src") or "extend" not in script.text:
                continue

            if match := re.search(r"JSON\s*\.\s*parse\s*\(\s*'(.*)'\s*\)\s*\)\s*;?\s*$", script.text, flags=re.IGNORECASE):
                result = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), match.group(1))
                data = json.loads(result.replace("\\\\", "\\"))
                with contextlib.suppress(KeyError, TypeError, IndexError):
                    self.authenticated_user = data["vars"]["authenticatedUser"]
                    return

    @cached_property
    def _url(self) -> str:
        return "https://" + self.creds.main_url

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(for: {self.creds.username})"


@dataclass
class SessionMixin:
    session: Smartschool
