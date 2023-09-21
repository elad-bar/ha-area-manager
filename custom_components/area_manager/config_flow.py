"""Config flow to configure."""
from __future__ import annotations

import logging

from homeassistant import config_entries

from .common.consts import DEFAULT_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class DomainFlowHandler(config_entries.ConfigFlow):
    """Handle a domain config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle a flow start."""
        _LOGGER.debug(f"Starting async_step_user of {DEFAULT_NAME}")

        already_exists = False

        if already_exists:
            errors = {"base": "already_configured"}

            return self.async_show_form(step_id="user", errors=errors)

        return self.async_create_entry(title=DEFAULT_NAME, data={})
