from __future__ import annotations

import json
from dataclasses import dataclass

import requests

from app.kakao_tokens import KakaoTokenError, KakaoTokenManager


class KakaoMessageError(RuntimeError):
    pass


@dataclass(slots=True)
class KakaoNotifier:
    token_manager: KakaoTokenManager

    def send_text(self, text: str, *, web_url: str = "https://new.land.naver.com/") -> dict:
        try:
            access_token = self.token_manager.ensure_access_token()
        except KakaoTokenError as exc:
            raise KakaoMessageError(str(exc)) from exc

        template_object = {
            "object_type": "text",
            "text": text,
            "link": {
                "web_url": web_url,
                "mobile_web_url": web_url,
            },
        }
        try:
            response = requests.post(
                "https://kapi.kakao.com/v2/api/talk/memo/default/send",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
                },
                data={"template_object": json.dumps(template_object, ensure_ascii=False)},
                timeout=20,
                verify=not self.token_manager.skip_ssl_verify,
            )
        except requests.RequestException as exc:
            raise KakaoMessageError(str(exc)) from exc

        if response.status_code == 401 and self.token_manager.refresh_token:
            try:
                self.token_manager.refresh_access_token()
            except KakaoTokenError as exc:
                raise KakaoMessageError(str(exc)) from exc
            return self.send_text(text, web_url=web_url)

        if response.status_code != 200:
            raise KakaoMessageError(f"HTTP {response.status_code}: {response.text}")

        payload = response.json()
        if payload.get("result_code") not in (0, None):
            raise KakaoMessageError(f"Kakao send failed: {payload}")
        return payload

    def get_profile(self) -> dict:
        try:
            access_token = self.token_manager.ensure_access_token()
        except KakaoTokenError as exc:
            raise KakaoMessageError(str(exc)) from exc

        try:
            response = requests.get(
                "https://kapi.kakao.com/v2/user/me",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=20,
                verify=not self.token_manager.skip_ssl_verify,
            )
        except requests.RequestException as exc:
            raise KakaoMessageError(str(exc)) from exc

        if response.status_code == 401 and self.token_manager.refresh_token:
            try:
                self.token_manager.refresh_access_token()
            except KakaoTokenError as exc:
                raise KakaoMessageError(str(exc)) from exc
            return self.get_profile()

        if response.status_code != 200:
            raise KakaoMessageError(f"HTTP {response.status_code}: {response.text}")
        return response.json()
