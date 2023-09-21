"""
Support for sensor
"""
from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_NAME, ATTR_STATE, Platform
from homeassistant.core import HomeAssistant, callback

from .common.base_entity import IntegrationBaseEntity, async_setup_base_entry
from .common.consts import DOMAIN
from .common.entity_descriptions import HASensorEntityDescription
from .managers.ha_coordinator import HACoordinator

_LOGGER = logging.getLogger(__name__)

_PLATFORM = Platform.SENSOR


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    await async_setup_base_entry(
        hass,
        entry,
        _PLATFORM,
        HASensorEntity,
        async_add_entities,
    )


class HASensorEntity(IntegrationBaseEntity, SensorEntity):
    """Representation of a sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        entity_description: HASensorEntityDescription,
        coordinator: HACoordinator,
        area_id: str,
    ):
        super().__init__(hass, entity_description, coordinator, area_id)

        self._attr_device_class = entity_description.device_class

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        attributes = {"generated_by": DOMAIN}

        entities = self.coordinator.get_related_entities(
            self.area_id, self.entity_description
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
