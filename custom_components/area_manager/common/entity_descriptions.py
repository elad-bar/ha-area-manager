from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntityDescription
from homeassistant.components.light import LightEntityDescription
from homeassistant.components.select import SelectEntityDescription
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.const import Platform
from homeassistant.helpers.entity import EntityDescription
from homeassistant.util import slugify


@dataclass(slots=True)
class BaseEntityDescription(EntityDescription):
    platform: Platform | None = None
    attributes: dict[str, list[Any]] | None = None
    include_nested: bool = False
    config_key: str | None = None


@dataclass(slots=True)
class HABinarySensorEntityDescription(
    BinarySensorEntityDescription, BaseEntityDescription
):
    platform: Platform | None = Platform.BINARY_SENSOR


@dataclass(slots=True)
class HASensorEntityDescription(SensorEntityDescription, BaseEntityDescription):
    platform: Platform | None = Platform.SENSOR


@dataclass(slots=True)
class HASelectEntityDescription(SelectEntityDescription, BaseEntityDescription):
    platform: Platform | None = Platform.SELECT


@dataclass(slots=True)
class HASwitchEntityDescription(SwitchEntityDescription, BaseEntityDescription):
    platform: Platform | None = Platform.SWITCH


@dataclass(slots=True)
class HALightEntityDescription(LightEntityDescription, BaseEntityDescription):
    platform: Platform | None = Platform.LIGHT


def get_entity_description(
    platform: Platform,
    name: str,
    include_nested: bool,
    attributes: dict[str, list[Any]] | None = None,
):
    if platform == Platform.SELECT:
        return HASelectEntityDescription(
            key=slugify(name),
            name=name,
            attributes=attributes,
            include_nested=include_nested,
        )
    elif platform == Platform.LIGHT:
        return HALightEntityDescription(
            key=slugify(name),
            name=name,
            attributes=attributes,
            include_nested=include_nested,
        )
    elif platform == Platform.SWITCH:
        return HASwitchEntityDescription(
            key=slugify(name),
            name=name,
            attributes=attributes,
            include_nested=include_nested,
        )
    elif platform == Platform.SENSOR:
        return HASensorEntityDescription(
            key=slugify(name),
            name=name,
            attributes=attributes,
            include_nested=include_nested,
        )
    elif platform == Platform.BINARY_SENSOR:
        return HABinarySensorEntityDescription(
            key=slugify(name),
            name=name,
            attributes=attributes,
            include_nested=include_nested,
        )
    else:
        return BaseEntityDescription(
            key=slugify(name),
            name=name,
            attributes=attributes,
            include_nested=include_nested,
        )
