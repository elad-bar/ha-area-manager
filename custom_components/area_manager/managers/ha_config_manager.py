import logging
from typing import Any

from homeassistant.config_entries import STORAGE_VERSION, ConfigEntry
from homeassistant.const import ATTR_DOMAIN, ATTR_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.json import JSONEncoder
from homeassistant.helpers.storage import Store

from ..common.consts import (
    ATTR_ATTRIBUTES,
    CONF_AREA_PARENT,
    DOMAIN,
    STORAGE_DATA_AREA_ATTRIBUTES,
    STORAGE_DATA_AREA_ENTITIES,
    STORAGE_DATA_AREA_SETTINGS,
)
from ..common.exceptions import SystemAttributeError

_LOGGER = logging.getLogger(__name__)


class HAConfigManager:
    def __init__(self, hass: HomeAssistant | None, entry: ConfigEntry | None):
        self._hass = hass
        self._entry = entry
        self.data = {}

        if entry is not None:
            file_name = f"{DOMAIN}.{entry.entry_id}.config.json"

            self._store = Store(hass, STORAGE_VERSION, file_name, encoder=JSONEncoder)

    @property
    def name(self):
        return self._entry.title

    @property
    def unique_id(self):
        return self._entry.unique_id

    @property
    def area_settings(self) -> dict:
        result = self.data.get(STORAGE_DATA_AREA_SETTINGS, {})

        return result

    @property
    def area_attributes(self) -> dict[str, list[str | int | bool]]:
        result = self.data.get(STORAGE_DATA_AREA_ATTRIBUTES, {})

        return result

    @property
    def area_entities(self) -> dict:
        result = self.data.get(STORAGE_DATA_AREA_ENTITIES, {})

        return result

    async def initialize(self):
        local_data = await self._load()

        for key in local_data:
            value = local_data[key]

            self.data[key] = value

    async def _load(self):
        result = await self._store.async_load()

        if result is None:
            result = {
                STORAGE_DATA_AREA_SETTINGS: {},
                STORAGE_DATA_AREA_ATTRIBUTES: {},
                STORAGE_DATA_AREA_ENTITIES: {},
            }

        return result

    async def _save(self):
        await self._store.async_save(self.data)

    async def _update_area(self, area_id: str, key: str, value: str | bool | None):
        area_details = self.area_settings.get(area_id)

        if area_details is None:
            area_details = self.get_default_area_configuration()

        else:
            self.area_settings.pop(area_id)

        area_details[key] = value

        self.area_settings[area_id] = area_details

        await self._save()

    @staticmethod
    def get_default_area_configuration():
        config = {CONF_AREA_PARENT: None}

        return config

    async def set_area_attribute(self, name: str, options: list[str | int | bool]):
        _LOGGER.debug(f"Set area attribute: {name}, Options: {options}")

        attribute_key = name.lower()

        await self.remove_area_attribute(name)

        self.area_attributes[attribute_key] = options

        await self._save()

    async def remove_area_attribute(self, name: str):
        _LOGGER.debug(f"Remove area attribute: {name}")

        attribute_key = name.lower()

        if attribute_key == CONF_AREA_PARENT.lower():
            raise SystemAttributeError(name)

        if attribute_key in self.area_attributes:
            self.area_attributes.pop(attribute_key)

        await self._save()

    async def set_area_entity(
        self, name: str, domain: str, attribute: str, values: list[str]
    ):
        _LOGGER.debug(f"Set area entity: {name}, domain: {domain}, values: {values}")

        attribute_key = name.lower()

        entity = self.area_entities.get(
            attribute_key, {ATTR_NAME: name, ATTR_DOMAIN: domain, ATTR_ATTRIBUTES: {}}
        )

        self.area_entities[attribute_key][ATTR_ATTRIBUTES][attribute] = entity

        await self._save()

    async def remove_area_entity(self, name: str):
        _LOGGER.debug(f"Remove area entity: {name}")

        attribute_key = name.lower()

        if attribute_key == CONF_AREA_PARENT.lower():
            raise SystemAttributeError(name)

        if attribute_key in self.area_entities:
            self.area_entities.pop(attribute_key)

        await self._save()

    async def set_configuration(self, area_id: str, value: Any, config_key: str):
        await self._update_area(area_id, config_key, value)
