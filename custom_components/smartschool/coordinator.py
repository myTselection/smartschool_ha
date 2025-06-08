from datetime import datetime, timedelta
import logging

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.components.todo import TodoItem, TodoItemStatus

from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME
)
from .const import (
    CONF_BIRTH_DATE,
    CONF_SMARTSCHOOL_DOMAIN
)

from .storage import ChecklistStatusStorage
from .utils import *

from . import DOMAIN

_LOGGER = logging.getLogger(DOMAIN)

class ComponentUpdateCoordinator(DataUpdateCoordinator):

    def __init__(self, hass, config_entry, refresh_interval):
        super().__init__(hass, _LOGGER, config_entry = config_entry, name = f"{DOMAIN} ChecklistCoordinator", update_interval = timedelta(minutes = refresh_interval))
        self._status_store = ChecklistStatusStorage(hass)
        self._lists = {}  # list_id -> list[TodoItem]
        self._hass = hass
        self._session = ComponentSession()
        config = config_entry.data
        self._username = config.get(CONF_USERNAME)
        self._password = config.get(CONF_PASSWORD)
        self._smartschool_domain = config.get(CONF_SMARTSCHOOL_DOMAIN)
        self._birth_date = config.get(CONF_BIRTH_DATE)
        self._unique_user_id = f"{self._username}_{self._smartschool_domain}"

    async def async_initialize(self):
        
        await self._status_store.async_load()
        await self.async_refresh()

    async def _async_update_data(self):
        # Replace this with real external data source
        # external_data = {
        #     "devops": [
        #         {"uid": "abc", "summary": "Deploy release"},
        #         {"uid": "def", "summary": "Restart server"},
        #     ],
        #     "household": [
        #         {"uid": "xyz", "summary": "Clean garage"},
        #     ]
        # }

        # Structure:
        # {
        #     "Taak": [
        #         {
        #             "uid": "abc",
        #             "summary": "Deploy release"
        #         },
        #         {
        #             "uid": "def",
        #             "summary": "Restart server"
        #         }
        #     ],
        #     "Toets": [
        #         {
        #             "uid": "xyz",
        #             "summary": "Clean garage"
        #         }
        #     ],
        #     "Meebrengen / afwerken": [
        #         {
        #             "uid": "xyz",
        #             "summary": "Clean garage"
        #         }
        #     ]
        # }

        _LOGGER.debug(f"{DOMAIN} ComponentUpdateCoordinator update started, username: {self._username}, smartschool_domain: {self._smartschool_domain}, birth_date: {self._birth_date}")
        if not(self._session):
            self._session = ComponentSession()

        if self._session:
            self._userdetails = await self._hass.async_add_executor_job(lambda: self._session.login(self._username, self._password, self._smartschool_domain, self._birth_date))
            assert self._userdetails is not None

            future_tasks = await self._hass.async_add_executor_job(lambda: self._session.getFutureTasks())
            _LOGGER.debug(f"{DOMAIN} external data: {future_tasks}")
            _LOGGER.debug(f"{DOMAIN} update login completed")

            self._lastupdate = datetime.now()

        new_lists = {
            "taken": [],
            "toetsen": [],
            "meebrengen": []
        }

        try:
            for day in future_tasks.days:
                for course in day.courses:
                    for task in course.items.tasks:
                        if task.label == "Taak":
                            list_id = "taken"
                        elif task.label == "Toets":
                            list_id = "toetsen"
                        else:
                            list_id = "meebrengen"
                        
                        status = self._status_store.get_status(self._unique_user_id, task.assignmentID)
                        new_lists[list_id].append(TodoItem(
                            uid=task.assignmentID,
                            summary=course.course_title,
                            status=TodoItemStatus(status),
                            description=task.description
                            # due=task.date
                        ))

        except Exception as e:
            _LOGGER.error(f"Error future tasks: {e}")


            
        # for list_id, items in future_tasks.items():
        #     todo_items = []
        #     for item in items:
        #         status = self._status_store.get_status(list_id, item["uid"])
        #         todo_items.append(TodoItem(
        #             uid=item["uid"],
        #             summary=item["summary"],
        #             status=TodoItemStatus(status)
        #         ))
        #     new_lists[list_id] = todo_items

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

    async def update_status(self, unique_user_id, uid, status):
        self._status_store.set_status(unique_user_id, uid, status)
        await self._status_store.async_save()

    async def delete_status(self, unique_user_id, uid):
        self._status_store.delete_status(unique_user_id, uid)
        await self._status_store.async_save()

    async def remove_list(self, list_id: str, unique_user_id: str):
        """Remove a to-do list and its saved statuses."""
        if list_id in self._lists:
            del self._lists[list_id]
        if unique_user_id in self._status_store._data:
            del self._status_store._data[unique_user_id]
            await self._status_store.async_save()