import json
import logging
import pprint
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import List
import requests
from pydantic import BaseModel
from enum import Enum
import re
import urllib.parse
from ratelimit import limits, sleep_and_retry

import voluptuous as vol
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

TELENET_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.0%z"

def check_settings(config, hass):
    if not any(config.get(i) for i in ["username"]):
        _LOGGER.error("username was not set")
    else:
        return True
    if not config.get("password"):
        _LOGGER.error("password was not set")
    else:
        return True

    raise vol.Invalid("Missing settings to setup the sensor.")

class HttpMethod(Enum):
    GET = 'GET'
    POST = 'POST'
    PUT = 'PUT'
    PATCH = 'PATCH'
    DELETE = 'DELETE'
    HEAD = 'HEAD'
    OPTIONS = 'OPTIONS'
    

from .smartschool_api import (
    Smartschool,
    AppCredentials,
    FutureTasks,
)

class ComponentSession(object):
    def __init__(self):
        self.session = None
        self.creds = None

    
    @sleep_and_retry
    @limits(calls=1, period=5)
    def login(self, username, password, smartschool_domain, birth_date):
        _LOGGER.info("Trying to login to Smartschool")
        self.creds = AppCredentials(username, password, smartschool_domain, birth_date)
        self.session = Smartschool.start(self.creds)
        return {}

