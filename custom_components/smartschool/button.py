import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.const import CONF_USERNAME
from homeassistant.helpers.entity import DeviceInfo

from . import NAME
from .const import CONF_SMARTSCHOOL_DOMAIN, DOMAIN
from .coordinator import ComponentUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    async_add_entities([ComponentMarkMessagesReadButton(coordinator, config_entry.data)])
    return True


class ComponentMarkMessagesReadButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:email-check"
    _attr_name = "Mark all unread messages read"

    def __init__(self, coordinator: ComponentUpdateCoordinator, config: dict):
        self.coordinator = coordinator
        self._username = config.get(CONF_USERNAME)
        self._school = config.get(CONF_SMARTSCHOOL_DOMAIN).replace(".smartschool.be", "")
        self._device_unique_id = f"{NAME} {self._username} {self._school}"
        self._attr_unique_id = f"{DOMAIN}_{self._username}_{self._school}_mark_all_messages_read"

    async def async_press(self) -> None:
        marked_count = await self.coordinator.async_mark_all_unread_messages_read()
        _LOGGER.debug("Marked %s Smartschool messages as read", marked_count)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(NAME, self._device_unique_id)},
            name=self._device_unique_id.title(),
            manufacturer=NAME,
        )
