"""릴스 미리보기를 텔레그램 채널로 보내는 플로우
   python3 n8n/build_reel_notify.py --push
   POST /webhook/mtu-api/reel-preview  (multipart: video=<mp4>, caption=<글>)  헤더 X-MTU-Token
   POST /webhook/mtu-api/notify        (json: {text})                          헤더 X-MTU-Token
   GET  /webhook/mtu-api/drive-list    드라이브 MyTechUncle 폴더의 영상 목록
   GET  /webhook/mtu-api/drive-file?id= 영상 내려받기
   텔레그램 채널 "릴스 올려" -> mtu_reel_approvals(pending) / GET mtu-api/approvals / POST mtu-api/approval-done {id,status,result}
"""
import json, os, sys, uuid, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sec = json.load(open(os.path.join(HERE, '..', 'app', 'secrets.json')))
AUTH = {'httpHeaderAuth': {'id': sec['CRED_ID'], 'name': 'MyTechUncle 앱 토큰'}}
TG = {'telegramApi': {'id': 'ydX5qYevNyp4pd21', 'name': 'Telegram account (@mytechuncle_bot)'}}  # 전용 봇(채널 관리자)
APPROVALS = '7qEJZYP0mhT1rXKb'  # n8n 데이터 테이블 mtu_reel_approvals
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

# 구글 드라이브 'MyTechUncle' 폴더(light.ez.jjack) — 배경 영상 목록과 내려받기
DRIVE = {'googleDriveOAuth2Api': {'id': 'PGoQcxgOwMDBmQff', 'name': 'Google Drive account (light.ez.jjack@gmail.com)'}}
FOLDER = '1b09FOQnLdUneSZmflpcVP91gNkPJGuFQ'


def drive_get(name, url, pos, query=None, file=False):
    params = {'url': url, 'authentication': 'predefinedCredentialType', 'nodeCredentialType': 'googleDriveOAuth2Api', 'options': {}}
    if query:
        params.update({'sendQuery': True, 'queryParameters': {'parameters': [{'name': k, 'value': v} for k, v in query.items()]}})
    if file:
        params['options'] = {'response': {'response': {'responseFormat': 'file', 'outputPropertyName': 'data'}}}
    return node(name, 'n8n-nodes-base.httpRequest', 4.2, params, pos, credentials=DRIVE)


def get_hook(name, path, pos):
    n = hook(name, path, pos); n['parameters']['httpMethod'] = 'GET'; n['parameters']['responseMode'] = 'responseNode'
    return n


l_hook = get_hook('배경 목록 요청', 'mtu-api/drive-list', [0, 480])
l_get = drive_get('드라이브 폴더 목록', 'https://www.googleapis.com/drive/v3/files', [240, 480], {
    'q': f"'{FOLDER}' in parents and mimeType contains 'video/' and trashed = false",
    'fields': 'files(id,name,size,createdTime)', 'orderBy': 'createdTime', 'pageSize': '100'})
l_resp = node('목록 응답', 'n8n-nodes-base.respondToWebhook', 1.1, {'respondWith': 'json', 'responseBody': '={{ JSON.stringify($json) }}', 'options': {}}, [480, 480])
f_hook = get_hook('배경 파일 요청', 'mtu-api/drive-file', [0, 720])
f_get = drive_get('드라이브 파일 받기', "={{ 'https://www.googleapis.com/drive/v3/files/' + $json.query.id }}", [240, 720], {'alt': 'media'}, file=True)
f_resp = node('파일 응답', 'n8n-nodes-base.respondToWebhook', 1.1, {'respondWith': 'binary', 'options': {}}, [480, 720])

# 채널에 "릴스 올려"(또는 "릴스 올려 qa02")를 쓰면 승인 대기에 넣고, 맥이 1분마다 가져가 인스타에 올린다
tbl = {'__rl': True, 'mode': 'id', 'value': APPROVALS}
a_trig = node('채널 글 받기', 'n8n-nodes-base.telegramTrigger', 1.2, {'updates': ['channel_post', 'message'], 'additionalFields': {}}, [0, 960],
              credentials=TG, webhookId=str(uuid.uuid4()))
a_pick = code_node = node('올려인지 확인', 'n8n-nodes-base.code', 2, {'jsCode': r"""
const out = [];
for (const it of $input.all()) {
  const p = it.json.channel_post || it.json.message || {};
  const text = String(p.text || '').trim();
  if (String((p.chat || {}).id || '') !== '%s' || !/^릴스\\s*올려/.test(text)) continue;
  const ep = ((text.match(/qa\d+/i) || [''])[0]).toLowerCase();
  out.push({ json: { workspace_id: 'lightez', episode: ep, text: text.slice(0, 200), message_id: p.message_id || 0, status: 'pending', result: '' } });
}
return out;""" % CHAT}, [240, 960])
a_ins = node('승인 대기에 넣기', 'n8n-nodes-base.dataTable', 1.1, {'operation': 'insert', 'dataTableId': tbl, 'columns': {'mappingMode': 'autoMapInputData', 'value': {}}}, [480, 960])
a_ack = node('받았다고 알리기', 'n8n-nodes-base.telegram', 1.2, {'chatId': CHAT, 'text': '받았어요. 1분 안에 인스타에 올리고 링크를 보내 드릴게요.',
             'additionalFields': {'appendAttribution': False}}, [720, 960], credentials=TG, executeOnce=True)
q_hook = get_hook('승인 목록 요청', 'mtu-api/approvals', [0, 1200])
q_get = node('대기 중 승인', 'n8n-nodes-base.dataTable', 1.1, {'operation': 'get', 'dataTableId': tbl, 'matchType': 'allConditions',
             'filters': {'conditions': [{'keyName': 'status', 'condition': 'eq', 'keyValue': 'pending'}]}, 'returnAll': True}, [240, 1200], alwaysOutputData=True)
q_resp = node('승인 목록 응답', 'n8n-nodes-base.respondToWebhook', 1.1, {'respondWith': 'json',
              'responseBody': "={{ JSON.stringify({ items: $input.all().map(i => i.json).filter(r => r.id != null) }) }}", 'options': {}}, [480, 1200])
d_hook = hook('승인 처리 완료', 'mtu-api/approval-done', [0, 1440])
d_upd = node('승인 상태 바꾸기', 'n8n-nodes-base.dataTable', 1.1, {'operation': 'update', 'dataTableId': tbl, 'matchType': 'allConditions',
             'filters': {'conditions': [{'keyName': 'id', 'condition': 'eq', 'keyValue': '={{ $json.body.id }}'}]},
             'columns': {'mappingMode': 'defineBelow', 'value': {'status': '={{ $json.body.status }}', 'result': '={{ $json.body.result }}'}}}, [240, 1440])

wf = {'name': NAME, 'nodes': [v_hook, v_send, t_hook, t_send, l_hook, l_get, l_resp, f_hook, f_get, f_resp,
                              a_trig, a_pick, a_ins, a_ack, q_hook, q_get, q_resp, d_hook, d_upd], 'settings': {'executionOrder': 'v1'},
      'connections': {v_hook['name']: {'main': [[{'node': v_send['name'], 'type': 'main', 'index': 0}]]},
                      t_hook['name']: {'main': [[{'node': t_send['name'], 'type': 'main', 'index': 0}]]},
                      l_hook['name']: {'main': [[{'node': l_get['name'], 'type': 'main', 'index': 0}]]},
                      l_get['name']: {'main': [[{'node': l_resp['name'], 'type': 'main', 'index': 0}]]},
                      f_hook['name']: {'main': [[{'node': f_get['name'], 'type': 'main', 'index': 0}]]},
                      f_get['name']: {'main': [[{'node': f_resp['name'], 'type': 'main', 'index': 0}]]},
                      a_trig['name']: {'main': [[{'node': a_pick['name'], 'type': 'main', 'index': 0}]]},
                      a_pick['name']: {'main': [[{'node': a_ins['name'], 'type': 'main', 'index': 0}]]},
                      a_ins['name']: {'main': [[{'node': a_ack['name'], 'type': 'main', 'index': 0}]]},
                      q_hook['name']: {'main': [[{'node': q_get['name'], 'type': 'main', 'index': 0}]]},
                      q_get['name']: {'main': [[{'node': q_resp['name'], 'type': 'main', 'index': 0}]]},
                      d_hook['name']: {'main': [[{'node': d_upd['name'], 'type': 'main', 'index': 0}]]}}}

if '--push' in sys.argv:
    existing = [w for w in call('GET', '/api/v1/workflows?limit=250')['data'] if w['name'] == NAME]
    wid = existing[0]['id'] if existing else None
    if wid:
        call('PUT', f'/api/v1/workflows/{wid}', wf)
    else:
        wid = call('POST', '/api/v1/workflows', wf)['id']
    call('POST', f'/api/v1/workflows/{wid}/activate')
    print('pushed + active', wid)
