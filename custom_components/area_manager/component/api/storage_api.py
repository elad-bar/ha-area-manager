"""Storage handlers."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.json import JSONEncoder
from homeassistant.helpers.storage import Store

from ...configuration.models.config_data import ConfigData
from ...core.api.base_api import BaseAPI
from ...core.helpers.const import DOMAIN, STORAGE_VERSION
from ...core.helpers.enums import ConnectivityStatus
from ..helpers.const import (
    STORAGE_DATA_AREA_CONFIGURATION,
    STORAGE_DATA_AREA_TYPES,
    STORAGE_DATA_FILE_CONFIG,
    STORAGE_DATA_FILES,
)

_LOGGER = logging.getLogger(__name__)


class StorageAPI(BaseAPI):
    _stores: dict[str, Store] | None
    _config_data: ConfigData | None
    _data: dict

    def __init__(
        self,
        hass: HomeAssistant | None,
        async_on_data_changed: Callable[[], Awaitable[None]] | None = None,
        async_on_status_changed: Callable[[ConnectivityStatus], Awaitable[None]]
        | None = None,
    ):
        super().__init__(hass, async_on_data_changed, async_on_status_changed)

        self._config_data = None
        self._stores = None
        self._data = {}

    @property
    def _storage_config(self) -> Store:
        storage = self._stores.get(STORAGE_DATA_FILE_CONFIG)

        return storage

    @property
    def area_configurations(self) -> dict:
        result = self.data.get(STORAGE_DATA_AREA_CONFIGURATION, {})

        return result

    @property
    def area_types(self) -> list:
        result = self.data.get(STORAGE_DATA_AREA_TYPES, [])

        return result

    async def initialize(self, config_data: ConfigData):
        self._config_data = config_data

        self._initialize_storages()

        await self._async_load_configuration()

    def _initialize_storages(self):
        stores = {}

        entry_id = self._config_data.entry.entry_id

        for storage_data_file in STORAGE_DATA_FILES:
            file_name = f"{DOMAIN}.{entry_id}.{storage_data_file}.json"

            stores[storage_data_file] = Store(
                self.hass, STORAGE_VERSION, file_name, encoder=JSONEncoder
            )

        self._stores = stores

    async def _async_load_configuration(self):
        """Load the retained data from store and return de-serialized data."""
        self.data = await self._storage_config.async_load()

        if self.data is None:
            self.data = {
                STORAGE_DATA_AREA_CONFIGURATION: {},
                STORAGE_DATA_AREA_TYPES: [],
            }

            await self._async_save()

        _LOGGER.debug(f"Loaded configuration data: {self.data}")

        await self.set_status(ConnectivityStatus.Connected)
        await self.fire_data_changed_event()

    async def _async_save(self):
        """Generate dynamic data to store and save it to the filesystem."""
        _LOGGER.info(f"Save configuration, Data: {self.data}")

        await self._storage_config.async_save(self.data)

        await self.fire_data_changed_event()

    async def update_area_type(self, area_id: str, area_type: str):
        _LOGGER.debug(f"Update area {area_id} to Type: {area_type}")

        await self._update_area(area_id, "type", area_type)

    async def update_area_is_outdoor(self, area_id: str, is_outdoor: bool):
        _LOGGER.debug(f"Update area {area_id} as outdoor: {is_outdoor}")

        await self._update_area(area_id, "outdoor", is_outdoor)

    async def update_area_parent(self, area_id: str, parent_area_id: str):
        _LOGGER.debug(f"Update area {area_id} parent to Area: {parent_area_id}")

        await self._update_area(area_id, "parent", parent_area_id)

    async def _update_area(self, area_id: str, key: str, value: str | bool | None):
        area_details = self.area_configurations.get(area_id)

        if area_details is None:
            area_details = self.get_default_area_configuration()

        else:
            self.area_configurations.pop(area_id)

        area_details[key] = value

        self.area_configurations[area_id] = area_details

        await self._async_save()

    @staticmethod
    def get_default_area_configuration():
        config = {"outdoor": False, "type": None, "parent": None}

        return config

    async def set_area_type(self, area_type: str):
        _LOGGER.debug(f"Set area type: {area_type}")

        self.area_types.append(area_type)

        await self._async_save()

    async def remove_area_type(self, area_type: str):
        _LOGGER.debug(f"Remove area type: {area_type}")

        if area_type in self.area_types:
            self.area_types.remove(area_type)

            # Clear area configuration with that area type

        await self._async_save()
