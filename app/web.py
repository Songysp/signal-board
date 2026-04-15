from __future__ import annotations


def render_dashboard() -> str:
    return """
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SignalBoard 관리</title>
  <style>
    :root {
      --ink: #182018;
      --muted: #647067;
      --line: #dce4dc;
      --paper: #fbfaf4;
      --panel: #ffffff;
      --accent: #1f7a4f;
      --accent-dark: #10543a;
      --warn: #b35a12;
      --shadow: 0 22px 60px rgba(30, 48, 35, 0.12);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      color: var(--ink);
      background:
        radial-gradient(circle at 10% 5%, rgba(31, 122, 79, 0.18), transparent 28rem),
        radial-gradient(circle at 85% 20%, rgba(179, 90, 18, 0.12), transparent 24rem),
        linear-gradient(135deg, #f6f2e7 0%, #eff6ef 100%);
      font-family: Georgia, "Malgun Gothic", serif;
      min-height: 100vh;
    }

    main {
      width: min(1120px, calc(100% - 32px));
      margin: 0 auto;
      padding: 48px 0;
    }

    header {
      display: grid;
      gap: 12px;
      margin-bottom: 28px;
    }

    .eyebrow {
      color: var(--accent-dark);
      font: 700 13px/1.2 "Malgun Gothic", sans-serif;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }

    h1 {
      font-size: clamp(38px, 7vw, 76px);
      line-height: 0.92;
      margin: 0;
      max-width: 820px;
    }

    .lead {
      color: var(--muted);
      font: 500 17px/1.7 "Malgun Gothic", sans-serif;
      max-width: 720px;
    }

    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
    }

    .card {
      background: rgba(255, 255, 255, 0.82);
      border: 1px solid var(--line);
      border-radius: 26px;
      box-shadow: var(--shadow);
      padding: 22px;
      backdrop-filter: blur(16px);
    }

    .wide { grid-column: 1 / -1; }

    h2 {
      margin: 0 0 16px;
      font-size: 24px;
    }

    label {
      display: block;
      color: var(--muted);
      font: 700 13px/1.4 "Malgun Gothic", sans-serif;
      margin: 12px 0 6px;
    }

    input, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: var(--paper);
      color: var(--ink);
      font: 500 14px/1.5 "Malgun Gothic", sans-serif;
      padding: 12px 14px;
      outline: none;
    }

    textarea { min-height: 96px; resize: vertical; }

    button {
      border: 0;
      border-radius: 999px;
      background: var(--accent);
      color: white;
      cursor: pointer;
      font: 800 14px/1 "Malgun Gothic", sans-serif;
      padding: 13px 18px;
      margin: 14px 8px 0 0;
      transition: transform 140ms ease, background 140ms ease;
    }

    button:hover {
      background: var(--accent-dark);
      transform: translateY(-1px);
    }

    pre, .list {
      overflow: auto;
      border-radius: 18px;
      background: #102118;
      color: #e6f4e8;
      font: 13px/1.55 Consolas, monospace;
      padding: 16px;
      min-height: 92px;
      white-space: pre-wrap;
    }

    .event-list {
      display: grid;
      gap: 12px;
      background: transparent;
      color: var(--ink);
      padding: 0;
      overflow: visible;
    }

    .event-card {
      border: 1px solid var(--line);
      border-radius: 18px;
      background: var(--paper);
      padding: 14px;
    }

    .event-meta {
      align-items: center;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 10px;
    }

    .badge {
      border-radius: 999px;
      display: inline-flex;
      font: 800 12px/1 "Malgun Gothic", sans-serif;
      padding: 7px 10px;
    }

    .badge-new { background: #dff4e7; color: #125c3d; }
    .badge-change { background: #fff1d6; color: #87500f; }
    .badge-status { background: #e7ece8; color: #4d5b51; }
    .badge-failed { background: #ffe0dc; color: #9d281c; }

    .event-title {
      font: 800 14px/1.4 "Malgun Gothic", sans-serif;
    }

    .event-message {
      color: #233026;
      font: 500 13px/1.6 "Malgun Gothic", sans-serif;
      white-space: pre-wrap;
    }

    .status {
      color: var(--warn);
      font: 700 13px/1.5 "Malgun Gothic", sans-serif;
      min-height: 20px;
      margin-top: 10px;
    }

    @media (max-width: 760px) {
      main { padding: 28px 0; }
      .grid { grid-template-columns: 1fr; }
      .wide { grid-column: auto; }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <div class="eyebrow">SignalBoard / 부동산알리미</div>
      <h1>검색 결과 변화를 놓치지 않는 운영 보드</h1>
      <p class="lead">네이버부동산 저장 검색 URL을 등록하고, 단지/클러스터 검색 결과 변화와 카카오 테스트를 한 화면에서 확인하는 MVP 관리 화면입니다.</p>
    </header>

    <section class="grid">
      <article class="card">
        <h2>감시 URL 등록</h2>
        <label for="label">이름</label>
        <input id="label" value="부동산알리미 테스트">
        <label for="searchUrl">네이버 저장 검색 URL</label>
        <textarea id="searchUrl" placeholder="https://new.land.naver.com/..."></textarea>
        <button onclick="createWatch()">등록</button>
        <button onclick="previewSearch()">미리보기</button>
        <div class="status" id="formStatus"></div>
      </article>

      <article class="card">
        <h2>수동 실행</h2>
        <p class="lead">첫 poll은 baseline만 저장하고, 두 번째부터 신규 검색 결과를 알림으로 보냅니다.</p>
        <button onclick="runPoll()">전체 poll</button>
        <button onclick="sendKakaoTest()">카카오 테스트</button>
        <button onclick="refreshAll()">새로고침</button>
        <div class="status" id="actionStatus"></div>
      </article>

      <article class="card wide">
        <h2>감시 목록</h2>
        <div class="list" id="watches">loading...</div>
      </article>

      <article class="card wide">
        <h2>최근 알림</h2>
        <div class="event-list" id="alerts">loading...</div>
      </article>

      <article class="card wide">
        <h2>실행 결과</h2>
        <pre id="output">ready</pre>
      </article>
    </section>
  </main>

  <script>
    const $ = (id) => document.getElementById(id);

    async function api(path, options = {}) {
      const response = await fetch(path, {
        headers: { "Content-Type": "application/json" },
        ...options
      });
      const text = await response.text();
      let payload;
      try { payload = text ? JSON.parse(text) : null; } catch { payload = text; }
      if (!response.ok) {
        const detail = payload && payload.detail ? payload.detail : text;
        throw new Error(detail || response.statusText);
      }
      return payload;
    }

    function show(id, value) {
      $(id).textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
    }

    function escapeHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function eventTypeLabel(eventType) {
      return eventType && eventType.startsWith("changed_result") ? "검색 결과 변화" : "신규 검색 결과";
    }

    function eventTypeClass(eventType) {
      return eventType && eventType.startsWith("changed_result") ? "badge-change" : "badge-new";
    }

    function statusClass(status) {
      return status === "failed" ? "badge-failed" : "badge-status";
    }

    function renderAlerts(alerts) {
      if (!alerts.length) {
        $("alerts").innerHTML = '<div class="event-card">아직 알림 이벤트가 없습니다.</div>';
        return;
      }
      $("alerts").innerHTML = alerts.map((event) => `
        <article class="event-card">
          <div class="event-meta">
            <span class="badge ${eventTypeClass(event.event_type)}">${eventTypeLabel(event.event_type)}</span>
            <span class="badge ${statusClass(event.status)}">${escapeHtml(event.status)}</span>
            <span class="event-title">${escapeHtml(event.watch_label)} · ${escapeHtml(event.external_listing_id)}</span>
          </div>
          <div class="event-message">${escapeHtml(event.message || event.failure_reason || "(message missing)")}</div>
        </article>
      `).join("");
    }

    async function refreshAll() {
      try {
        const [watches, alerts] = await Promise.all([
          api("/watches"),
          api("/alerts?limit=20")
        ]);
        show("watches", watches);
        renderAlerts(alerts);
      } catch (error) {
        show("output", error.message);
      }
    }

    async function createWatch() {
      $("formStatus").textContent = "등록 중...";
      try {
        const payload = {
          label: $("label").value,
          search_url: $("searchUrl").value
        };
        const result = await api("/watches", { method: "POST", body: JSON.stringify(payload) });
        $("formStatus").textContent = `등록 완료: id=${result.id}`;
        await refreshAll();
      } catch (error) {
        $("formStatus").textContent = error.message;
      }
    }

    async function previewSearch() {
      $("formStatus").textContent = "조회 중...";
      try {
        const result = await api("/preview-search", {
          method: "POST",
          body: JSON.stringify({ search_url: $("searchUrl").value || null, limit: 5 })
        });
        $("formStatus").textContent = `미리보기 완료: total=${result.total}`;
        show("output", result);
      } catch (error) {
        $("formStatus").textContent = error.message;
      }
    }

    async function runPoll() {
      $("actionStatus").textContent = "poll 실행 중...";
      try {
        const result = await api("/poll", { method: "POST", body: "{}" });
        $("actionStatus").textContent = "poll 완료";
        show("output", result);
        await refreshAll();
      } catch (error) {
        $("actionStatus").textContent = error.message;
      }
    }

    async function sendKakaoTest() {
      $("actionStatus").textContent = "카카오 발송 중...";
      try {
        const result = await api("/kakao/test", { method: "POST", body: "{}" });
        $("actionStatus").textContent = "카카오 테스트 발송 완료";
        show("output", result);
      } catch (error) {
        $("actionStatus").textContent = error.message;
      }
    }

    refreshAll();
  </script>
</body>
</html>
"""
