"""릴스 미리보기를 텔레그램 채널로 보내는 플로우
   python3 n8n/build_reel_notify.py --push
   POST /webhook/mtu-api/reel-preview  (multipart: video=<mp4>, caption=<글>)  헤더 X-MTU-Token
   POST /webhook/mtu-api/notify        (json: {text})                          헤더 X-MTU-Token
"""
import json, os, sys, uuid, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sec = json.load(open(os.path.join(HERE, '..', 'app', 'secrets.json')))
AUTH = {'httpHeaderAuth': {'id': sec['CRED_ID'], 'name': 'MyTechUncle 앱 토큰'}}
TG = {'telegramApi': {'id': 'B2fSwl8ppGfhN8QZ', 'name': 'Telegram (@illey_secretary_bot)'}}
CHAT = '-1003659059794'  # 텔레그램 채널 '나의 기술고문 알림'
NAME = '나의기술고문_릴스미리보기'

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


def hook(name, path, pos):
    return node(name, 'n8n-nodes-base.webhook', 2.1, {'httpMethod': 'POST', 'path': path, 'authentication': 'headerAuth',
                'responseMode': 'lastNode', 'options': {}}, pos, webhookId=str(uuid.uuid4()), credentials=AUTH)


v_hook = hook('미리보기 받기', 'mtu-api/reel-preview', [0, 0])
v_send = node('채널에 영상 보내기', 'n8n-nodes-base.telegram', 1.2, {
    'operation': 'sendVideo', 'chatId': CHAT, 'binaryData': True, 'binaryPropertyName': 'video',
    'additionalFields': {'caption': '={{ ($json.body || {}).caption || "" }}'}}, [240, 0], credentials=TG)
t_hook = hook('알림 받기', 'mtu-api/notify', [0, 240])
t_send = node('채널에 글 보내기', 'n8n-nodes-base.telegram', 1.2, {
    'chatId': CHAT, 'text': '={{ ($json.body || {}).text || "" }}', 'additionalFields': {'appendAttribution': False}}, [240, 240], credentials=TG)

wf = {'name': NAME, 'nodes': [v_hook, v_send, t_hook, t_send], 'settings': {'executionOrder': 'v1'},
      'connections': {v_hook['name']: {'main': [[{'node': v_send['name'], 'type': 'main', 'index': 0}]]},
                      t_hook['name']: {'main': [[{'node': t_send['name'], 'type': 'main', 'index': 0}]]}}}

if '--push' in sys.argv:
    existing = [w for w in call('GET', '/api/v1/workflows?limit=250')['data'] if w['name'] == NAME]
    wid = existing[0]['id'] if existing else None
    if wid:
        call('PUT', f'/api/v1/workflows/{wid}', wf)
    else:
        wid = call('POST', '/api/v1/workflows', wf)['id']
    call('POST', f'/api/v1/workflows/{wid}/activate')
    print('pushed + active', wid)
