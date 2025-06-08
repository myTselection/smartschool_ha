import logging
import asyncio
from datetime import date, datetime, timedelta
import random

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity, SensorDeviceClass
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import Entity, DeviceInfo
from homeassistant.util import Throttle

from . import DOMAIN, NAME
from .utils import *

_LOGGER = logging.getLogger(__name__)
_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.0%z"


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required("username"): cv.string,
        vol.Required("password"): cv.string,
    }
)

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=120 + random.uniform(10, 20))


async def dry_setup(hass, config_entry, async_add_devices):
    config = config_entry
    username = config.get("username")
    password = config.get("password")
    smartschool_domain = config.get("smartschool_domain")

    check_settings(config, hass)
    sensors = []
    
    componentData = ComponentData(
        username,
        password,
        smartschool_domain,
        async_get_clientsession(hass),
        hass
    )
    await componentData._force_update()
    
    sensorUser = ComponentUserSensor(componentData, hass)
    sensors.append(sensorUser)
        
    async_add_devices(sensors)


async def async_setup_platform(
    hass, config_entry, async_add_devices, discovery_info=None
):
    """Setup sensor platform for the ui"""
    _LOGGER.info("async_setup_platform " + NAME)
    await dry_setup(hass, config_entry, async_add_devices)
    return True


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Setup sensor platform for the ui"""
    _LOGGER.info("async_setup_entry " + NAME)
    config = config_entry.data
    await dry_setup(hass, config, async_add_devices)
    return True


async def async_remove_entry(hass, config_entry):
    _LOGGER.info("async_remove_entry " + NAME)
    try:
        await hass.config_entries.async_forward_entry_unload(config_entry, "sensor")
        _LOGGER.info("Successfully removed sensor from the integration")
    except ValueError:
        pass
        

class ComponentData:
    def __init__(self, username, password, smartschool_domain, client, hass):
        self._username = username
        self._password = password
        self._smartschool_domain = smartschool_domain
        self._client = client
        self._hass = hass
        self._session = ComponentSession()
        self._userdetails = None
        self._lastupdate = None
        
    # same as update, but without throttle to make sure init is always executed
    async def _force_update(self):
        _LOGGER.info("Fetching update stuff for " + NAME)
        if not(self._session):
            self._session = ComponentSession()

        if self._session:
            self._userdetails = await self._hass.async_add_executor_job(lambda: self._session.login(self._username, self._password, self._smartschool_domain))
            assert self._userdetails is not None
            _LOGGER.debug(f"{NAME} update login completed")
            # for user_id, userdetail in self._userdetails.items():
            #     url = userdetail.get('loans').get('url')
            #     if url:
            #         _LOGGER.info(f"Calling loan details {userdetail.get('account_details').get('userName')}")
            #         loandetails = await self._hass.async_add_executor_job(lambda: self._session.loan_details(url))
            #         assert loandetails is not None
            #         username = userdetail.get('account_details').get('userName')
            #         barcode = userdetail.get('account_details').get('barcode')
            #         barcode_spell = userdetail.get('account_details').get('barcode_spell')
            #         for loan_info in loandetails.values():
            #             loan_info["user"] = username
            #             loan_info["userid"] = user_id
            #             loan_info["barcode"] = barcode
            #             loan_info["barcode_spell"] = barcode_spell
            #             libraryName = loan_info.get('library')
            #             libraryurl = f"{loan_info['url'].split('/resolver')[0]}/adres-en-openingsuren"
            #             if not self._librarydetails.get(libraryName):
            #                 _LOGGER.info(f"Calling library details {userdetail.get('account_details').get('userName')}")
            #                 librarydetails = await self._hass.async_add_executor_job(lambda: self._session.library_details(libraryurl))
            #                 assert librarydetails is not None
            #                 self._librarydetails[libraryName] = librarydetails
            #         _LOGGER.debug(f"loandetails {json.dumps(loandetails,indent=4)}") 
            #         self._loandetails[user_id] = loandetails

            self._lastupdate = datetime.now()
                
    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def _update(self):
        await self._force_update()

    async def update(self):        
        await self._update()
    
    def clear_session(self):
        self._session : None


    @property
    def unique_id(self):
        return f"{NAME} {self._username}"
    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self.unique_id

class ComponentUserSensor(Entity):
    def __init__(self, data, hass):
        self._data = data
        self._hass = hass
        self._last_update = None
        self._state = "TEST"
        self._school = "SCHOOL"
        self._username = self._data._username

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    async def async_update(self):
        await self._data.update()
        self._last_update =  self._data._lastupdate
        self._school = None
        
        self._state = "TEST UPDATED"
        self._school = "SCHOOL UPDATED"
        
        
    async def async_will_remove_from_hass(self):
        """Clean up after entity before removal."""
        _LOGGER.info("async_will_remove_from_hass " + NAME)
        self._data.clear_session()


    @property
    def icon(self) -> str:
        """Shows the correct icon for container."""
        return "mdi:bookshelf"
        
    @property
    def unique_id(self) -> str:
        """Return the name of the sensor."""
        return (
            f"{NAME} {self._username} {self._school}"
        )

    @property
    def name(self) -> str:
        return self.unique_id

    @property
    def extra_state_attributes(self) -> dict:
        """Return the state attributes."""
        return {
            ATTR_ATTRIBUTION: NAME,
            "last update": self._last_update,
            "username": self._username,
            "school": self._school,
            "entity_picture": "https://raw.githubusercontent.com/myTselection/smartschool_ha/master/icon.png",
            "state": self._state
        }

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                # Serial numbers are unique identifiers within a specific domain
                (NAME, self._data.unique_id)
            },
            name=self._data.name,
            manufacturer= NAME
        )
    

    @property
    def unit(self) -> int:
        """Unit"""
        return int

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement this sensor expresses itself in."""
        return "TBD"

    @property
    def friendly_name(self) -> str:
        return self.name
        