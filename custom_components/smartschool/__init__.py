import logging
import json
from pathlib import Path

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import Platform
from .utils import *
from homeassistant.const import (
    CONF_NAME,
    CONF_PASSWORD,
    CONF_RESOURCES,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    EVENT_HOMEASSISTANT_STOP,
    Platform
)
from homeassistant.core import (
    HomeAssistant,
    ServiceResponse,
    SupportsResponse
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .coordinator import ComponentUpdateCoordinator

from .const import (
    CONF_MFA,
    CONF_SMARTSCHOOL_DOMAIN,
    CONF_REFRESH_INTERVAL
)

manifestfile = Path(__file__).parent / 'manifest.json'
with open(manifestfile, 'r') as json_file:
    manifest_data = json.load(json_file)
    
DOMAIN = manifest_data.get("domain")
NAME = manifest_data.get("name")
VERSION = manifest_data.get("version")
ISSUEURL = manifest_data.get("issue_tracker")
PLATFORMS = [Platform.SENSOR, Platform.TODO]
# PLATFORMS = [Platform.TODO]

STARTUP = """
-------------------------------------------------------------------
{name}
Version: {version}
This is a custom component
If you have any issues with this you need to open an issue here:
{issueurl}
-------------------------------------------------------------------
""".format(
    name=NAME, version=VERSION, issueurl=ISSUEURL
)


_LOGGER = logging.getLogger(__name__)


# async def async_setup(hass: HomeAssistant, config: ConfigType):
#     """Set up this component using YAML."""
#     _LOGGER.info(STARTUP)
#     if config.get(DOMAIN) is None:
#         # We get here if the integration is set up using config flow
#         return True

#     try:
#         await hass.config_entries.async_forward_entry(config, Platform.SENSOR)
#         _LOGGER.info("Successfully added platform from the integration")
#     except ValueError:
#         pass

#     await hass.config_entries.flow.async_init(
#             DOMAIN, context={"source": config_entries.SOURCE_IMPORT}, data={}
#         )
#     return True

async def async_update_options(hass: HomeAssistant, config_entry: ConfigEntry):
    await hass.config_entries.async_reload(config_entry.entry_id)

async def update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    """Reload integration when options changed"""
    await hass.config_entries.async_reload(config_entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Flag that a reload is in progress
    hass.data[DOMAIN]["reloading"] = True

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    hass.data[DOMAIN].pop("reloading", None)
    return unload_ok


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up component as config entry."""
    refresh_interval = config_entry.options.get(CONF_REFRESH_INTERVAL, 30)
    # refresh_interval = 1 #DEBUG
    _LOGGER.debug(f"{DOMAIN} async_setup_entry refresh_interval : {refresh_interval}")
    coordinator = ComponentUpdateCoordinator(hass, config_entry, refresh_interval)
    await coordinator.async_initialize() 
    
    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = {
        "coordinator": coordinator
    }
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    config_entry.async_on_unload(config_entry.add_update_listener(async_update_options))
    _LOGGER.info(f"{DOMAIN} register_services")
    register_services(hass, config_entry)
    return True


async def async_remove_entry(hass, config_entry):
    try:
        for platform in PLATFORMS:
            await hass.config_entries.async_forward_entry_unload(config_entry, platform)
            _LOGGER.info("Successfully removed sensor from the integration")
    except ValueError:
        pass


def register_services(hass, config_entry):
        
    async def handle_manual_refresh(call):
        """Handle the service call."""
        coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
        await coordinator.async_request_refresh()
        

    hass.services.async_register(DOMAIN, 'manual_refresh', handle_manual_refresh)
    _LOGGER.info(f"async_register done")