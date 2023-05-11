"""
Support for HA manager.
"""
from __future__ import annotations

import logging
import sys

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntityDescription,
)
from homeassistant.components.select import SelectEntityDescription
from homeassistant.components.sensor import (
    DOMAIN as DOMAIN_SENSOR,
    SensorDeviceClass,
    SensorEntityDescription,
)
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_FRIENDLY_NAME,
    ATTR_IDENTIFIERS,
    ATTR_MANUFACTURER,
    ATTR_NAME,
    STATE_OFF,
    EntityCategory,
)
from homeassistant.core import HomeAssistant

from ...configuration.helpers.const import DEFAULT_NAME, DOMAIN, MANUFACTURER
from ...configuration.managers.configuration_manager import ConfigurationManager
from ...configuration.models.config_data import ConfigData
from ...core.helpers.const import (
    ACTION_CORE_ENTITY_SELECT_OPTION,
    ACTION_CORE_ENTITY_TURN_OFF,
    ACTION_CORE_ENTITY_TURN_ON,
    DOMAIN_BINARY_SENSOR,
    DOMAIN_SELECT,
    DOMAIN_SWITCH,
)
from ...core.helpers.enums import ConnectivityStatus
from ...core.managers.home_assistant import HomeAssistantManager
from ...core.models.entity_data import EntityData
from ..api.api import IntegrationAPI
from ..api.storage_api import StorageAPI
from ..helpers.const import (
    AREA_ID,
    AREA_TYPE,
    DEFAULT_UPDATE_API_INTERVAL,
    DEFAULT_UPDATE_ENTITIES_INTERVAL,
    SERVICE_REMOVE_AREA_TYPE,
    SERVICE_REMOVE_ENTITY,
    SERVICE_SCHEMA_REMOVE_ENTITY,
    SERVICE_SCHEMA_SET_ENTITY,
    SERVICE_SCHEMA_UPDATE_AREA_TYPE,
    SERVICE_SET_AREA_TYPE,
    SERVICE_SET_ENTITY,
)

_LOGGER = logging.getLogger(__name__)


class AreaHomeAssistantManager(HomeAssistantManager):
    def __init__(self, hass: HomeAssistant):
        super().__init__(hass, DEFAULT_UPDATE_API_INTERVAL)

        self._storage_api: StorageAPI = StorageAPI(self._hass)
        self._api: IntegrationAPI = IntegrationAPI(
            self._hass, self._api_data_changed, self._api_status_changed
        )
        self._config_manager: ConfigurationManager | None = None
        self._can_load_components: bool = False
        self._unique_messages: list[str] = []

    @property
    def hass(self) -> HomeAssistant:
        return self._hass

    @property
    def api(self) -> IntegrationAPI:
        return self._api

    @property
    def storage_api(self) -> StorageAPI:
        return self._storage_api

    @property
    def config_data(self) -> ConfigData:
        return self._config_manager.get(self.entry_id)

    async def _api_data_changed(self):
        if self.api.status == ConnectivityStatus.Connected:
            await self._extract_api_data()

    async def _api_status_changed(self, status: ConnectivityStatus):
        _LOGGER.info(f"API Status changed to {status.name}")
        if status == ConnectivityStatus.Connected:
            self.api.update_configuration(self.storage_api.area_configurations)

            await self.api.async_update()

    async def async_component_initialize(self, entry: ConfigEntry):
        try:
            self._config_manager = ConfigurationManager(self._hass, self.api)
            await self._config_manager.load(entry)

            await self.storage_api.initialize(self.config_data)

            self.update_intervals(
                DEFAULT_UPDATE_ENTITIES_INTERVAL, DEFAULT_UPDATE_API_INTERVAL
            )

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to async_component_initialize, error: {ex}, line: {line_number}"
            )

    async def async_initialize_data_providers(self):
        await self.storage_api.initialize(self.config_data)

    async def async_stop_data_providers(self):
        await self.api.terminate()

    async def async_update_data_providers(self):
        try:
            self.api.update_configuration(self.storage_api.area_configurations)

            await self.api.async_update()

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to async_update_data_providers, Error: {ex}, Line: {line_number}"
            )

    def register_services(self, entry: ConfigEntry | None = None):
        self._hass.services.async_register(
            DOMAIN,
            SERVICE_SET_AREA_TYPE,
            self._set_area_type,
            SERVICE_SCHEMA_UPDATE_AREA_TYPE,
        )

        self._hass.services.async_register(
            DOMAIN,
            SERVICE_REMOVE_AREA_TYPE,
            self._remove_area_type,
            SERVICE_SCHEMA_UPDATE_AREA_TYPE,
        )

        self._hass.services.async_register(
            DOMAIN,
            SERVICE_SET_ENTITY,
            self._set_area_entity,
            SERVICE_SCHEMA_SET_ENTITY,
        )

        self._hass.services.async_register(
            DOMAIN,
            SERVICE_REMOVE_ENTITY,
            self._remove_area_entity,
            SERVICE_SCHEMA_REMOVE_ENTITY,
        )

    def load_devices(self):
        if not self._can_load_components:
            return

        for area_id in self.api.areas:
            area = self.api.areas.get(area_id)

            self._set_ha_device(area)

    def load_entities(self):
        _LOGGER.debug("Loading entities")

        if not self._can_load_components:
            return

        for area_id in self.api.areas:
            area = self.api.areas.get(area_id)
            area_config = self.storage_api.area_configurations.get(area_id, {})

            self._load_area_parent_select(area, area_config)
            self._load_area_type_select(area, area_config)
            self._load_area_is_outdoor_switch(area, area_config)

            self._load_area_security_status_binary_sensor(area, area_config)

            self._load_area_temperature_sensor(area)
            self._load_area_humidity_sensor(area)

    async def _extract_api_data(self):
        try:
            _LOGGER.debug("Extracting API Data")

            self.load_devices()
            self.load_entities()

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to extract API data, Error: {ex}, Line: {line_number}"
            )

    @staticmethod
    def get_area_name(area: dict):
        area_name = area.get(ATTR_NAME)

        return f"Area {area_name}"

    def _set_ha_device(self, area: dict):
        name = self.get_area_name(area)

        device_details = self.device_manager.get(name)

        device_details_data = {
            ATTR_IDENTIFIERS: {(DEFAULT_NAME, name)},
            ATTR_NAME: name,
            ATTR_MANUFACTURER: MANUFACTURER,
        }

        if device_details is None or device_details != device_details_data:
            self.device_manager.set(name, device_details_data)

            _LOGGER.debug(f"Created HA device {name} [{device_details_data}]")

    def _load_area_security_status_binary_sensor(self, area: dict, area_config: dict):
        try:
            area_name = self.get_area_name(area)
            entity_name = f"{area_name} Security Status"

            state = area.get("security", STATE_OFF)

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name,
            }

            unique_id = EntityData.generate_unique_id(DOMAIN_BINARY_SENSOR, entity_name)

            entity_description = BinarySensorEntityDescription(
                key=unique_id,
                name=entity_name,
                device_class=BinarySensorDeviceClass.SAFETY,
            )

            self.entity_manager.set_entity(
                DOMAIN_BINARY_SENSOR,
                self.entry_id,
                state,
                attributes,
                area_name,
                entity_description,
            )

        except Exception as ex:
            self.log_exception(
                ex, f"Failed to load security status binary sensor for {area}"
            )

    def _load_area_temperature_sensor(self, area: dict):
        try:
            area_name = self.get_area_name(area)
            entity_name = f"{area_name} Temperature"

            state = area.get("temperature", 0)

            attributes = {ATTR_FRIENDLY_NAME: entity_name}

            unique_id = EntityData.generate_unique_id(DOMAIN_SENSOR, entity_name)

            entity_description = SensorEntityDescription(
                key=unique_id,
                name=entity_name,
                device_class=SensorDeviceClass.TEMPERATURE,
            )

            self.entity_manager.set_entity(
                DOMAIN_SENSOR,
                self.entry_id,
                state,
                attributes,
                area_name,
                entity_description,
            )

        except Exception as ex:
            self.log_exception(ex, f"Failed to load area temperature sensor for {area}")

    def _load_area_humidity_sensor(self, area: dict):
        try:
            area_name = self.get_area_name(area)
            entity_name = f"{area_name} Humidity"

            state = area.get("humidity", 0)

            attributes = {ATTR_FRIENDLY_NAME: entity_name}

            unique_id = EntityData.generate_unique_id(DOMAIN_SENSOR, entity_name)

            entity_description = SensorEntityDescription(
                key=unique_id,
                name=entity_name,
                device_class=SensorDeviceClass.HUMIDITY,
            )

            self.entity_manager.set_entity(
                DOMAIN_SENSOR,
                self.entry_id,
                state,
                attributes,
                area_name,
                entity_description,
            )

        except Exception as ex:
            self.log_exception(ex, f"Failed to load area temperature sensor for {area}")

    def _load_area_is_outdoor_switch(self, area: dict, area_config: dict):
        try:
            area_name = self.get_area_name(area)
            entity_name = f"{area_name} Type"
            state = area_config.get("outdoor", False)

            attributes = {ATTR_FRIENDLY_NAME: entity_name}

            unique_id = EntityData.generate_unique_id(DOMAIN_SWITCH, entity_name)
            icon = "mdi:eye-settings"

            entity_description = SwitchEntityDescription(
                key=unique_id,
                name=entity_name,
                icon=icon,
                entity_category=EntityCategory.CONFIG,
            )

            self.set_action(
                unique_id, ACTION_CORE_ENTITY_TURN_ON, self._set_area_outdoor
            )
            self.set_action(
                unique_id, ACTION_CORE_ENTITY_TURN_OFF, self._set_area_indoor
            )

            self.entity_manager.set_entity(
                DOMAIN_SWITCH,
                self.entry_id,
                state,
                attributes,
                area_name,
                entity_description,
                details=area,
            )

        except Exception as ex:
            self.log_exception(ex, f"Failed to load switch for {area}")

    def _load_area_type_select(self, area: dict, area_config: dict):
        try:
            area_name = self.get_area_name(area)
            entity_name = f"{area_name} Type"

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name,
            }

            state = area_config.get("type")
            area_types = self.storage_api.area_types
            unique_id = EntityData.generate_unique_id(DOMAIN_SELECT, entity_name)

            entity_description = SelectEntityDescription(
                key=unique_id,
                name=entity_name,
                options=area_types,
                entity_category=EntityCategory.CONFIG,
            )

            self.set_action(
                unique_id,
                ACTION_CORE_ENTITY_SELECT_OPTION,
                self._set_area_type_configuration,
            )

            self.entity_manager.set_entity(
                DOMAIN_SELECT,
                self.entry_id,
                state,
                attributes,
                area_name,
                entity_description,
                details=area,
            )

        except Exception as ex:
            self.log_exception(ex, f"Failed to load select for {area}")

    def _load_area_parent_select(self, area: dict, area_config: dict):
        try:
            area_name = self.get_area_name(area)
            entity_name = f"{area_name} Parent"

            attributes = {
                ATTR_FRIENDLY_NAME: entity_name,
            }

            state = area_config.get("parent")
            area_names = self.api.get_area_names()
            unique_id = EntityData.generate_unique_id(DOMAIN_SELECT, entity_name)

            entity_description = SelectEntityDescription(
                key=unique_id,
                name=entity_name,
                options=area_names,
                entity_category=EntityCategory.CONFIG,
            )

            self.set_action(
                unique_id,
                ACTION_CORE_ENTITY_SELECT_OPTION,
                self._set_area_parent_configuration,
            )

            self.entity_manager.set_entity(
                DOMAIN_SELECT,
                self.entry_id,
                state,
                attributes,
                area_name,
                entity_description,
                details=area,
            )

        except Exception as ex:
            self.log_exception(ex, f"Failed to load select for {area}")

    def _set_area_type(self, service_call):
        self._hass.async_create_task(self._async_set_area_type(service_call))

    def _remove_area_type(self, service_call):
        self._hass.async_create_task(self._async_remove_area_type(service_call))

    async def _async_set_area_type(self, service_call):
        await self._async_update_area_type(service_call, False)

    async def _async_remove_area_type(self, service_call):
        await self._async_update_area_type(service_call, False)

    def _set_area_entity(self, service_call):
        self._hass.async_create_task(self._async_set_area_entity(service_call))

    def _remove_area_entity(self, service_call):
        self._hass.async_create_task(self._async_remove_area_entity(service_call))

    async def _async_set_area_entity(self, service_call):
        pass

    async def _async_remove_area_entity(self, service_call):
        pass

    async def _async_update_area_type(self, service_call, link: bool):
        action_name = "Set" if link else "Remove"

        service_data = service_call.data
        area_type = service_data.get(AREA_TYPE)

        _LOGGER.info(f"{action_name} area type called with data: {service_data}")

        if area_type is None:
            _LOGGER.error("Operation cannot be performed, invalid request data")

        else:
            if link:
                await self.storage_api.set_area_type(area_type)
            else:
                await self.storage_api.remove_area_type(area_type)

    async def _set_area_type_configuration(
        self, entity: EntityData, option: str
    ) -> None:
        """Handles ACTION_CORE_ENTITY_SELECT_OPTION."""
        area_id = entity.details.get(AREA_ID)

        if area_id is not None:
            await self.storage_api.update_area_type(area_id, option)

            await self.async_update_data_providers()

    async def _set_area_parent_configuration(
        self, entity: EntityData, option: str
    ) -> None:
        """Handles ACTION_CORE_ENTITY_SELECT_OPTION."""
        area_id = entity.details.get(AREA_ID)
        selected_area_id = None
        for area_name_id in self.api.areas:
            area_data = self.api.areas[area_name_id]
            if area_data.get(ATTR_NAME) == option:
                selected_area_id = area_name_id
                break

        if area_id is not None and selected_area_id is not None:
            await self.storage_api.update_area_parent(area_id, selected_area_id)

            await self.async_update_data_providers()

    async def _set_area_outdoor(self, entity: EntityData):
        await self._set_area_outdoor_configuration(entity, True)

    async def _set_area_indoor(self, entity: EntityData):
        await self._set_area_outdoor_configuration(entity, False)

    async def _set_area_outdoor_configuration(self, entity: EntityData, state: bool):
        area_id = entity.details.get(AREA_ID)

        if area_id is not None:
            await self.storage_api.update_area_is_outdoor(area_id, state)

            await self.async_update_data_providers()
