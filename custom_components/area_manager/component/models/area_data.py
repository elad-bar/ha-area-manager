from __future__ import annotations

from ...core.helpers.const import ENTITY_UNIQUE_ID
from ..helpers.const import AREA_ID, AREA_IS_OUTDOOR, AREA_NESTED, AREA_TYPE


class AreaData:
    area_id: str
    is_outdoor: bool | None
    area_type: str | None
    nested: list[str] | None

    def __init__(
        self, area_id: str, is_outdoor: bool, area_type: str, nested: list[str]
    ):
        self.area_id = area_id
        self.is_outdoor = is_outdoor
        self.area_type = area_type
        self.nested = nested

    @property
    def unique_id(self) -> str:
        return self.area_id

    def to_dict(self):
        obj = {
            AREA_ID: self.area_id,
            AREA_IS_OUTDOOR: self.is_outdoor,
            AREA_TYPE: self.area_type,
            AREA_NESTED: self.nested,
            ENTITY_UNIQUE_ID: self.unique_id,
        }

        return obj

    def __repr__(self):
        to_string = f"{self.to_dict()}"

        return to_string
