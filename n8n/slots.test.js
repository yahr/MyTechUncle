// node --test n8n/slots.test.js
const test = require('node:test');
const assert = require('node:assert');
const { computeSlots, CFG } = require('./slots.js');

const kst = (s) => new Date(s + '+09:00').getTime(); // '2026-10-05T07:00:00' -> ms
const NOW = kst('2026-10-02T09:00:00'); // 금요일 아침

test('평일 하루 슬롯은 07:00부터 21:30까지 30분 간격', () => {
  const r = computeSlots({ date: '2026-10-05', now: NOW, events: [] }); // 월
  assert.strictEqual(r[0], '07:00');
  assert.strictEqual(r[r.length - 1], '21:30');
  assert.strictEqual(r.length, 30);
});

test('주말은 예약 불가', () => {
  assert.deepStrictEqual(computeSlots({ date: '2026-10-03', now: NOW, events: [] }), []); // 토
  assert.deepStrictEqual(computeSlots({ date: '2026-10-04', now: NOW, events: [] }), []); // 일
});

test('오늘은 지금부터 준비 시간(3시간) 이후 슬롯만', () => {
  const r = computeSlots({ date: '2026-10-02', now: NOW, events: [] }); // 금 09:00 -> 12:00부터
  assert.strictEqual(r[0], '12:00');
});

test('지난 날짜와 예약 가능 기간(14일) 밖은 빈 배열', () => {
  assert.deepStrictEqual(computeSlots({ date: '2026-10-01', now: NOW, events: [] }), []);
  assert.deepStrictEqual(computeSlots({ date: '2026-10-16', now: NOW, events: [] }), []); // 오늘 포함 14일 = 10/15까지
  assert.ok(computeSlots({ date: '2026-10-15', now: NOW, events: [] }).length > 0);
});

test('바쁜 일정과 겹치는 슬롯은 빠진다(경계는 겹치지 않음)', () => {
  const events = [{ start: '2026-10-05T10:00:00+09:00', end: '2026-10-05T11:00:00+09:00' }];
  const r = computeSlots({ date: '2026-10-05', now: NOW, events });
  assert.ok(r.includes('09:30'));
  assert.ok(!r.includes('10:00'));
  assert.ok(!r.includes('10:30'));
  assert.ok(r.includes('11:00'));
});

test('투명(한가함) 일정과 종일 일정은 막지 않는다', () => {
  const events = [
    { start: '2026-10-05T10:00:00+09:00', end: '2026-10-05T11:00:00+09:00', transparency: 'transparent' },
    { start: '2026-10-05', end: '2026-10-06', allDay: true },
  ];
  assert.strictEqual(computeSlots({ date: '2026-10-05', now: NOW, events }).length, 30);
});

test('하루 상담 예약이 한도(8건)를 채우면 그날은 마감', () => {
  const events = Array.from({ length: CFG.maxPerDay }, (_, i) => ({
    start: `2026-10-05T${String(7 + i).padStart(2, '0')}:00:00+09:00`,
    end: `2026-10-05T${String(7 + i).padStart(2, '0')}:30:00+09:00`,
    summary: '[무료상담] 테스트',
  }));
  assert.deepStrictEqual(computeSlots({ date: '2026-10-05', now: NOW, events }), []);
});

test('잘못된 날짜 형식은 빈 배열', () => {
  assert.deepStrictEqual(computeSlots({ date: '2026-13-40', now: NOW, events: [] }), []);
  assert.deepStrictEqual(computeSlots({ date: 'abc', now: NOW, events: [] }), []);
});

test('isSlotFree: 예약 직전 재확인', () => {
  const { isSlotFree } = require('./slots.js');
  const events = [{ start: '2026-10-05T10:00:00+09:00', end: '2026-10-05T10:30:00+09:00' }];
  assert.strictEqual(isSlotFree({ date: '2026-10-05', time: '10:00', now: NOW, events }), false);
  assert.strictEqual(isSlotFree({ date: '2026-10-05', time: '10:30', now: NOW, events }), true);
  assert.strictEqual(isSlotFree({ date: '2026-10-05', time: '10:15', now: NOW, events }), false); // 슬롯 경계가 아님
});
