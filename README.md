# My Tech Uncle (나의 기술고문 아저씨)

개발자 없는 회사 대표님이 기술 결정을 할 때 전화로 편히 물어볼 수 있는 DX·AX 기술고문 서비스의 랜딩 페이지와 무료 상담 예약 시스템.

- `docs/` — 정적 랜딩 페이지 (GitHub Pages). `?mock=1` 을 붙이면 서버 없이 예약 화면을 시험할 수 있다.
- `n8n/` — 예약 플로우. 빈 시간 조회(`GET /webhook/advisor-slots?date=`)와 예약 접수(`POST /webhook/advisor-book`)를 처리하고 구글 캘린더에 일정을 등록한다.
  - `slots.js` 예약 가능 시간 계산 (테스트: `node --test n8n/slots.test.js`)
  - `build_workflow.py` 워크플로 JSON 생성, `--push` 로 n8n 에 반영 (비활성으로 생성)

`n8n/slots.js` 를 고치면 `docs/assets/slots.js` 에도 복사한다.
