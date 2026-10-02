"""n8n 예약 플로우 JSON 생성 (+ --push 이면 n8n 에 비활성으로 생성/갱신)
   python3 n8n/build_workflow.py          -> n8n/advisor-booking.json 만 생성
   python3 n8n/build_workflow.py --push   -> n8n 에도 반영
"""
import json, os, sys, uuid, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SLOTS = open(os.path.join(HERE, 'slots.js')).read().split("if (typeof module")[0]
ORIGINS = 'https://yahr.github.io,http://localhost:8766'
# 예약 전용 캘린더 'MyTechUncle' (light.ez.jjack@gmail.com 계정)
CAL_ID = '24f8c32d583ad5ade6f55c65bb7bba3c6f1af3b8838106c3161342b65c2907bb@group.calendar.google.com'
CAL_EVENTS = 'https://www.googleapis.com/calendar/v3/calendars/' + CAL_ID.replace('@', '%40') + '/events'
TG_CRED = {'telegramApi': {'id': 'B2fSwl8ppGfhN8QZ', 'name': 'Telegram (@illey_secretary_bot)'}}
CHAT_ID = '6630606379'
CAL_CRED = {'googleCalendarOAuth2Api': {'id': 'QNKMHoO0PJUojtFo', 'name': 'Google Calendar account - light.ez.jjack@gmail.com'}}
NAME = '나의기술고문_무료상담_예약'

DAY_RANGE = r'''
function dayRange(date) {
  const ok = /^\d{4}-\d{2}-\d{2}$/.test(date || '') && !isNaN(Date.parse(date + 'T00:00:00+09:00'));
  const d = ok ? date : '1970-01-01';
  const start = new Date(d + 'T00:00:00+09:00');
  return { timeMin: start.toISOString(), timeMax: new Date(start.getTime() + 86400000).toISOString() };
}
function toEvents(items) {
  return (items || []).filter(e => e.status !== 'cancelled').map(e => ({
    start: (e.start && (e.start.dateTime || e.start.date)) || '',
    end: (e.end && (e.end.dateTime || e.end.date)) || '',
    allDay: !!(e.start && e.start.date),
    transparency: e.transparency || 'opaque',
    summary: e.summary || '',
  }));
}
'''

def node(name, type_, ver, params, pos, **extra):
    n = {'id': str(uuid.uuid4()), 'name': name, 'type': type_, 'typeVersion': ver, 'position': pos, 'parameters': params}
    n.update(extra)
    return n

def webhook(name, path, method, pos):
    return node(name, 'n8n-nodes-base.webhook', 2.1,
                {'httpMethod': method, 'path': path, 'responseMode': 'responseNode', 'options': {'allowedOrigins': ORIGINS}},
                pos, webhookId=str(uuid.uuid4()))

def code(name, js, pos):
    return node(name, 'n8n-nodes-base.code', 2, {'jsCode': js}, pos)

def cal_list(name, pos):
    return node(name, 'n8n-nodes-base.httpRequest', 4.2, {
        'url': CAL_EVENTS, 'authentication': 'predefinedCredentialType', 'nodeCredentialType': 'googleCalendarOAuth2Api',
        'sendQuery': True, 'queryParameters': {'parameters': [
            {'name': 'timeMin', 'value': '={{ $json.timeMin }}'}, {'name': 'timeMax', 'value': '={{ $json.timeMax }}'},
            {'name': 'singleEvents', 'value': 'true'}, {'name': 'maxResults', 'value': '250'}]},
        'options': {}}, pos, credentials=CAL_CRED)

def respond(name, body_expr, pos, code_=200):
    opts = {'responseCode': code_} if code_ != 200 else {}
    return node(name, 'n8n-nodes-base.respondToWebhook', 1.1,
                {'respondWith': 'json', 'responseBody': body_expr, 'options': opts}, pos)

def if_true(name, field, pos):
    return node(name, 'n8n-nodes-base.if', 2, {'conditions': {
        'options': {'caseSensitive': True, 'leftValue': '', 'typeValidation': 'loose'},
        'conditions': [{'id': str(uuid.uuid4()), 'leftValue': '={{ $json.%s }}' % field, 'rightValue': '',
                        'operator': {'type': 'boolean', 'operation': 'true', 'singleValue': True}}],
        'combinator': 'and'}, 'options': {}}, pos)

# --- 1) 빈 시간 조회 ---------------------------------------------------------
s_hook = webhook('예약 가능 시간 요청', 'advisor-slots', 'GET', [0, 0])
s_range = code('조회 날짜 범위', DAY_RANGE + r'''
const date = String(($input.first().json.query || {}).date || '');
return [{ json: { date, ...dayRange(date) } }];''', [220, 0])
s_cal = cal_list('캘린더 일정 조회', [440, 0])
s_calc = code('빈 시간 계산', SLOTS + DAY_RANGE + r'''
const date = $('조회 날짜 범위').first().json.date;
const events = toEvents($input.first().json.items);
return [{ json: { date, slots: computeSlots({ date, now: Date.now(), events }) } }];''', [660, 0])
s_resp = respond('빈 시간 응답', '={{ JSON.stringify({ date: $json.date, slots: $json.slots }) }}', [880, 0])

# --- 2) 예약 접수 ------------------------------------------------------------
b_hook = webhook('예약 접수 요청', 'advisor-book', 'POST', [0, 400])
b_check = code('입력 확인', DAY_RANGE + r'''
const b = $input.first().json.body || {};
const s = (v, n) => String(v == null ? '' : v).trim().slice(0, n);
const d = { name: s(b.name, 40), company: s(b.company, 60), industry: s(b.industry, 40), phone: s(b.phone, 20),
  email: s(b.email, 80), topic: s(b.topic, 500), product: ['free', 'annual', 'founder'].includes(b.product) ? b.product : 'free',
  date: s(b.date, 10), time: s(b.time, 5) };
const valid = !b.website && b.consent === true && d.name && d.company && d.topic
  && /^0[0-9\- ]{8,12}$/.test(d.phone) && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(d.email)
  && /^\d{4}-\d{2}-\d{2}$/.test(d.date) && /^\d{2}:\d{2}$/.test(d.time);
return [{ json: { valid: !!valid, ...d, ...dayRange(d.date) } }];''', [220, 400])
b_valid = if_true('입력이 올바른가', 'valid', [440, 400])
b_bad = respond('입력 오류 응답', '={{ JSON.stringify({ ok: false, reason: "invalid" }) }}', [660, 560], 400)
b_cal = cal_list('예약 직전 일정 조회', [660, 320])
b_free = code('그 시간이 비었나', SLOTS + DAY_RANGE + r'''
const d = $('입력 확인').first().json;
const free = isSlotFree({ date: d.date, time: d.time, now: Date.now(), events: toEvents($input.first().json.items) });
const r = slotRange(d.date, d.time);
const label = { free: '무료 상담', annual: '연간 기술고문', founder: 'Founder 기술고문' }[d.product];
const event = {
  summary: `${CFG.bookingPrefix} ${d.company} ${d.name}`,
  description: `회사: ${d.company}\n업종: ${d.industry || '-'}\n이름: ${d.name}\n휴대폰: ${d.phone}\n이메일: ${d.email}\n관심 상품: ${label}\n\n고민:\n${d.topic}\n\n— 나의 기술고문 아저씨 무료 상담 (20분 전화)`,
  start: { dateTime: r.start, timeZone: 'Asia/Seoul' },
  end: { dateTime: r.end, timeZone: 'Asia/Seoul' },
  attendees: [{ email: d.email, displayName: d.name }],
  reminders: { useDefault: false, overrides: [{ method: 'popup', minutes: 30 }] },
};
return [{ json: { free, event, d, label } }];''', [880, 320])
b_isfree = if_true('비어 있나', 'free', [1100, 320])
b_taken = respond('이미 찬 시간 응답', '={{ JSON.stringify({ ok: false, reason: "taken" }) }}', [1320, 480], 409)
b_create = node('캘린더에 예약 등록', 'n8n-nodes-base.httpRequest', 4.2, {
    'method': 'POST', 'url': CAL_EVENTS, 'authentication': 'predefinedCredentialType', 'nodeCredentialType': 'googleCalendarOAuth2Api',
    'sendQuery': True, 'queryParameters': {'parameters': [{'name': 'sendUpdates', 'value': 'all'}]},
    'sendBody': True, 'specifyBody': 'json', 'jsonBody': '={{ JSON.stringify($json.event) }}', 'options': {}}, [1320, 240], credentials=CAL_CRED)
b_ok = respond('예약 완료 응답', '={{ JSON.stringify({ ok: true }) }}', [1540, 240])
b_tg = node('텔레그램 알림', 'n8n-nodes-base.telegram', 1.2, {
    'chatId': CHAT_ID,
    'text': "={{ '📞 무료 상담 예약\\n' + $('그 시간이 비었나').first().json.d.date + ' ' + $('그 시간이 비었나').first().json.d.time + '\\n' + $('그 시간이 비었나').first().json.d.company + ' ' + $('그 시간이 비었나').first().json.d.name + ' (' + $('그 시간이 비었나').first().json.d.phone + ')\\n' + $('그 시간이 비었나').first().json.label + '\\n고민: ' + $('그 시간이 비었나').first().json.d.topic + '\\n\\n📅 캘린더: ' + $('캘린더에 예약 등록').first().json.htmlLink }}",
    'additionalFields': {'appendAttribution': False}}, [1760, 240], credentials=TG_CRED)

# 앱용 기록: 전화번호로 고객을 찾거나 만들고, 신청 한 줄 추가 (테이블은 build_app_api.py 참고)
D = "$('그 시간이 비었나').first().json.d"
tbl = lambda v: {'__rl': True, 'mode': 'id', 'value': v}
b_cust = node('고객 찾기·만들기', 'n8n-nodes-base.dataTable', 1.1, {
    'operation': 'upsert', 'dataTableId': tbl('5qDtcVGsBuMFKueV'), 'matchType': 'allConditions',
    'filters': {'conditions': [{'keyName': 'workspace_id', 'condition': 'eq', 'keyValue': 'lightez'},
                               {'keyName': 'phone', 'condition': 'eq', 'keyValue': '={{ %s.phone.replace(/\\D/g, "") }}' % D}]},
    'columns': {'mappingMode': 'defineBelow', 'value': {
        'workspace_id': 'lightez', 'phone': '={{ %s.phone.replace(/\\D/g, "") }}' % D,
        'company': '={{ %s.company }}' % D, 'name': '={{ %s.name }}' % D, 'email': '={{ %s.email }}' % D,
        'industry': '={{ %s.industry }}' % D}}}, [1980, 240], executeOnce=True)
b_app = node('신청 추가', 'n8n-nodes-base.dataTable', 1.1, {
    'operation': 'insert', 'dataTableId': tbl('SOVh9O6LyXcADRzE'),
    'columns': {'mappingMode': 'defineBelow', 'value': {
        'workspace_id': 'lightez', 'customer_id': '={{ $json.id }}', 'product': '={{ %s.product }}' % D,
        'topic': '={{ %s.topic }}' % D, 'slot': '={{ %s.date + " " + %s.time }}' % (D, D), 'status': 'new',
        'calendar_link': "={{ $('캘린더에 예약 등록').first().json.htmlLink }}", 'source': 'landing'}}}, [2200, 240], executeOnce=True)

nodes = [s_hook, s_range, s_cal, s_calc, s_resp, b_hook, b_check, b_valid, b_bad, b_cal, b_free, b_isfree, b_taken, b_create, b_ok, b_tg, b_cust, b_app]
def link(a, b, out=0):
    return a['name'], out, b['name']
links = [link(s_hook, s_range), link(s_range, s_cal), link(s_cal, s_calc), link(s_calc, s_resp),
         link(b_hook, b_check), link(b_check, b_valid), link(b_valid, b_cal, 0), link(b_valid, b_bad, 1),
         link(b_cal, b_free), link(b_free, b_isfree), link(b_isfree, b_create, 0), link(b_isfree, b_taken, 1),
         link(b_create, b_ok), link(b_ok, b_tg), link(b_tg, b_cust), link(b_cust, b_app)]
connections = {}
for src, out, dst in links:
    c = connections.setdefault(src, {'main': []})['main']
    while len(c) <= out: c.append([])
    c[out].append({'node': dst, 'type': 'main', 'index': 0})

wf = {'name': NAME, 'nodes': nodes, 'connections': connections, 'settings': {'executionOrder': 'v1'}}
out_path = os.path.join(HERE, 'advisor-booking.json')
json.dump(wf, open(out_path, 'w'), ensure_ascii=False, indent=2)
print('wrote', out_path)

if '--push' in sys.argv:
    cfg = json.load(open(os.path.expanduser('~/.claude.json')))
    env = next(p['mcpServers']['n8n-mcp']['env'] for p in cfg['projects'].values()
               if (p.get('mcpServers') or {}).get('n8n-mcp', {}).get('env', {}).get('N8N_API_KEY'))
    base, key = env['N8N_API_URL'].rstrip('/'), env['N8N_API_KEY']
    def call(method, path, body=None):
        req = urllib.request.Request(base + path, method=method, headers={'X-N8N-API-KEY': key, 'Content-Type': 'application/json'},
                                     data=json.dumps(body).encode() if body is not None else None)
        return json.load(urllib.request.urlopen(req, timeout=30))
    existing = [w for w in call('GET', '/api/v1/workflows?limit=250')['data'] if w['name'] == NAME]
    if existing:
        r = call('PUT', f"/api/v1/workflows/{existing[0]['id']}", wf); print('updated', r['id'], 'active', r.get('active'))
    else:
        r = call('POST', '/api/v1/workflows', wf); print('created', r['id'], 'active', r.get('active'))
