from datetime import datetime, timedelta
import logging

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.components.todo import TodoItem, TodoItemStatus

from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME
)
from .const import (
    DOMAIN,
    CONF_MFA,
    CONF_SMARTSCHOOL_DOMAIN,
    LIST_TAKEN,
    LIST_TOETSEN,
    LIST_MEEBRENGEN,
    LIST_VOLGENDE,
    LIST_SCHOOLTAS,
    TASK_LABEL_TAAK,
    TASK_LABEL_TOETS,
    TASK_LABEL_MEEBRENGEN
)

from .storage import ChecklistStatusStorage
from .utils import *


_LOGGER = logging.getLogger(DOMAIN)

class ComponentUpdateCoordinator(DataUpdateCoordinator):

    def __init__(self, hass, config_entry, refresh_interval):
        self._config = config_entry.data
        self._username = self._config.get(CONF_USERNAME)
        self._password = self._config.get(CONF_PASSWORD)
        self._smartschool_domain = self._config.get(CONF_SMARTSCHOOL_DOMAIN)
        self._mfa = self._config.get(CONF_MFA)
        self._unique_user_id = f"{self._username}_{self._smartschool_domain}"
        super().__init__(hass, _LOGGER, config_entry = config_entry, name = f"{DOMAIN} ChecklistCoordinator {self._unique_user_id}", update_method=self._async_update_data, update_interval = timedelta(minutes = refresh_interval))
        self._status_store = ChecklistStatusStorage(hass)
        
        self._lists = {}  # list_id -> list[TodoItem]
        self._hass = hass
        self._session = ComponentSession()
        self._agenda = None
        
        #  🇫🇷🇳🇱✝️🌎🎼🏛️🏺📜🧮🟰🏀🎨🤯🚸
        self._course_icons = {
                "FR": "🇫🇷 ",
                "NE": "🇳🇱 ",
                "EN": "🇬🇧 ",
                "DE": "🇩🇪 ",
                "SP": "🇪🇸 ",
                "GO": "✝️ ",
                "AA": "🌎 ",
                "MU": "🎼 ",
                "LA": "🏛️ ",
                "GR": "🏺 ",
                "GE": "📜 ",
                "LO": "🏀 ",
                "BE": "🎨 ",
                "WI": "🧮 ",
                "M&S": "🚸 ",
                "TE": "🪛 ",
                "NW": "🧪 ",
                "CH": "🧪 "
        }

    async def async_initialize(self):
        await self._status_store.async_load()
        await self.async_config_entry_first_refresh()
        
        # await self._status_store.async_load()
        # await self.async_refresh()

    async def _async_update_data(self):

        _LOGGER.debug(f"{DOMAIN} ComponentUpdateCoordinator update started, username: {self._username}, smartschool_domain: {self._smartschool_domain}, mfa: *******")
        if not(self._session):
            self._session = ComponentSession()

        if self._session:
            self._userdetails = await self._hass.async_add_executor_job(lambda: self._session.login(self._username, self._password, self._smartschool_domain, self._mfa))
            assert self._userdetails is not None

            self._future_tasks = await self._hass.async_add_executor_job(lambda: self._session.getFutureTasks())
            _LOGGER.debug(f"{DOMAIN} external data: {self._future_tasks}")
            
            agenda_timestamp_to_use = datetime.now()
            now = datetime.now()
            if now.hour >= 16:
                agenda_timestamp_to_use=date.today() + timedelta(days=1)
            

            self._agenda = await self._hass.async_add_executor_job(lambda: self._session.getAgenda(agenda_timestamp_to_use))
            _LOGGER.debug(f"{DOMAIN} update login completed")

            self._lastupdate = datetime.now()

        await self._async_local_refresh_data()
        return self._lists
    
    
    async def _async_local_refresh_data(self):        
        current_list_taken = f"{LIST_TAKEN} ({self._username})"
        current_list_toetsen = f"{LIST_TOETSEN} ({self._username})"
        current_list_meebrengen = f"{LIST_MEEBRENGEN} ({self._username})"
        current_list_volgende = f"{LIST_VOLGENDE} ({self._username})"
        current_list_schooltas = f"{LIST_SCHOOLTAS} ({self._username})"
        new_lists = {
            current_list_taken: [],
            current_list_toetsen: [],
            current_list_meebrengen: [],
            current_list_volgende: [],
            current_list_schooltas: []
        }

        valid_uids = set()

        if len(self._agenda) > 0:
            next_schoolday = self._agenda[0].date
            _LOGGER.debug(f"{DOMAIN} next schoolday: {next_schoolday}")
        

        for day in self._future_tasks.days:
            for course in day.courses:
                for task in course.items.tasks:
                    
                    # course_name = course.course_title.split(" - ")[1] if " - " in course.course_title else course.course_title
                    course_name = task.course
                    course_icon = self._course_icons.get(course_name,"")
                    lesson_hour = course.course_title.split(" - ")[0] if " - " in course.course_title else ""
                    summary = f"{course_icon}{course_name} ({lesson_hour}e u)"
                    task_type = task.label.replace(" / afwerken", "")
                    description = task.description
                    if task.label == TASK_LABEL_TAAK:
                        list_id = current_list_taken
                        action_icon = "🛠️"
                    elif task.label == TASK_LABEL_TOETS:
                        list_id = current_list_toetsen
                        action_icon = "💡"
                        # action_icon = "🤯"
                    else:
                        list_id = current_list_meebrengen
                        description = f"{course_icon}{course_name} ({lesson_hour}e u)"
                        summary = task.description
                        action_icon = "🎒"

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
                        summary_next = f"{action_icon} {course_icon}{course_name}: {task_type} ({lesson_hour}e u)"
                        description_next = task.description
                        new_lists[current_list_volgende].append(TodoItem(
                            uid=task.assignmentID,
                            summary=f"{summary_next}",
                            status=TodoItemStatus(status),
                            description=description_next,
                            due=task.date
                        ))

                        
                        if task.label == TASK_LABEL_MEEBRENGEN:
                            new_lists[current_list_schooltas].append(TodoItem(
                                uid=task.assignmentID,
                                summary=summary_next,
                                status=TodoItemStatus(status),
                                description=description_next,
                                due=task.date
                            ))


        #School bag list
        for agendaitem in self._agenda:
            if agendaitem.date == next_schoolday:
                course_icon = self._course_icons.get(agendaitem.course,"")
                status = self._status_store.get_status(self._unique_user_id, agendaitem.momentID)
                summary = f"{course_icon}{agendaitem.course} {agendaitem.hour}"
                description = f"{agendaitem.subject + "\n" if agendaitem.subject else ''}{agendaitem.classroom}, {agendaitem.teacher}\n{agendaitem.hourValue}"
                valid_uids.add(agendaitem.momentID)
                new_lists[current_list_schooltas].append(TodoItem(
                    uid=agendaitem.momentID,
                    summary=summary,
                    status=TodoItemStatus(status),
                    description=description,
                    due=agendaitem.date
                ))
            else:
                break

        if len(valid_uids) > 0: # Only remove unused items if we have valid_uids.
            _LOGGER.debug(f"{DOMAIN} valid uids: {valid_uids}, list {self._unique_user_id}")
            # self._status_store.remove_unused_items(self._unique_user_id, valid_uids)

        self._lists = new_lists
        return self._lists

    def get_items(self, list_id):
        return self._lists.get(list_id, [])

    async def update_status(self, unique_user_id, uid, status):
        self._status_store.set_status(unique_user_id, uid, status)
        await self._status_store.async_save()
        await self._async_local_refresh_data()

    async def delete_status(self, unique_user_id, uid):
        self._status_store.delete_status(unique_user_id, uid)
        await self._status_store.async_save()

    async def remove_list(self, list_id: str, unique_user_id: str):
        """Remove a to-do list and its saved statuses."""
        _LOGGER.info(f"Removing list {list_id} for user {unique_user_id}")
        if list_id in self._lists:
            del self._lists[list_id]
        if unique_user_id in self._status_store._data:
            del self._status_store._data[unique_user_id]
            await self._status_store.async_save()