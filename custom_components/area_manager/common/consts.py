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
DEFAULT_NAME = "Area Manager"

DATA_CONFIG = "config-data"
DATA_HA = "ha-data"
HA_NAME = "homeassistant"

DATA_AREAS_KEY = "areas"
DATA_ENTITIES_KEY = "entities"

ATTR_FRIENDLY_NAME = "friendly_name"
ATTR_ATTRIBUTES = "attributes"
ATTR_ATTRIBUTE = "attribute"
ATTR_INCLUDE_NESTED = "include_nested"
ATTR_VALUES = "values"
ATTR_NESTED = "nested"
ATTR_PARENT = "parent"

CONF_NESTED_AREA_ID = "nested_area_id"

SIGNAL_AREA_LOADED = f"{DOMAIN}_SIGNAL_AREA_LOADED"
SIGNAL_INTEGRATION_LOADED = f"{DOMAIN}_SIGNAL_INTEGRATION_LOADED"

ADD_COMPONENT_SIGNALS = [SIGNAL_AREA_LOADED, SIGNAL_INTEGRATION_LOADED]

DEFAULT_UPDATE_API_INTERVAL = timedelta(seconds=1)
DEFAULT_UPDATE_ENTITIES_INTERVAL = timedelta(seconds=1)
DEFAULT_HEARTBEAT_INTERVAL = timedelta(seconds=50)
DEFAULT_CONSIDER_AWAY_INTERVAL = timedelta(minutes=3)

ENTITY_CONFIG_ENTRY_ID = "entry_id"

STORAGE_DATA_FILE_CONFIG = "config"

STORAGE_DATA_FILES = [STORAGE_DATA_FILE_CONFIG]
STORAGE_DATA_AREA_PARENTS = "parents"
STORAGE_DATA_AREA_DETAILS = "details"
STORAGE_DATA_AREA_ENTITIES = "entities"
STORAGE_DATA_AREA_ATTRIBUTES = "attributes"

DEFAULT_ENTRY_ID = STORAGE_DATA_FILE_CONFIG

API_DATA_LAST_UPDATE = "lastUpdate"

SERVICE_SET_ATTRIBUTE = "set_attribute"
SERVICE_REMOVE_ATTRIBUTE = "remove_attribute"
SERVICE_SET_ENTITY = "set_entity"
SERVICE_REMOVE_ENTITY = "remove_entity"

ENTITY_PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.LIGHT,
    Platform.SENSOR,
    Platform.SWITCH,
]

SUPPORTED_PLATFORMS = ENTITY_PLATFORMS.copy()
SUPPORTED_PLATFORMS.append(Platform.SELECT)

SERVICE_SCHEMA_SET_ATTRIBUTE = vol.Schema(
    {
        vol.Required(ATTR_NAME): cv.string,
        vol.Required(ATTR_VALUES): vol.All(cv.ensure_list, [cv.string]),
    }
)

SERVICE_SCHEMA_SET_ENTITY = vol.Schema(
    {
        vol.Required(ATTR_NAME): cv.string,
        vol.Required(ATTR_DOMAIN): vol.In(
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

DEFAULT_ENTITY_DESCRIPTIONS = [
    HASelectEntityDescription(
        key=ATTR_PARENT,
        name=ATTR_PARENT,
        config_key=ATTR_PARENT,
        entity_category=EntityCategory.CONFIG,
        translation_key=ATTR_PARENT,
    )
]
