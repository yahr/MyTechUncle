"""휴대폰 '릴스배경' 앨범을 무선 디버깅으로 살펴 새 영상이 있으면 릴스를 만들어 텔레그램 채널로 미리보기를 보낸다.
   launchd 가 1분마다 실행 (com.lightez.mtu-reels). 직접 실행: python3 reels/watch_phone.py
   상태: reels/state.json (처리한 파일, 쓴 대본). 기록: reels/watch.log
대본은 episodes.json 에서 approved=true 이고 아직 안 쓴 것을 순서대로 쓴다. 인스타 게시는 하지 않는다(승인 후 따로).
"""
import fcntl, json, os, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ADB = os.path.expanduser('~/Library/Android/sdk/platform-tools/adb')
ALBUMS = ['/sdcard/DCIM/릴스배경', '/sdcard/Pictures/릴스배경', '/sdcard/Movies/릴스배경']
VIDEO_EXT = ('.mp4', '.mov', '.m4v', '.3gp')
STATE = os.path.join(HERE, 'state.json')
SECRETS = json.load(open(os.path.join(HERE, '..', 'app', 'secrets.json')))


def log(msg):
    with open(os.path.join(HERE, 'watch.log'), 'a') as f:
        f.write(time.strftime('%Y-%m-%d %H:%M:%S ') + msg + '\n')


def adb(*args, serial=None, timeout=60):
    cmd = [ADB] + (['-s', serial] if serial else []) + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def connect():
    """무선 디버깅 기기를 찾아 연결. 포트가 바뀌어도 mDNS 로 다시 찾는다."""
    for line in adb('devices').stdout.splitlines()[1:]:
        if line.endswith('\tdevice'):
            return line.split('\t')[0]
    for line in adb('mdns', 'services').stdout.splitlines():
        if '_adb-tls-connect' in line:
            adb('connect', line.split()[-1], timeout=15)
    for line in adb('devices').stdout.splitlines()[1:]:
        if line.endswith('\tdevice'):
            return line.split('\t')[0]
    return None


def notify_text(text):
    req = urllib.request.Request(SECRETS['API_BASE'] + '/notify', method='POST',
                                 headers={'X-MTU-Token': SECRETS['API_TOKEN'], 'Content-Type': 'application/json'},
                                 data=json.dumps({'text': text}).encode())
    urllib.request.urlopen(req, timeout=60)


def notify_video(mp4, caption):
    subprocess.run(['curl', '-sf', '-H', f"X-MTU-Token: {SECRETS['API_TOKEN']}", '-F', f'video=@{mp4};type=video/mp4',
                    '-F', f'caption={caption[:1000]}', SECRETS['API_BASE'] + '/reel-preview'], check=True, capture_output=True, timeout=300)


def main():
    lock = open(os.path.join(HERE, '.watch.lock'), 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)  # 렌더 중이면 다음 실행은 건너뛴다
    except BlockingIOError:
        return
    serial = connect()
    if not serial:
        return
    state = json.load(open(STATE)) if os.path.exists(STATE) else {'processed': [], 'used': [], 'warned': []}
    files = []
    for d in ALBUMS:
        out = adb('shell', f'ls -1 "{d}" 2>/dev/null', serial=serial).stdout
        files += [f'{d}/{n.strip()}' for n in out.splitlines() if n.strip().lower().endswith(VIDEO_EXT)]
    new = [f for f in files if f not in state['processed']]
    if not new:
        return
    episodes = json.load(open(os.path.join(HERE, 'episodes.json')))
    for remote in new:
        ep = next((e for e in episodes if e.get('approved') and e['id'] not in state['used']), None)
        if not ep:
            if remote not in state['warned']:
                notify_text(f'새 배경 영상이 들어왔어요({os.path.basename(remote)}). 승인된 대본이 남아 있지 않아서 아직 만들지 않았어요. Claude에게 다음 대본을 부탁해 주세요.')
                state['warned'].append(remote)
            continue
        local = os.path.join(HERE, 'inbox', os.path.basename(remote))
        log(f'pull {remote} -> {ep["id"]}')
        try:
            r = adb('pull', remote, local, serial=serial, timeout=600)
            if r.returncode:
                raise RuntimeError(r.stderr.strip()[:200])
            out = subprocess.run([sys.executable, os.path.join(HERE, 'build_reel.py'), local, ep['id']],
                                 capture_output=True, text=True, check=True, timeout=1800).stdout.strip().splitlines()[-1]
            res = json.loads(out)
            notify_video(res['mp4'], f'[미리보기] {ep["label"]} — {ep["title"]}\n배경: {os.path.basename(remote)} · {res["seconds"]}초\n\n'
                                     f'올리려면 Claude에게 "릴스 {ep["id"]} 올려"라고 말해 주세요.')
            state['used'].append(ep['id'])
            ep_out = dict(ep, built=res['mp4'], cover=res['cover'], bg=remote)
            json.dump(ep_out, open(res['mp4'][:-4] + '.json', 'w'), ensure_ascii=False, indent=2)
            log(f'built {res["mp4"]}')
        except Exception as e:  # 실패해도 같은 파일을 1분마다 다시 시도하지 않게 처리 목록에 넣고 알린다
            log(f'fail {remote}: {e}')
            notify_text(f'릴스를 만들지 못했어요({os.path.basename(remote)}): {str(e)[:300]}')
        state['processed'].append(remote)
        json.dump(state, open(STATE, 'w'), ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
