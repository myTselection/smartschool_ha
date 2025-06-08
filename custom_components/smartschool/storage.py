from homeassistant.helpers.storage import Store
import logging
from . import DOMAIN
_LOGGER = logging.getLogger(DOMAIN)

class ChecklistStatusStorage:
    def __init__(self, hass):
        self._store = Store(hass, 1, "checklist_status")
        self._data = {}  # list_id -> { uid -> status }

    async def async_load(self):
        self._data = await self._store.async_load() or {}

    async def async_save(self):
        await self._store.async_save(self._data)

    def get_status(self, list_id: str, uid: str) -> str:
        status= self._data.get(list_id, {}).get(uid, "needs_action")
        _LOGGER.debug("get_status %s %s %s", list_id, uid, status)
        return status

    def set_status(self, list_id: str, uid: str, status: str):
        if list_id not in self._data:
            self._data[list_id] = {}
        self._data[list_id][uid] = status

    def delete_status(self, list_id: str, uid: str):
        if list_id in self._data:
            self._data[list_id].pop(uid, None)

    def remove_unused_items(self, list_id: str, valid_uids: set):
        # Remove anything not in the latest data set
        if list_id in self._data:
            self._data[list_id] = {k: v for k, v in self._data[list_id].items() if k in valid_uids}
