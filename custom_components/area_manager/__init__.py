import logging
import sys

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .common.consts import DEFAULT_NAME, DOMAIN, SUPPORTED_PLATFORMS
from .managers.ha_config_manager import HAConfigManager
from .managers.ha_coordinator import HACoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup(_hass, _config):
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a Shinobi Video component."""
    initialized = False

    try:
        config_manager = HAConfigManager(hass, entry)
        await config_manager.initialize()

        coordinator = HACoordinator(hass, config_manager)

        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

        await hass.config_entries.async_forward_entry_setups(entry, SUPPORTED_PLATFORMS)

        await coordinator.async_config_entry_first_refresh()

        _LOGGER.info("Finished loading integration")

        initialized = True

    except Exception as ex:
        exc_type, exc_obj, tb = sys.exc_info()
        line_number = tb.tb_lineno

        _LOGGER.error(
            f"Failed to load {DEFAULT_NAME}, error: {ex}, line: {line_number}"
        )

    return initialized


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    _LOGGER.info(f"Unloading {DOMAIN} integration, Entry ID: {entry.entry_id}")

    coordinator: HACoordinator = hass.data[DOMAIN][entry.entry_id]

    await coordinator.terminate()

    for platform in SUPPORTED_PLATFORMS:
        await hass.config_entries.async_forward_entry_unload(entry, platform)

    del hass.data[DOMAIN][entry.entry_id]

    return True
