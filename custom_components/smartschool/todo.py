from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)

# https://developers.home-assistant.io/docs/core/entity/todo

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import ComponentUpdateCoordinator
from . import DOMAIN

from .const import (
    CONF_BIRTH_DATE,
    CONF_SMARTSCHOOL_DOMAIN,
    LIST_TAKEN,
    LIST_TOETSEN,
    LIST_MEEBRENGEN,
    LIST_VOLGENDE,
    TASK_LABEL_TAAK,
    TASK_LABEL_TOETS,
    CONF_REFRESH_INTERVAL
)

from .storage import ChecklistStatusStorage
import logging
_LOGGER = logging.getLogger(DOMAIN)

async def async_setup_entry(hass, config_entry, async_add_entities):
    refresh_interval = config_entry.options.get(CONF_REFRESH_INTERVAL, 30)
    coordinator = ComponentUpdateCoordinator(hass, config_entry, refresh_interval)
    await coordinator.async_initialize()

    list_ids = coordinator._lists.keys()
    async_add_entities([ComponentTodoListEntity(hass, coordinator, list_name, coordinator._unique_user_id) for list_name in list_ids])

    return True


class ComponentTodoListEntity(CoordinatorEntity[ComponentUpdateCoordinator], TodoListEntity):

    
    _LOGGER = logging.getLogger(DOMAIN)
    _attr_has_entity_name = True
    _attr_supported_features = (
        TodoListEntityFeature.UPDATE_TODO_ITEM | 
        TodoListEntityFeature.SET_DUE_DATE_ON_ITEM | 
        TodoListEntityFeature.SET_DUE_DATETIME_ON_ITEM |
        TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM 
    )

    def __init__(self, hass, coordinator, list_name: str, unique_user_id: str):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_unique_id = f"{DOMAIN}_{list_name}"
        self._attr_name = list_name
        self._list_name = list_name
        self._unique_user_id = unique_user_id
        self.hass = hass
        self._status_store = ChecklistStatusStorage(hass)
        self._items = []
        _LOGGER.debug(f"Initialized todolist entity for list_name: {self._list_name}")

    @property
    def icon(self) -> str:
        """Shows the correct icon for container."""
        if LIST_TOETSEN in self._list_name:
            return "mdi:head-cog"
        elif LIST_TAKEN in self._list_name:
            return "mdi:hammer-wrench"
        elif LIST_VOLGENDE in self._list_name:
            return "mdi:timetable"
        elif LIST_MEEBRENGEN in self._list_name:
            return "mdi:briefcase"
        else: # meebrengen
            return "mdi:bookshelf"
    
    @property
    def todo_items(self):
        return self.coordinator.get_items(self._list_name)
        # if self.coordinator.data is None:
        #     return None

        # items = [
        #     TodoItem(
        #         summary = item.get(ATTR_NAME,"TODO"),
        #         uid = item[ATTR_ID],
        #         status = TodoItemStatus.COMPLETED if item.get(ATTR_CHECKED, False)else TodoItemStatus.NEEDS_ACTION,
        #         due = item.get(ATTR_DUEDATE, None).isoformat() if item.get(ATTR_DUEDATE, None) else None,
        #         description = item.get(ATTR_NOTES, None)
        #     )
        #     for item in self.coordinator.data
        # ]
        # return items

    async def async_added_to_hass(self) -> None:
        _LOGGER.debug(f"Checklist entity added to hass: {self._list_name}")

    async def async_update_todo_item(self, item: TodoItem) -> None:
        _LOGGER.debug(f"Updating todo item in '{self._list_name}': {item}")
        items = self.coordinator.get_items(self._list_name)
        for idx, existing in enumerate(items):
            if existing.uid == item.uid:
                items[idx] = item
                await self.coordinator.update_status(self._unique_user_id, item.uid, item.status)
                self.async_write_ha_state()
                return

    # not used
    async def async_create_todo_item(self, item: TodoItem) -> None:
        _LOGGER.debug(f"Creating todo item in '{self._list_name}': {item}")
        items = self.coordinator.get_items(self._list_name)
        items.append(item)
        await self.coordinator.update_status(self._unique_user_id, item.uid, item.status)
        self.async_write_ha_state()



    # not used
    async def async_delete_todo_items(self, uids: list[str]) -> None:
        _LOGGER.debug(f"Deleting todo item {uids}")
        items = self.coordinator.get_items(self._list_name)
        self.coordinator._lists[self._list_name] = [i for i in items if i.uid not in uids]
        for uid in uids:
            await self.coordinator.delete_status(self._unique_user_id, uid)
        self.async_write_ha_state()
        

    async def async_will_remove_from_hass(self) -> None:
        """Clean up storage when entity is removed."""
        _LOGGER.info("Checklist entity removed from hass: %s", self._list_name)
        await self.coordinator.remove_list(self._list_name, self._unique_user_id)