import json
import logging
from typing import Any

from homeassistant.config_entries import STORAGE_VERSION, ConfigEntry
from homeassistant.const import ATTR_DOMAIN, ATTR_NAME, CONF_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import translation
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.json import JSONEncoder
from homeassistant.helpers.storage import Store
from homeassistant.util import slugify

from ..common.consts import (
    ATTR_ATTRIBUTES,
    ATTR_INCLUDE_NESTED,
    ATTR_PARENT,
    DEFAULT_ENTRY_ID,
    DOMAIN,
    STORAGE_DATA_AREA_ATTRIBUTES,
    STORAGE_DATA_AREA_DETAILS,
    STORAGE_DATA_AREA_ENTITIES,
    STORAGE_DATA_AREA_PARENTS,
)
from ..common.entity_descriptions import BaseEntityDescription
from ..common.exceptions import SystemAttributeError

_LOGGER = logging.getLogger(__name__)


class HAConfigManager:
    _translations: dict | None
    _store: Store | None

    def __init__(self, hass: HomeAssistant | None, entry: ConfigEntry | None):
        self._hass = hass
        self._entry = entry
        self._data = {}
        self._translations = None
        self._unique_id = None
        self._entry_id = DEFAULT_ENTRY_ID
        self._store = None

        if entry is not None:
            self._unique_id = self._entry.unique_id
            self._entry_id = self._entry.entry_id

            file_name = f"{DOMAIN}.config.json"

            self._store = Store(hass, STORAGE_VERSION, file_name, encoder=JSONEncoder)

    @property
    def name(self):
        return self._entry.title

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def entry_id(self):
        return self._entry_id

    @property
    def area_parents(self) -> dict:
        result = self._data.get(STORAGE_DATA_AREA_PARENTS, {})

        return result

    @property
    def area_attributes(self) -> dict[str, list[str | int | bool]]:
        result = self._data.get(STORAGE_DATA_AREA_ATTRIBUTES, {})

        return result

    @property
    def area_entities(self) -> dict:
        result = self._data.get(STORAGE_DATA_AREA_ENTITIES, {})

        return result

    @property
    def area_details(self) -> dict:
        result = self._data.get(STORAGE_DATA_AREA_DETAILS, {})

        return result

    async def initialize(self):
        if self._hass is None:
            self._translations = {}

        else:
            self._translations = await translation.async_get_translations(
                self._hass, self._hass.config.language, "entity", {DOMAIN}
            )

        await self._load()

    def get_translation(
        self,
        platform: Platform,
        entity_key: str,
        attribute: str,
        default_value: str | None = None,
    ) -> str | None:
        translation_key = (
            f"component.{DOMAIN}.entity.{platform}.{entity_key}.{attribute}"
        )

        translated_value = self._translations.get(translation_key, default_value)

        _LOGGER.debug(
            "Translations requested, "
            f"Key: {translation_key}, "
            f"Default value: {default_value}, "
            f"Value: {translated_value}"
        )

        return translated_value

    def get_config_data(self):
        return self._data

    async def _load(self):
        self._data = None

        await self._load_config_from_file()

        if self._data is None:
            self._data = {}

        default_configuration = self._get_defaults()

        for key in default_configuration:
            value = default_configuration[key]

            if key not in self._data:
                self._data[key] = value

        await self._save()

    async def _load_config_from_file(self):
        if self._store is not None:
            self._data = await self._store.async_load()

    @staticmethod
    def _get_defaults() -> dict:
        data = {
            STORAGE_DATA_AREA_ATTRIBUTES: {},
            STORAGE_DATA_AREA_ENTITIES: {},
            STORAGE_DATA_AREA_PARENTS: {},
            STORAGE_DATA_AREA_DETAILS: {},
        }

        return data

    async def _save(self):
        if self._store is None:
            return

        _LOGGER.info(json.dumps(self._data, indent=4))

        await self._store.async_load()
        await self._store.async_save(self._data)

    def get_entity_name(
        self,
        entity_description: BaseEntityDescription,
        device_info: DeviceInfo,
    ) -> str:
        entity_key = entity_description.key

        device_name = device_info.get("name")
        platform = entity_description.platform

        translated_name = self.get_translation(
            platform, entity_key, CONF_NAME, entity_description.name
        )

        entity_name = (
            device_name
            if translated_name is None or translated_name == ""
            else f"{device_name} {translated_name}"
        )

        return entity_name

    async def set_area_parent(self, area_id, parent_area_id: str | None):
        self._data[STORAGE_DATA_AREA_PARENTS][area_id] = parent_area_id

        await self._save()

    async def set_area_attribute(self, name: str, options: list[str | int | bool]):
        _LOGGER.debug(f"Set area attribute: {name}, Options: {options}")

        for area_name in self.area_attributes:
            if area_name.lower() == name.lower() and area_name != name:
                raise SystemAttributeError(name)

        self._data[STORAGE_DATA_AREA_ATTRIBUTES][name] = options

        await self._save()

    async def remove_area_attribute(self, name: str):
        _LOGGER.debug(f"Remove area attribute: {name}")

        if name.lower() == ATTR_PARENT.lower():
            raise SystemAttributeError(name)

        if name in self.area_attributes:
            self._data[STORAGE_DATA_AREA_ATTRIBUTES].pop(name)

            await self._save()

    async def set_area_entity(
        self,
        name: str,
        domain: str,
        include_nested: bool,
        attribute: str,
        values: list[str],
    ):
        _LOGGER.debug(f"Set area entity: {name}, domain: {domain}, values: {values}")

        entity_key = slugify(name)

        entity = self.area_entities.get(entity_key, self.get_default_area_entity(name))

        entity[ATTR_DOMAIN] = domain
        entity[ATTR_INCLUDE_NESTED] = include_nested
        entity[ATTR_ATTRIBUTES][attribute] = values

        self._data[STORAGE_DATA_AREA_ENTITIES][entity_key] = entity

        await self._save()

    async def remove_area_entity(self, name: str):
        _LOGGER.debug(f"Remove area entity: {name}")

        entity_key = slugify(name)

        if entity_key in self.area_entities:
            self._data[STORAGE_DATA_AREA_ENTITIES].pop(entity_key)

            await self._save()

    async def set_area_details(self, area_id: str, value: Any, config_key: str):
        area_details = self.area_details.get(area_id)

        if area_details is None:
            area_details = {}

        area_details[config_key] = value

        self._data[STORAGE_DATA_AREA_DETAILS][area_id] = area_details

        await self._save()

    def get_area_details(self, area_id: str, config_key: str) -> Any:
        area_details = self.area_details.get(area_id, {})
        area_config_details = area_details.get(config_key, {})

        return area_config_details

    @staticmethod
    def get_default_area_entity(name):
        config = {ATTR_NAME: name, ATTR_ATTRIBUTES: {}, ATTR_INCLUDE_NESTED: False}

        return config
