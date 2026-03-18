from __future__ import annotations

import contextlib
import functools
import json
import time
import re
import logging
import datetime # Added import
import requests # Added import
# import httpx
# import http.cookiejar
from http.cookiejar import LWPCookieJar
from requests import Session
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Self
from urllib.parse import urljoin
import pyotp
import types


from .common import bs4_html, get_all_values_from_form
from .exceptions import SmartSchoolAuthenticationError, SmartSchoolException # Corrected casing

if TYPE_CHECKING:  # pragma: no cover
    from requests import Response

    from .credentials import Credentials


logger = logging.getLogger(__name__) # Use a logger instance

def _handle_cookies_and_login(func):
    @functools.wraps(func)
    def inner(self: 'Smartschool', *args, **kwargs):
        if self.creds is None:
            raise RuntimeError("Smartschool instance must have valid credentials.")

        self._try_login()  # Ensures login/session validity

        return func(self, *args, **kwargs)

    return inner


@dataclass
class Smartschool:
    creds: Credentials = None
    authenticated_user: dict | None = field(init=False, default=None)
    
    # _session = httpx.Client(http2=True)
    _session: Session = field(init=False)
    # Remove already_logged_on flag
    # already_logged_on: bool = field(init=False, default=None) # REMOVED

    def __post_init__(self):
        # logger.debug(f"Smartschool.__post_init__(): creds = {self.creds}") # Added self.creds)
        self._session = Session()
        if self.creds is not None:
            self.creds.validate()
        # Apply decorator to post and get methods *after* the decorator is defined
        # Ensure the methods exist on the class *before* this step
        self.post = types.MethodType(_handle_cookies_and_login(Smartschool.post), self)
        self.get = types.MethodType(_handle_cookies_and_login(Smartschool.get), self)
        
    # def __post_init__(self) -> None:
        
    #     self._session.cookies = LWPCookieJar(self.cookie_file)
    #     with contextlib.suppress(FileNotFoundError):
    #         self._session.cookies.load(ignore_discard=True)
            
        # # Load cookies using LWPCookieJar
        # self.cookiejar = http.cookiejarLWPCookieJar(self.cookie_file)
        # with contextlib.suppress(FileNotFoundError):
        #     self.cookiejar.load(ignore_discard=True, ignore_expires=True)
        #     # Convert to httpx format
        #     client_cookies = {}
        #     for cookie in self.cookiejar:
        #         client_cookies[cookie.name] = cookie.value

        #     # Initialize httpx client with cookies
        #     self._session = httpx.Client(http2=True, cookies=client_cookies)

        
        # self._session.headers.update({'Content-Type': 'application/json',
        #                             #   "Origin": "https://ruusbroec.smartschool.be",
        #                             #   "Referer": "https://ruusbroec.smartschool.be/",
        #                               "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        #                               "Sec-Fetch-Dest": "empty",
        #                               "Sec-Fetch-Mode": "cors",
        #                               "Sec-Fetch-Site": "same-origin",
        #                               "Sec-Fetch-User": "?1",
        #                             #   "sec-ch-ua-platform": "Windows",
        #                               "Accept": "application/json, text/plain, */*",
        #                               "Accept-Encoding": "gzip, deflate, br, zstd",
        #                               "Accept-Language": "en-US,en;q=0.9"})
        
        # self._session.headers.update({'Content-Type': 'application/json',
        #                               "Origin": "https://ruusbroec.smartschool.be",
        #                               "Referer": "https://ruusbroec.smartschool.be/",
        #                               "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        #                               "Sec-Fetch-Dest": "empty",
        #                               "Sec-Fetch-Mode": "cors",
        #                               "Sec-Fetch-Site": "same-origin",
        #                               "Sec-Fetch-User": "?1",
        #                               "sec-ch-ua-platform": "Windows",
        #                               "Accept": "application/json, text/plain, */*",
        #                               "Accept-Encoding": "gzip, deflate, br, zstd",
        #                               "Accept-Language": "en-US,en;q=0.9"})


    def _try_login(self) -> None:
        """
        Ensures the session is authenticated. Checks current session validity first,
        then attempts login and verification if necessary.
        Raises SmartSchoolAuthenticationError on failure.
        """
        logger.debug("Entering _try_login: Checking session validity.")

        # 1. Quick check: Try accessing the homepage. If it works, we're likely logged in.
        try:
            # Use allow_redirects=True to see the final destination
            # https: follow_redirects=False
            # check_resp = self._session.get(self.create_url("/"), follow_redirects=True)
            check_resp = self._session.get(self.create_url("/"), allow_redirects=True)
            check_resp.raise_for_status() # Check for HTTP errors

            final_url = str(check_resp.url)
            logger.debug(f"Session validity check (GET /): Status {check_resp.status_code}, Final URL: {final_url}")

            if final_url.endswith(("/login", "/account-verification", "/2fa")):
                logger.debug("Session check indicates login/verification needed.")
                # Proceed to full login flow below
            elif check_resp.status_code == 200:
                 logger.debug("Session appears to be valid based on GET /. Skipping login.")
                 # Save cookies just in case they were updated by the check
                #  self._session.cookies.save(ignore_discard=True)
                 return # Session is valid
            else:
                 logger.warning(f"Session check GET / resulted in unexpected state: Status {check_resp.status_code}, URL {final_url}")
                 # Proceed to login flow just in case

        except requests.exceptions.RequestException as e:
            logger.warning(f"Session validity check failed with exception: {e}. Proceeding with login attempt.")
            # Fall through to login attempt

        # 2. Perform full login/verification flow if check failed or indicated need
        logger.debug("Performing full login/verification flow.")
        try:
            # Get login page first, follow redirects to see where we land
            # login_page_resp = self._session.get(self.create_url("/login"), follow_redirects=True)
            login_page_resp = self._session.get(self.create_url("/login"), allow_redirects=True)
            login_page_resp.raise_for_status()
            final_login_get_url = str(login_page_resp.url)
            logger.debug(f"GET /login resulted in final URL: {final_login_get_url}")

            if final_login_get_url.endswith("/login"):
                # Landed on login page as expected, proceed with POSTing credentials
                logger.debug("Landed on /login page, calling _do_login.")
                final_resp = self._do_login(login_page_resp)
            elif final_login_get_url.endswith("/account-verification"):
                # GET /login redirected straight to verification
                logger.info("GET /login redirected to basicverification page. Proceeding directly with verification.")
                final_resp = self._complete_verification(login_page_resp)
            elif final_login_get_url.endswith("/2fa"):
                # GET /login redirected straight to verification
                logger.info("GET /login redirected to 2fa verification page. Proceeding directly with verification.")
                final_resp = self._complete_verification_2fa(login_page_resp)
            else:
                # GET /login redirected somewhere else (likely '/', indicating already logged in)
                logger.info(f"GET /login redirected to {final_login_get_url}. Assuming session is valid and complete.")
                # We trust this redirect indicates success. Save cookies and return.
                # self._session.cookies.save(ignore_discard=True)
                return # Assume success based on redirect

            # 3. Final verification after login/verification attempt
            # (This block now only runs if we went through _do_login or _complete_verification above)
            if str(final_resp.url).endswith(("/login", "/account-verification", "/2fa")):
                logger.error(f"Login/Verification process ended unexpectedly on {final_resp.url}")
                raise SmartSchoolAuthenticationError(f"Authentication failed, ended on {final_resp.url}") # Corrected casing
            elif final_resp.status_code != 200:
                logger.error(f"Login/Verification process ended with status {final_resp.status_code} at {final_resp.url}")
                raise SmartSchoolAuthenticationError(f"Authentication failed, status {final_resp.status_code} at {final_resp.url}") # Corrected casing
            else:
                logger.debug("Login/Verification process completed successfully after _do_login/_complete_verification.")
                # self._session.cookies.save(ignore_discard=True)
                # # After request
                # for cookie in self._session.cookies.jar:
                #     self.cookiejar.set_cookie(http.cookiejar.Cookie(
                #         version=0,
                #         name=cookie.name,
                #         value=cookie.value,
                #         port=None,
                #         port_specified=False,
                #         domain=cookie.domain,
                #         domain_specified=True,
                #         domain_initial_dot=False,
                #         path=cookie.path,
                #         path_specified=True,
                #         secure=cookie.secure,
                #         expires=None,
                #         discard=False,
                #         comment=None,
                #         comment_url=None,
                #         rest={},
                #         rfc2109=False
                #     ))
                # self.cookiejar.save(ignore_discard=True)

        except Exception as e:
            logger.exception("Exception during login/verification process.")
            # Wrap other exceptions in SmartSchoolAuthenticationError
            if not isinstance(e, SmartSchoolAuthenticationError): # Corrected casing
                 raise SmartSchoolAuthenticationError(f"An unexpected error occurred during authentication: {e}") from e # Corrected casing
            else:
                 raise # Re-raise specific auth errors

    def _check_final_authentication(self) -> bool:
        """Helper to perform a final GET / check."""
        logger.debug("Performing _check_final_authentication (GET /)")
        try:
            # check_resp = self._session.get(self.create_url("/"), follow_redirects=True)
            check_resp = self._session.get(self.create_url("/"), allow_redirects=True)
            check_resp.raise_for_status()
            if check_resp.status_code == 200 and not str(check_resp.url).endswith(("/login", "/account-verification", "/2fa")):
                logger.debug("Final authentication check successful.")
                # self._session.cookies.save(ignore_discard=True) # Save potentially updated cookies
                return True
            else:
                logger.error(f"Final authentication check failed: Status {check_resp.status_code}, URL {check_resp.url}")
                return False
        except Exception as e:
            logger.exception(f"Final authentication check failed with exception: {e}")
            return False

    # ... existing __post_init__, create_url etc ...

    # @_handle_cookies_and_login # Decorator applied below methods
    # def post(...)
    # @_handle_cookies_and_login # Decorator applied below methods
    # def get(...)
    # def json(...) # No decorator needed here, calls self.get/self.post

    def _do_login(self, login_page_response: Response) -> Response:
        """
        Handles the login POST and triggers verification if needed.
        Returns the *final* response object after login and potential verification.
        """
        logger.debug("Entering _do_login")
        html = bs4_html(login_page_response)
        inputs = get_all_values_from_form(html, 'form[name="login_form"]')
        if not inputs:
            raise SmartSchoolAuthenticationError("Could not find login form inputs.") # Corrected casing
        logger.debug(f"Found {len(inputs)} inputs in login form")

        # Prepare login data
        data = {}
        username_field_found = False
        password_field_found = False
        for input_ in inputs:
            input_name = input_.get("name")
            input_value = input_.get("value")
            if not input_name: continue

            if "username" in input_name:
                data[input_name] = self.creds.username
                username_field_found = True
            elif "password" in input_name:
                data[input_name] = self.creds.password
                password_field_found = True
            else:
                data[input_name] = input_value

        if not username_field_found or not password_field_found:
             logger.error(f"Did not find both username and password fields in the login form. Fields found: {list(data.keys())}")
             raise SmartSchoolAuthenticationError("Login form parsing failed: Missing username or password field.") # Corrected casing

        logged_data = {k: (v if 'password' not in k else '********') for k, v in data.items()}
        logger.debug(f"Data prepared for login POST: {logged_data}")

        # POST the login form, following redirects
        login_post_url = str(login_page_response.url) # Post back to the same URL we got the form from
        logger.debug(f"Posting login form to {login_post_url}")
        # login_post_resp = self._session.post(login_post_url, data=data, follow_redirects=True)
        login_post_resp = self._session.post(login_post_url, data=data, allow_redirects=True)
        login_post_resp.raise_for_status() # Check for HTTP errors after redirects
        logger.debug(f"Login POST completed. Final URL after redirects: {login_post_resp.url}")

        # Check if verification is needed based on the final URL
        if str(login_post_resp.url).endswith("/account-verification"):
            logger.info("Account basic verification required, calling _complete_verification.")
            # Pass the response containing the verification page HTML
            return self._complete_verification(login_post_resp)
        elif str(login_post_resp.url).endswith("/2fa"):
            logger.info("Account 2fa verification required, calling _complete_verification_2fa.")
            # Pass the response containing the verification page HTML
            return self._complete_verification_2fa(login_post_resp)
        else:
            # If not verification, this is the final response from the login attempt
            return login_post_resp

    def _complete_verification(self, verification_page_response: Response) -> Response:
        """
        Completes the verification step by submitting the birth date.
        Returns the *final* response object after the verification POST.
        """
        logger.debug("Entering _complete_verification")
        html = bs4_html(verification_page_response)
        for script in html.select("script"):
            if script.get("src") or "extend" not in script.text:
                logger.debug(f"extend source scritpt not found or script has src, skipping script tag: {script}")
                continue

            if match := re.search(r"JSON\s*\.\s*parse\s*\(\s*'(.*)'\s*\)\s*\)\s*;?\s*$", script.text, flags=re.IGNORECASE):
                result = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), match.group(1))
                data = json.loads(result.replace("\\\\", "\\"))
                with contextlib.suppress(KeyError, TypeError, IndexError):
                    self.authenticated_user = data["vars"]["authenticatedUser"]
                    logger.debug(f"Authenticated user info extracted: {self.authenticated_user}")
                    break
                    # return
        current_verification_url = str(verification_page_response.url) # URL we are currently on

        # Parse verification form
        logger.debug(f"Parsing verification form... {current_verification_url}")
        inputs = get_all_values_from_form(html, 'form[name="account_verification_form"]')
        if not inputs: inputs = get_all_values_from_form(html, 'form:has(input#account_verification_form__token)') # Fallback
        if not inputs:
            raise SmartSchoolAuthenticationError("Could not find verification form fields") # Corrected casing

        # Prepare verification data
        verification_data = {}
        security_question_field = None
        for input_ in inputs:
            input_name = input_.get("name")
            input_value = input_.get("value")
            if not input_name: continue

            if "_security_question_answer" in input_name:
                security_question_field = input_name
            else:
                verification_data[input_name] = input_value

        if not security_question_field:
            raise SmartSchoolAuthenticationError("Could not find security question field in verification form") # Corrected casing

        # Ensure birth date is present and correctly formatted
        if not hasattr(self.creds, 'mfa') or not self.creds.mfa:
            raise SmartSchoolAuthenticationError("Birth date is required for verification but not provided in credentials") # Corrected casing

        birth_date_str = self.creds.mfa
        if isinstance(birth_date_str, datetime.date):
            birth_date_str = birth_date_str.strftime('%Y-%m-%d')
            logger.debug(f"Formatted birth date from date object to: {birth_date_str}")
        elif isinstance(birth_date_str, str):
            original_birth_date_str = birth_date_str
            birth_date_str = birth_date_str.replace('/', '-')
            if birth_date_str != original_birth_date_str:
                 logger.debug(f"Formatted birth date from string: {birth_date_str}")
        else:
             logger.warning(f"Birth date is of unexpected type: {type(birth_date_str)}. Attempting to use as is.")

        verification_data[security_question_field] = birth_date_str

        logger.debug(f"Verification POST data prepared: {verification_data}")

        # POST the verification form, following redirects
        logger.info(f"POSTing verification data to {current_verification_url}")
        # verification_post_resp = self._session.post(current_verification_url, data=verification_data, follow_redirects=True)
        verification_post_resp = self._session.post(current_verification_url, data=verification_data, allow_redirects=True)
        verification_post_resp.raise_for_status() # Check for HTTP errors after redirects
        logger.debug(f"Verification POST completed. Final URL: {verification_post_resp.url}")

        # Return the final response after the verification POST
        return verification_post_resp



    def _complete_verification_2fa(self, verification_page_response: Response) -> Response:
        """
        Completes the verification step by submitting the birth date.
        Returns the *final* response object after the verification POST.
        """
        logger.debug("Entering _complete_verification_2fa")
        html = bs4_html(verification_page_response)
        for script in html.select("script"):
            if script.get("src") or "extend" not in script.text:
                # logger.debug(f"extend source scritpt not found or script has src, skipping script tag: {script}")
                continue
            # if match := re.search(r"JSON\s*\.\s*parse\s*\(\s*'(.*)'\s*\)\s*\)\s*;?\s*$", script.text, flags=re.IGNORECASE):
            #     result = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), match.group(1))
            #     data = json.loads(result.replace("\\\\", "\\"))
            if match := re.search(r"JSON\s*\.\s*parse\s*\(\s*'(.*)'\s*\)\s*\)\s*;?\s*$",
                                script.text, flags=re.IGNORECASE | re.DOTALL):
                raw = match.group(1)

                # 1) restore escaped single quotes (JS single-quoted string)
                raw = raw.replace("\\'", "'")

                # 2) escape any backslash that is NOT followed by a valid JSON escape char
                #    valid JSON escapes are: " \ / b f n r t and uXXXX
                #    The negative lookahead says: if backslash is followed by none of those, double it.
                safe = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', raw)

                # 3) Now safe should be a valid JSON text string (with \uXXXX preserved).
                try:
                    data = json.loads(safe)
                except json.JSONDecodeError:
                    # Extra fallback: log snippet for debugging and try a gentler unescape
                    logger.debug("json.loads failed on safe string; dumping snippet for inspection")
                    logger.debug("offending snippet: %s", safe[:1000])  # don't log entire huge blob
                    # Optionally try a last-resort unescape via unicode_escape (caveat: may change semantics)
                    try:
                        alt = safe.encode('utf-8').decode('unicode_escape')
                        data = json.loads(alt)
                    except Exception:
                        # re-raise original decode error for the caller
                        raise
                with contextlib.suppress(KeyError, TypeError, IndexError):
                    self.authenticated_user = data["vars"]["authenticatedUser"]
                    logger.debug(f"Authenticated user info extracted: {self.authenticated_user}")
                    break
                    # return
        
        # check_resp = self._session.get(self.create_url("/2fa/api/v1/config"), follow_redirects=True)
        check_resp = self._session.get(self.create_url("/2fa/api/v1/config"), allow_redirects=True)
        check_resp.raise_for_status()
        if check_resp.status_code == 200:
            supported_authentication_methods = json.loads(check_resp.text)
            if not 'googleAuthenticator' in supported_authentication_methods.get('possibleAuthenticationMechanisms',[]):
                raise SmartSchoolAuthenticationError("Could not find supported 2fa verification method, only googleAuthenticator is supported")
        else:
            raise SmartSchoolAuthenticationError("Could not find supported 2fa API endpoint")
        
        totp = pyotp.TOTP(self.creds.mfa)
        code = totp.now()
        # google2fa = {'google2fa':code}
        google2fa = '{"google2fa":"%s"}' % code        
        # self._session.headers['Content-Type'] = "application/x-www-form-urlencoded"
        # googleAuthenticatorResp = self._session.post(self.create_url("/2fa/api/v1/google-authenticator"), data=google2fa, follow_redirects=True)
        googleAuthenticatorResp = self._session.post(self.create_url("/2fa/api/v1/google-authenticator"), data=google2fa, allow_redirects=True)
        googleAuthenticatorResp.raise_for_status()
        
        # Return the final response after the verification POST
        return googleAuthenticatorResp

    # @classmethod
    # def start(cls, creds: Credentials) -> Self:
    #     global session

    #     creds.validate()
    #     session.creds = creds

    #     return session

    # @property
    # def cookie_file(self) -> Path:
    #     return Path.cwd() / "cookies.txt"

    def create_url(self, endpoint: str) -> str:
        return f"{self._url}/{endpoint.lstrip('/')}"
    
    # Re-add create_url method
    # def create_url(self, path: str) -> str:
    #     """Create a full URL from a path."""
    #     return urljoin(self._url, path)

    @cached_property
    def _url(self) -> str:
        return "https://" + self.creds.main_url

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(for: {self.creds.username})"

    # Re-add the json method
    def json(self, url, *args, method: str = "get", **kwargs) -> dict | list:
        """
        Performs a GET or POST request and parses the JSON response.
        Handles potential double JSON encoding.
        """
        logger.debug(f"Calling json method: method={method.upper()}, url={url}")
        if method.lower() == "post":
            logger.debug(f"Making POST request to {url}, args: {args}, with data: {kwargs.get('data', {})}")
            r = self.post(url, *args, **kwargs) # Uses the decorated post method
        else:
            r = self.get(url, *args, **kwargs) # Uses the decorated get method

        logger.debug(f"Response status code: {r.status_code}, URL: {r.url}, response text snippet: {r.text[:200]}")
        json_ = r.text

        try:
            while isinstance(json_, str):
                # Check for empty string before trying to load
                if not json_:
                    logger.warning(f"Empty response text received for {method.upper()} {url}")
                    # Return empty dict for empty response
                    return {} 
                json_ = json.loads(json_)
            return json_
        except json.JSONDecodeError as e:
            logger.error(f"JSONDecodeError encountered for URL: {r.url}")
            logger.error(f"Response status code: {r.status_code}")
            logger.error("--- Response Text Start ---")
            logger.error(r.text[:1000]) # Log the first 1000 characters
            logger.error("--- Response Text End ---")
            # Re-raise the original error with context
            raise json.JSONDecodeError(msg=f"Failed to decode JSON from {r.url}: {e.msg}", doc=r.text, pos=e.pos) from None
        except Exception as e:
             logger.exception(f"Unexpected error parsing JSON response from {r.url}")
             raise # Re-raise other unexpected errors

    # Original post and get methods (before decoration)
    # These are needed so the decorator can wrap them.
    def post(self, url, *args, **kwargs) -> Response:
        return self._session.post(self.create_url(url), *args, **kwargs)

    def get(self, url, *args, **kwargs) -> Response:
        return self._session.get(self.create_url(url), *args, **kwargs)


session: Smartschool = Smartschool()
