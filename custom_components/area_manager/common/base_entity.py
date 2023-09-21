import logging
import sys

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from ..managers.ha_coordinator import HACoordinator
from .consts import ADD_COMPONENT_SIGNALS, DEFAULT_NAME, DOMAIN
from .entity_descriptions import BaseEntityDescription

_LOGGER = logging.getLogger(__name__)


async def async_setup_base_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    platform: Platform,
    entity_type: type,
    async_add_entities,
):
    @callback
    def _async_handle_device(entry_id: str, area_id: str | None = None):
        if entry.entry_id != entry_id:
            return

        try:
            coordinator = hass.data[DOMAIN][entry.entry_id]

            entity_descriptions = coordinator.get_entity_descriptions(platform)

            entities = [
                entity_type(hass, entity_description, coordinator, area_id)
                for entity_description in entity_descriptions
            ]

            async_add_entities(entities, True)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to initialize {platform}, Area: {area_id}, Error: {ex}, Line: {line_number}"
            )

    for add_component_signal in ADD_COMPONENT_SIGNALS:
        entry.async_on_unload(
            async_dispatcher_connect(hass, add_component_signal, _async_handle_device)
        )


class IntegrationBaseEntity(CoordinatorEntity):
    _entity_description: BaseEntityDescription

    def __init__(
        self,
        hass: HomeAssistant,
        entity_description: BaseEntityDescription,
        coordinator: HACoordinator,
        area_id: str | None,
    ):
        super().__init__(coordinator)

        try:
            self.hass = hass
            self.area_id = None

            if area_id is None:
                device_info = coordinator.get_default_device_info()
                context_id = DEFAULT_NAME

            else:
                self.area_id = area_id
                device_info = coordinator.get_device_info(area_id)
                context_id = area_id

            entity_name = coordinator.config_manager.get_entity_name(
                entity_description, device_info
            )

            unique_id_parts = [
                DOMAIN,
                entity_description.platform,
                entity_description.key,
                context_id,
            ]

            unique_id = slugify("_".join(unique_id_parts))

            self.entity_description = entity_description
            self._entity_description = entity_description

            self._attr_device_info = device_info
            self._attr_name = entity_name
            self._attr_unique_id = unique_id

            self._data = {}

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to initialize {entity_description}, Error: {ex}, Line: {line_number}"
            )

    @property
    def _local_coordinator(self) -> HACoordinator:
        return self.coordinator

    @property
    def data(self) -> dict | None:
        return self._data
