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
    EntityCategory,
    Platform,
)
import homeassistant.helpers.config_validation as cv

from .entity_descriptions import HASelectEntityDescription

DOMAIN = "area_manager"

DATA_CONFIG = "config-data"
DATA_HA = "ha-data"
HA_NAME = "homeassistant"

ATTR_FRIENDLY_NAME = "friendly_name"
ATTR_ATTRIBUTES = "attributes"
ATTR_ATTRIBUTE = "attribute"
ATTR_INCLUDE_NESTED = "include_nested"
ATTR_VALUES = "values"

CONF_NESTED_AREA_ID = "nested_area_id"

WS_MAX_MSG_SIZE = 0

DEFAULT_UPDATE_API_INTERVAL = timedelta(seconds=1)
DEFAULT_UPDATE_ENTITIES_INTERVAL = timedelta(seconds=1)
DEFAULT_HEARTBEAT_INTERVAL = timedelta(seconds=50)
DEFAULT_CONSIDER_AWAY_INTERVAL = timedelta(minutes=3)

ENTITY_CONFIG_ENTRY_ID = "entry_id"

STORAGE_DATA_FILE_CONFIG = "config"

STORAGE_DATA_FILES = [STORAGE_DATA_FILE_CONFIG]
STORAGE_DATA_AREA_SETTINGS = "area"
STORAGE_DATA_AREA_ENTITIES = "entities"
STORAGE_DATA_AREA_ATTRIBUTES = "attributes"

API_DATA_LAST_UPDATE = "lastUpdate"

AREA_NESTED = "nested"

SERVICE_SET_ATTRIBUTE = "set_attribute"
SERVICE_REMOVE_ATTRIBUTE = "remove_attribute"
SERVICE_SET_ENTITY = "set_entity"
SERVICE_REMOVE_ENTITY = "remove_entity"

SERVICE_SCHEMA_SET_ATTRIBUTE = vol.Schema(
    {
        vol.Required(ATTR_NAME): cv.string,
        vol.Required(ATTR_VALUES): vol.All(cv.ensure_list, [cv.string]),
    }
)

SERVICE_SCHEMA_SET_ENTITY = vol.Schema(
    {
        vol.Required(ATTR_NAME): cv.string,
        vol.Required(ATTR_DOMAIN): cv.entity_domain(
            [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.LIGHT, Platform.SWITCH]
        ),
        vol.Required(ATTR_INCLUDE_NESTED): cv.boolean,
        vol.Required(ATTR_ATTRIBUTE): cv.string,
        vol.Required(ATTR_VALUES): vol.All(cv.ensure_list, [cv.string]),
    }
)

SERVICE_SCHEMA_REMOVE_AREA_X = vol.Schema({vol.Required(ATTR_NAME): cv.string})

ALLOWED_STATE_TRANSITIONS = {
    STATE_OFF: [STATE_ON, STATE_UNAVAILABLE],
    STATE_ON: [STATE_UNAVAILABLE],
}

CONF_AREA_PARENT = "parent"

DEFAULT_ENTITY_DESCRIPTIONS = [
    HASelectEntityDescription(
        key=CONF_AREA_PARENT,
        name="Parent",
        config_key=CONF_AREA_PARENT,
        entity_category=EntityCategory.CONFIG,
    )
]
