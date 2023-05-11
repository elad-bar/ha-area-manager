from __future__ import annotations

from collections.abc import Awaitable, Callable, ValuesView
import logging
import sys

from homeassistant.components.binary_sensor import (
    DOMAIN as DOMAIN_BINARY_SENSOR,
    BinarySensorDeviceClass,
)
from homeassistant.components.sensor import DOMAIN as DOMAIN_SENSOR, SensorDeviceClass
from homeassistant.const import (
    ATTR_AREA_ID,
    ATTR_DEVICE_CLASS,
    ATTR_DOMAIN,
    ATTR_ENTITY_ID,
    ATTR_NAME,
    ATTR_STATE,
    STATE_OFF,
)
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers.area_registry import AreaRegistry, async_get as async_ar_get
from homeassistant.helpers.device_registry import (
    DeviceRegistry,
    DeviceRegistryItems,
    async_get as async_dr_get,
)
from homeassistant.helpers.entity_registry import (
    EntityRegistry,
    RegistryEntry,
    async_get as async_er_get,
)
from homeassistant.helpers.event import async_track_state_change_event

from ...configuration.models.config_data import ConfigData
from ...core.api.base_api import BaseAPI
from ...core.helpers.enums import ConnectivityStatus
from ..helpers.const import ALLOWED_STATE_TRANSITIONS

_LOGGER = logging.getLogger(__name__)


class IntegrationAPI(BaseAPI):
    """The Class for handling the data retrieval."""

    _config_data: ConfigData | None

    _ar: AreaRegistry
    _dr: DeviceRegistry
    _er: EntityRegistry

    _area_configuration: dict

    def __init__(
        self,
        hass: HomeAssistant | None,
        async_on_data_changed: Callable[[], Awaitable[None]] | None = None,
        async_on_status_changed: Callable[[ConnectivityStatus], Awaitable[None]]
        | None = None,
    ):
        super().__init__(hass, async_on_data_changed, async_on_status_changed)

        try:
            self._track_state_handler = None
            self._config_data = None
            self._cookies = {}
            self._last_valid = None

            self.data = {"entities": {}, "areas": {}, "events": {}}

            self._ar = async_ar_get(self.hass)
            self._dr = async_dr_get(self.hass)
            self._er = async_er_get(self.hass)

            self._area_configuration = {}

            self._listen_domain_device_class = {
                DOMAIN_BINARY_SENSOR: [
                    BinarySensorDeviceClass.SAFETY,
                    BinarySensorDeviceClass.CO,
                    BinarySensorDeviceClass.DOOR,
                    BinarySensorDeviceClass.WINDOW,
                    BinarySensorDeviceClass.SMOKE,
                    BinarySensorDeviceClass.MOTION,
                    BinarySensorDeviceClass.MOISTURE,
                    BinarySensorDeviceClass.GAS,
                    BinarySensorDeviceClass.OCCUPANCY,
                ],
                DOMAIN_SENSOR: [
                    SensorDeviceClass.TEMPERATURE,
                    SensorDeviceClass.HUMIDITY,
                ],
            }
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(f"Failed to load API, error: {ex}, line: {line_number}")

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

        entity_id = to_state.get(ATTR_ENTITY_ID)

        if entity_id in self.data["entities"]:
            entity_data = self.data["entities"][entity_id]

            entity_data[ATTR_STATE] = to_state.state

            area_id = entity_data[ATTR_AREA_ID]

            if area_id is not None:
                self.recalculate_area(area_id)

    def recalculate_area(self, area_id):
        security_state = STATE_OFF
        area_security_entities = {}
        area_data = self.areas.get(area_id)

        nested_areas = area_data.get("nested", [])

        for entity_id in self.entities:
            entity_data = self.entities.get(entity_id, {})
            entity_area_id = entity_data.get(ATTR_AREA_ID)

            state = entity_data.get(ATTR_STATE)
            domain = entity_data.get(ATTR_DOMAIN, "")

            if domain == DOMAIN_SENSOR and entity_area_id == area_id:
                device_class = entity_data.get(ATTR_DEVICE_CLASS, "")

                area_data[device_class] = state

            if (
                domain == DOMAIN_BINARY_SENSOR
                and area_id in nested_areas
                or entity_area_id == area_id
            ):
                area_security_entities[entity_id] = state

                security_state = self.get_security_binary_state(security_state, state)

        area_data["security"] = security_state
        area_data["entities"] = area_security_entities

    @staticmethod
    def get_security_binary_state(current: str, state: str):
        allowed_state_transitions = ALLOWED_STATE_TRANSITIONS.get(current, [])

        if len(allowed_state_transitions) > 0 and state in allowed_state_transitions:
            current = state

        return current

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

        for area_config_id in self._area_configuration:
            area_config = self._area_configuration.get(area_config_id, {})
            area_parent = area_config.get("parent")

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
                entity_data[ATTR_DEVICE_CLASS] = entity.device_class
                entity_data[ATTR_STATE] = self.hass.states.get(entity.entity_id)

                self._set_entity(entity_data)
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to load entity, Entity: {entity_data}, Error: {ex}, Line: {line_number}"
            )

    def _set_entity(self, entity: dict):
        entity_id = entity.get(ATTR_ENTITY_ID)
        self.data["entities"][entity_id] = entity

    def _remove_entity(self, entity: dict):
        entity_id = entity.get(ATTR_ENTITY_ID)

        if entity_id in self.entities:
            self.data["entities"].pop(entity_id)

    def update_configuration(self, area_configuration):
        self._area_configuration = area_configuration

    async def async_update(self):
        try:
            self.load_areas()
            self.load_entities()

            for area_id in self.areas:
                self.recalculate_area(area_id)

            await self.start_listen_entity_change()

            await self.fire_data_changed_event()
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to extract WS data, Error: {ex}, Line: {line_number}"
            )
