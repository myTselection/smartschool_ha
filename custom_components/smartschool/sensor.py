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
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME
)
from .const import (
    CONF_MFA,
    CONF_SMARTSCHOOL_DOMAIN
)

_LOGGER = logging.getLogger(__name__)
_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.0%z"


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_SMARTSCHOOL_DOMAIN): cv.string,
        vol.Required(CONF_MFA): cv.string,
    }
)

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=120 + random.uniform(10, 20))



async def async_setup_entry(hass, config_entry, async_add_devices):
    """Setup sensor platform for the ui"""
    _LOGGER.info("async_setup_entry " + NAME)
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    config = config_entry.data
    await dry_setup(hass, config, async_add_devices, coordinator)
    return True


async def async_remove_entry(hass, config_entry):
    _LOGGER.info("async_remove_entry " + NAME)
    try:
        await hass.config_entries.async_forward_entry_unload(config_entry, "sensor")
        _LOGGER.info("Successfully removed sensor from the integration")
    except ValueError:
        pass
        

async def dry_setup(hass, config_entry, async_add_devices, coordinator):
    config = config_entry
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)
    smartschool_domain = config.get(CONF_SMARTSCHOOL_DOMAIN)
    mfa = config.get(CONF_MFA)

    check_settings(config, hass)
    sensors = []
    
    componentData = ComponentData(
        username,
        password,
        smartschool_domain,
        mfa,
        async_get_clientsession(hass),
        hass, 
        coordinator
    )
    
    sensorTasks = ComponentUserSensor(componentData, hass)
    sensors.append(sensorTasks)
    sensorMessages = ComponentMessageSensor(componentData, hass)
    sensors.append(sensorMessages)
    sensorResults = ComponentResultsSensor(componentData, hass)
    sensors.append(sensorResults)
        
    async_add_devices(sensors)


class ComponentData:
    def __init__(self, username, password, smartschool_domain, mfa, client, hass, coordinator):
        self._username = username
        self._password = password
        self._smartschool_domain = smartschool_domain
        self._school = self._smartschool_domain.replace(".smartschool.be", "")
        self._mfa = mfa
        self._client = client
        self._hass = hass
        self._coordinator = coordinator
        self._userdetails = None
        self._lastupdate = None
        self._number_of_tasks_next = None
        self._number_of_read_messages = None
        self._number_of_outstanding_messages = None
        self._total_number_of_messages = None
        self._total_result = None
        

    async def update(self):        
        await self._coordinator._async_local_refresh_data()
        self._lastupdate = self._coordinator.get_last_updated()
        self._number_of_tasks_next = self._coordinator.get_number_of_tasks_next()
        self._number_of_read_messages = self._coordinator.get_number_of_read_messages()
        self._number_of_outstanding_messages = self._coordinator.get_number_of_outstanding_messages()
        self._total_number_of_messages = self._coordinator.get_total_number_of_messages()
        self._total_result = self._coordinator.get_total_result()

    @property
    def unique_id(self):
        return f"{NAME} {self._username} {self._school}"
    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self.unique_id.title()

class ComponentUserSensor(Entity):
    def __init__(self, data, hass):
        self._data = data
        self._hass = hass
        self._last_update = None
        self._school = self._data._smartschool_domain.replace(".smartschool.be", "")
        self._username = self._data._username

    @property
    def state(self) -> int | None:
        """Return the state of the sensor."""
        # return self._last_update.strftime("%Y-%m-%d %H:%M:%S") if self._last_update else None
        return self._data._number_of_tasks_next

    async def async_update(self):
        await self._data.update()
        self._last_update =  self._data._lastupdate
        
        
    async def async_will_remove_from_hass(self):
        """Clean up after entity before removal."""
        _LOGGER.info("async_will_remove_from_hass " + NAME)


    @property
    def icon(self) -> str:
        """Shows the correct icon for container."""
        return "mdi:account-school"
        
    @property
    def unique_id(self) -> str:
        """Return the name of the sensor."""
        return (
            f"{NAME} {self._username} {self._school} tasks"
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
            "entity_picture": "https://raw.githubusercontent.com/myTselection/smartschool_ha/master/icon.png"
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
        return "tasks"

    @property
    def friendly_name(self) -> str:
        return self.name.title()
        

class ComponentMessageSensor(Entity):
    def __init__(self, data, hass):
        self._data = data
        self._hass = hass
        self._last_update = None
        self._school = self._data._smartschool_domain.replace(".smartschool.be", "")
        self._username = self._data._username

    @property
    def state(self) -> int | None:
        """Return the state of the sensor."""
        return self._data._number_of_outstanding_messages

    async def async_update(self):
        await self._data.update()
        self._last_update =  self._data._lastupdate
        
        
    async def async_will_remove_from_hass(self):
        """Clean up after entity before removal."""
        _LOGGER.info("async_will_remove_from_hass " + NAME)


    @property
    def icon(self) -> str:
        """Shows the correct icon for container."""
        return "mdi:email-alert"
        
    @property
    def unique_id(self) -> str:
        """Return the name of the sensor."""
        return (
            f"{NAME} {self._username} {self._school} messages"
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
            "number of read messages": self._data._number_of_read_messages,
            "number of onread messages": self._data._number_of_outstanding_messages,
            "total number of messages": self._data._total_number_of_messages,
            "username": self._username,
            "school": self._school,
            "entity_picture": "https://raw.githubusercontent.com/myTselection/smartschool_ha/master/icon.png"
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
        return "messages"

    @property
    def friendly_name(self) -> str:
        return self.name.title()
    


class ComponentResultsSensor(Entity):
    def __init__(self, data, hass):
        self._data = data
        self._hass = hass
        self._last_update = None
        self._school = self._data._smartschool_domain.replace(".smartschool.be", "")
        self._username = self._data._username

    @property
    def state(self) -> int | None:
        """Return the state of the sensor."""
        return self._data._total_result

    async def async_update(self):
        await self._data.update()
        self._last_update =  self._data._lastupdate
        
        
    async def async_will_remove_from_hass(self):
        """Clean up after entity before removal."""
        _LOGGER.info("async_will_remove_from_hass " + NAME)


    @property
    def icon(self) -> str:
        """Shows the correct icon for container."""
        return "mdi:counter"
        
    @property
    def unique_id(self) -> str:
        """Return the name of the sensor."""
        return (
            f"{NAME} {self._username} {self._school} results"
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
            "total result": self._data._total_result,
            "username": self._username,
            "school": self._school,
            "entity_picture": "https://raw.githubusercontent.com/myTselection/smartschool_ha/master/icon.png"
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
        return "%"

    @property
    def friendly_name(self) -> str:
        return self.name.title()