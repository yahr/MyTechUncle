"""고문용 앱 API 플로우 (n8n 데이터 테이블 4개 위에 웹훅 2개)
   python3 n8n/build_app_api.py --push
   GET  /webhook/mtu-api/data            -> { customers, applications, subscriptions, consultations }
   POST /webhook/mtu-api/save {table,row} -> 저장된 행 (row.id 가 있으면 수정, 없으면 추가)
   두 웹훅 모두 헤더 X-MTU-Token 필요. 토큰은 app/secrets.json (저장소에 올리지 않음)
"""
import json, os, secrets, sys, uuid, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SECRETS = os.path.join(HERE, '..', 'app', 'secrets.json')
NAME = '나의기술고문_앱API'
WS = 'lightez'  # 워크스페이스(사업자). 지금은 하나뿐
TABLES = {  # n8n 데이터 테이블 id
    'customers': '5qDtcVGsBuMFKueV', 'applications': 'SOVh9O6LyXcADRzE',
    'subscriptions': '2ZX9iNXiAqrMXaMz', 'consultations': 'SjS8D9OKcSlDIcD5',
}
COLUMNS = {  # 앱이 쓸 수 있는 칸과 형식 (s 문자, n 숫자, b 참거짓)
    'customers': {'company': 's', 'name': 's', 'phone': 's', 'email': 's', 'industry': 's', 'memo': 's'},
    'applications': {'customer_id': 'n', 'product': 's', 'topic': 's', 'slot': 's', 'status': 's', 'calendar_link': 's', 'source': 's'},
    'subscriptions': {'customer_id': 'n', 'product': 's', 'start_date': 's', 'end_date': 's', 'amount': 'n', 'paid': 'b', 'status': 's'},
    'consultations': {'customer_id': 'n', 'date': 's', 'title': 's', 'content': 's', 'next_action': 's'},
}

cfg = json.load(open(os.path.expanduser('~/.claude.json')))
env = next(p['mcpServers']['n8n-mcp']['env'] for p in cfg['projects'].values()
           if (p.get('mcpServers') or {}).get('n8n-mcp', {}).get('env', {}).get('N8N_API_KEY'))
BASE, KEY = env['N8N_API_URL'].rstrip('/'), env['N8N_API_KEY']

def call(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method, headers={'X-N8N-API-KEY': KEY, 'Content-Type': 'application/json'},
                                 data=json.dumps(body).encode() if body is not None else None)
    return json.load(urllib.request.urlopen(req, timeout=30))

# 토큰·헤더 인증 자격증명: 처음 한 번 만들고 app/secrets.json 에 둔다
if os.path.exists(SECRETS):
    sec = json.load(open(SECRETS))
else:
    token = secrets.token_urlsafe(32)
    cred = call('POST', '/api/v1/credentials', {'name': 'MyTechUncle 앱 토큰', 'type': 'httpHeaderAuth',
                                                 'data': {'name': 'X-MTU-Token', 'value': token}})
    sec = {'API_BASE': BASE + '/webhook/mtu-api', 'API_TOKEN': token, 'CRED_ID': cred['id']}
    os.makedirs(os.path.dirname(SECRETS), exist_ok=True)
    json.dump(sec, open(SECRETS, 'w'), indent=2)
AUTH = {'httpHeaderAuth': {'id': sec['CRED_ID'], 'name': 'MyTechUncle 앱 토큰'}}

def node(name, type_, ver, params, pos, **extra):
    n = {'id': str(uuid.uuid4()), 'name': name, 'type': type_, 'typeVersion': ver, 'position': pos, 'parameters': params}
    n.update(extra)
    return n

def hook(name, path, method, pos):
    return node(name, 'n8n-nodes-base.webhook', 2.1, {'httpMethod': method, 'path': path, 'authentication': 'headerAuth',
                'responseMode': 'responseNode', 'options': {}}, pos, webhookId=str(uuid.uuid4()), credentials=AUTH)

def table_ref(value):
    return {'__rl': True, 'mode': 'id', 'value': value}

def code(name, js, pos):
    return node(name, 'n8n-nodes-base.code', 2, {'jsCode': js}, pos)

def respond(name, expr, pos):
    return node(name, 'n8n-nodes-base.respondToWebhook', 1.1, {'respondWith': 'json', 'responseBody': expr, 'options': {}}, pos)

# --- 1) 전체 조회 ---
d_hook = hook('앱 데이터 요청', 'mtu-api/data', 'GET', [0, 0])
d_gets = [node(f'{t} 조회', 'n8n-nodes-base.dataTable', 1.1, {'operation': 'get', 'dataTableId': table_ref(TABLES[t]),
               'matchType': 'allConditions', 'filters': {'conditions': [{'keyName': 'workspace_id', 'condition': 'eq', 'keyValue': WS}]},
               'returnAll': True}, [220 * (i + 1), 0], executeOnce=True, alwaysOutputData=True)
          for i, t in enumerate(TABLES)]
d_pack = code('앱 데이터 묶기', 'const rows = (n) => $(n).all().map((i) => i.json).filter((r) => r.id != null);\nreturn [{ json: {\n'
              + ',\n'.join(f"  {t}: rows('{t} 조회')" for t in TABLES) + '\n} }];', [220 * 5 + 220, 0])
d_resp = respond('앱 데이터 응답', '={{ JSON.stringify($json) }}', [220 * 7, 0])

# --- 2) 저장 (추가·수정) ---
s_hook = hook('앱 저장 요청', 'mtu-api/save', 'POST', [0, 400])
s_check = code('저장 확인', f'const TABLES = {json.dumps(TABLES)};\nconst COLUMNS = {json.dumps(COLUMNS)};\nconst WS = {json.dumps(WS)};\n' + r'''
const b = $input.first().json.body || {};
const cols = COLUMNS[b.table];
if (!cols || !b.row || typeof b.row !== 'object') throw new Error('table 또는 row 가 올바르지 않아요');
const row = { workspace_id: WS };
for (const [k, t] of Object.entries(cols)) {
  if (!(k in b.row)) continue;
  const v = b.row[k];
  row[k] = t === 'n' ? (v === '' || v == null ? null : Number(v)) : t === 'b' ? !!v : String(v ?? '').slice(0, 5000);
}
const id = Number(b.row.id) || 0;
return [{ json: { tableId: TABLES[b.table], id, isUpdate: id > 0, row } }];''', [220, 400])
s_if = node('수정인가', 'n8n-nodes-base.if', 2, {'conditions': {
    'options': {'caseSensitive': True, 'leftValue': '', 'typeValidation': 'loose'},
    'conditions': [{'id': str(uuid.uuid4()), 'leftValue': '={{ $json.isUpdate }}', 'rightValue': '',
                    'operator': {'type': 'boolean', 'operation': 'true', 'singleValue': True}}],
    'combinator': 'and'}, 'options': {}}, [440, 400])
s_row_u = code('수정할 칸', "return [{ json: $('저장 확인').first().json.row }];", [660, 320])
s_row_i = code('추가할 칸', "return [{ json: $('저장 확인').first().json.row }];", [660, 480])
DYN = table_ref("={{ $('저장 확인').first().json.tableId }}")
s_upd = node('행 수정', 'n8n-nodes-base.dataTable', 1.1, {'operation': 'update', 'dataTableId': DYN, 'matchType': 'allConditions',
             'filters': {'conditions': [{'keyName': 'id', 'condition': 'eq', 'keyValue': "={{ $('저장 확인').first().json.id }}"},
                                        {'keyName': 'workspace_id', 'condition': 'eq', 'keyValue': WS}]},
             'columns': {'mappingMode': 'autoMapInputData', 'value': {}}}, [880, 320])
s_ins = node('행 추가', 'n8n-nodes-base.dataTable', 1.1, {'operation': 'insert', 'dataTableId': DYN,
             'columns': {'mappingMode': 'autoMapInputData', 'value': {}}}, [880, 480])
s_resp = respond('저장 응답', '={{ JSON.stringify($json) }}', [1100, 400])

nodes = [d_hook, *d_gets, d_pack, d_resp, s_hook, s_check, s_if, s_row_u, s_row_i, s_upd, s_ins, s_resp]
links = [(d_hook, d_gets[0], 0)] + [(a, b, 0) for a, b in zip(d_gets, d_gets[1:])] + [(d_gets[-1], d_pack, 0), (d_pack, d_resp, 0),
         (s_hook, s_check, 0), (s_check, s_if, 0), (s_if, s_row_u, 0), (s_if, s_row_i, 1),
         (s_row_u, s_upd, 0), (s_row_i, s_ins, 0), (s_upd, s_resp, 0), (s_ins, s_resp, 0)]
connections = {}
for a, b, out in links:
    c = connections.setdefault(a['name'], {'main': []})['main']
    while len(c) <= out: c.append([])
    c[out].append({'node': b['name'], 'type': 'main', 'index': 0})
wf = {'name': NAME, 'nodes': nodes, 'connections': connections, 'settings': {'executionOrder': 'v1'}}
json.dump(wf, open(os.path.join(HERE, 'app-api.json'), 'w'), ensure_ascii=False, indent=2)
print('wrote n8n/app-api.json')

if '--push' in sys.argv:
    existing = [w for w in call('GET', '/api/v1/workflows?limit=250')['data'] if w['name'] == NAME]
    if existing:
        wid = existing[0]['id']; call('PUT', f'/api/v1/workflows/{wid}', wf)
    else:
        wid = call('POST', '/api/v1/workflows', wf)['id']
    call('POST', f'/api/v1/workflows/{wid}/activate')
    print('pushed + active', wid)
