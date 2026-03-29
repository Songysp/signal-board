from __future__ import annotations

import json
from dataclasses import dataclass

import httpx


class KakaoMessageError(RuntimeError):
    pass


@dataclass(slots=True)
class KakaoMessageClient:
    access_token: str

    def send_text(self, text: str, *, web_url: str = "https://new.land.naver.com/") -> dict:
        template_object = {
            "object_type": "text",
            "text": text,
            "link": {
                "web_url": web_url,
                "mobile_web_url": web_url,
            },
        }
        response = httpx.post(
            "https://kapi.kakao.com/v2/api/talk/memo/default/send",
            headers={"Authorization": f"Bearer {self.access_token}"},
            data={"template_object": json.dumps(template_object, ensure_ascii=False)},
            timeout=20.0,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("result_code") not in (0, None):
            raise KakaoMessageError(f"Kakao send failed: {payload}")
        return payload
