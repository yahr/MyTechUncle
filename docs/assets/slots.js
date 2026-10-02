// 예약 가능 시간 계산 — n8n Code 노드와 테스트가 같이 쓰는 순수 함수.
// 모든 시각은 한국 시간(KST, UTC+9) 기준.
const CFG = {
  openMin: 7 * 60,        // 07:00
  closeMin: 22 * 60,      // 22:00 (마지막 슬롯 21:30)
  slotMin: 30,            // 통화 20분 + 정리 10분
  leadMin: 180,           // 지금부터 3시간 뒤부터 예약 가능
  windowDays: 14,         // 오늘 포함 14일 앞까지
  maxPerDay: 8,           // 하루 상담 예약 한도
  weekdays: [1, 2, 3, 4, 5],
  bookingPrefix: '[무료상담]',
};
const KST = 9 * 60 * 60 * 1000;
const DAY = 24 * 60 * 60 * 1000;

function parseDate(date) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date || '');
  if (!m) return null;
  const [y, mo, d] = [+m[1], +m[2], +m[3]];
  const t = Date.UTC(y, mo - 1, d);
  const back = new Date(t);
  if (back.getUTCFullYear() !== y || back.getUTCMonth() !== mo - 1 || back.getUTCDate() !== d) return null;
  return t; // 그 날짜 00:00 UTC (요일·날짜 비교용)
}

// 그 날짜 KST 00:00 의 실제 시각(ms)
const kstMidnight = (dayUtc) => dayUtc - KST;

function busyRanges(events) {
  return (events || [])
    .filter((e) => !e.allDay && e.transparency !== 'transparent' && e.start && e.end && String(e.start).includes('T'))
    .map((e) => [new Date(e.start).getTime(), new Date(e.end).getTime()]);
}

function dayAllowed(dayUtc, now, cfg) {
  if (dayUtc == null) return false;
  if (!cfg.weekdays.includes(new Date(dayUtc).getUTCDay())) return false;
  const todayUtc = Math.floor((now + KST) / DAY) * DAY;
  return dayUtc >= todayUtc && dayUtc < todayUtc + cfg.windowDays * DAY;
}

function bookedCount(events, cfg) {
  return (events || []).filter((e) => String(e.summary || '').startsWith(cfg.bookingPrefix)).length;
}

function computeSlots({ date, now, events, cfg = CFG }) {
  const dayUtc = parseDate(date);
  if (!dayAllowed(dayUtc, now, cfg)) return [];
  if (bookedCount(events, cfg) >= cfg.maxPerDay) return [];
  const busy = busyRanges(events);
  const base = kstMidnight(dayUtc);
  const out = [];
  for (let m = cfg.openMin; m + cfg.slotMin <= cfg.closeMin; m += cfg.slotMin) {
    const s = base + m * 60000, e = s + cfg.slotMin * 60000;
    if (s < now + cfg.leadMin * 60000) continue;
    if (busy.some(([bs, be]) => bs < e && be > s)) continue;
    out.push(`${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`);
  }
  return out;
}

function isSlotFree({ date, time, now, events, cfg = CFG }) {
  return computeSlots({ date, now, events, cfg }).includes(time);
}

// 슬롯 시작·끝을 KST ISO 문자열로 (캘린더 일정 생성용)
function slotRange(date, time, cfg = CFG) {
  const end = new Date(new Date(`${date}T${time}:00+09:00`).getTime() + cfg.slotMin * 60000);
  const pad = (n) => String(n).padStart(2, '0');
  const k = new Date(end.getTime() + KST);
  const endStr = `${k.getUTCFullYear()}-${pad(k.getUTCMonth() + 1)}-${pad(k.getUTCDate())}T${pad(k.getUTCHours())}:${pad(k.getUTCMinutes())}:00+09:00`;
  return { start: `${date}T${time}:00+09:00`, end: endStr };
}

if (typeof module !== 'undefined') module.exports = { computeSlots, isSlotFree, slotRange, CFG };
