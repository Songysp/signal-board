from __future__ import annotations

import json
import math
import re
from collections.abc import Iterable
from dataclasses import asdict
from urllib.parse import parse_qs, quote, urlencode, urlparse

import requests

from app.models import NaverListing, NaverSearchFilters, RangeFilter


class NaverFetchError(RuntimeError):
    pass


class NaverSearchClient:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
                ),
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                "Referer": "https://m.land.naver.com/",
            }
        )
        self._location_cache: dict[str, tuple[str, str]] = {}

    def fetch_listings(self, search_url: str) -> list[NaverListing]:
        filters = parse_search_filters(search_url)
        params = self._build_mobile_article_params(filters)
        response = self._get("https://m.land.naver.com/cluster/ajax/articleList", params=params)
        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise NaverFetchError("Naver articleList returned non-JSON response.") from exc

        if payload is None:
            return self._fetch_complex_listings(params, search_url, filters)
        if not isinstance(payload, dict):
            raise NaverFetchError("Naver articleList returned an unexpected JSON shape.")

        body = payload.get("body")
        if body is None:
            return self._fetch_complex_listings(params, search_url, filters)
        if not isinstance(body, list):
            raise NaverFetchError("Naver articleList response did not include a listing body.")

        listings: list[NaverListing] = []
        seen: set[str] = set()
        for item in body:
            if not isinstance(item, dict):
                continue
            listing = self._normalize_listing(item, search_url)
            if listing and listing.listing_id not in seen:
                seen.add(listing.listing_id)
                listings.append(listing)
        return listings

    def _fetch_complex_listings(
        self,
        params: dict[str, str],
        search_url: str,
        filters: NaverSearchFilters,
    ) -> list[NaverListing]:
        probe_params = {key: value for key, value in params.items() if not key.startswith("_")}
        try:
            response = self._get("https://m.land.naver.com/cluster/ajax/complexList", params=probe_params)
            payload = response.json()
        except (NaverFetchError, json.JSONDecodeError):
            return []
        if not isinstance(payload, dict):
            return []

        complexes = payload.get("result")
        if not isinstance(complexes, list):
            return []

        listings: list[NaverListing] = []
        seen: set[str] = set()
        for item in complexes:
            if not isinstance(item, dict):
                continue
            listing = self._normalize_complex_result(item, search_url, filters)
            if listing and listing.listing_id not in seen:
                seen.add(listing.listing_id)
                listings.append(listing)
        return listings

    def _normalize_complex_result(
        self,
        item: dict,
        search_url: str,
        filters: NaverSearchFilters,
    ) -> NaverListing | None:
        complex_no = self._pick(item, "hscpNo", "complexNo")
        if not complex_no:
            return None

        relevant_count = _complex_relevant_count(item, filters.trade_types)
        if relevant_count <= 0:
            return None

        complex_name = self._pick(item, "hscpNm", "complexName")
        trade_type = _complex_trade_type_label(filters.trade_types)
        price_text = _complex_price_text(item, filters.trade_types)
        area_text = _complex_area_text(item)
        detail_url = _build_fin_complex_url(str(complex_no), filters)
        raw_payload = dict(item)
        raw_payload["_signalboard_result_level"] = "complex"

        title = f"{complex_name} 단지 결과" if complex_name else f"단지 {complex_no}"
        return NaverListing(
            listing_id=f"complex:{complex_no}",
            result_level="complex",
            title=title,
            price_text=price_text,
            trade_type=trade_type,
            area_text=area_text,
            floor_text=None,
            complex_name=str(complex_name) if complex_name is not None else None,
            detail_url=detail_url or search_url,
            result_count=relevant_count,
            raw_payload=raw_payload,
        )

    def _raise_if_complex_results_exist(self, params: dict[str, str]) -> None:
        complex_listings = self._fetch_complex_listings(
            params,
            "",
            NaverSearchFilters(source_url="", source_version="unknown"),
        )
        if complex_listings:
            sample_text = ", ".join(listing.complex_name or listing.title or listing.listing_id for listing in complex_listings[:3])
            raise NaverFetchError(
                (
                    "Naver returned complex-level results, but the article-level listing endpoint returned empty. "
                    "SignalBoard is stopping instead of reporting a false total=0."
                    f" 예: {sample_text}"
                )
            )

    def _build_mobile_article_params(self, filters: NaverSearchFilters) -> dict[str, str]:
        if filters.center_lat is None or filters.center_lon is None:
            raise NaverFetchError("Search URL does not include center coordinates.")

        zoom = filters.zoom or 15
        bounds = _compute_bounds(filters.center_lat, filters.center_lon, zoom)
        try:
            cortar_no, search_query = self._resolve_cortar_no(filters)
        except NaverFetchError:
            cortar_no = ""
            search_query = "coordinate-bounds"

        params: dict[str, str] = {
            "rletTpCd": ":".join(_map_real_estate_types_to_mobile(filters)),
            "tradTpCd": ":".join(filters.trade_types or ["A1:B1"]),
            "z": str(zoom),
            "lat": str(filters.center_lat),
            "lon": str(filters.center_lon),
            "btm": str(bounds["btm"]),
            "lft": str(bounds["lft"]),
            "top": str(bounds["top"]),
            "rgt": str(bounds["rgt"]),
            "sort": "prc",
            "page": "1",
            "totCnt": "999",
        }
        if cortar_no:
            params["cortarNo"] = cortar_no

        legacy_query = _build_legacy_query_params(filters)
        params.update(legacy_query)
        params["_resolvedQuery"] = search_query
        return params

    def _resolve_cortar_no(self, filters: NaverSearchFilters) -> tuple[str, str]:
        cache_key = f"{filters.center_lat}:{filters.center_lon}:{filters.zoom}"
        cached = self._location_cache.get(cache_key)
        if cached:
            return cached

        for search_query in self._build_region_search_queries(filters):
            search_url = f"https://m.land.naver.com/search/result/{quote(search_query)}"
            response = self._get(search_url, allow_redirects=True)
            parsed = urlparse(response.url)

            cortar_no = _extract_cortar_no_from_map_url(parsed.path)
            if not cortar_no:
                match = re.search(r"cortarNo:\s*'(\d{10})'", response.text)
                if match:
                    cortar_no = match.group(1)

            if cortar_no:
                resolved = (cortar_no, search_query)
                self._location_cache[cache_key] = resolved
                return resolved

        raise NaverFetchError("Could not resolve cortarNo from the search area.")

    def _build_region_search_queries(self, filters: NaverSearchFilters) -> list[str]:
        if filters.center_lat is None or filters.center_lon is None:
            raise NaverFetchError("Cannot reverse geocode without center coordinates.")

        reverse = self._get(
            "https://nominatim.openstreetmap.org/reverse",
            params={
                "lat": str(filters.center_lat),
                "lon": str(filters.center_lon),
                "format": "jsonv2",
                "zoom": "15",
                "accept-language": "ko",
            },
            headers={"User-Agent": "SignalBoard/0.1"},
        )
        try:
            address = reverse.json().get("address", {})
        except json.JSONDecodeError as exc:
            raise NaverFetchError("Reverse geocoder returned invalid JSON.") from exc

        city = address.get("city") or address.get("state")
        borough = address.get("borough") or address.get("city_district")
        quarter = address.get("quarter")
        suburb = address.get("suburb")

        candidates = [
            " ".join(part for part in [city, borough, quarter] if part),
            " ".join(part for part in [borough, quarter] if part),
            " ".join(part for part in [city, borough, suburb] if part),
            " ".join(part for part in [borough, suburb] if part),
            " ".join(part for part in [quarter, borough, city] if part),
            " ".join(part for part in [suburb, borough, city] if part),
            quarter or "",
            suburb or "",
        ]
        queries = [candidate for candidate in candidates if candidate]
        if not queries:
            raise NaverFetchError("Could not derive a Korean region query from coordinates.")
        return list(dict.fromkeys(queries))

    def _get(
        self,
        url: str,
        *,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
        allow_redirects: bool = True,
    ) -> requests.Response:
        try:
            response = self.session.get(
                url,
                params=params,
                headers=headers,
                timeout=20,
                allow_redirects=allow_redirects,
            )
        except requests.RequestException as exc:
            raise NaverFetchError(str(exc)) from exc
        if response.status_code != 200:
            raise NaverFetchError(f"HTTP {response.status_code} from {url}")
        return response

    def _normalize_listing(self, item: dict, search_url: str) -> NaverListing | None:
        listing_id = self._pick(item, "atclNo", "articleNo", "articleNumber", "listingId")
        if not listing_id:
            return None
        title = self._pick(item, "atclNm", "articleName", "atclName", "title")
        trade_type = self._pick(item, "tradTpNm", "tradeTypeName", "tradeType")
        price_text = self._pick(item, "prcInfo", "dealOrWarrantPrc", "hanPrc", "price", "formattedPrice")
        area_value = self._pick(item, "spc2", "area2", "areaName", "area")
        area_text = str(area_value) if area_value is not None else None
        floor_text = self._pick(item, "flrInfo", "floorInfo", "floor")
        complex_name = self._pick(item, "cpNm", "cortarName", "complexName", "aptName")
        detail_url = self._build_detail_url(search_url, item, str(listing_id))
        return NaverListing(
            listing_id=str(listing_id),
            result_level="article",
            title=str(title) if title is not None else None,
            price_text=str(price_text) if price_text is not None else None,
            trade_type=str(trade_type) if trade_type is not None else None,
            area_text=area_text,
            floor_text=str(floor_text) if floor_text is not None else None,
            complex_name=str(complex_name) if complex_name is not None else None,
            detail_url=detail_url,
            result_count=None,
            raw_payload=item,
        )

    def _pick(self, item: dict, *keys: str) -> object | None:
        for key in keys:
            value = item.get(key)
            if value not in (None, ""):
                return value
        return None

    def _build_detail_url(self, search_url: str, item: dict, listing_id: str) -> str:
        complex_no = self._pick(item, "hscpNo", "cpid", "complexNo")
        if complex_no and re.fullmatch(r"\d+", str(complex_no)):
            return f"https://new.land.naver.com/complexes/{complex_no}?articleNo={listing_id}"
        match = re.search(r"/complexes/(\d+)", search_url)
        if match:
            return f"https://new.land.naver.com/complexes/{match.group(1)}?articleNo={listing_id}"
        return search_url


def parse_search_filters(search_url: str) -> NaverSearchFilters:
    parsed = urlparse(search_url)
    query = {key: values[-1] for key, values in parse_qs(parsed.query).items() if values}

    if parsed.netloc == "fin.land.naver.com":
        return _parse_fin_filters(search_url, query)
    if parsed.netloc == "new.land.naver.com":
        return _parse_legacy_filters(search_url, query)
    if parsed.netloc == "m.land.naver.com":
        return _parse_mobile_filters(search_url, parsed, query)
    raise NaverFetchError(f"Unsupported Naver host: {parsed.netloc}")


def build_legacy_search_url(filters: NaverSearchFilters) -> str:
    if filters.center_lat is None or filters.center_lon is None:
        raise NaverFetchError("center coordinates are required to build a legacy URL.")

    query: dict[str, str] = {
        "ms": f"{filters.center_lat},{filters.center_lon},{filters.zoom or 15}",
    }

    mapped_real_estate = _map_real_estate_types_to_legacy(filters.real_estate_types or [])
    if mapped_real_estate:
        query["a"] = ":".join(mapped_real_estate)
    elif filters.real_estate_type_codes_legacy:
        query["a"] = ":".join(filters.real_estate_type_codes_legacy)

    if filters.trade_types:
        mapped_trade = _map_trade_types_to_legacy(filters.trade_types)
        if mapped_trade:
            query["b"] = mapped_trade

    if filters.deal_price:
        if filters.deal_price.minimum:
            query["f"] = filters.deal_price.minimum
        if filters.deal_price.maximum:
            query["g"] = filters.deal_price.maximum

    if filters.space:
        if filters.space.minimum:
            query["h"] = filters.space.minimum
        if filters.space.maximum:
            query["i"] = filters.space.maximum

    if filters.direction:
        mapped_direction = _map_direction_to_legacy(filters.direction)
        if mapped_direction:
            query["s"] = mapped_direction

    if filters.floor:
        mapped_floor = _map_floor_to_legacy(filters.floor)
        if mapped_floor:
            query["u"] = mapped_floor

    if filters.one_room_shape_types:
        mapped_room_shape = _map_one_room_shape_to_legacy(filters.one_room_shape_types)
        if mapped_room_shape:
            query["q"] = mapped_room_shape

    if filters.bathroom_count:
        mapped_bath = _map_bathroom_to_legacy(filters.bathroom_count)
        if mapped_bath:
            query["r"] = mapped_bath

    if filters.move_in_types and set(filters.move_in_types) == {"MVF01", "MVF02"}:
        query["e"] = "RETAIL"

    if filters.management_fee and filters.management_fee.maximum:
        query["j"] = filters.management_fee.maximum

    return f"https://new.land.naver.com/complexes?{urlencode(query)}"


def filters_as_dict(filters: NaverSearchFilters) -> dict:
    return asdict(filters)


def _parse_fin_filters(search_url: str, query: dict[str, str]) -> NaverSearchFilters:
    center_lat = None
    center_lon = None
    center = query.get("center")
    if center and "-" in center:
        lon_value, lat_value = center.split("-", 1)
        center_lon = float(lon_value)
        center_lat = float(lat_value)

    return NaverSearchFilters(
        source_url=search_url,
        source_version="fin.land",
        center_lat=center_lat,
        center_lon=center_lon,
        zoom=_to_int(query.get("zoom")),
        trade_types=_split_dash(query.get("tradeTypes")),
        real_estate_types=_split_dash(query.get("realEstateTypes")),
        deal_price=_parse_range(query.get("dealPrice")),
        warranty_price=_parse_range(query.get("warrantyPrice")),
        rent_price=_parse_range(query.get("rentPrice")),
        space=_parse_range(query.get("space")),
        household_number=_parse_range(query.get("householdNumber")),
        parking_types=_split_dash(query.get("parkingTypes")),
        entrance_types=_split_dash(query.get("entranceTypes")),
        room_count=_split_dash(query.get("roomCount")),
        bathroom_count=_split_dash(query.get("bathRoomCount")),
        floor=_split_dash(query.get("floor")),
        direction=_split_dash(query.get("direction")),
        approval_elapsed_year=_parse_range(query.get("approvalElapsedYear")),
        management_fee=_parse_range(query.get("managementFee")),
        move_in_types=_split_dash(query.get("moveInTypes")),
        facilities=_split_dash(query.get("facilities")),
        one_room_shape_types=_split_dash(query.get("oneRoomShapeTypes")),
        raw_query=query,
    )


def _parse_legacy_filters(search_url: str, query: dict[str, str]) -> NaverSearchFilters:
    center_lat = None
    center_lon = None
    zoom = None
    ms = query.get("ms")
    if ms:
        parts = ms.split(",")
        if len(parts) == 3:
            try:
                center_lat = float(parts[0])
                center_lon = float(parts[1])
                zoom = _to_int(parts[2])
            except ValueError as exc:
                raise NaverFetchError(
                    "Legacy search URL has an unsupported ms format. Copy the full Naver map URL after the map fully loads."
                ) from exc
        else:
            raise NaverFetchError(
                "Legacy search URL has an unsupported ms format. Copy the full Naver map URL after the map fully loads."
            )

    return NaverSearchFilters(
        source_url=search_url,
        source_version="new.land.legacy",
        center_lat=center_lat,
        center_lon=center_lon,
        zoom=zoom,
        trade_types=[query["b"]] if query.get("b") else None,
        real_estate_type_codes_legacy=query.get("a", "").split(":") if query.get("a") else None,
        deal_price=RangeFilter(query.get("f"), query.get("g")) if query.get("f") or query.get("g") else None,
        space=RangeFilter(query.get("h"), query.get("i")) if query.get("h") or query.get("i") else None,
        raw_query=query,
    )


def _parse_mobile_filters(search_url: str, parsed, query: dict[str, str]) -> NaverSearchFilters:
    center_lat = None
    center_lon = None
    zoom = None
    path_parts = [part for part in parsed.path.split("/") if part]
    if len(path_parts) >= 2 and path_parts[0] == "map":
        segments = path_parts[1].split(":")
        if len(segments) >= 3:
            center_lat = float(segments[0])
            center_lon = float(segments[1])
            zoom = _to_int(segments[2])
            if len(segments) >= 4:
                query.setdefault("cortarNo", segments[3])

    return NaverSearchFilters(
        source_url=search_url,
        source_version="m.land",
        center_lat=center_lat,
        center_lon=center_lon,
        zoom=zoom,
        trade_types=query.get("tradTpCds", query.get("b", "")).split(":") if query.get("tradTpCds") or query.get("b") else None,
        real_estate_type_codes_legacy=query.get("rletTpCds", query.get("a", "")).split(":")
        if query.get("rletTpCds") or query.get("a")
        else None,
        deal_price=RangeFilter(query.get("f"), query.get("g")) if query.get("f") or query.get("g") else None,
        space=RangeFilter(query.get("h"), query.get("i")) if query.get("h") or query.get("i") else None,
        raw_query=query,
    )


def _split_dash(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [item for item in value.split("-") if item]


def _parse_range(value: str | None) -> RangeFilter | None:
    if not value or "-" not in value:
        return None
    minimum, maximum = value.split("-", 1)
    return RangeFilter(minimum=minimum or None, maximum=maximum or None)


def _to_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    return int(float(value))


def _map_real_estate_types_to_legacy(values: list[str]) -> list[str]:
    mapping = {
        "A01": "APT",
        "A02": "ABYG",
        "A04": "OPST",
        "A05": "OBYG",
        "A06": "JGB",
        "A07": "JGC",
    }
    mapped: list[str] = []
    for value in values:
        legacy = mapping.get(value, value)
        if legacy and legacy not in mapped:
            mapped.append(legacy)
    return mapped


def _map_real_estate_types_to_mobile(filters: NaverSearchFilters) -> list[str]:
    if filters.real_estate_type_codes_legacy:
        return filters.real_estate_type_codes_legacy
    if filters.real_estate_types:
        mapped = _map_real_estate_types_to_legacy(filters.real_estate_types)
        if mapped:
            return mapped
    return ["APT"]


def _map_trade_types_to_legacy(values: list[str]) -> str | None:
    if "B1" in values:
        return "B1"
    if "A1" in values:
        return "A1"
    if values:
        return values[0]
    return None


def _map_direction_to_legacy(values: list[str]) -> str | None:
    allowed = [value for value in values if value in {"EE", "EN", "ES", "WW", "WN", "WS", "SS", "NN"}]
    return ":".join(allowed) if allowed else None


def _map_floor_to_legacy(values: list[str]) -> str | None:
    if "FLF03" in values:
        return "MIDFLOOR"
    if "FLF02" in values:
        return "LOWFLOOR"
    if "FLF04" in values:
        return "HIGHFLOOR"
    return None


def _map_one_room_shape_to_legacy(values: list[str]) -> str | None:
    if "10" in values and "20" in values:
        return "ONEROOM"
    if "20" in values:
        return "TWOROOM"
    if "10" in values:
        return "ONEROOM"
    return None


def _map_bathroom_to_legacy(values: list[str]) -> str | None:
    if "RCF01" in values:
        return "ONEBATH"
    if "RCF02" in values:
        return "TWOBATH"
    return None


def _build_legacy_query_params(filters: NaverSearchFilters) -> dict[str, str]:
    params: dict[str, str] = {}
    if filters.deal_price:
        if filters.deal_price.minimum:
            params["f"] = filters.deal_price.minimum
        if filters.deal_price.maximum:
            params["g"] = filters.deal_price.maximum
    if filters.space:
        if filters.space.minimum:
            params["h"] = filters.space.minimum
        if filters.space.maximum:
            params["i"] = filters.space.maximum
    if filters.management_fee and filters.management_fee.maximum:
        params["j"] = filters.management_fee.maximum
    if filters.direction:
        mapped_direction = _map_direction_to_legacy(filters.direction)
        if mapped_direction:
            params["s"] = mapped_direction
    if filters.floor:
        mapped_floor = _map_floor_to_legacy(filters.floor)
        if mapped_floor:
            params["u"] = mapped_floor
    if filters.one_room_shape_types:
        mapped_room_shape = _map_one_room_shape_to_legacy(filters.one_room_shape_types)
        if mapped_room_shape:
            params["q"] = mapped_room_shape
    if filters.bathroom_count:
        mapped_bath = _map_bathroom_to_legacy(filters.bathroom_count)
        if mapped_bath:
            params["r"] = mapped_bath
    if filters.move_in_types and set(filters.move_in_types) == {"MVF01", "MVF02"}:
        params["e"] = "RETAIL"
    return params


def _complex_relevant_count(item: dict, trade_types: list[str] | None) -> int:
    trade_types = trade_types or ["A1"]
    total = 0
    if "A1" in trade_types:
        total += _to_int(str(item.get("dealCnt") or "0")) or 0
    if "B1" in trade_types:
        total += _to_int(str(item.get("leaseCnt") or "0")) or 0
    if "B2" in trade_types:
        total += _to_int(str(item.get("rentCnt") or "0")) or 0
    if "B3" in trade_types:
        total += _to_int(str(item.get("strmRentCnt") or "0")) or 0
    if total:
        return total
    return _to_int(str(item.get("totalAtclCnt") or "0")) or 0


def _complex_trade_type_label(trade_types: list[str] | None) -> str | None:
    labels = {
        "A1": "매매",
        "B1": "전세",
        "B2": "월세",
        "B3": "단기임대",
    }
    if not trade_types:
        return None
    return ", ".join(labels.get(value, value) for value in trade_types)


def _complex_price_text(item: dict, trade_types: list[str] | None) -> str | None:
    trade_types = trade_types or ["A1"]
    ranges: list[str] = []
    specs = [
        ("A1", "매매", "dealPrcMin", "dealPrcMax"),
        ("B1", "전세", "leasePrcMin", "leasePrcMax"),
        ("B2", "월세", "rentPrcMin", "rentPrcMax"),
        ("B3", "단기", "strmRentPrcMin", "strmRentPrcMax"),
    ]
    for code, label, min_key, max_key in specs:
        if code not in trade_types:
            continue
        minimum = _clean_html_text(item.get(min_key))
        maximum = _clean_html_text(item.get(max_key))
        if minimum and maximum and minimum != maximum:
            ranges.append(f"{label} {minimum}~{maximum}")
        elif minimum:
            ranges.append(f"{label} {minimum}")
        elif maximum:
            ranges.append(f"{label} {maximum}")
    return " / ".join(ranges) if ranges else None


def _complex_area_text(item: dict) -> str | None:
    minimum = item.get("minSpc")
    maximum = item.get("maxSpc")
    if minimum and maximum and str(minimum) != str(maximum):
        return f"{minimum}~{maximum}㎡"
    if minimum:
        return f"{minimum}㎡"
    if maximum:
        return f"{maximum}㎡"
    return None


def _build_fin_complex_url(complex_no: str, filters: NaverSearchFilters) -> str:
    params: dict[str, str] = {}
    if filters.trade_types:
        params["articleTradeTypes"] = ",".join(filters.trade_types)
        params["transactionTradeType"] = filters.trade_types[0]
    if filters.space:
        if filters.space.minimum:
            params["supplySpaceMin"] = filters.space.minimum
        if filters.space.maximum:
            params["supplySpaceMax"] = filters.space.maximum
    query = urlencode(params)
    suffix = f"?{query}" if query else ""
    return f"https://fin.land.naver.com/complexes/{complex_no}{suffix}"


def _clean_html_text(value: object | None) -> str | None:
    if value in (None, ""):
        return None
    text = re.sub(r"<[^>]+>", "", str(value))
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _compute_bounds(lat: float, lon: float, zoom: int, width: int = 390, height: int = 844) -> dict[str, float]:
    scale = 2**zoom

    def lon_to_x(value: float) -> float:
        return (value + 180.0) / 360.0 * 256 * scale

    def lat_to_y(value: float) -> float:
        radians = math.radians(value)
        return (1 - math.log(math.tan(radians) + (1 / math.cos(radians))) / math.pi) / 2 * 256 * scale

    def x_to_lon(value: float) -> float:
        return value / (256 * scale) * 360.0 - 180.0

    def y_to_lat(value: float) -> float:
        n = math.pi - (2 * math.pi * value) / (256 * scale)
        return math.degrees(math.atan(math.sinh(n)))

    center_x = lon_to_x(lon)
    center_y = lat_to_y(lat)
    return {
        "lft": x_to_lon(center_x - width / 2),
        "rgt": x_to_lon(center_x + width / 2),
        "top": y_to_lat(center_y - height / 2),
        "btm": y_to_lat(center_y + height / 2),
    }


def _extract_cortar_no_from_map_url(path: str) -> str | None:
    path_parts = [part for part in path.split("/") if part]
    if len(path_parts) < 2 or path_parts[0] != "map":
        return None
    segments = path_parts[1].split(":")
    if len(segments) >= 4 and re.fullmatch(r"\d{10}", segments[3]):
        return segments[3]
    return None
