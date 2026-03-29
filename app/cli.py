import typer

from app.config import settings
from app.kakao import KakaoMessageClient


app = typer.Typer(help="SignalBoard CLI")


@app.command()
def health() -> None:
    """Basic scaffold check."""
    typer.echo("signal-board ready")


@app.command("send-test-kakao")
def send_test_kakao(
    message: str = typer.Option(
        "[부동산알리미] 카카오 테스트 발송\nSignalBoard 연결이 정상입니다.",
        help="Text message to send to Kakao memo API",
    ),
) -> None:
    """Send a Kakao self-message using the token from .env."""
    if not settings.kakao_access_token:
        raise typer.BadParameter("KAKAO_ACCESS_TOKEN is not set in .env")

    client = KakaoMessageClient(settings.kakao_access_token)
    client.send_text(message)
    typer.echo("kakao test message sent")
