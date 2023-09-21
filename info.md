# Area Manager

## Monitor and control HA at scale

Integration to represent each Area as device, define parent area, set custom attributes and entities.

### Use cases

- Define whether the area is Indoor or Outdoor for automation of turn all lights off / on
- Define security sensor per area whether there is motion and using automation send notification
- Define security sensor that identify risks in each area (including sub area) using entity rule of device class in [motion, sound, gas, smoke, door, window, etc...] to use with automation of alert
- Build dynamic UI that will work according to area and allow to draw automatically all custom entities, dive into specific sub area, etc...

[Changelog](https://github.com/elad-bar/ha-area-manager/blob/master/CHANGELOG.md)

## How to

### Installation

1. Add Custom Integration Repository

   Currently, integration is not officially available, please add the repo to HACS before trying to install it in HACS > Integrations > 3 dots menu > Custom repository
   Repository: _elad-bar/ha-area-manager_
   Category: _Integration_

2. Install integration via HACS

   In HACS, look for "Area Manager" and install and restart

3. Setup HA integration

   Settings > Devices & Services (Lower Right) > Add Integration > _Area Manager_

## Devices & Components

### Per area

- Device: Name after the area name
- SELECT Entity: Area {Area Name} Parent

#### Custom Attributes

By adding attributes using _Set attribute_ (_area_manager.set_attribute_) service, each area will include _SELECT_ entity that will allow user to set the relevant attribute from available values,
later it will allow to use in automation and UI.

#### Custom Entities

By adding entity rules using _Set entity_ (_area_manager.set_entity_) service, each area will include relevant entity that aggregates status of entities in the area,
Service description is available below and allows to set whether to include just the entities directly connected to the area or include nested as well,
Setting the entity rules requires setting domain, domain aggregation work according to the following flow:

- Binary Sensor, Light, Switch - If one of the component in the rule are on, custom entity will be on, otherwise - off
- Sensor - If numeric value, will perform average evaluation of relevant entities, otherwise, will take first

## Services

### Set attribute

Sets custom attribute for an area and reload the `area_manager` integration,
Name is unique identifier of the entity

#### Example

```yaml
service: area_manager.set_attribute
data:
  name: "Location"
  attribute: "device_class"
  values:
    - Indoor
    - Outdoor
```

### Remove attribute

Removes custom attribute for an area and reload the `area_manager` integration

#### Example

```yaml
service: area_manager.remove_attribute
data:
  name: "Location"
```

### Set entity

Sets custom entity rule for an area and reload the `area_manager` integration,
Name is unique identifier of the entity,
Supported domains:

- Binary Sensor
- Light
- Sensor
- Switch

#### Example

```yaml
service: area_manager.set_entity
data:
  name: "Security Status"
  attribute: "device_class"
  nested: False
  values:
    - motion
    - sound
```

### Remove entity

Removes custom entity rule for an area and reload the `area_manager` integration.

#### Example

```yaml
service: area_manager.remove_entity
data:
  name: "Security Status"
```

## Debugging

To set the log level of the component to DEBUG, please set it from the options of the component if installed, otherwise, set it within configuration YAML of HA:

```yaml
logger:
  default: warning
  logs:
    custom_components.area_manager: debug
```
