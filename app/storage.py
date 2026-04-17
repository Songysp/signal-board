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
    result_level TEXT NOT NULL DEFAULT 'article',
    title TEXT,
    price_text TEXT,
    trade_type TEXT,
    area_text TEXT,
    floor_text TEXT,
    complex_name TEXT,
    source_url TEXT,
    result_count INTEGER,
    raw_json JSONB
);

CREATE TABLE IF NOT EXISTS listing_current_state (
    watch_target_id BIGINT NOT NULL REFERENCES watch_targets(id) ON DELETE CASCADE,
    external_listing_id TEXT NOT NULL,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_snapshot_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    result_level TEXT NOT NULL DEFAULT 'article',
    title TEXT,
    price_text TEXT,
    trade_type TEXT,
    area_text TEXT,
    floor_text TEXT,
    complex_name TEXT,
    source_url TEXT,
    result_count INTEGER,
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
        cursor.execute("ALTER TABLE listing_snapshots ADD COLUMN IF NOT EXISTS result_level TEXT NOT NULL DEFAULT 'article'")
        cursor.execute("ALTER TABLE listing_current_state ADD COLUMN IF NOT EXISTS result_level TEXT NOT NULL DEFAULT 'article'")
        cursor.execute("ALTER TABLE listing_snapshots ADD COLUMN IF NOT EXISTS result_count INTEGER")
        cursor.execute("ALTER TABLE listing_current_state ADD COLUMN IF NOT EXISTS result_count INTEGER")


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
                w.id,
                w.label,
                w.search_url,
                w.source_version,
                w.resolved_search_url,
                w.is_active,
                w.created_at,
                w.last_checked_at,
                COUNT(DISTINCT s.external_listing_id) AS current_result_count,
                COUNT(DISTINCT e.id) AS alert_event_count
            FROM watch_targets w
            LEFT JOIN listing_current_state s ON s.watch_target_id = w.id AND s.is_active = TRUE
            LEFT JOIN alert_events e ON e.watch_target_id = w.id
            GROUP BY w.id
            ORDER BY w.id
            """
        )
        return list(cursor.fetchall())


def set_watch_active(watch_id: int, is_active: bool) -> bool:
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE watch_targets
            SET is_active = %s
            WHERE id = %s
            RETURNING id
            """,
            (is_active, watch_id),
        )
        return cursor.fetchone() is not None


def list_alert_events(limit: int = 50) -> list[tuple]:
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                e.id,
                e.watch_target_id,
                w.label,
                e.external_listing_id,
                e.event_type,
                e.status,
                e.message,
                e.failure_reason,
                e.created_at,
                e.sent_at
            FROM alert_events e
            JOIN watch_targets w ON w.id = e.watch_target_id
            ORDER BY e.created_at DESC, e.id DESC
            LIMIT %s
            """,
            (limit,),
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


def get_current_listing_states(watch_id: int) -> dict[str, dict]:
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                external_listing_id,
                result_level,
                title,
                price_text,
                trade_type,
                area_text,
                floor_text,
                complex_name,
                source_url,
                result_count
            FROM listing_current_state
            WHERE watch_target_id = %s
            """,
            (watch_id,),
        )
        return {
            str(row[0]): {
                "result_level": row[1],
                "title": row[2],
                "price_text": row[3],
                "trade_type": row[4],
                "area_text": row[5],
                "floor_text": row[6],
                "complex_name": row[7],
                "source_url": row[8],
                "result_count": row[9],
            }
            for row in cursor.fetchall()
        }


def list_current_results(watch_id: int, limit: int = 100) -> list[tuple]:
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                external_listing_id,
                result_level,
                title,
                price_text,
                trade_type,
                area_text,
                floor_text,
                complex_name,
                source_url,
                result_count,
                first_seen_at,
                last_seen_at,
                last_snapshot_at
            FROM listing_current_state
            WHERE watch_target_id = %s
              AND is_active = TRUE
            ORDER BY COALESCE(result_count, 0) DESC, external_listing_id
            LIMIT %s
            """,
            (watch_id, limit),
        )
        return list(cursor.fetchall())


def save_snapshot(watch_id: int, search_url: str, listings: list[NaverListing]) -> None:
    now = datetime.now(timezone.utc)
    with connect() as conn:
        cursor = conn.cursor()
        for listing in listings:
            cursor.execute(
                """
                INSERT INTO listing_snapshots (
                    watch_target_id, snapshot_at, external_listing_id, result_level, title, price_text,
                    trade_type, area_text, floor_text, complex_name, source_url, result_count, raw_json
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    watch_id,
                    now,
                    listing.listing_id,
                    listing.result_level,
                    listing.title,
                    listing.price_text,
                    listing.trade_type,
                    listing.area_text,
                    listing.floor_text,
                    listing.complex_name,
                    listing.detail_url or search_url,
                    listing.result_count,
                    json.dumps(listing.raw_payload or {}, ensure_ascii=False),
                ),
            )
            cursor.execute(
                """
                INSERT INTO listing_current_state (
                    watch_target_id, external_listing_id, first_seen_at, last_seen_at,
                    last_snapshot_at, result_level, title, price_text, trade_type, area_text, floor_text,
                    complex_name, source_url, result_count, is_active
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                ON CONFLICT (watch_target_id, external_listing_id)
                DO UPDATE SET
                    last_seen_at = EXCLUDED.last_seen_at,
                    last_snapshot_at = EXCLUDED.last_snapshot_at,
                    result_level = EXCLUDED.result_level,
                    title = EXCLUDED.title,
                    price_text = EXCLUDED.price_text,
                    trade_type = EXCLUDED.trade_type,
                    area_text = EXCLUDED.area_text,
                    floor_text = EXCLUDED.floor_text,
                    complex_name = EXCLUDED.complex_name,
                    source_url = EXCLUDED.source_url,
                    result_count = EXCLUDED.result_count,
                    is_active = TRUE
                """,
                (
                    watch_id,
                    listing.listing_id,
                    now,
                    now,
                    now,
                    listing.result_level,
                    listing.title,
                    listing.price_text,
                    listing.trade_type,
                    listing.area_text,
                    listing.floor_text,
                    listing.complex_name,
                    listing.detail_url or search_url,
                    listing.result_count,
                ),
            )
        cursor.execute(
            "UPDATE watch_targets SET last_checked_at = %s WHERE id = %s",
            (now, watch_id),
        )


def create_alert_event(
    watch_id: int,
    listing: NaverListing,
    message: str,
    event_type: str = "new_listing",
) -> bool:
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO alert_events (watch_target_id, external_listing_id, event_type, message)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (watch_target_id, external_listing_id, event_type)
            DO NOTHING
            RETURNING id
            """,
            (watch_id, listing.listing_id, event_type, message),
        )
        row = cursor.fetchone()
        return row is not None


def mark_alert_sent(watch_id: int, listing_id: str, event_type: str = "new_listing") -> None:
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE alert_events
            SET status = 'sent', sent_at = NOW()
            WHERE watch_target_id = %s
              AND external_listing_id = %s
              AND event_type = %s
            """,
            (watch_id, listing_id, event_type),
        )


def mark_alert_failed(
    watch_id: int,
    listing_id: str,
    reason: str,
    event_type: str = "new_listing",
) -> None:
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE alert_events
            SET status = 'failed', failure_reason = %s
            WHERE watch_target_id = %s
              AND external_listing_id = %s
              AND event_type = %s
            """,
            (reason[:1000], watch_id, listing_id, event_type),
        )


def prune_alert_events(days: int, *, apply: bool = False) -> int:
    with connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM alert_events
            WHERE created_at < NOW() - make_interval(days => %s)
            """,
            (days,),
        )
        count = int(cursor.fetchone()[0])
        if apply and count:
            cursor.execute(
                """
                DELETE FROM alert_events
                WHERE created_at < NOW() - make_interval(days => %s)
                """,
                (days,),
            )
        return count
