# Area Manager

## Description

Provides an ability to create entities for each area and define nested areas.

[Changelog](https://github.com/elad-bar/ha-area-manager/blob/master/CHANGELOG.md)

## How to

#### Installations via HACS

- In HACS, look for "Area Manager" and install and restart
- In Settings --> Devices & Services - (Lower Right) "Add Integration"

#### Setup

To add integration use Configuration -> Integrations -> Add `Area Manager`

#### Debugging

To set the log level of the component to DEBUG, please set it from the options of the component if installed, otherwise, set it within configuration YAML of HA:

```yaml
logger:
  default: warning
  logs:
    custom_components.area_manager: debug
```

## Components

### Per area

| Entity Name              | Type   | Description                                   |
| ------------------------ | ------ | --------------------------------------------- |
| Area {Area Name} Parent  | Select | Represents the parent area                    |
| Area {Area Name} Type    | Select | Represents the type of the area               |
| Area {Area Name} Outdoor | Select | Represents whether the area is outdoor or not |

## Services

### Set area type

Links nested area to specific area

```yaml
service: area_manager.set_area_type
data:
  area_type: string
```

### Unlink area

Unlinks nested area to specific area

```yaml
service: area_manager.remove_area_type
data:
  area_type: string
```

### Set area entity definition

Creates area entity according to definition

```yaml
service: area_manager.set_entity
data:
  name: string
  domain: string
  attributes:
    - name:
      value:
        - a
        - b
```

### Remove area entity definition

Remove area entity according to definition

```yaml
service: area_manager.remove_entity
data:
  name: string
```

### Action

```yaml
service: area_manager.call_service
data:
  area_id: { Area ID }
  domain:
  service:
  data: {}
```
