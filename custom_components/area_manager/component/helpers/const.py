"""
Support for Constants.
"""
from datetime import timedelta

import voluptuous as vol

from homeassistant.const import (
    ATTR_DOMAIN,
    ATTR_NAME,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)
import homeassistant.helpers.config_validation as cv

ATTR_FRIENDLY_NAME = "friendly_name"
ATTR_ATTRIBUTES = "attributes"
ATTR_VALUES = "values"

CONF_NESTED_AREA_ID = "nested_area_id"

WS_MAX_MSG_SIZE = 0

DEFAULT_UPDATE_API_INTERVAL = timedelta(seconds=1)
DEFAULT_UPDATE_ENTITIES_INTERVAL = timedelta(seconds=1)
DEFAULT_HEARTBEAT_INTERVAL = timedelta(seconds=50)
DEFAULT_CONSIDER_AWAY_INTERVAL = timedelta(minutes=3)

STORAGE_DATA_FILE_CONFIG = "config"

STORAGE_DATA_FILES = [STORAGE_DATA_FILE_CONFIG]
STORAGE_DATA_AREA_CONFIGURATION = "area"
STORAGE_DATA_AREA_TYPES = "types"

API_DATA_LAST_UPDATE = "lastUpdate"

DEFAULT_AREA_TYPE = ["Service", "Hosting", "Passage", "Bedroom", "Office"]

AREA_ID = "id"
AREA_IS_OUTDOOR = "is_outdoor"
AREA_TYPE = "type"
AREA_NESTED = "nested"

SERVICE_SET_AREA_TYPE = "set_area_type"
SERVICE_REMOVE_AREA_TYPE = "remove_area_type"
SERVICE_SET_ENTITY = "set_entity"
SERVICE_REMOVE_ENTITY = "remove_entity"

SERVICE_SCHEMA_UPDATE_AREA_TYPE = vol.Schema({vol.Required(AREA_TYPE): cv.string})

SERVICE_SCHEMA_ATTRIBUTE = vol.Schema(
    {
        vol.Required(ATTR_NAME): cv.string,
        vol.Required(ATTR_VALUES): vol.All(cv.ensure_list, [cv.string]),
    }
)

SERVICE_SCHEMA_SET_ENTITY = vol.Schema(
    {
        vol.Required(ATTR_NAME): cv.string,
        vol.Required(ATTR_DOMAIN): cv.string,
        vol.Required(ATTR_ATTRIBUTES): vol.All(
            cv.ensure_list, [SERVICE_SCHEMA_ATTRIBUTE]
        ),
    }
)

SERVICE_SCHEMA_REMOVE_ENTITY = vol.Schema({vol.Required(ATTR_NAME): cv.string})

ALLOWED_STATE_TRANSITIONS = {
    STATE_OFF: [STATE_ON, STATE_UNAVAILABLE],
    STATE_ON: [STATE_UNAVAILABLE],
}
