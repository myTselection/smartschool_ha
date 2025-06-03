from homeassistant.components.todo import TodoEntity
import uuid

class MyChecklistTodoEntity(TodoEntity):
    def __init__(self, hass, checklist_id, name, items):
        self._attr_name = name
        self._checklist_id = checklist_id
        self._items = items
        self._attr_has_todo_item_add = True
        self._attr_has_todo_item_update = True
        self._attr_has_todo_item_remove = True

    @property
    def todo_items(self):
        return self._items

    async def async_add_todo_item(self, item):
        new_item = {
            "uid": str(uuid.uuid4()),
            "summary": item["summary"],
            "status": "needs_action"
        }
        self._items.append(new_item)
        self.async_write_ha_state()

    async def async_update_todo_item(self, uid, changes):
        for item in self._items:
            if item["uid"] == uid:
                item.update(changes)
                break
        self.async_write_ha_state()

    async def async_remove_todo_item(self, uid):
        self._items = [item for item in self._items if item["uid"] != uid]
        self.async_write_ha_state()