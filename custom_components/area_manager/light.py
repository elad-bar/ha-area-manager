"""
Support for sensor
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_NAME,
    ATTR_STATE,
    STATE_ON,
    STATE_UNAVAILABLE,
    Platform,
)
from homeassistant.core import HomeAssistant, callback

from .common.base_entity import IntegrationBaseEntity, async_setup_base_entry
from .common.consts import ALLOWED_STATE_TRANSITIONS, ATTR_ATTRIBUTES, DOMAIN
from .common.entity_descriptions import HALightEntityDescription
from .managers.ha_coordinator import HACoordinator

_LOGGER = logging.getLogger(__name__)

_PLATFORM = Platform.LIGHT


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    await async_setup_base_entry(
        hass,
        entry,
        _PLATFORM,
        HALightEntity,
        async_add_entities,
    )


class HALightEntity(IntegrationBaseEntity, LightEntity):
    """Representation of a light."""

    def __init__(
        self,
        hass: HomeAssistant,
        entity_description: HALightEntityDescription,
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

        state = STATE_UNAVAILABLE if len(entities) == 0 else STATE_ON
        entity_attributes = None

        for entity in entities:
            entity_state = entity[ATTR_STATE]
            entity_name = entity[ATTR_NAME]

            attributes[entity_name] = entity_state.state

            state = self.get_light_state(state, entity_state.state)

            if entity_attributes is None:
                entity_attributes = entity.get(ATTR_ATTRIBUTES)

        if entity_attributes is not None:
            attributes.update(entity_attributes)

        self._attr_is_on = None if state == STATE_UNAVAILABLE else state
        self._attr_extra_state_attributes = attributes

        self.async_write_ha_state()

    @staticmethod
    def get_light_state(current: str, state: str):
        allowed_state_transitions = ALLOWED_STATE_TRANSITIONS.get(current, [])

        if len(allowed_state_transitions) > 0 and state in allowed_state_transitions:
            current = state

        return current

    async def async_turn_on(self, **kwargs: Any) -> None:
        value = kwargs.get(ATTR_STATE)

        await self.coordinator.set_state(self.area_id, value, self.entity_description)

    async def async_turn_off(self, **kwargs: Any) -> None:
        value = kwargs.get(ATTR_STATE)

        await self.coordinator.set_state(self.area_id, value, self.entity_description)
