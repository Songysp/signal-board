from __future__ import annotations

import json
from datetime import datetime, timezone

from app.db import connect
from app.models import NaverListing
from app.naver import build_legacy_search_url, filters_as_dict, parse_search_filters


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS watch_targets (
    id BIGSERIAL PRIMARY KEY,
    label TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'naver',
    search_url TEXT NOT NULL UNIQUE,
    source_version TEXT,
    resolved_search_url TEXT,
    normalized_filters_json JSONB,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_checked_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS listing_snapshots (
    id BIGSERIAL PRIMARY KEY,
    watch_target_id BIGINT NOT NULL REFERENCES watch_targets(id) ON DELETE CASCADE,
    snapshot_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    external_listing_id TEXT NOT NULL,
    title TEXT,
    price_text TEXT,
    trade_type TEXT,
    area_text TEXT,
    floor_text TEXT,
    complex_name TEXT,
    source_url TEXT,
    raw_json JSONB
);

CREATE TABLE IF NOT EXISTS listing_current_state (
    watch_target_id BIGINT NOT NULL REFERENCES watch_targets(id) ON DELETE CASCADE,
    external_listing_id TEXT NOT NULL,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_snapshot_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    title TEXT,
    price_text TEXT,
    trade_type TEXT,
    area_text TEXT,
    floor_text TEXT,
    complex_name TEXT,
    source_url TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (watch_target_id, external_listing_id)
);

CREATE TABLE IF NOT EXISTS alert_events (
    id BIGSERIAL PRIMARY KEY,
    watch_target_id BIGINT NOT NULL REFERENCES watch_targets(id) ON DELETE CASCADE,
    external_listing_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    message TEXT,
    failure_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at TIMESTAMPTZ,
    UNIQUE (watch_target_id, external_listing_id, event_type)
);

CREATE TABLE IF NOT EXISTS notification_channels (
    id BIGSERIAL PRIMARY KEY,
    channel_type TEXT NOT NULL,
    label TEXT NOT NULL,
    config_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_verified_at TIMESTAMPTZ
);
"""


def init_db() -> None:
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute(SCHEMA_SQL)
        cursor.execute("ALTER TABLE watch_targets ADD COLUMN IF NOT EXISTS source_version TEXT")
        cursor.execute("ALTER TABLE watch_targets ADD COLUMN IF NOT EXISTS resolved_search_url TEXT")
        cursor.execute("ALTER TABLE watch_targets ADD COLUMN IF NOT EXISTS normalized_filters_json JSONB")
        cursor.execute("ALTER TABLE alert_events ADD COLUMN IF NOT EXISTS failure_reason TEXT")


def add_watch(label: str, search_url: str) -> int:
    filters = parse_search_filters(search_url)
    try:
        resolved_search_url = build_legacy_search_url(filters)
    except Exception:
        resolved_search_url = search_url
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO watch_targets (label, search_url, source_version, resolved_search_url, normalized_filters_json)
            VALUES (%s, %s, %s, %s, %s::jsonb)
            ON CONFLICT (search_url)
            DO UPDATE SET
                label = EXCLUDED.label,
                source_version = EXCLUDED.source_version,
                resolved_search_url = EXCLUDED.resolved_search_url,
                normalized_filters_json = EXCLUDED.normalized_filters_json
            RETURNING id
            """,
            (
                label,
                search_url,
                filters.source_version,
                resolved_search_url,
                json.dumps(filters_as_dict(filters), ensure_ascii=False),
            ),
        )
        row = cursor.fetchone()
        return int(row[0])


def list_watches() -> list[tuple]:
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                id,
                label,
                search_url,
                source_version,
                resolved_search_url,
                is_active,
                created_at,
                last_checked_at
            FROM watch_targets
            ORDER BY id
            """
        )
        return list(cursor.fetchall())


def get_active_watches() -> list[tuple]:
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, label, search_url, resolved_search_url
            FROM watch_targets
            WHERE is_active = TRUE
            ORDER BY id
            """
        )
        return list(cursor.fetchall())


def has_snapshot_history(watch_id: int) -> bool:
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                last_checked_at IS NOT NULL
                OR EXISTS(SELECT 1 FROM listing_snapshots WHERE watch_target_id = %s)
            FROM watch_targets
            WHERE id = %s
            """,
            (watch_id, watch_id),
        )
        row = cursor.fetchone()
        if row is None:
            return False
        return bool(row[0])


def existing_listing_ids(watch_id: int) -> set[str]:
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT external_listing_id
            FROM listing_current_state
            WHERE watch_target_id = %s
            """,
            (watch_id,),
        )
        return {str(row[0]) for row in cursor.fetchall()}


def save_snapshot(watch_id: int, search_url: str, listings: list[NaverListing]) -> None:
    now = datetime.now(timezone.utc)
    with connect() as conn:
        cursor = conn.cursor()
        for listing in listings:
            cursor.execute(
                """
                INSERT INTO listing_snapshots (
                    watch_target_id, snapshot_at, external_listing_id, title, price_text,
                    trade_type, area_text, floor_text, complex_name, source_url, raw_json
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    watch_id,
                    now,
                    listing.listing_id,
                    listing.title,
                    listing.price_text,
                    listing.trade_type,
                    listing.area_text,
                    listing.floor_text,
                    listing.complex_name,
                    listing.detail_url or search_url,
                    json.dumps(listing.raw_payload or {}, ensure_ascii=False),
                ),
            )
            cursor.execute(
                """
                INSERT INTO listing_current_state (
                    watch_target_id, external_listing_id, first_seen_at, last_seen_at,
                    last_snapshot_at, title, price_text, trade_type, area_text, floor_text,
                    complex_name, source_url, is_active
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                ON CONFLICT (watch_target_id, external_listing_id)
                DO UPDATE SET
                    last_seen_at = EXCLUDED.last_seen_at,
                    last_snapshot_at = EXCLUDED.last_snapshot_at,
                    title = EXCLUDED.title,
                    price_text = EXCLUDED.price_text,
                    trade_type = EXCLUDED.trade_type,
                    area_text = EXCLUDED.area_text,
                    floor_text = EXCLUDED.floor_text,
                    complex_name = EXCLUDED.complex_name,
                    source_url = EXCLUDED.source_url,
                    is_active = TRUE
                """,
                (
                    watch_id,
                    listing.listing_id,
                    now,
                    now,
                    now,
                    listing.title,
                    listing.price_text,
                    listing.trade_type,
                    listing.area_text,
                    listing.floor_text,
                    listing.complex_name,
                    listing.detail_url or search_url,
                ),
            )
        cursor.execute(
            "UPDATE watch_targets SET last_checked_at = %s WHERE id = %s",
            (now, watch_id),
        )


def create_alert_event(watch_id: int, listing: NaverListing, message: str) -> bool:
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO alert_events (watch_target_id, external_listing_id, event_type, message)
            VALUES (%s, %s, 'new_listing', %s)
            ON CONFLICT (watch_target_id, external_listing_id, event_type)
            DO NOTHING
            RETURNING id
            """,
            (watch_id, listing.listing_id, message),
        )
        row = cursor.fetchone()
        return row is not None


def mark_alert_sent(watch_id: int, listing_id: str) -> None:
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE alert_events
            SET status = 'sent', sent_at = NOW()
            WHERE watch_target_id = %s
              AND external_listing_id = %s
              AND event_type = 'new_listing'
            """,
            (watch_id, listing_id),
        )


def mark_alert_failed(watch_id: int, listing_id: str, reason: str) -> None:
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE alert_events
            SET status = 'failed', failure_reason = %s
            WHERE watch_target_id = %s
              AND external_listing_id = %s
              AND event_type = 'new_listing'
            """,
            (reason[:1000], watch_id, listing_id),
        )
