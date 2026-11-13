"""1분마다(launchd com.lightez.mtu-reels) 채널의 "릴스 올려" 요청만 확인한다(2026-10-28). 드라이브는 요청이 왔을 때만 본다.
예전 설명(참고):
1) 구글 드라이브 'MyTechUncle/숏폼' 폴더에 새 원본(목소리+손) → 자막 숏폼 렌더(shorts/build_short.py) → 텔레그램 미리보기
   (말풍선 릴스 new_videos 는 2026-10-05 중지)
2) 채널에 "릴스 올려"(또는 "릴스 올려 qa02") → 아직 안 올린 최신 릴스를 Aside 브라우저로 @mytechuncle 에 게시 → 링크 알림
상태: reels/state.json / 기록: reels/watch.log. 드라이브·텔레그램은 n8n(나의기술고문_릴스미리보기)을 거친다.
"""
import calendar, fcntl, json, os, re, subprocess, sys, time, urllib.request

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


SETTLE = 180  # 마지막 영상이 올라오고 3분 지나야 만든다(여러 개를 올리는 중일 수 있어서)


def join_clips(paths, out, fade=0.4):
    """여러 배경 영상을 9:16 으로 맞춰 0.4초씩 겹치며 이어 붙인다"""
    durs = [float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p],
                                 capture_output=True, text=True, check=True).stdout) for p in paths]
    norm = 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setsar=1,format=yuv420p,settb=AVTB'
    chain = [f'[{i}:v]{norm}[c{i}]' for i in range(len(paths))]
    prev, offset = 'c0', durs[0] - fade
    for i in range(1, len(paths)):
        chain.append(f'[{prev}][c{i}]xfade=transition=fade:duration={fade}:offset={offset:.3f}[x{i}]')
        prev, offset = f'x{i}', offset + durs[i] - fade
    cmd = ['ffmpeg', '-loglevel', 'error', '-y'] + sum([['-i', p] for p in paths], []) + \
          ['-filter_complex', ';'.join(chain), '-map', f'[{prev}]', '-an', '-c:v', 'libx264', '-crf', '18', out]
    subprocess.run(cmd, check=True, timeout=900)
    return out


def new_videos(state, force=False):
    """드라이브의 새 배경 영상들 -> 다음 승인 대본 한 편. 여러 개가 함께 올라오면 이어 붙여 한 편으로 만든다(2026-10-14)"""
    episodes = json.load(open(os.path.join(HERE, 'episodes.json')))
    files = [f for f in api('GET', '/drive-list').get('files', []) if 'drive:' + f['id'] not in state['processed']]
    if not files:
        return
    newest = max(calendar.timegm(time.strptime(f['createdTime'][:19], '%Y-%m-%dT%H:%M:%S')) for f in files)  # createdTime 은 UTC
    if not force and time.time() - newest < SETTLE:
        return
    keys = ['drive:' + f['id'] for f in files]
    names = ', '.join(f['name'] for f in files)
    ep = next((e for e in episodes if e.get('approved') and e['id'] not in state['used']), None)
    if not ep:
        if keys[0] not in state['warned']:
            say(f'새 배경 영상({names})이 들어왔어요. 승인된 대본이 남아 있지 않아서 아직 만들지 않았어요. Claude에게 다음 대본을 부탁해 주세요.')
            state['warned'].append(keys[0])
        return
    log(f'download {names} -> {ep["id"]}')
    try:
        locals_ = []
        for f in files:  # 드라이브 목록은 올린 순서(createdTime)
            local = os.path.join(HERE, 'inbox', f['name'])
            open(local, 'wb').write(api('GET', f'/drive-file?id={f["id"]}', raw=True, timeout=600))
            locals_.append(local)
        bg = locals_[0] if len(locals_) == 1 else join_clips(locals_, os.path.join(HERE, 'inbox', time.strftime('%Y%m%d-%H%M%S') + '_합본.mp4'))
        ep = dict(ep, label=f'대표님 질문 #{len(state["built"]) + 1}')  # 화면 번호는 만든(올릴) 순서대로
        out = subprocess.run([sys.executable, os.path.join(HERE, 'build_reel.py'), bg, ep['id'], ep['label']],
                             capture_output=True, text=True, check=True, timeout=1800).stdout.strip().splitlines()[-1]
        res = json.loads(out)
        json.dump(dict(ep, built=res['mp4'], bg=names), open(res['mp4'][:-4] + '.json', 'w'), ensure_ascii=False, indent=2)
        state['used'].append(ep['id'])
        state['built'].append({'id': ep['id'], 'mp4': res['mp4'], 'posted': ''})
        preview(res['mp4'], f'[미리보기] {ep["label"]} — {ep["title"]} ({res["seconds"]}초)\n배경: {names}\n\n괜찮으면 이 채널에 "릴스 올려"라고 써 주세요.')
        log(f'built {res["mp4"]}')
    except Exception as e:  # 같은 파일을 1분마다 다시 시도하지 않게 처리 목록에 넣고 알린다
        log(f'fail {names}: {e}')
        say(f'릴스를 만들지 못했어요({names}): {str(e)[:300]}')
    state['processed'].extend(keys)
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
    from post_instagram import post, comment, COMMENT
    for a in api('GET', '/approvals').get('items', []):
        waiting = [b for b in state['built'] if not b['posted'] and (not a.get('episode') or b['id'] == a['episode'])]
        if not waiting:  # 만들어 둔 편이 없으면 이때만 드라이브를 확인한다(2026-10-28, 1분마다 드라이브를 부르지 않음)
            before = len(state['built'])
            for step in (new_videos, shorts):
                try:
                    step(state, force=True) if step is new_videos else step(state)
                except Exception as e:
                    log(f'{step.__name__} error: {e}')
            made = state['built'][before:]
            api('POST', '/approval-done', {'id': a['id'], 'status': 'previewed' if made else 'skipped', 'result': ','.join(m['id'] for m in made) or 'no reel'})
            if made:
                say('새 영상으로 만들어 미리보기를 보냈어요. 확인하고 괜찮으면 한 번 더 "릴스 올려"라고 써 주세요.')
            else:
                say('올릴 릴스도, 드라이브의 새 영상도 없어요. 배경 영상을 먼저 올린 뒤 "릴스 올려"라고 써 주세요.')
            continue
        b = waiting[0]  # 지정 안 하면 안 올린 것 중 먼저 만든 편부터
        api('POST', '/approval-done', {'id': a['id'], 'status': 'posting', 'result': b['id']})  # 중복 게시 방지: 먼저 표시
        log(f'post {b["id"]} {b["mp4"]}')
        try:
            link = post(b['mp4']).get('link', '')
            meta = json.load(open(b['mp4'][:-4] + '.json')) if os.path.exists(b['mp4'][:-4] + '.json') else {}
            b.update(posted=link or 'posted', posted_at=time.time(), keyword=meta.get('keyword', ''), material=meta.get('material', ''), dm=meta.get('dm', ''))
            save(state)
            if link:
                try:
                    comment(link, meta.get('comment') or COMMENT)  # 편마다 키워드 댓글이 있으면 그걸로
                except Exception as e:  # 댓글은 실패해도 게시는 끝난 것
                    log(f'comment fail {link}: {e}')
            api('POST', '/approval-done', {'id': a['id'], 'status': 'done', 'result': link})
            say(f'인스타에 올렸어요: {link}' if link else '인스타에 올렸어요. 링크는 프로필에서 확인해 주세요.')
        except Exception as e:
            log(f'post fail {b["id"]}: {e}')
            api('POST', '/approval-done', {'id': a['id'], 'status': 'failed', 'result': re.sub(r'\x1b\[[0-9;]*m', '', str(e))[-200:]})  # 색 코드가 있으면 n8n 이 500
            say(f'인스타에 올리지 못했어요({b["id"]}): {str(e)[:200]}\n다시 "릴스 올려"라고 써 주시면 다시 시도해요.')


def keyword_comments(state):
    """키워드 댓글(episodes.json keyword, 예: '보고서')이 달리면 채널에 알린다. 게시 뒤 3일 동안, 30분마다만 본다"""
    if time.time() - state.get('comments_checked', 0) < 1800:  # 브라우저 자동화라 계정 제한 위험: 30분 간격·게시 뒤 3일만
        return
    state['comments_checked'] = time.time()
    from post_instagram import comments, ACCOUNT
    seen = state.setdefault('seen_comments', [])
    for b in state['built']:
        kw = b.get('keyword')
        if not kw or not b['posted'].startswith('http') or time.time() - b.get('posted_at', 0) > 3 * 86400:
            continue
        for user, text in comments(b['posted']):
            key = f"{b['posted']}|{user}|{text}"
            if user == ACCOUNT or kw.lower() not in text.replace(' ', '').lower() or key in seen:
                continue
            seen.append(key)
            dm = b.get('dm') or f"말씀하신 체크리스트예요.\n{b.get('material', '')}"  # 자료 먼저, 조건 없이, 끝에 짧은 질문 하나(episodes.json dm)
            say(f"💬 '{kw}' 댓글이 달렸어요\n@{user}: {text}\n\nDM 열기: https://ig.me/m/{user}\n릴스: {b['posted']}\n\n보낼 DM ↓\n{dm}")
            log(f'keyword comment {user} {b["id"]}')
        save(state)


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
    for step in (approvals, keyword_comments):  # 드라이브(new_videos·shorts)는 "릴스 올려" 요청이 왔을 때만 approvals 안에서 확인
        try:
            step(state)
        except Exception as e:
            log(f'{step.__name__} error: {e}')
    save(state)


if __name__ == '__main__':
    main()
