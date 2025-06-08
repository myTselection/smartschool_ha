from datetime import datetime, timedelta
import logging

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from . import DOMAIN

_LOGGER = logging.getLogger(DOMAIN)

class ComponentUpdateCoordinator(DataUpdateCoordinator):

    def __init__(self, hass, config_entry, list_name, refresh_interval):
        super().__init__(hass, _LOGGER, config_entry = config_entry, name = f"{DOMAIN} {list_name}", update_interval = timedelta(minutes = refresh_interval))
        self.list_name = list_name
        self.hass = hass

    async def _async_update_data(self):
        # code, items = await self.hass.data[DOMAIN].get_detailed_items(self.list_name)
        items = [{"id" : "id1",
                  "name" : "name1",
                  "list" : "list1",
                  "checked" : True,
                  "notes" : "notes1"},
                  {"id" : "id2",
                  "name" : "name2",
                  "list" : "list1",
                  "checked" : False,
                  "notes" : "notes2"},
                  {"id" : "id3",
                  "name" : "name3",
                  "list" : "list3",
                  "checked" : True,
                  "notes" : "notes3"},
                  {"id" : "id4",
                  "name" : "test2item",
                  "list" : "Test2",
                  "checked" : False,
                  "notes" : "notes3",
                  "duedate": datetime(2025, 6, 10, 18, 0)}
        ]
        return items
