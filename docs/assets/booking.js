// 무료 상담 예약 — 캘린리식 2단계(날짜·시간 → 정보) + 확인
// API: GET  {API}/advisor-slots?date=YYYY-MM-DD  -> { slots: ["07:00", ...] }
//      POST {API}/advisor-book  (JSON)          -> { ok: true } | 409 { ok:false, reason:'taken' }
(function () {
  var API = window.ADVISOR_API || '';
  var MOCK = /[?&]mock=1/.test(location.search) || !API;
  var dlg = document.getElementById('book');
  if (!dlg) return;
  var $ = function (id) { return document.getElementById(id); };
  var form = $('book-form'), msg = $('book-msg'), submitBtn = $('book-submit');
  var calGrid = $('cal-grid'), calTitle = $('cal-title'), calPrev = $('cal-prev'), calNext = $('cal-next');
  var timesEl = $('book-times'), timesHead = $('book-times-head');
  var DOW = ['일', '월', '화', '수', '목', '금', '토'];
  var KST = 9 * 3600 * 1000, DAY = 86400000;
  var state = { date: '', time: '', month: 0 }; // month: 화면에 보이는 달의 1일(UTC ms)

  function kstToday() { return Math.floor((Date.now() + KST) / DAY) * DAY; }
  function ymd(t) { return new Date(t).toISOString().slice(0, 10); }
  function monthStart(t) { var d = new Date(t); return Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), 1); }
  function addMonths(t, n) { var d = new Date(t); return Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + n, 1); }
  function bookable(t) {
    var today = kstToday();
    return t >= today && t < today + CFG.windowDays * DAY && CFG.weekdays.indexOf(new Date(t).getUTCDay()) >= 0;
  }
  function label(date, time) {
    var t = Date.parse(date + 'T00:00:00Z'), d = new Date(t);
    return (d.getUTCMonth() + 1) + '월 ' + d.getUTCDate() + '일 (' + DOW[d.getUTCDay()] + ')' + (time ? ' ' + time : '');
  }

  function showStep(n) {
    dlg.dataset.step = String(n);
    $('step-pick').hidden = n !== 1;
    $('step-form').hidden = n !== 2;
    $('step-done').hidden = n !== 3;
    $('book-when').textContent = state.date && n > 1 ? label(state.date, state.time) + ' · 20분' : '';
  }

  function renderCal() {
    var m = state.month, d = new Date(m);
    calTitle.textContent = d.getUTCFullYear() + '년 ' + (d.getUTCMonth() + 1) + '월';
    var first = monthStart(kstToday()), last = monthStart(kstToday() + (CFG.windowDays - 1) * DAY);
    calPrev.disabled = m <= first; calNext.disabled = m >= last;
    calGrid.innerHTML = '';
    for (var i = 0; i < d.getUTCDay(); i++) calGrid.appendChild(document.createElement('span'));
    var days = new Date(addMonths(m, 1) - DAY).getUTCDate();
    for (var k = 1; k <= days; k++) {
      var t = m + (k - 1) * DAY, b = document.createElement('button');
      b.type = 'button'; b.textContent = k; b.dataset.date = ymd(t);
      b.className = 'cal-day' + (t === kstToday() ? ' is-today' : '');
      if (!bookable(t)) b.disabled = true;
      b.setAttribute('aria-pressed', String(b.dataset.date === state.date));
      b.setAttribute('aria-label', label(b.dataset.date) + (b.disabled ? ' 예약 불가' : ''));
      b.addEventListener('click', function () { pickDay(this.dataset.date); });
      calGrid.appendChild(b);
    }
  }

  function pickDay(date) {
    state.date = date; state.time = '';
    renderCal();
    timesHead.textContent = label(date);
    timesEl.innerHTML = '<p class="note">빈 시간을 불러오고 있어요</p>';
    loadSlots(date).then(function (slots) {
      if (state.date !== date) return;
      timesEl.innerHTML = '';
      if (!slots.length) { timesEl.innerHTML = '<p class="note">이날은 예약이 다 찼어요. 다른 날을 골라 주세요</p>'; return; }
      slots.forEach(function (s) {
        var row = document.createElement('div'); row.className = 'slot';
        var b = document.createElement('button'); b.type = 'button'; b.className = 'slot-time'; b.textContent = s;
        var go = document.createElement('button'); go.type = 'button'; go.className = 'slot-next btn btn-primary'; go.textContent = '다음';
        b.addEventListener('click', function () {
          state.time = s;
          timesEl.querySelectorAll('.slot').forEach(function (r) { r.classList.toggle('is-picked', r === row); });
          go.focus();
        });
        go.addEventListener('click', function () { showStep(2); $('bk-name').focus(); });
        row.appendChild(b); row.appendChild(go); timesEl.appendChild(row);
      });
    }).catch(function () {
      timesEl.innerHTML = '<p class="note">시간을 불러오지 못했어요. 잠시 뒤 날짜를 다시 눌러 주세요</p>';
    });
  }

  function loadSlots(date) {
    if (MOCK) return Promise.resolve(computeSlots({ date: date, now: Date.now(), events: [] }));
    return fetch(API + '/advisor-slots?date=' + encodeURIComponent(date))
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (j) { return j.slots || []; });
  }

  function firstBookable() {
    for (var i = 0; i < CFG.windowDays; i++) { var t = kstToday() + i * DAY; if (bookable(t)) return ymd(t); }
    return '';
  }

  function open(product) {
    form.reset(); msg.textContent = '';
    if (product) form.elements.product.value = product;
    state = { date: '', time: '', month: monthStart(kstToday()) };
    timesHead.textContent = '날짜를 골라 주세요';
    timesEl.innerHTML = '';
    showStep(1); renderCal();
    dlg.showModal();
    var f = firstBookable(); if (f) { state.month = monthStart(Date.parse(f + 'T00:00:00Z')); pickDay(f); }
  }

  calPrev.addEventListener('click', function () { state.month = addMonths(state.month, -1); renderCal(); });
  calNext.addEventListener('click', function () { state.month = addMonths(state.month, 1); renderCal(); });
  $('book-back').addEventListener('click', function () { showStep(1); });
  document.querySelectorAll('[data-book]').forEach(function (a) {
    a.addEventListener('click', function (e) { e.preventDefault(); open(a.dataset.book); });
  });
  dlg.querySelectorAll('[data-close]').forEach(function (b) { b.addEventListener('click', function () { dlg.close(); }); });
  dlg.addEventListener('click', function (e) { if (e.target === dlg) dlg.close(); });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    if (!form.reportValidity()) return;
    var f = form.elements; // form.name 은 폼 자체 속성이라 elements 로 읽는다
    var data = {
      name: f.name.value.trim(), company: f.company.value.trim(), industry: f.industry.value.trim(),
      phone: f.phone.value.trim(), email: f.email.value.trim(), topic: f.topic.value.trim(),
      product: f.product.value, date: state.date, time: state.time,
      consent: f.consent.checked, website: f.website.value // 스팸 방지용 빈 칸
    };
    submitBtn.disabled = true; msg.textContent = '예약을 접수하고 있어요';
    var req = MOCK
      ? new Promise(function (r) { setTimeout(function () { r({ status: 200, json: function () { return Promise.resolve({ ok: true }); } }); }, 600); })
      : fetch(API + '/advisor-book', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    req.then(function (r) { return r.json().then(function (j) { return { status: r.status, body: j }; }); })
      .then(function (res) {
        submitBtn.disabled = false; msg.textContent = '';
        if (res.body && res.body.ok) { $('done-when').textContent = label(state.date, state.time) + ' · 20분 통화'; showStep(3); return; }
        if (res.status === 409) { showStep(1); pickDay(state.date); timesHead.textContent = '방금 다른 분이 예약한 시간이에요. 다른 시간을 골라 주세요'; return; }
        msg.textContent = '입력한 내용을 다시 확인해 주세요';
      })
      .catch(function () { submitBtn.disabled = false; msg.textContent = '접수하지 못했어요. 잠시 뒤 다시 눌러 주세요'; });
  });
})();
