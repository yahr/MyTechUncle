"""n8n 플로우가 실패하면 텔레그램 채널 '나의 기술고문 알림'으로 알리는 오류 플로우
   python3 n8n/build_error_alert.py --push   -> 오류 플로우를 만들고/고치고, 아래 WATCH 플로우들의 settings.errorWorkflow 로 건다
같은 플로우·단계·오류는 1시간에 한 번만 보낸다(예약 화면을 열 때마다 같은 오류가 반복되므로).
"""
import json, os, sys, uuid, urllib.request

NAME = '나의기술고문_오류알림'
CHAT = '-1003659059794'  # 텔레그램 채널 '나의 기술고문 알림'
TG = {'telegramApi': {'id': 'ydX5qYevNyp4pd21', 'name': 'Telegram (@mytechuncle_bot)'}}  # 채널 관리자 봇(illey_secretary_bot 은 채널에 없어 chat not found)
WATCH = ['나의기술고문_무료상담_예약', '나의기술고문_앱API', '나의기술고문_릴스미리보기']

cfg = json.load(open(os.path.expanduser('~/.claude.json')))
env = next(p['mcpServers']['n8n-mcp']['env'] for p in cfg['projects'].values()
           if (p.get('mcpServers') or {}).get('n8n-mcp', {}).get('env', {}).get('N8N_API_KEY'))
BASE, KEY = env['N8N_API_URL'].rstrip('/'), env['N8N_API_KEY']


def call(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method, headers={'X-N8N-API-KEY': KEY, 'Content-Type': 'application/json'},
                                 data=json.dumps(body).encode() if body is not None else None)
    return json.load(urllib.request.urlopen(req, timeout=30))


def node(name, type_, ver, params, pos, **extra):
    n = {'id': str(uuid.uuid4()), 'name': name, 'type': type_, 'typeVersion': ver, 'position': pos, 'parameters': params}
    n.update(extra)
    return n


trig = node('오류 받기', 'n8n-nodes-base.errorTrigger', 1, {}, [0, 0])
pick = node('1시간에 한 번만', 'n8n-nodes-base.code', 2, {'jsCode': r"""
const s = $getWorkflowStaticData('global');
const j = $json, ex = j.execution || {}, msg = String((ex.error || {}).message || '');
const key = (j.workflow || {}).name + '|' + (ex.lastNodeExecuted || '') + '|' + msg.slice(0, 80);
const now = Date.now();
for (const k of Object.keys(s)) if (now - s[k] > 86400000) delete s[k];
if (s[key] && now - s[key] < 3600000) return [];
s[key] = now;
const h = (v) => String(v).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');  // 텔레그램 HTML 서식(밑줄 _ 이 Markdown 에서 깨진다)
return [{ json: { text: `⚠️ n8n 플로우가 실패했어요\n플로우: ${h((j.workflow || {}).name)}\n단계: ${h(ex.lastNodeExecuted || '?')}\n오류: ${h(msg.slice(0, 300))}\n${h(ex.url || '')}\n(같은 오류는 1시간 동안 다시 알리지 않아요)` } }];
"""}, [240, 0])
send = node('채널에 알리기', 'n8n-nodes-base.telegram', 1.2, {'chatId': CHAT, 'text': '={{ $json.text }}',
            'additionalFields': {'appendAttribution': False, 'parse_mode': 'HTML'}}, [480, 0], credentials=TG)
wf = {'name': NAME, 'nodes': [trig, pick, send], 'settings': {'executionOrder': 'v1', 'saveDataSuccessExecution': 'all'},
      'connections': {trig['name']: {'main': [[{'node': pick['name'], 'type': 'main', 'index': 0}]]},
                      pick['name']: {'main': [[{'node': send['name'], 'type': 'main', 'index': 0}]]}}}

if '--push' in sys.argv:
    flows = call('GET', '/api/v1/workflows?limit=250')['data']
    mine = [w for w in flows if w['name'] == NAME]
    wid = call('PUT', f'/api/v1/workflows/{mine[0]["id"]}', wf)['id'] if mine else call('POST', '/api/v1/workflows', wf)['id']
    for w in flows:
        if w['name'] in WATCH:
            full = call('GET', f'/api/v1/workflows/{w["id"]}')
            settings = dict(full.get('settings') or {}, errorWorkflow=wid)
            call('PUT', f'/api/v1/workflows/{w["id"]}', {k: full[k] for k in ('name', 'nodes', 'connections')} | {'settings': settings})
            print('errorWorkflow ->', w['name'])
    call('POST', f'/api/v1/workflows/{wid}/activate')  # 이 n8n 은 오류 플로우도 켜 둬야 불린다
    print('pushed + active', wid)
