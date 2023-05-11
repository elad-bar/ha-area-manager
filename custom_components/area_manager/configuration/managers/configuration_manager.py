from __future__ import annotations

import logging
import sys
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from ...core.api.base_api import BaseAPI
from ..models.config_data import ConfigData

_LOGGER = logging.getLogger(__name__)


class ConfigurationManager:
    config: dict[str, ConfigData]
    api: BaseAPI | None

    def __init__(self, hass: HomeAssistant, api: BaseAPI | None = None):
        self.hass = hass
        self.config = {}
        self.api = api

    async def initialize(self):
        pass

    def get(self, entry_id: str):
        config = self.config.get(entry_id)

        return config

    async def load(self, entry: ConfigEntry):
        try:
            await self.initialize()

            config = {k: entry.data[k] for k in entry.data}

            config_data = ConfigData.from_dict(config)

            if config_data is not None:
                config_data.entry = entry

                self.config[entry.entry_id] = config_data
        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to load configuration, error: {str(ex)}, line: {line_number}"
            )

    async def validate(self, data: dict[str, Any]):
        if self.api is None:
            _LOGGER.error("Validate configuration is not supported through that flow")
            return

        _LOGGER.debug("Validate login")

        await self.api.validate(data)

    @staticmethod
    def get_data_fields(user_input: dict[str, Any] | None) -> dict[vol.Marker, Any]:
        fields = {}

        return fields

    def get_options_fields(self, user_input: dict[str, Any]) -> dict[vol.Marker, Any]:
        if user_input is None:
            data = ConfigData.from_dict().to_dict()

        else:
            data = {k: user_input[k] for k in user_input}

        fields = self.get_data_fields(data)

        return fields

    def remap_entry_data(
        self, entry: ConfigEntry, options: dict[str, Any]
    ) -> dict[str, Any]:
        config_options = {}
        config_data = {}

        for key in options:
            config_options[key] = options.get(key)

        config_entries = self.hass.config_entries
        config_entries.async_update_entry(entry, data=config_data)

        return config_options
