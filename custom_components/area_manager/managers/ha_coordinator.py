from collections.abc import ValuesView
from datetime import timedelta
import logging
import sys
from typing import Any

import async_timeout

from homeassistant.components.select import ATTR_OPTIONS
from homeassistant.const import (
    ATTR_AREA_ID,
    ATTR_DOMAIN,
    ATTR_ENTITY_ID,
    ATTR_NAME,
    ATTR_OPTION,
    ATTR_STATE,
    SERVICE_SELECT_OPTION,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
    EntityCategory,
    Platform,
)
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.area_registry import async_get as async_ar_get
from homeassistant.helpers.device_registry import (
    DeviceRegistryItems,
    async_get as async_dr_get,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_registry import (
    RegistryEntry,
    async_get as async_er_get,
)
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ..common.consts import (
    ATTR_ATTRIBUTE,
    ATTR_ATTRIBUTES,
    ATTR_INCLUDE_NESTED,
    ATTR_VALUES,
    CONF_AREA_PARENT,
    DATA_CONFIG,
    DATA_HA,
    DEFAULT_ENTITY_DESCRIPTIONS,
    DOMAIN,
    SERVICE_REMOVE_AREA_ATTRIBUTE,
    SERVICE_REMOVE_AREA_ENTITY,
    SERVICE_SCHEMA_REMOVE_AREA_X,
    SERVICE_SCHEMA_SET_AREA_ATTRIBUTE,
    SERVICE_SCHEMA_SET_AREA_ENTITY,
    SERVICE_SET_AREA_ATTRIBUTE,
    SERVICE_SET_AREA_ENTITY,
)
from ..common.entity_descriptions import (
    BaseEntityDescription,
    HASelectEntityDescription,
    get_entity_description,
)
from .ha_config_manager import HAConfigManager

_LOGGER = logging.getLogger(__name__)


class HACoordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(self, hass: HomeAssistant, config_manager: HAConfigManager):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=config_manager.name,
            update_interval=timedelta(seconds=30),
            update_method=self._async_update_data,
        )

        self._track_state_handler = None
        self._listen_domain_device_class = {}

        self._config_manager = config_manager
        self._ha_data = {}
        self._area_configuration = {}

        self._ar = async_ar_get(self.hass)
        self._dr = async_dr_get(self.hass)
        self._er = async_er_get(self.hass)

    @property
    def config_data(self):
        return self._config_manager.data

    @property
    def ha_data(self):
        return self._ha_data

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            async with async_timeout.timeout(10):
                await self.async_update()

                return {
                    DATA_HA: self._ha_data,
                    DATA_CONFIG: self._config_manager.data,
                }

        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    @property
    def areas(self) -> dict:
        return self.data.get("areas", {})

    @property
    def entities(self) -> dict:
        return self.data.get("entities", {})

    @property
    def _devices(self) -> DeviceRegistryItems:
        return self._dr.devices

    @property
    def _entities(self) -> ValuesView[RegistryEntry]:
        return self._er.entities.values()

    async def start_listen_entity_change(self):
        if self._track_state_handler is not None:
            self._track_state_handler()

        entity_ids = []
        for entity in self._entities:
            allowed_device_class = self._listen_domain_device_class.get(entity.domain)
            if (
                allowed_device_class is not None
                and entity.device_class in allowed_device_class
            ):
                entity_ids.append(entity.entity_id)

        self._track_state_handler = async_track_state_change_event(
            self.hass, entity_ids, self.watched_entity_change
        )

    async def watched_entity_change(self, event: Event) -> None:
        if (to_state := event.data.get("new_state")) is None:
            return

        if (old_state := event.data.get("old_state")) is None:
            return

        if to_state.state == old_state.state:
            return

        await self.async_request_refresh()

    def get_device_info(self, area_id: str) -> DeviceInfo:
        area_details = self.areas.get(area_id)
        area_name = area_details.get(ATTR_NAME)

        device_info = DeviceInfo(identifiers={(DOMAIN, area_id)}, name=area_name)

        return device_info

    def load_areas(self):
        self.data["areas"] = {}

        for area in self._ar.async_list_areas():
            nested_area = self.get_nested_area(area.id)

            self.data["areas"][area.id] = {
                ATTR_NAME: area.name,
                ATTR_AREA_ID: area.id,
                "nested": nested_area,
            }

    def get_area_names(self) -> list[str]:
        area_names = [self.areas[area_id][ATTR_NAME] for area_id in self.areas]

        return area_names

    def get_nested_area(self, area_id: str, nested_areas=None) -> list[str]:
        if nested_areas is None:
            nested_areas = []

        area_settings = self._config_manager.area_settings

        for area_config_id in area_settings:
            area_config = area_settings.get(area_config_id, {})
            area_parent = area_config.get(CONF_AREA_PARENT)

            if area_parent == area_id:
                nested_areas.append(area_config_id)

                self.get_nested_area(area_config_id, nested_areas)

        return nested_areas

    def load_entities(self):
        self.data["entities"] = {}

        for entity in self._entities:
            self._load_entity(entity)

    def _load_entity(self, entity: RegistryEntry):
        entity_data = entity.as_partial_dict
        try:
            area_id = entity.area_id

            if entity.area_id is None and entity.device_id is not None:
                device = self._devices.get(entity.device_id)
                area_id = device.area_id

            if area_id is not None:
                area_data = self.areas.get(area_id)

                if area_data is not None:
                    entity_data[ATTR_AREA_ID] = area_id
                    entity_data[ATTR_NAME] = area_data.get(ATTR_NAME)

                entity_data[ATTR_DOMAIN] = entity.domain
                entity_data[ATTR_STATE] = self.hass.states.get(entity.entity_id)

                self.data["entities"][entity.entity_id] = entity
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to load entity, Entity: {entity_data}, Error: {ex}, Line: {line_number}"
            )

    def get_entity_descriptions(self, platform: Platform) -> list:
        entity_descriptions = []

        for entity_description in DEFAULT_ENTITY_DESCRIPTIONS:
            if platform == entity_description.platform:
                entity_descriptions.append(entity_description)

        for attribute_key in self._config_manager.area_attributes:
            options = self._config_manager.area_attributes[attribute_key]

            entity_description = HASelectEntityDescription(
                key=attribute_key,
                name=attribute_key.capitalize(),
                config_key=attribute_key,
                entity_category=EntityCategory.CONFIG,
                options=options,
            )

            entity_descriptions.append(entity_description)

        for entity_key in self._config_manager.area_entities:
            entity_details = self._config_manager.area_entities[entity_key]
            name = entity_details.get(ATTR_NAME)
            domain = entity_details.get(ATTR_DOMAIN)
            attributes = entity_details.get(ATTR_ATTRIBUTES)
            include_nested = entity_details.get(ATTR_INCLUDE_NESTED, False)

            entity_description = get_entity_description(
                domain, name, attributes, include_nested
            )

            entity_descriptions.append(entity_description)

        return entity_descriptions

    def get_related_entities(
        self, area_id: str, entity_description: BaseEntityDescription
    ) -> list[dict[str, Any]]:
        result = []
        area_lookup = [area_id]

        if entity_description.include_nested:
            area_details = self.areas.get(area_id, {})
            nested_area = area_details.get("nested", [])

            area_lookup.extend(nested_area)

        for entity_id in self.entities:
            entity_details = self.entities[entity_id]
            entity_area_id = entity_details.get(ATTR_AREA_ID)
            entity_state = entity_details[ATTR_STATE]

            entity_attributes = entity_state.get(ATTR_ATTRIBUTES)
            generated_by = entity_attributes.get("generated_by")

            relevant_entity = generated_by != DOMAIN
            relevant_domain = entity_id.startswith(f"{entity_description.platform}.")
            relevant_area = entity_area_id in area_lookup
            relevant_attributes = True

            if entity_description.attributes is not None:
                for attribute_key in entity_description.attributes:
                    attributes_values = entity_description.attributes[attribute_key]
                    entity_attribute = entity_attributes.get(attribute_key)

                    if entity_attribute not in attributes_values:
                        relevant_attributes = False
                        break

            is_relevant = False not in [
                relevant_entity,
                relevant_area,
                relevant_domain,
                relevant_attributes,
            ]

            if is_relevant:
                result.append(entity_details)

        return result

    async def async_update(self):
        try:
            self.load_areas()
            self.load_entities()

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to extract WS data, Error: {ex}, Line: {line_number}"
            )

    def _register_services(self):
        self.hass.services.async_register(
            DOMAIN,
            SERVICE_SET_AREA_ATTRIBUTE,
            self._handle_service_set_area_attribute,
            SERVICE_SCHEMA_SET_AREA_ATTRIBUTE,
        )

        self.hass.services.async_register(
            DOMAIN,
            SERVICE_REMOVE_AREA_ATTRIBUTE,
            self._handle_service_remove_area_attribute,
            SERVICE_SCHEMA_REMOVE_AREA_X,
        )

        self.hass.services.async_register(
            DOMAIN,
            SERVICE_SET_AREA_ENTITY,
            self._handle_service_set_area_entity,
            SERVICE_SCHEMA_SET_AREA_ENTITY,
        )

        self.hass.services.async_register(
            DOMAIN,
            SERVICE_REMOVE_AREA_ENTITY,
            self._handle_service_remove_area_entity,
            SERVICE_SCHEMA_REMOVE_AREA_X,
        )

    def _handle_service_set_area_attribute(self, service_call):
        self.hass.async_create_task(
            self._async_handle_service_set_area_attribute(service_call)
        )

    def _handle_service_remove_area_attribute(self, service_call):
        self.hass.async_create_task(
            self._async_handle_service_remove_area_attribute(service_call)
        )

    def _handle_service_set_area_entity(self, service_call):
        self.hass.async_create_task(
            self._async_handle_service_set_area_entity(service_call)
        )

    def _handle_service_remove_area_entity(self, service_call):
        self.hass.async_create_task(
            self._async_handle_service_remove_area_entity(service_call)
        )

    async def _async_handle_service_set_area_attribute(self, service_call):
        data = service_call.data
        name = data.get(ATTR_NAME)
        options = data.get(ATTR_OPTIONS)

        await self._config_manager.set_area_attribute(name, options)

    async def _async_handle_service_remove_area_attribute(self, service_call):
        data = service_call.data
        name = data.get(ATTR_NAME)

        await self._config_manager.remove_area_attribute(name)

    async def _async_handle_service_set_area_entity(self, service_call):
        data = service_call.data
        name = data.get(ATTR_NAME)
        domain = data.get(ATTR_DOMAIN)
        attribute = data.get(ATTR_ATTRIBUTE)
        values = data.get(ATTR_VALUES)
        include_nested = data.get(ATTR_INCLUDE_NESTED, False)

        await self._config_manager.set_area_entity(
            name, domain, include_nested, attribute, values
        )

    async def _async_handle_service_remove_area_entity(self, service_call):
        data = service_call.data
        name = data.get(ATTR_NAME)

        await self._config_manager.remove_area_entity(name)

    def set_state(
        self, area_id: str, value: Any, entity_description: BaseEntityDescription
    ) -> None:
        """Handles ACTION_CORE_ENTITY_SELECT_OPTION."""
        self.hass.async_create_task(
            self._async_set_state(area_id, value, entity_description)
        )

    async def _async_set_state(
        self, area_id: str, value: Any, entity_description: BaseEntityDescription
    ) -> None:
        """Handles ACTION_CORE_ENTITY_SELECT_OPTION."""
        if entity_description.config_key is not None:
            await self._config_manager.set_configuration(
                area_id, value, entity_description.key
            )

            await self.async_request_refresh()

        else:
            entities = self.get_related_entities(area_id, entity_description)
            entity_ids = [entity[ATTR_ENTITY_ID] for entity in entities]
            service_data = {ATTR_ENTITY_ID: entity_ids}
            service_name = None

            if entity_description.platform == Platform.SELECT:
                service_name = SERVICE_SELECT_OPTION
                service_data[ATTR_OPTION] = value

            elif entity_description.platform in [Platform.SWITCH, Platform.LIGHT]:
                service_name = (
                    SERVICE_TURN_ON if value == STATE_ON else SERVICE_TURN_OFF
                )

            if service_name is not None:
                self.hass.services.call(
                    entity_description.platform, service_name, service_data
                )
