"""1분마다(launchd com.lightez.mtu-reels) 두 가지를 본다.
1) 구글 드라이브 'MyTechUncle/숏폼' 폴더에 새 원본(목소리+손) → 자막 숏폼 렌더(shorts/build_short.py) → 텔레그램 미리보기
   (말풍선 릴스 new_videos 는 2026-10-05 중지)
2) 채널에 "릴스 올려"(또는 "릴스 올려 qa02") → 아직 안 올린 최신 릴스를 Aside 브라우저로 @mytechuncle 에 게시 → 링크 알림
상태: reels/state.json / 기록: reels/watch.log. 드라이브·텔레그램은 n8n(나의기술고문_릴스미리보기)을 거친다.
"""
import fcntl, json, os, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, 'state.json')
SEC = json.load(open(os.path.join(HERE, '..', 'app', 'secrets.json')))
sys.path.insert(0, HERE)


def log(msg):
    with open(os.path.join(HERE, 'watch.log'), 'a') as f:
        f.write(time.strftime('%Y-%m-%d %H:%M:%S ') + msg + '\n')


def api(method, path, body=None, raw=False, timeout=60):
    req = urllib.request.Request(SEC['API_BASE'] + path, method=method,
                                 headers={'X-MTU-Token': SEC['API_TOKEN'], 'Content-Type': 'application/json'},
                                 data=json.dumps(body).encode() if body is not None else None)
    data = urllib.request.urlopen(req, timeout=timeout).read()
    return data if raw else (json.loads(data) if data else {})


def say(text):
    api('POST', '/notify', {'text': text})


def preview(mp4, caption):
    subprocess.run(['curl', '-sf', '-H', f"X-MTU-Token: {SEC['API_TOKEN']}", '-F', f'video=@{mp4};type=video/mp4',
                    '-F', f'caption={caption[:1000]}', SEC['API_BASE'] + '/reel-preview'], check=True, capture_output=True, timeout=300)


def new_videos(state):
    episodes = json.load(open(os.path.join(HERE, 'episodes.json')))
    for f in api('GET', '/drive-list').get('files', []):
        key = 'drive:' + f['id']
        if key in state['processed']:
            continue
        ep = next((e for e in episodes if e.get('approved') and e['id'] not in state['used']), None)
        if not ep:
            if key not in state['warned']:
                say(f'새 배경 영상({f["name"]})이 들어왔어요. 승인된 대본이 남아 있지 않아서 아직 만들지 않았어요. Claude에게 다음 대본을 부탁해 주세요.')
                state['warned'].append(key)
            continue
        local = os.path.join(HERE, 'inbox', f['name'])
        log(f'download {f["name"]} -> {ep["id"]}')
        try:
            open(local, 'wb').write(api('GET', f'/drive-file?id={f["id"]}', raw=True, timeout=600))
            ep = dict(ep, label=f'대표님 질문 #{len(state["built"]) + 1}')  # 화면 번호는 만든(올릴) 순서대로
            out = subprocess.run([sys.executable, os.path.join(HERE, 'build_reel.py'), local, ep['id'], ep['label']],
                                 capture_output=True, text=True, check=True, timeout=1800).stdout.strip().splitlines()[-1]
            res = json.loads(out)
            json.dump(dict(ep, built=res['mp4'], bg=f['name']), open(res['mp4'][:-4] + '.json', 'w'), ensure_ascii=False, indent=2)
            state['used'].append(ep['id'])
            state['built'].append({'id': ep['id'], 'mp4': res['mp4'], 'posted': ''})
            preview(res['mp4'], f'[미리보기] {ep["label"]} — {ep["title"]} ({res["seconds"]}초)\n배경: {f["name"]}\n\n괜찮으면 이 채널에 "릴스 올려"라고 써 주세요.')
            log(f'built {res["mp4"]}')
        except Exception as e:  # 같은 파일을 1분마다 다시 시도하지 않게 처리 목록에 넣고 알린다
            log(f'fail {f["name"]}: {e}')
            say(f'릴스를 만들지 못했어요({f["name"]}): {str(e)[:300]}')
        state['processed'].append(key)
        save(state)


SHORTS_FOLDER = '12fEXpBBWyzfPOaQlIRNC_BT0DuQq8Zbx'  # 드라이브 MyTechUncle/숏폼


def shorts(state):
    """목소리+손 원본 → 자막 숏폼 (shorts/build_short.py). 어느 편인지는 대본과 비교해 스스로 찾는다"""
    for f in api('GET', f'/drive-list?folder={SHORTS_FOLDER}').get('files', []):
        key = 'shorts:' + f['id']
        if key in state['processed']:
            continue
        local = os.path.join(HERE, '..', 'shorts', 'inbox', f['name'])
        os.makedirs(os.path.dirname(local), exist_ok=True)
        log(f'shorts download {f["name"]}')
        try:
            open(local, 'wb').write(api('GET', f'/drive-file?id={f["id"]}', raw=True, timeout=600))
            out = subprocess.run([sys.executable, os.path.join(HERE, '..', 'shorts', 'build_short.py'), local],
                                 capture_output=True, text=True, check=True, timeout=1800).stdout.strip().splitlines()[-1]
            res = json.loads(out)
            if res['episode']:
                state['built'].append({'id': res['episode'], 'mp4': res['mp4'], 'posted': ''})
                preview(res['mp4'], f'[미리보기] 숏폼 {res["episode"]} ({res["seconds"]}초) · 원본: {f["name"]}\n\n괜찮으면 이 채널에 "릴스 올려"라고 써 주세요.')
            else:
                preview(res['mp4'], f'[확인 필요] 대본과 맞는 편을 찾지 못했어요({f["name"]}). 자막은 받아쓴 그대로예요. Claude에게 캡션을 부탁해 주세요.')
            log(f'shorts built {res["mp4"]} ep={res["episode"]} score={res["score"]}')
        except Exception as e:
            log(f'shorts fail {f["name"]}: {e}')
            say(f'숏폼을 만들지 못했어요({f["name"]}): {str(e)[:300]}')
        state['processed'].append(key)
        save(state)


def approvals(state):
    from post_instagram import post
    for a in api('GET', '/approvals').get('items', []):
        waiting = [b for b in state['built'] if not b['posted'] and (not a.get('episode') or b['id'] == a['episode'])]
        if not waiting:
            api('POST', '/approval-done', {'id': a['id'], 'status': 'skipped', 'result': 'no reel'})
            say('올릴 릴스가 없어요. 드라이브에 배경 영상을 먼저 올려 주세요.')
            continue
        b = waiting[0]  # 지정 안 하면 안 올린 것 중 먼저 만든 편부터
        api('POST', '/approval-done', {'id': a['id'], 'status': 'posting', 'result': b['id']})  # 중복 게시 방지: 먼저 표시
        log(f'post {b["id"]} {b["mp4"]}')
        try:
            link = post(b['mp4']).get('link', '')
            b['posted'] = link or 'posted'
            save(state)
            api('POST', '/approval-done', {'id': a['id'], 'status': 'done', 'result': link})
            say(f'인스타에 올렸어요: {link}' if link else '인스타에 올렸어요. 링크는 프로필에서 확인해 주세요.')
        except Exception as e:
            log(f'post fail {b["id"]}: {e}')
            api('POST', '/approval-done', {'id': a['id'], 'status': 'failed', 'result': str(e)[:200]})
            say(f'인스타에 올리지 못했어요({b["id"]}): {str(e)[:200]}\n다시 "릴스 올려"라고 써 주시면 다시 시도해요.')


def save(state):
    json.dump(state, open(STATE, 'w'), ensure_ascii=False, indent=2)


def main():
    lock = open(os.path.join(HERE, '.watch.lock'), 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)  # 렌더·게시 중이면 다음 실행은 건너뛴다
    except BlockingIOError:
        return
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    for k in ('processed', 'used', 'warned', 'built'):
        state.setdefault(k, [])
    for step in (approvals, shorts):  # 말풍선 릴스(new_videos)는 2026-10-05 중지
        try:
            step(state)
        except Exception as e:
            log(f'{step.__name__} error: {e}')
    save(state)


if __name__ == '__main__':
    main()
