from datetime import timedelta
import logging
import sys
from typing import Any

import async_timeout

from homeassistant.components.homeassistant import SERVICE_RELOAD_CONFIG_ENTRY
from homeassistant.const import (
    ATTR_AREA_ID,
    ATTR_DOMAIN,
    ATTR_ENTITY_ID,
    ATTR_NAME,
    ATTR_STATE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
    EntityCategory,
    Platform,
)
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.area_registry import (
    EVENT_AREA_REGISTRY_UPDATED,
    AreaEntry,
    AreaRegistry,
    async_get as async_ar_get,
)
from homeassistant.helpers.device_registry import (
    DeviceRegistry,
    async_get as async_dr_get,
)
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_registry import (
    EVENT_ENTITY_REGISTRY_UPDATED,
    EntityRegistry,
    RegistryEntry,
    async_get as async_er_get,
)
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ..common.consts import (
    ATTR_ATTRIBUTE,
    ATTR_ATTRIBUTES,
    ATTR_INCLUDE_NESTED,
    ATTR_NESTED,
    ATTR_PARENT,
    ATTR_VALUES,
    DATA_AREAS_KEY,
    DATA_CONFIG,
    DATA_ENTITIES_KEY,
    DATA_HA,
    DEFAULT_NAME,
    DOMAIN,
    ENTITY_CONFIG_ENTRY_ID,
    ENTITY_PLATFORMS,
    HA_NAME,
    SERVICE_REMOVE_ATTRIBUTE,
    SERVICE_REMOVE_ENTITY,
    SERVICE_SCHEMA_REMOVE_AREA_X,
    SERVICE_SCHEMA_SET_ATTRIBUTE,
    SERVICE_SCHEMA_SET_ENTITY,
    SERVICE_SET_ATTRIBUTE,
    SERVICE_SET_ENTITY,
    SIGNAL_AREA_LOADED,
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
        self._track_areas_handler = None
        self._track_entities_handler = None

        self._config_manager = config_manager

        self._ar: AreaRegistry | None = None
        self._dr: DeviceRegistry | None = None
        self._er: EntityRegistry | None = None

        self._data = {}
        self._dispatched_areas = []

    @property
    def config_manager(self) -> HAConfigManager:
        return self._config_manager

    @property
    def areas(self) -> dict:
        return self._data.get(DATA_AREAS_KEY, {})

    @property
    def entities(self) -> dict:
        return self._data.get(DATA_ENTITIES_KEY, {})

    async def async_config_entry_first_refresh(self) -> None:
        await super().async_config_entry_first_refresh()

        if self._er is None:
            self._er = async_er_get(self.hass)
            await self._er.async_load()

        if self._ar is None:
            self._ar = async_ar_get(self.hass)
            await self._ar.async_load()

        if self._dr is None:
            self._dr = async_dr_get(self.hass)
            await self._dr.async_load()

        self._track_areas_handler = self.hass.bus.async_listen(
            EVENT_AREA_REGISTRY_UPDATED, self._handle_area_or_entity_changed_event
        )

        self._track_entities_handler = self.hass.bus.async_listen(
            EVENT_ENTITY_REGISTRY_UPDATED, self._handle_area_or_entity_changed_event
        )

        self._register_services()

        await self._reload_data()

    async def terminate(self):
        if self._track_state_handler is not None:
            self._track_state_handler()

        if self._track_areas_handler is not None:
            self._track_areas_handler()

        if self._track_entities_handler is not None:
            self._track_entities_handler()

    @staticmethod
    def get_default_device_info() -> DeviceInfo:
        device_info = DeviceInfo(
            identifiers={(DOMAIN, DEFAULT_NAME)}, name=DEFAULT_NAME
        )

        return device_info

    def get_device_info(self, area_id: str) -> DeviceInfo:
        area_details = self.areas.get(area_id)
        area_name = area_details.get(ATTR_NAME)

        device_info = DeviceInfo(identifiers={(DOMAIN, area_id)}, name=area_name)

        return device_info

    def get_area_names(self) -> list[str]:
        area_names = [self.get_area_name(area_id) for area_id in self.areas]

        return area_names

    def get_area_name(self, area_id) -> str:
        area = self.get_area(area_id)
        area_name = area.get(ATTR_NAME)

        return area_name

    def get_area(self, area_id) -> dict:
        area = self.areas[area_id]

        return area

    def get_entity_descriptions(self, platform: Platform) -> list:
        parent_entity_description = HASelectEntityDescription(
            key=ATTR_PARENT,
            name=ATTR_PARENT,
            config_key=ATTR_PARENT,
            entity_category=EntityCategory.CONFIG,
            translation_key=ATTR_PARENT,
            options=[self.get_area_name(area_id) for area_id in self.areas],
        )

        entity_descriptions = [parent_entity_description]

        for attribute_key in self._config_manager.area_attributes:
            options = self._config_manager.area_attributes.get(attribute_key, [])

            entity_description = HASelectEntityDescription(
                key=attribute_key,
                name=attribute_key.capitalize(),
                config_key=attribute_key,
                entity_category=EntityCategory.CONFIG,
                options=options,
            )

            entity_descriptions.append(entity_description)

        for entity_key in self._config_manager.area_entities:
            entity_details = self._config_manager.area_entities.get(entity_key)
            name = entity_details.get(ATTR_NAME)
            domain = entity_details.get(ATTR_DOMAIN)
            attributes = entity_details.get(ATTR_ATTRIBUTES)
            include_nested = entity_details.get(ATTR_INCLUDE_NESTED, False)

            entity_description = get_entity_description(
                Platform(domain), name, include_nested, attributes
            )

            entity_descriptions.append(entity_description)

        result = [
            entity_description
            for entity_description in entity_descriptions
            if entity_description.platform == platform
        ]

        return result

    async def set_parent(self, area_id: str, value: Any) -> None:
        await self._config_manager.set_area_parent(area_id, value)

        await self.async_request_refresh()

    def get_area_details(
        self, area_id: str, entity_description: BaseEntityDescription
    ) -> Any:
        return self._config_manager.get_area_details(area_id, entity_description.key)

    async def set_area_details(
        self, area_id: str, value: Any, entity_description: BaseEntityDescription
    ) -> None:
        await self._config_manager.set_area_details(
            area_id, value, entity_description.key
        )

        await self.async_request_refresh()

    async def set_state(
        self, area_id: str, value: Any, entity_description: BaseEntityDescription
    ) -> None:
        entities = self.get_related_entities(area_id, entity_description)
        entity_ids = [entity[ATTR_ENTITY_ID] for entity in entities]
        service_data = {ATTR_ENTITY_ID: entity_ids}
        service_name = None

        if entity_description.platform in [Platform.SWITCH, Platform.LIGHT]:
            service_name = SERVICE_TURN_ON if value == STATE_ON else SERVICE_TURN_OFF

        if service_name is not None:
            self.hass.services.call(
                entity_description.platform, service_name, service_data
            )

    def get_related_entities(
        self, area_id: str, entity_description: BaseEntityDescription
    ) -> list[dict[str, Any]]:
        result = []
        area_lookup = [area_id]

        if entity_description.include_nested:
            area_details = self.areas.get(area_id, {})
            nested_area = area_details.get(ATTR_NESTED, [])

            area_lookup.extend(nested_area)

        for entity_id in self.entities:
            entity_details = self.entities[entity_id]
            entity_area_id = entity_details.get(ATTR_AREA_ID)

            entity_attributes = entity_details.get(ATTR_ATTRIBUTES, {})
            generated_by = entity_attributes.get("generated_by")

            relevant_entity = generated_by != DOMAIN
            relevant_domain = entity_id.startswith(f"{entity_description.platform}.")
            relevant_area = entity_area_id in area_lookup
            relevant_attributes = True

            if entity_description.attributes is not None:
                for attribute_key in entity_description.attributes:
                    attributes_values = entity_description.attributes.get(attribute_key)
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

    def _register_services(self):
        self.hass.services.async_register(
            DOMAIN,
            SERVICE_SET_ATTRIBUTE,
            self._handle_service_set_attribute,
            SERVICE_SCHEMA_SET_ATTRIBUTE,
        )

        self.hass.services.async_register(
            DOMAIN,
            SERVICE_REMOVE_ATTRIBUTE,
            self._handle_service_remove_attribute,
            SERVICE_SCHEMA_REMOVE_AREA_X,
        )

        self.hass.services.async_register(
            DOMAIN,
            SERVICE_SET_ENTITY,
            self._handle_service_set_entity,
            SERVICE_SCHEMA_SET_ENTITY,
        )

        self.hass.services.async_register(
            DOMAIN,
            SERVICE_REMOVE_ENTITY,
            self._handle_service_remove_entity,
            SERVICE_SCHEMA_REMOVE_AREA_X,
        )

    def _handle_service_set_attribute(self, service_call):
        self.hass.async_create_task(
            self._async_handle_service_set_attribute(service_call)
        )

    def _handle_service_remove_attribute(self, service_call):
        self.hass.async_create_task(
            self._async_handle_service_remove_attribute(service_call)
        )

    def _handle_service_set_entity(self, service_call):
        self.hass.async_create_task(self._async_handle_service_set_entity(service_call))

    def _handle_service_remove_entity(self, service_call):
        self.hass.async_create_task(
            self._async_handle_service_remove_entity(service_call)
        )

    async def _async_handle_service_set_attribute(self, service_call):
        data = service_call.data
        name = data.get(ATTR_NAME)
        options = data.get(ATTR_VALUES)

        await self._config_manager.set_area_attribute(name, options)

        await self._reload_integration()

    async def _async_handle_service_remove_attribute(self, service_call):
        data = service_call.data
        name = data.get(ATTR_NAME)

        await self._config_manager.remove_area_attribute(name)

        await self._reload_integration()

    async def _async_handle_service_set_entity(self, service_call):
        data = service_call.data
        name = data.get(ATTR_NAME)
        domain = data.get(ATTR_DOMAIN)
        attribute = data.get(ATTR_ATTRIBUTE)
        values = data.get(ATTR_VALUES)
        include_nested = data.get(ATTR_INCLUDE_NESTED, False)

        await self._config_manager.set_area_entity(
            name, domain, include_nested, attribute, values
        )

        await self._reload_integration()

    async def _async_handle_service_remove_entity(self, service_call):
        data = service_call.data
        name = data.get(ATTR_NAME)

        await self._config_manager.remove_area_entity(name)

        await self._reload_integration()

    async def _reload_integration(self):
        data = {ENTITY_CONFIG_ENTRY_ID: self.config_entry.entry_id}

        await self.hass.services.async_call(HA_NAME, SERVICE_RELOAD_CONFIG_ENTRY, data)

    async def _handle_area_or_entity_changed_event(self, _event: Event):
        await self._reload_data()

    async def _reload_data(self):
        self._load_areas()
        self._load_entities()

        await self._start_listen_entity_change()

    def get_area_parent_id(self, area_id: str) -> str | None:
        area_parent = self._config_manager.area_parents.get(area_id)

        return area_parent

    def _get_nested_area(self, area_id: str, nested_areas=None) -> list[str]:
        if nested_areas is None:
            nested_areas = []

        area_parents = self._config_manager.area_parents

        for area_config_id in area_parents:
            area_parent = self.get_area_parent_id(area_config_id)

            if area_parent == area_id:
                nested_areas.append(area_config_id)

                self._get_nested_area(area_config_id, nested_areas)

        return nested_areas

    def _load_areas(self):
        try:
            _LOGGER.debug("Start loading areas")

            area_current_key = "|".join(self._ar.areas.keys())
            area_previous_key = "|".join(self.areas.keys())

            if area_current_key != area_previous_key:
                self._data[DATA_AREAS_KEY] = {}
                self._dispatched_areas = []

                for area in self._ar.areas.values():
                    self._load_area(area)

                _LOGGER.debug(f"Loaded {len(self.areas.keys())} areas")

            else:
                _LOGGER.debug("No changes for areas list")

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to load areas, Error: {ex}, Line: {line_number}")

    def _load_area(self, area: AreaEntry):
        _LOGGER.debug(f"Loading are '{area.name}'")

        nested_area = self._get_nested_area(area.id)

        self._data[DATA_AREAS_KEY][area.id] = {
            ATTR_NAME: area.name,
            ATTR_AREA_ID: area.id,
            ATTR_NESTED: nested_area,
        }

    def _load_entities(self):
        try:
            _LOGGER.debug("Start loading entities")

            all_area_entities = {
                area_id: self._get_relevant_entities(area_id) for area_id in self.areas
            }

            entities = []

            for area_id in all_area_entities:
                area_entities = all_area_entities[area_id]

                entities.extend(area_entities)

            current_entities = [entity.entity_id for entity in entities]

            current_key = "|".join(current_entities)
            previous_key = "|".join(self.entities.keys())

            if current_key != previous_key:
                self._data[DATA_ENTITIES_KEY] = {}

                for area_id in all_area_entities:
                    area = self.areas.get(area_id)
                    entities = all_area_entities[area_id]

                    for entity in entities:
                        self._load_entity(entity, area)

                _LOGGER.debug(f"Loaded {len(self.entities.keys())} entities")

            else:
                _LOGGER.debug("No changes for entity list")

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to load entities, Error: {ex}, Line: {line_number}")

    def _get_relevant_entities(self, look_for_area_id: str) -> list[RegistryEntry]:
        result: list[RegistryEntry] = []

        try:
            all_devices = self._dr.devices

            for entity in self._er.entities.values():
                area_id = entity.area_id

                if entity.area_id is None and entity.device_id is not None:
                    device = all_devices.get(entity.device_id)
                    area_id = device.area_id

                if area_id == look_for_area_id and entity.domain in ENTITY_PLATFORMS:
                    result.append(entity)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to get relevant entities, Area: {look_for_area_id}, Error: {ex}, Line: {line_number}"
            )

        return result

    def _load_entity(self, entity: RegistryEntry, area: dict):
        entity_data = entity.as_partial_dict

        try:
            entity_data[ATTR_AREA_ID] = area.get(ATTR_AREA_ID)
            entity_data[ATTR_NAME] = area.get(ATTR_NAME)

            entity_data[ATTR_DOMAIN] = entity.domain
            entity_data[ATTR_STATE] = self.hass.states.get(entity.entity_id)

            self._data[DATA_ENTITIES_KEY][entity.entity_id] = entity_data

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to load entity, Entity: {entity_data}: Area: {area}, Error: {ex}, Line: {line_number}"
            )

    async def _start_listen_entity_change(self):
        try:
            _LOGGER.debug("Start listening to entity's changes")

            for area_id in self.areas:
                if area_id not in self._dispatched_areas:
                    self._dispatched_areas.append(area_id)

                    async_dispatcher_send(
                        self.hass,
                        SIGNAL_AREA_LOADED,
                        self._config_manager.entry_id,
                        area_id,
                    )

            if self._track_state_handler is not None:
                self._track_state_handler()

            entity_ids = list(self.entities.keys())

            self._track_state_handler = async_track_state_change_event(
                self.hass, entity_ids, self._watched_entity_change
            )

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to start listening to entity events, Error: {ex}, Line: {line_number}"
            )

    async def _watched_entity_change(self, event: Event) -> None:
        if (to_state := event.data.get("new_state")) is None:
            return

        if (old_state := event.data.get("old_state")) is None:
            return

        if to_state.state == old_state.state:
            return

        entity_id = event.data.get(ATTR_ENTITY_ID)
        _LOGGER.debug(
            f"Entity: {entity_id}, Changed from {old_state.state} to {to_state.state}"
        )

        self._data[DATA_ENTITIES_KEY][entity_id][ATTR_STATE] = to_state.state

        await self.async_request_refresh()

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            async with async_timeout.timeout(10):
                return {
                    DATA_HA: self._data,
                    DATA_CONFIG: self._config_manager.get_config_data(),
                }

        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")
