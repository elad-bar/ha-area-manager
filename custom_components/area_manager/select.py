"""
Support for sensor
"""
from __future__ import annotations

import logging
import sys

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback

from .common.base_entity import IntegrationBaseEntity, async_setup_base_entry
from .common.consts import ATTR_PARENT
from .common.entity_descriptions import HASelectEntityDescription
from .managers.ha_coordinator import HACoordinator

_LOGGER = logging.getLogger(__name__)

_PLATFORM = Platform.SELECT


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    await async_setup_base_entry(
        hass,
        entry,
        _PLATFORM,
        HASelectEntity,
        async_add_entities,
    )


class HASelectEntity(IntegrationBaseEntity, SelectEntity):
    """Representation of a select."""

    def __init__(
        self,
        hass: HomeAssistant,
        entity_description: HASelectEntityDescription,
        coordinator: HACoordinator,
        area_id: str,
    ):
        super().__init__(hass, entity_description, coordinator, area_id)

        self._attr_device_class = entity_description.device_class
        self._attr_current_option = None
        self._attr_options = entity_description.options

        self._set_parent_context()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        self._set_parent_context()

        self.async_write_ha_state()

    def _set_parent_context(self):
        try:
            if self.entity_description.key == ATTR_PARENT:
                parent_area_id = self.coordinator.get_area_parent_id(self.area_id)
                parent_area_name = (
                    None
                    if parent_area_id is None
                    else self.coordinator.get_area_name(parent_area_id)
                )

                self._attr_current_option = parent_area_name

            else:
                self._attr_current_option = self.coordinator.get_area_details(
                    self.area_id, self.entity_description
                )

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to set parent context for SELECT, Error: {ex}, Line: {line_number}"
            )

    async def async_select_option(self, option: str) -> None:
        if self.entity_description.key == ATTR_PARENT:
            areas_reverse = {
                self.coordinator.get_area_name(area_id): area_id
                for area_id in self.coordinator.areas
            }

            option = areas_reverse.get(option)

            await self.coordinator.set_parent(self.area_id, option)
        else:
            await self.coordinator.set_state(
                self.area_id, option, self.entity_description
            )
