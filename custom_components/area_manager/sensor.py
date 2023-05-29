"""
Support for sensor
"""
from __future__ import annotations

import logging
import sys

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_NAME, ATTR_STATE, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .common.consts import DOMAIN
from .common.entity_descriptions import HASensorEntityDescription
from .managers.ha_coordinator import HACoordinator

_LOGGER = logging.getLogger(__name__)

_PLATFORM = Platform.SENSOR


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up the sensor platform."""
    try:
        coordinator = hass.data[DOMAIN][entry.entry_id]
        entities = []
        entity_descriptions = coordinator.get_entity_descriptions(_PLATFORM)

        for entity_description in entity_descriptions:
            for area_id in coordinator.areas:
                entity = HASensorEntity(area_id, entity_description, coordinator)

                entities.append(entity)

        _LOGGER.debug(f"Setting up {_PLATFORM} entities: {entities}")

        async_add_entities(entities, True)

    except Exception as ex:
        exc_type, exc_obj, tb = sys.exc_info()
        line_number = tb.tb_lineno

        _LOGGER.error(
            f"Failed to initialize {_PLATFORM}, Error: {ex}, Line: {line_number}"
        )


class HASensorEntity(CoordinatorEntity, SensorEntity):
    """Representation of a sensor."""

    def __init__(
        self,
        area_id: str,
        entity_description: HASensorEntityDescription,
        coordinator: HACoordinator,
    ):
        super().__init__(coordinator)

        area_name = coordinator.areas.get(area_id)

        entity_name = f"{area_name} {entity_description.name}"

        unique_id = slugify(f"{entity_description.platform} {entity_name} {area_id}")

        self.entity_description: HASensorEntityDescription = entity_description
        self._area_id = area_id
        self._attr_device_info = coordinator.get_device_info(area_id)
        self._attr_name = entity_name
        self._attr_unique_id = unique_id
        self._attr_device_class = entity_description.device_class

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        attributes = {"generated_by": DOMAIN}

        entities = self.coordinator.get_related_entities(
            self._area_id, self.entity_description
        )

        native_value = None

        for entity in entities:
            entity_state = entity[ATTR_STATE]
            entity_name = entity[ATTR_NAME]

            attributes[entity_name] = entity_state.state

            if native_value is None:
                native_value = entity_state.state

        self._attr_native_value = native_value
        self._attr_extra_state_attributes = attributes

        self.async_write_ha_state()
