"""배경 영상 1개 + 대화 대본 1편 → 나의 기술고문 아저씨 대화 릴스 (1080x1920)
   python3 reels/build_reel.py <배경영상> <에피소드 id> [화면 라벨]  -> reels/out/<id>-<시각>.mp4 + 커버 png
   python3 reels/build_reel.py --selftest                   -> 타이밍 계산 확인
대본은 reels/episodes.json. 배경은 세로로 맞춰 자르고 소리는 뺀다. 대본보다 짧으면 반복한다.
"""
import html, json, math, os, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
START = 1.4          # 제목이 먼저 보이는 시간
TYPING = 0.6         # 아저씨가 입력 중(…) 표시
END_CARD = 3.4       # 마무리 화면


def hold_for(text):
    """한 말풍선을 읽을 시간: 글자 수에 비례, 1.6~3.4초"""
    return min(3.4, max(1.6, 0.065 * len(text) + 0.85))


def schedule(lines):
    """[(화자, 문장)] -> ([{who,text,typing,show}], 마무리 시작, 전체 길이)"""
    t, out = START, []
    for who, text in lines:
        typing = None
        if who == 'uncle':
            typing, t = t, t + TYPING
        out.append({'who': who, 'text': text, 'typing': typing, 'show': round(t, 2)})
        t += hold_for(text)
    end = round(t, 2)
    return out, end, round(end + END_CARD, 2)


def probe(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def page(ep, items, end, total, bg_dur):
    esc = html.escape
    clips = []
    for i in range(math.ceil(total / bg_dur)):
        s = i * bg_dur
        clips.append(f'<video id="bg{i}" class="clip bg" src="assets/bg.mp4" muted playsinline data-start="{s:.2f}" '
                     f'data-duration="{min(bg_dur, total - s):.2f}" data-media-start="0" data-track-index="0"></video>')
    bubbles, js = [], []
    KEEP = 3  # 화면에는 최근 말풍선 3개만 (오래된 건 위로 밀려 잘리지 않게 지운다)
    for i, it in enumerate(items):
        if i >= KEEP:
            js.append(f'hide("#b{i - KEEP}", {it["typing"] if it["typing"] is not None else it["show"]});')
        if it['who'] == 'uncle':
            bubbles.append(f'<div class="row uncle typing" id="t{i}"><div class="bub"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div>'
                           f'<img class="av" src="assets/character-face.png" alt=""></div>')
            bubbles.append(f'<div class="row uncle" id="b{i}"><div class="col"><span class="who">기술고문 아저씨</span>'
                           f'<div class="bub">{esc(it["text"])}</div></div><img class="av" src="assets/character-face.png" alt=""></div>')
            js.append(f'show("#t{i}", {it["typing"]}); hide("#t{i}", {it["show"]}); show("#b{i}", {it["show"]});')
        else:
            bubbles.append(f'<div class="row ceo" id="b{i}"><span class="av ceo-av">대표</span><div class="col"><span class="who">대표님</span>'
                           f'<div class="bub">{esc(it["text"])}</div></div></div>')
            js.append(f'show("#b{i}", {it["show"]});')
    return f'''<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width={W}, height={H}">
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
@font-face {{ font-family: "A2z"; font-weight: 700; src: url("assets/a2z-700.woff2") format("woff2"); }}
@font-face {{ font-family: "A2z"; font-weight: 500; src: url("assets/a2z-500.woff2") format("woff2"); }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: {W}px; height: {H}px; overflow: hidden; background: #0f1720; }}
body {{ font-family: "A2z", sans-serif; word-break: keep-all; color: #16202b; }}
#root {{ position: relative; width: 100%; height: 100%; overflow: hidden; }}
.bg {{ position: absolute; inset: 0; width: {W}px; height: {H}px; object-fit: cover; }}
.shade {{ position: absolute; inset: 0; background: linear-gradient(180deg, rgba(8,20,24,.72) 0%, rgba(8,20,24,.38) 34%, rgba(8,20,24,.38) 66%, rgba(8,20,24,.7) 100%); }}
/* 글자 안전 영역: 세로 230~1480px */
.head {{ position: absolute; left: 70px; right: 70px; top: 230px; }}
.label {{ display: inline-block; background: #2ed8c3; color: #04211e; font-weight: 700; font-size: 38px; line-height: 1; padding: 16px 28px; border-radius: 999px; }}
.title {{ display: block; margin-top: 22px; color: #fff; font-weight: 700; font-size: 72px; line-height: 1.2; letter-spacing: -0.03em; text-shadow: 0 4px 24px rgba(0,0,0,.35); }}
.chat {{ position: absolute; left: 50px; right: 50px; top: 520px; bottom: 440px; display: flex; flex-direction: column; justify-content: flex-end; gap: 26px; overflow: hidden;
  -webkit-mask-image: linear-gradient(180deg, transparent 0, #000 110px); mask-image: linear-gradient(180deg, transparent 0, #000 110px); }}
.row {{ display: none; align-items: flex-end; gap: 18px; }}
.row.uncle {{ justify-content: flex-end; }}
.col {{ display: flex; flex-direction: column; align-items: flex-start; gap: 8px; max-width: 780px; }}
.uncle .col {{ align-items: flex-end; }}
.who {{ color: #fff; background: rgba(8,20,24,.62); font-weight: 500; font-size: 30px; line-height: 1; padding: 10px 18px; border-radius: 999px; }}
.bub {{ font-weight: 700; font-size: 50px; line-height: 1.38; letter-spacing: -0.02em; padding: 26px 34px; border-radius: 40px; box-shadow: 0 10px 30px rgba(0,0,0,.22); }}
.ceo .bub {{ background: #fff; color: #16202b; border-bottom-left-radius: 12px; }}
.uncle .bub {{ background: #2ed8c3; color: #04211e; border-bottom-right-radius: 12px; }}
.av {{ flex: none; width: 104px; height: 104px; border-radius: 50%; display: block; }}
.ceo-av {{ background: #e1e6ec; color: #4c5866; display: grid; place-items: center; font-weight: 700; font-size: 34px; }}
.typing .bub {{ display: flex; gap: 14px; padding: 34px 38px; }}
.dot {{ width: 20px; height: 20px; border-radius: 50%; background: #04211e; opacity: .45; display: block; }}
.end {{ position: absolute; inset: 0; background: #2ed8c3; color: #04211e; opacity: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 64px; text-align: center; padding: 248px 86px 562px; }}
.end img {{ width: 780px; display: block; }}
.pill {{ background: #fff; color: #16202b; border-radius: 999px; padding: 50px 92px; font-weight: 700; font-size: 80px; line-height: 1; box-shadow: 0 22px 65px rgba(4,33,30,.2); }}
.sub {{ font-weight: 500; font-size: 48px; line-height: 1.35; }}
</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{total}" data-width="{W}" data-height="{H}">
{chr(10).join(clips)}
<div class="shade"></div>
<div class="head"><span class="label">{esc(ep["label"])}</span><span class="title" id="title">{esc(ep["title"])}</span></div>
<div class="chat">
{chr(10).join(bubbles)}
</div>
<div class="end" id="end"><img src="assets/logo-vertical-light.png" alt="나의 기술고문 아저씨"><span class="pill">첫 상담 20분 무료</span>
<span class="sub">저장해 두고 필요할 때 꺼내 보세요<br>프로필 링크에서 예약</span></div>
</div>
<script>
const tl = gsap.timeline({{ paused: true }});
const E = "power3.out";
const show = (s, t) => {{ tl.set(s, {{ display: "flex" }}, t); tl.fromTo(s, {{ opacity: 0, y: 40, scale: 0.94 }}, {{ opacity: 1, y: 0, scale: 1, duration: 0.35, ease: E }}, t); }};
const hide = (s, t) => tl.set(s, {{ display: "none" }}, t);
tl.fromTo(".head", {{ opacity: 0, y: -30 }}, {{ opacity: 1, y: 0, duration: 0.5, ease: E }}, 0.2);
gsap.utils.toArray(".typing .dot").forEach((d, i) => tl.to(d, {{ opacity: 1, duration: 0.2, yoyo: true, repeat: 1 }}, 0.01 * i));
{chr(10).join(js)}
tl.to([".chat", ".head"], {{ opacity: 0, duration: 0.3 }}, {end});
tl.set([".chat", ".head"], {{ display: "none" }}, {end + 0.3:.2f});
tl.fromTo("#end", {{ opacity: 0, y: 200 }}, {{ opacity: 1, y: 0, duration: 0.5, ease: "power3.inOut" }}, {end});
tl.fromTo("#end img", {{ scale: 0.85 }}, {{ scale: 1, duration: 0.6, ease: E }}, {end + 0.3:.2f});
tl.fromTo("#end .pill", {{ scale: 0.5, opacity: 0 }}, {{ scale: 1, opacity: 1, duration: 0.5, ease: E }}, {end + 0.8:.2f});
tl.fromTo("#end .sub", {{ y: 24, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.4, ease: E }}, {end + 1.2:.2f});
tl.set({{}}, {{}}, {total});
window.__timelines = window.__timelines || {{}};
window.__timelines["main"] = tl;
</script></body></html>
'''


def compress(src, dst):
    """텔레그램 봇 한도(50MB) 안으로: 6Mbps 상한, 25초면 약 20MB"""
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
                    '-maxrate', '6M', '-bufsize', '12M', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-an', dst], check=True)


def build(bg, ep_id, label=None):
    eps = {e['id']: e for e in json.load(open(os.path.join(HERE, 'episodes.json')))}
    ep = dict(eps[ep_id], **({'label': label} if label else {}))  # 화면 번호는 올리는 순서대로
    items, end, total = schedule(ep['lines'])
    stamp = time.strftime('%Y%m%d-%H%M%S')
    work = os.path.join(HERE, 'work', f'{ep_id}-{stamp}')
    shutil.copytree(os.path.join(HERE, 'template'), work)
    out_bg = os.path.join(work, 'assets', 'bg.mp4')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', bg, '-vf',
                    f'scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}', '-an',
                    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21', '-pix_fmt', 'yuv420p', out_bg], check=True)
    open(os.path.join(work, 'index.html'), 'w').write(page(ep, items, end, total, probe(out_bg)))
    subprocess.run(['npm', 'run', 'check'], cwd=work, check=True, capture_output=True)
    subprocess.run(['npm', 'run', 'render'], cwd=work, check=True, capture_output=True)
    renders = sorted(os.listdir(os.path.join(work, 'renders')))
    mp4 = os.path.join(HERE, 'out', f'{ep_id}-{stamp}.mp4')
    compress(os.path.join(work, 'renders', renders[-1]), mp4)
    cover = mp4[:-4] + '-cover.png'  # 첫 질문과 답이 보이는 순간
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(items[1]['show'] + 0.8), '-i', mp4, '-frames:v', '1', cover], check=True)
    return mp4, cover, total


def selftest():
    items, end, total = schedule([['ceo', '가' * 20], ['uncle', '나' * 10]])
    assert items[0] == {'who': 'ceo', 'text': '가' * 20, 'typing': None, 'show': START}
    assert items[1]['typing'] == round(START + hold_for('가' * 20), 2)
    assert items[1]['show'] == round(items[1]['typing'] + TYPING, 2)
    assert end == round(items[1]['show'] + hold_for('나' * 10), 2) and total == round(end + END_CARD, 2)
    assert hold_for('') == 1.6 and hold_for('x' * 100) == 3.4
    print('selftest ok')


if __name__ == '__main__':
    if sys.argv[1:] == ['--selftest']:
        selftest()
    else:
        mp4, cover, total = build(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
        print(json.dumps({'mp4': mp4, 'cover': cover, 'seconds': total}, ensure_ascii=False))
