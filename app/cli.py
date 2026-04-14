import typer
import json
import hashlib
import time
from pathlib import Path

from app.alerts import AlertService, format_listing_message
from app.config import settings
from app.db import connect
from app.debug import mask_secret
from app.kakao_notifier import KakaoMessageError, KakaoNotifier
from app.kakao_tokens import KakaoTokenManager
from app.naver import NaverSearchClient, build_legacy_search_url, filters_as_dict, parse_search_filters
from app.storage import add_watch, init_db, list_watches


app = typer.Typer(help="SignalBoard CLI")


def _default_state_file(search_url: str) -> Path:
    digest = hashlib.sha1(search_url.encode("utf-8")).hexdigest()[:12]
    return Path(f".signalboard-watch-{digest}.json")


def _resolve_search_url(search_url: str | None) -> str:
    resolved = search_url or settings.naver_search_url
    if not resolved:
        raise typer.BadParameter("Search URL is required or NAVER_SEARCH_URL must be set in .env")
    return resolved


def _build_token_manager() -> KakaoTokenManager:
    if not settings.kakao_rest_api_key:
        raise typer.BadParameter("KAKAO_REST_API_KEY is not set in .env")
    return KakaoTokenManager(
        rest_api_key=settings.kakao_rest_api_key,
        redirect_uri=settings.kakao_redirect_uri,
        access_token=settings.kakao_access_token,
        refresh_token=settings.kakao_refresh_token,
        client_secret=settings.kakao_client_secret,
        skip_ssl_verify=settings.skip_ssl_verify,
    )


def _build_notifier() -> KakaoNotifier:
    return KakaoNotifier(token_manager=_build_token_manager())


@app.command()
def health() -> None:
    """Basic scaffold check."""
    typer.echo("signal-board ready")


@app.command("init-db")
def init_db_command() -> None:
    """Create PostgreSQL tables for SignalBoard."""
    try:
        init_db()
    except Exception as exc:
        raise typer.BadParameter(
            "PostgreSQL connection failed. Start the DB first, for example: docker compose up -d postgres"
        ) from exc
    typer.echo("database initialized")


@app.command("db-check")
def db_check_command() -> None:
    """Verify PostgreSQL connectivity."""
    try:
        with connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:
        raise typer.BadParameter(
            "PostgreSQL connection failed. Start the DB first, for example: docker compose up -d postgres"
        ) from exc
    typer.echo("database connection ok")


@app.command("add-watch")
def add_watch_command(
    label: str = typer.Argument(..., help="Human label for the saved search"),
    search_url: str = typer.Argument(..., help="Naver saved search URL"),
) -> None:
    """Register or update a Naver saved search URL."""
    watch_id = add_watch(label, search_url)
    typer.echo(f"watch saved: id={watch_id}")


@app.command("list-watches")
def list_watches_command() -> None:
    """Show all registered watch targets."""
    rows = list_watches()
    if not rows:
        typer.echo("no watches registered")
        return
    for watch_id, label, search_url, source_version, resolved_search_url, is_active, created_at, last_checked_at in rows:
        typer.echo(
            f"id={watch_id} active={is_active} source={source_version or '-'} label={label} "
            f"created_at={created_at} last_checked_at={last_checked_at or '-'} "
            f"url={search_url} resolved={resolved_search_url or '-'}"
        )


@app.command("poll")
def poll_command() -> None:
    """Fetch all active Naver watches and send alerts for newly seen listings."""
    service = AlertService(_build_notifier())
    results = service.poll_all()
    if not results:
        typer.echo("no active watches")
        return
    for result in results:
        if result.baseline_created:
            typer.echo(
                f"id={result.watch_id} label={result.label} baseline-created total={result.total_count} new=0"
            )
        else:
            typer.echo(
                f"id={result.watch_id} label={result.label} total={result.total_count} "
                f"new={len(result.new_listings)}"
            )


@app.command("poll-loop")
def poll_loop_command(
    interval_seconds: int = typer.Option(60, min=10, help="Seconds to wait between DB-backed polls"),
) -> None:
    """Continuously poll all active PostgreSQL-backed watches."""
    typer.echo(f"polling DB watches every {interval_seconds}s; press Ctrl+C to stop")
    try:
        while True:
            poll_command()
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        typer.echo("polling stopped")


@app.command("inspect-search-url")
def inspect_search_url(
    search_url: str = typer.Argument(..., help="Naver search URL to inspect"),
) -> None:
    """Parse a Naver search URL and show normalized filters plus a legacy approximation."""
    filters = parse_search_filters(search_url)
    typer.echo(json.dumps(filters_as_dict(filters), ensure_ascii=False, indent=2))
    typer.echo("")
    typer.echo("legacy_url_approximation:")
    typer.echo(build_legacy_search_url(filters))


@app.command("preview-search")
def preview_search(
    search_url: str | None = typer.Argument(None, help="Naver search URL to fetch immediately"),
    limit: int = typer.Option(10, min=1, max=50, help="How many parsed listings to show"),
) -> None:
    """Fetch a Naver search once and print parsed listings without DB writes."""
    search_url = _resolve_search_url(search_url)
    client = NaverSearchClient()
    listings = client.fetch_listings(search_url)
    typer.echo(f"total={len(listings)}")
    for listing in listings[:limit]:
        lines = [
            f"id={listing.listing_id}",
            listing.title or listing.complex_name or "-",
            listing.trade_type or "-",
            listing.price_text or "-",
            listing.area_text or "-",
            listing.floor_text or "-",
            listing.detail_url or search_url,
        ]
        typer.echo(" | ".join(lines))


@app.command("poll-url")
def poll_url(
    search_url: str | None = typer.Argument(None, help="Naver search URL to watch"),
    label: str = typer.Option("빠른테스트", help="Label used in Kakao alert messages"),
    state_file: Path | None = typer.Option(None, help="JSON file storing previously seen listing IDs"),
    send_kakao: bool = typer.Option(True, "--send-kakao/--no-send-kakao", help="Send Kakao alerts for new listings"),
) -> None:
    """Poll a single URL without PostgreSQL by storing seen IDs in a local JSON file."""
    search_url = _resolve_search_url(search_url)
    _poll_url_once(search_url, label=label, state_file=state_file, send_kakao=send_kakao)


@app.command("poll-url-loop")
def poll_url_loop(
    search_url: str | None = typer.Argument(None, help="Naver search URL to watch"),
    label: str = typer.Option("빠른테스트", help="Label used in Kakao alert messages"),
    state_file: Path | None = typer.Option(None, help="JSON file storing previously seen listing IDs"),
    send_kakao: bool = typer.Option(True, "--send-kakao/--no-send-kakao", help="Send Kakao alerts for new listings"),
    interval_seconds: int = typer.Option(60, min=10, help="Seconds to wait between polls"),
) -> None:
    """Continuously poll a single URL without PostgreSQL."""
    search_url = _resolve_search_url(search_url)
    typer.echo(f"polling every {interval_seconds}s; press Ctrl+C to stop")
    try:
        while True:
            _poll_url_once(search_url, label=label, state_file=state_file, send_kakao=send_kakao)
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        typer.echo("polling stopped")


def _poll_url_once(
    search_url: str,
    *,
    label: str,
    state_file: Path | None,
    send_kakao: bool,
) -> None:
    client = NaverSearchClient()
    listings = client.fetch_listings(search_url)
    target_file = state_file or _default_state_file(search_url)

    previous_ids: set[str] = set()
    has_baseline = False
    if target_file.exists():
        try:
            payload = json.loads(target_file.read_text(encoding="utf-8"))
            previous_ids = set(str(item) for item in payload.get("listing_ids", []))
            has_baseline = bool(payload.get("initialized", True))
        except (OSError, json.JSONDecodeError):
            previous_ids = set()
            has_baseline = False

    current_ids = [listing.listing_id for listing in listings]
    if not has_baseline:
        target_file.write_text(
            json.dumps({"initialized": True, "listing_ids": current_ids}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        typer.echo(f"baseline-created total={len(listings)} state={target_file}")
        return

    new_listings = [listing for listing in listings if listing.listing_id not in previous_ids]
    target_file.write_text(
        json.dumps({"initialized": True, "listing_ids": current_ids}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    typer.echo(f"total={len(listings)} new={len(new_listings)} state={target_file}")

    if not new_listings:
        return

    notifier = _build_notifier() if send_kakao else None
    for listing in new_listings:
        message = format_listing_message(label, listing)
        typer.echo(message)
        typer.echo("")
        if notifier is not None:
            notifier.send_text(message, web_url=listing.detail_url or search_url)


@app.command("send-test-kakao")
def send_test_kakao(
    message: str = typer.Option(
        "[부동산알리미] 카카오 테스트 발송\nSignalBoard 연결이 정상입니다.",
        help="Text message to send to Kakao memo API",
    ),
) -> None:
    """Send a Kakao self-message using the token from .env."""
    client = _build_notifier()
    try:
        client.send_text(message)
    except KakaoMessageError as exc:
        if "code\":-401" in str(exc) and client.refresh_token:
            client.refresh_access_token()
            client.send_text(message)
        else:
            raise
    typer.echo("kakao test message sent")


@app.command("kakao-login")
def kakao_login(
    open_browser: bool = typer.Option(True, "--open-browser/--no-open-browser"),
) -> None:
    """Run local Kakao OAuth login and store tokens for future refresh."""
    token_manager = _build_token_manager()
    auth_url = token_manager.build_authorize_url()
    typer.echo(f"Open this URL and approve access:\n{auth_url}")
    token_manager.login(open_browser=open_browser)
    typer.echo("kakao login complete; tokens saved to .signalboard.tokens.json")


@app.command("kakao-exchange-code")
def kakao_exchange_code(
    code: str = typer.Option(..., help="Authorization code returned by Kakao after login"),
) -> None:
    """Exchange an authorization code for access and refresh tokens."""
    token_manager = _build_token_manager()
    token_manager.exchange_code(code)
    typer.echo("kakao token exchange complete; tokens saved to .signalboard.tokens.json")


@app.command("kakao-refresh")
def kakao_refresh() -> None:
    """Refresh access token using the configured refresh token."""
    token_manager = _build_token_manager()
    token_manager.refresh_access_token()
    typer.echo("kakao access token refreshed and saved")


@app.command("kakao-me")
def kakao_me() -> None:
    """Call Kakao user profile API with the current token."""
    payload = _build_notifier().get_profile()
    typer.echo(f"id={payload.get('id')}")


@app.command("show-config")
def show_config() -> None:
    """Show a masked view of current runtime config."""
    typer.echo(f"app_name={settings.app_name}")
    typer.echo(f"database_url={'set' if settings.database_url else 'missing'}")
    typer.echo(f"kakao_rest_api_key={mask_secret(settings.kakao_rest_api_key)}")
    typer.echo(f"kakao_access_token={mask_secret(settings.kakao_access_token)}")
    typer.echo(f"kakao_refresh_token={mask_secret(settings.kakao_refresh_token)}")
    typer.echo(f"kakao_redirect_uri={settings.kakao_redirect_uri}")
    typer.echo(f"naver_search_url={'set' if settings.naver_search_url else 'missing'}")
    typer.echo(f"skip_ssl_verify={settings.skip_ssl_verify}")


if __name__ == "__main__":
    app()
