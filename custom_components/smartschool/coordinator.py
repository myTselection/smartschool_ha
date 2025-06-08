from datetime import datetime, timedelta
import logging

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.components.todo import TodoItem, TodoItemStatus
from .storage import ChecklistStatusStorage

from . import DOMAIN

_LOGGER = logging.getLogger(DOMAIN)

class ComponentUpdateCoordinator(DataUpdateCoordinator):

    def __init__(self, hass, config_entry, refresh_interval):
        super().__init__(hass, _LOGGER, config_entry = config_entry, name = f"{DOMAIN} ChecklistCoordinator", update_interval = timedelta(minutes = refresh_interval))
        self._status_store = ChecklistStatusStorage(hass)
        self._lists = {}  # list_id -> list[TodoItem]
        self.hass = hass

    async def async_initialize(self):
        
        await self._status_store.async_load()
        await self.async_refresh()

    async def _async_update_data(self):
        # Replace this with real external data source
        external_data = {
            "devops": [
                {"uid": "abc", "summary": "Deploy release"},
                {"uid": "def", "summary": "Restart server"},
            ],
            "household": [
                {"uid": "xyz", "summary": "Clean garage"},
            ]
        }

        new_lists = {}
        for list_id, items in external_data.items():
            todo_items = []
            for item in items:
                status = self._status_store.get_status(list_id, item["uid"])
                todo_items.append(TodoItem(
                    uid=item["uid"],
                    summary=item["summary"],
                    status=TodoItemStatus(status)
                ))
            new_lists[list_id] = todo_items

        self._lists = new_lists
        return self._lists

    # async def _async_update_data(self):
    #     # code, items = await self.hass.data[DOMAIN].get_detailed_items(self.list_name)
    #     items = [{"id" : "id1",
    #               "name" : "name1",
    #               "list" : "list1",
    #               "checked" : True,
    #               "notes" : "notes1"},
    #               {"id" : "id2",
    #               "name" : "name2",
    #               "list" : "list1",
    #               "checked" : False,
    #               "notes" : "notes2"},
    #               {"id" : "id3",
    #               "name" : "name3",
    #               "list" : "list3",
    #               "checked" : True,
    #               "notes" : "notes3"},
    #               {"id" : "id4",
    #               "name" : "test2item",
    #               "list" : "Test2",
    #               "checked" : False,
    #               "notes" : "notes3",
    #               "duedate": datetime(2025, 6, 10, 18, 0)}
    #     ]
    #     return items
    def get_items(self, list_id):
        return self._lists.get(list_id, [])

    async def update_status(self, list_id, uid, status):
        self._status_store.set_status(list_id, uid, status)
        await self._status_store.async_save()

    async def delete_status(self, list_id, uid):
        self._status_store.delete_status(list_id, uid)
        await self._status_store.async_save()

    async def remove_list(self, list_id: str):
        """Remove a to-do list and its saved statuses."""
        if list_id in self._lists:
            del self._lists[list_id]
        if list_id in self._status_store._data:
            del self._status_store._data[list_id]
            await self._status_store.async_save()