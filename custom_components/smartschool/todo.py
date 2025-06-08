from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import ComponentUpdateCoordinator
from . import DOMAIN
from .const import (
    ATTR_ID,
    ATTR_NAME,
    ATTR_CHECKED,
    ATTR_NOTES,
    ATTR_DUEDATE,
    CONF_REFRESH_INTERVAL
)

async def async_setup_entry(hass, config_entry, async_add_entities):
    refresh_interval = config_entry.options.get(CONF_REFRESH_INTERVAL, 30)

    # code, lists = await hass.data[DOMAIN].get_lists()
    lists = ["TEST","Test2"]
    for list_name in lists:
        coordinator = ComponentUpdateCoordinator(hass, config_entry, list_name, refresh_interval)
        await coordinator.async_config_entry_first_refresh()

        async_add_entities(
            [ComponentTodoListEntity(hass, coordinator, list_name)]
        )

class ComponentTodoListEntity(CoordinatorEntity[ComponentUpdateCoordinator], TodoListEntity):

    _attr_has_entity_name = True
    _attr_supported_features = (
        TodoListEntityFeature.UPDATE_TODO_ITEM
    )

    def __init__(self, hass, coordinator, list_name):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{list_name}"
        self._attr_name = list_name
        self.list_name = list_name
        self.hass = hass

    @property
    def todo_items(self):
        if self.coordinator.data is None:
            return None

        items = [
            TodoItem(
                summary = item.get(ATTR_NAME,"TODO"),
                uid = item[ATTR_ID],
                status = TodoItemStatus.COMPLETED if item.get(ATTR_CHECKED, False)else TodoItemStatus.NEEDS_ACTION,
                due = item.get(ATTR_DUEDATE, None).isoformat() if item.get(ATTR_DUEDATE, None) else None,
                description = item.get(ATTR_NOTES, None)
            )
            for item in self.coordinator.data
        ]
        return items

    async def async_create_todo_item(self, item):
        updates = self.get_item_updates(item)
        await self.hass.data[DOMAIN].add_item(
            item.summary,
            updates = updates,
            list_name = self.list_name
        )
        await self.coordinator.async_refresh()

    async def async_delete_todo_items(self, uids):
        for uid in uids:
            await self.hass.data[DOMAIN].remove_item_by_id(uid, list_name = self.list_name)
        await self.coordinator.async_refresh()

    async def async_update_todo_item(self, item):
        updates = self.get_item_updates(item)
        await self.hass.data[DOMAIN].update_item(
            item.uid,
            updates = updates,
            list_name = self.list_name
        )
        await self.coordinator.async_refresh()

    def get_item_updates(self, item):
        updates = dict()
        updates[ATTR_NAME] = item.summary or ""
        updates[ATTR_NOTES] = item.description or ""

        if item.status is not None:
            updates[ATTR_CHECKED] = (item.status == TodoItemStatus.COMPLETED)

        return updates

    @property
    def extra_state_attributes(self):
        return {
            "source_name": f"{self.list_name}",
            "checked_items": [item[ATTR_NAME] for item in self.coordinator.data if item[ATTR_CHECKED]],
            "unchecked_items": [item[ATTR_NAME] for item in self.coordinator.data if not item[ATTR_CHECKED]]
        }
