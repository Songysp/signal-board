# SignalBoard Manual QA

## 2026-04-17 Management UI Smoke

Status: `PASS`

Environment:

- Local FastAPI app on `http://127.0.0.1:8001/`
- Local PostgreSQL via Docker Compose
- Chrome headless DOM smoke

Checks:

- `GET /health` returned `{"status":"ok","app":"SignalBoard"}`
- Dashboard HTML loaded with status `200`
- Dashboard included admin token input and result filter UI
- `GET /watches` returned registered watches
- Browser-rendered dashboard contained 3 watch cards
- Browser-rendered dashboard contained 20 alert event cards
- Browser-rendered dashboard contained result filter controls
- Browser-rendered dashboard contained 3 single-watch poll buttons

Notes:

- This was a smoke QA pass, not a full visual design review.
- No mutating UI action was clicked during this pass.
- Kakao messages were not sent during this pass.
