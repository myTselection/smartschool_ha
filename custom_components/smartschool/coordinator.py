from datetime import datetime, timedelta
import logging

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
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
        self._last_updated = None
        self._hass = hass
        self._session = ComponentSession()
        self._agenda = None
        self._numberOfTasksNext = None
        self._messages = None
        self._results = None
        self._total_result = None
        
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
                "CH": "🧪 ",
                "LEEFS & TRAJ": "🗝️ "
        }

    async def async_initialize(self):
        await self._status_store.async_load()
        await self.async_config_entry_first_refresh()
        
        # await self._status_store.async_load()
        # await self.async_refresh()

    async def _async_update_data(self):
        try:
            _LOGGER.debug(f"{DOMAIN} ComponentUpdateCoordinator update started, username: {self._username}, smartschool_domain: {self._smartschool_domain}, mfa: *******")
            if not(self._session):
                self._session = ComponentSession()

            if self._session:
                self._userdetails = await self._hass.async_add_executor_job(lambda: self._session.login(self._username, self._password, self._smartschool_domain, self._mfa))
                assert self._userdetails is not None

                self._future_tasks = await self._hass.async_add_executor_job(lambda: self._session.getFutureTasks())
                _LOGGER.debug(f"{DOMAIN} external data: {self._future_tasks}")
                
                agenda_timestamp_to_use = datetime.now()
                self._agenda = await self._hass.async_add_executor_job(lambda: self._session.getAgenda(agenda_timestamp_to_use))
                _LOGGER.debug(f"{DOMAIN} update login completed")

                self._messages = await self._hass.async_add_executor_job(lambda: self._session.getMessages())

                self._results = await self._hass.async_add_executor_job(lambda: self._session.getResults())

                self._last_updated = datetime.now()

            await self._async_local_refresh_data()
            return self._lists
        except Exception as err:
            _LOGGER.error(f"{DOMAIN} ComponentUpdateCoordinator update failed, username: {self._username}, smartschool_domain: {self._smartschool_domain}, mfa: *******", exc_info=err)
            raise UpdateFailed(f"Error fetching data: {err}")
    
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
        next_schoolday = None
        number_of_tasks_next = 0

        for agendaItem in self._agenda:
            agendaItemDate = agendaItem.date
            agendaItemHour = agendaItem.hourValue
            if agendaItemHour:
                # Extract the start time part, example value: hourValue: 15:10 - 16:00
                start_time_str = agendaItemHour.split(" - ")[0]  # "15:10"
                # Combine date and time into a single datetime object
                start_datetime = datetime.strptime(f"{agendaItemDate} {start_time_str}", "%Y-%m-%d %H:%M")
                if start_datetime > datetime.now():
                    next_schoolday = agendaItemDate
                    _LOGGER.debug(f"{DOMAIN} next schoolday: {next_schoolday}")
                    break  

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
                        # action_icon = "🤯"
                        action_icon = "💡"
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
                    
                    if task.date == None or task.date == next_schoolday:
                        number_of_tasks_next = number_of_tasks_next + 1
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
        if next_schoolday:
            next_schooldayDate = datetime.strptime(f"{next_schoolday}", "%Y-%m-%d")
            for agendaItem in self._agenda:
                _LOGGER.debug(f"{DOMAIN} agendaItem: {agendaItem}, agendaItem.date: {agendaItem.date}, next_schoolday: {next_schoolday}")
                agendaItemDate = datetime.strptime(f"{agendaItem.date}", "%Y-%m-%d")
                if agendaItem.date == next_schoolday:
                    agendaItemHour = agendaItem.hourValue
                    if agendaItemHour:
                        # Extract the start time part, example value: hourValue: 15:10 - 16:00
                        start_time_str = agendaItemHour.split(" - ")[0]  # "15:10"
                        # Combine date and time into a single datetime object
                        start_datetime = datetime.strptime(f"{agendaItem.date} {start_time_str}", "%Y-%m-%d %H:%M")
                    course_icon = self._course_icons.get(agendaItem.course,"")
                    status = self._status_store.get_status(self._unique_user_id, agendaItem.momentID)
                    summary = f"{course_icon}{agendaItem.course} {agendaItem.hour}"
                    subjectline =  ((agendaItem.subject + ' ') if agendaItem.subject else '') + ((agendaItem.courseTitle + ' ') if agendaItem.courseTitle else '')
                    roomLine = ((agendaItem.classroom + ', ') if agendaItem.classroom else '') + (agendaItem.teacher if agendaItem.teacher else '')
                    timeLine = agendaItem.hourValue
                    # _LOGGER.debug(f"{DOMAIN} subjectline: {subjectline}, roomLine: {roomLine}, timeLine: {timeLine}")
                    description = ((subjectline + '\n') if len(subjectline) > 0 else '') + ((roomLine + '\n') if len(roomLine) > 0 else '') + timeLine
                    agendatItemUid = f"{agendaItem.momentID}-{agendaItem.hourID}-{agendaItem.lessonID}-{agendaItem.date}-{agendaItem.activityID}"
                    valid_uids.add(agendatItemUid)
                    new_lists[current_list_schooltas].append(TodoItem(
                        uid=agendatItemUid,
                        summary=summary,
                        status=TodoItemStatus(status),
                        description=description,
                        due=start_datetime
                    ))
                elif agendaItemDate > next_schooldayDate:
                    break
                else:
                    continue

        if len(valid_uids) > 0: # Only remove unused items if we have valid_uids.
            _LOGGER.debug(f"{DOMAIN} valid uids: {valid_uids}, list {self._unique_user_id}")
            # self._status_store.remove_unused_items(self._unique_user_id, valid_uids)

        self._lists = new_lists
        self._numberOfTasksNext = number_of_tasks_next

        self._number_of_read_messages = 0
        self._number_of_outstanding_messages = 0
        self._total_number_of_messages = 0

        for message in self._messages:
            if message.status == 1:
                self._number_of_read_messages = self._number_of_read_messages + 1
            elif message.status == 0:
                self._number_of_outstanding_messages = self._number_of_outstanding_messages + 1
            self._total_number_of_messages = self._total_number_of_messages + 1

        self._number_of_read_messages
        self._number_of_outstanding_messages
        self._total_number_of_messages

        self._total_result = None
        subtotal = 0
        numberOfResults = 0
        for result in self._results:
            if result.doesCount and result.type == "normal":
                numberOfResults = numberOfResults + 1
                subtotal = subtotal + result.graphic.percentage

        if numberOfResults > 0:
            self._total_result = (subtotal / numberOfResults) * 100
        return

    def get_items(self, list_id):
        return self._lists.get(list_id, [])

    def get_last_updated(self):
        return self._last_updated

    def get_number_of_tasks_next(self):
        return self._numberOfTasksNext

    def get_number_of_read_messages(self):
        return self._number_of_read_messages

    def get_number_of_outstanding_messages(self):
        return self._number_of_outstanding_messages

    def get_total_number_of_messages(self):
        return self._total_number_of_messages

    def get_total_result(self):
        return round(self._total_result)

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
