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
    CONF_SMARTSCHOOL_DOMAIN,
    LIST_TAKEN,
    LIST_TOETSEN,
    LIST_MEEBRENGEN,
    LIST_VOLGENDE,
    TASK_LABEL_TAAK,
    TASK_LABEL_TOETS
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
            
            agenda = await self._hass.async_add_executor_job(lambda: self._session.getAgenda())
            _LOGGER.debug(f"{DOMAIN} update login completed")

            self._lastupdate = datetime.now()

        current_list_taken = f"{LIST_TAKEN} ({self._username})"
        current_list_toetsen = f"{LIST_TOETSEN} ({self._username})"
        current_list_meebrengen = f"{LIST_MEEBRENGEN} ({self._username})"
        current_list_volgende = f"{LIST_VOLGENDE} ({self._username})"
        new_lists = {
            current_list_taken: [],
            current_list_toetsen: [],
            current_list_meebrengen: [],
            current_list_volgende: []
        }

        valid_uids = set()

        if len(agenda) > 0:
            next_schoolday = agenda[0].date
            _LOGGER.debug(f"{DOMAIN} next schoolday: {next_schoolday}")
        

        for day in future_tasks.days:
            for course in day.courses:
                for task in course.items.tasks:
                    
                    # course_name = course.course_title.split(" - ")[1] if " - " in course.course_title else course.course_title
                    course_name = task.course
                    lesson_hour = course.course_title.split(" - ")[0] if " - " in course.course_title else ""
                    summary = f"{course_name} ({lesson_hour}e u)"
                    description = task.description
                    if task.label == TASK_LABEL_TAAK:
                        list_id = current_list_taken
                    elif task.label == TASK_LABEL_TOETS:
                        list_id = current_list_toetsen
                    else:
                        list_id = current_list_meebrengen
                        description = f"{course_name} ({lesson_hour}e u)"
                        summary = task.description

                    valid_uids.add(task.assignmentID)
                    status = self._status_store.get_status(self._unique_user_id, task.assignmentID)
                    new_lists[list_id].append(TodoItem(
                        uid=task.assignmentID,
                        summary=summary,
                        status=TodoItemStatus(status),
                        description=description,
                        due=task.date
                    ))
                    
                    if next_schoolday and task.date == next_schoolday:
                        new_lists[current_list_volgende].append(TodoItem(
                            uid=task.assignmentID,
                            summary=f"{task.label}: {summary}",
                            status=TodoItemStatus(status),
                            description=description,
                            due=task.date
                        ))

        if len(valid_uids) > 0: # Only remove unused items if we have valid_uids.
            self._status_store.remove_unused_items(self._unique_user_id, valid_uids)




        self._lists = new_lists
        return self._lists

    def get_items(self, list_id):
        return self._lists.get(list_id, [])

    async def update_status(self, unique_user_id, uid, status):
        self._status_store.set_status(unique_user_id, uid, status)
        await self._status_store.async_save()
        await self.async_refresh()

    async def delete_status(self, unique_user_id, uid):
        self._status_store.delete_status(unique_user_id, uid)
        await self._status_store.async_save()

    async def remove_list(self, list_id: str, unique_user_id: str):
        """Remove a to-do list and its saved statuses."""
        _LOGGER.info("Removing list %s for user %s", list_id, unique_user_id)
        if list_id in self._lists:
            del self._lists[list_id]
        if unique_user_id in self._status_store._data:
            del self._status_store._data[unique_user_id]
            await self._status_store.async_save()