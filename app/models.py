from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class NaverListing:
    listing_id: str
    result_level: str = "article"
    title: str | None = None
    price_text: str | None = None
    trade_type: str | None = None
    area_text: str | None = None
    floor_text: str | None = None
    complex_name: str | None = None
    detail_url: str | None = None
    raw_payload: dict | None = None


@dataclass(slots=True)
class PollResult:
    watch_id: int
    label: str
    search_url: str
    total_count: int
    baseline_created: bool
    new_listings: list[NaverListing]


@dataclass(slots=True)
class RangeFilter:
    minimum: str | None = None
    maximum: str | None = None


@dataclass(slots=True)
class NaverSearchFilters:
    source_url: str
    source_version: str
    center_lat: float | None = None
    center_lon: float | None = None
    zoom: int | None = None
    trade_types: list[str] | None = None
    real_estate_types: list[str] | None = None
    deal_price: RangeFilter | None = None
    warranty_price: RangeFilter | None = None
    rent_price: RangeFilter | None = None
    space: RangeFilter | None = None
    household_number: RangeFilter | None = None
    parking_types: list[str] | None = None
    entrance_types: list[str] | None = None
    room_count: list[str] | None = None
    bathroom_count: list[str] | None = None
    floor: list[str] | None = None
    direction: list[str] | None = None
    approval_elapsed_year: RangeFilter | None = None
    management_fee: RangeFilter | None = None
    move_in_types: list[str] | None = None
    facilities: list[str] | None = None
    one_room_shape_types: list[str] | None = None
    real_estate_type_codes_legacy: list[str] | None = None
    raw_query: dict[str, str] | None = None
