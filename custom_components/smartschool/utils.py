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
    

from .smartschool_api import (
    Smartschool,
    AppCredentials,
    FutureTasks,
    SmartschoolLessons, 
    Results,
    MessageHeaders
)

class ComponentSession(object):
    def __init__(self):
        self.smartschool = None
        self.creds = None

    
    @sleep_and_retry
    @limits(calls=1, period=5)
    def login(self, username, password, smartschool_domain, mfa):
        _LOGGER.info("Trying to login to Smartschool")
        self.creds = AppCredentials(username, password, smartschool_domain, mfa)
        self.smartschool = Smartschool(creds=self.creds)
        return {}

    @sleep_and_retry
    @limits(calls=1, period=5)
    def getFutureTasks(self):
        return FutureTasks(self.smartschool)

    @sleep_and_retry
    @limits(calls=1, period=5)
    def getAgenda(self, timestamp_to_use: datetime | None = None):
        agenda = list(SmartschoolLessons(self.smartschool, timestamp_to_use=timestamp_to_use))
        return agenda

    @sleep_and_retry
    @limits(calls=1, period=5)
    def getResults(self):
        results = list(Results(self.smartschool))
        return results
    
    @sleep_and_retry
    @limits(calls=1, period=5)
    def getMessages(self, timestamp_to_use: datetime | None = None):
        agenda = list(MessageHeaders(self.smartschool))
        return agenda