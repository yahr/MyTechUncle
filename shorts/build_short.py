"""목소리+손으로 찍은 원본 1개 → 자막 입힌 숏폼 (1080x1920, 소리 유지)
   python3 shorts/build_short.py <원본영상>        -> {"mp4", "cover", "episode", "seconds"}
   python3 shorts/build_short.py --selftest
1) mlx_whisper 로 받아쓰기 2) 대본(episodes.json)과 비교해 몇 편인지 고르고, 받아쓰기 오타는 대본 문장으로 바꾼다
3) 첫 말 0.15초 전 ~ 끝 말 1.2초 뒤로 자르고 4) HyperFrames 로 자막·끝 글자를 얹어 렌더 5) 텔레그램 한도 안으로 압축
"""
import difflib, html, json, math, os, re, shutil, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
MODEL = 'mlx-community/whisper-large-v3-turbo'
LEAD, TAIL, END_HOLD = 0.15, 1.2, 1.6   # 앞 여유, 끝 말 뒤 여유, 끝 글자 보이는 시간


def norm(t):
    return re.sub(r'[\s\.,!?\'"‘’“”·~]', '', t)


def sim(a, b):
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def match_episode(segments, episodes):
    """받아쓴 전체 문장과 각 편 대본을 비교해 가장 비슷한 편과 점수"""
    said = ' '.join(s['text'] for s in segments)
    scored = [(sim(said, ' '.join(e['lines'])), e) for e in episodes]
    score, ep = max(scored, key=lambda x: x[0]) if scored else (0, None)
    return (ep, round(score, 2)) if score >= 0.35 else (None, round(score, 2))


def cues(segments, lines):
    """받아쓰기 구간마다 가장 비슷한 대본 문장이 있으면 그 문장으로(오타 교정), 없으면 받아쓴 그대로"""
    out = []
    for s in segments:
        best = max(lines, key=lambda l: sim(s['text'], l)) if lines else None
        text = best if best and sim(s['text'], best) >= 0.55 else s['text'].strip()
        if out and out[-1]['text'] == text:  # 한 문장이 두 구간으로 나뉜 경우 이어 붙임
            out[-1]['end'] = s['end']
            continue
        out.append({'start': s['start'], 'end': s['end'], 'text': text})
    return out


def window(segments, duration):
    """잘라 쓸 구간: 첫 말 직전 ~ 끝 말 뒤 여유"""
    start = max(0.0, segments[0]['start'] - LEAD)
    end = min(duration, segments[-1]['end'] + TAIL)
    return round(start, 2), round(end, 2)


def transcribe(path):
    import mlx_whisper
    r = mlx_whisper.transcribe(path, path_or_hf_repo=MODEL, language='ko')
    return [{'start': s['start'], 'end': s['end'], 'text': s['text']} for s in r['segments'] if s['text'].strip()]


def probe(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def page(cs, start, end, end_text):
    esc = html.escape
    total = round(end - start, 2)
    divs, js = [], []
    for i, c in enumerate(cs):
        a, b = max(0, c['start'] - start), min(total, c['end'] - start)
        divs.append(f'<div class="cap" id="c{i}">{esc(c["text"])}</div>')
        js.append(f'show("#c{i}", {a:.2f}, {b:.2f});')
    end_at = max(0, total - END_HOLD)
    return f'''<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><meta name="viewport" content="width={W}, height={H}">
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
@font-face {{ font-family: "A2z"; font-weight: 700; src: url("assets/a2z-700.woff2") format("woff2"); }}
@font-face {{ font-family: "A2z"; font-weight: 500; src: url("assets/a2z-500.woff2") format("woff2"); }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: {W}px; height: {H}px; overflow: hidden; background: #000; }}
body {{ font-family: "A2z", sans-serif; word-break: keep-all; }}
#root {{ position: relative; width: 100%; height: 100%; overflow: hidden; }}
.src {{ position: absolute; inset: 0; width: {W}px; height: {H}px; object-fit: cover; }}
.tag {{ position: absolute; left: 60px; top: 240px; color: #fff; font-weight: 700; font-size: 34px; padding: 12px 22px; border-radius: 999px; background: rgba(8,20,24,.55); }}
/* 자막: 안전 영역 아래쪽(1180~1480px) */
.cap {{ position: absolute; left: 70px; right: 70px; top: 1180px; display: none; text-align: center; color: #fff; font-weight: 700; font-size: 66px; line-height: 1.3;
  letter-spacing: -0.02em; text-shadow: 0 0 6px #000, 0 0 14px rgba(0,0,0,.85), 0 3px 2px #000; }}
.end {{ position: absolute; left: 70px; right: 70px; top: 760px; display: none; justify-content: center; }}
.end span {{ background: #2ed8c3; color: #04211e; font-weight: 700; font-size: 58px; line-height: 1.3; padding: 30px 44px; border-radius: 40px; text-align: center; box-shadow: 0 16px 40px rgba(0,0,0,.35); }}
</style></head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{total}" data-width="{W}" data-height="{H}">
<video id="src" class="clip src" src="assets/src.mp4" data-start="0" data-duration="{total}" data-media-start="{start}" data-has-audio="true" data-track-index="0" playsinline></video>
<div class="tag">나의 기술고문 아저씨</div>
{chr(10).join(divs)}
<div class="end" id="end"><span>{"<br>".join(esc(t) for t in end_text.split(" · "))}</span></div>
</div>
<script>
const tl = gsap.timeline({{ paused: true }});
const show = (s, a, b) => {{ tl.set(s, {{ display: "block" }}, a); tl.fromTo(s, {{ opacity: 0, y: 14 }}, {{ opacity: 1, y: 0, duration: 0.15 }}, a); tl.set(s, {{ display: "none" }}, b); }};
{chr(10).join(js)}
tl.set("#end", {{ display: "flex" }}, {end_at:.2f});
tl.fromTo("#end span", {{ scale: 0.7, opacity: 0 }}, {{ scale: 1, opacity: 1, duration: 0.35, ease: "back.out(2)" }}, {end_at:.2f});
tl.set({{}}, {{}}, {total});
window.__timelines = window.__timelines || {{}};
window.__timelines["main"] = tl;
</script></body></html>
'''


def build(src):
    episodes = json.load(open(os.path.join(HERE, 'episodes.json')))
    stamp = time.strftime('%Y%m%d-%H%M%S')
    work = os.path.join(HERE, 'work', stamp)
    shutil.copytree(os.path.join(HERE, 'template'), work)
    norm_src = os.path.join(work, 'assets', 'src.mp4')  # 세로 1080x1920, 30fps, 소리 유지
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-vf',
                    f'scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}',
                    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', norm_src], check=True)
    segs = transcribe(norm_src)
    if not segs:
        raise RuntimeError('목소리를 찾지 못했어요')
    ep, score = match_episode(segs, episodes)
    start, end = window(segs, probe(norm_src))
    cs = cues(segs, ep['lines'] if ep else [])
    open(os.path.join(work, 'index.html'), 'w').write(page(cs, start, end, ep['end_text'] if ep else '궁금한 건 댓글로'))
    subprocess.run(['npm', 'run', 'check'], cwd=work, check=True, capture_output=True)
    subprocess.run(['npm', 'run', 'render'], cwd=work, check=True, capture_output=True)
    rendered = os.path.join(work, 'renders', sorted(os.listdir(os.path.join(work, 'renders')))[-1])
    name = f'{ep["id"] if ep else "X"}-{stamp}'
    mp4 = os.path.join(HERE, 'out', name + '.mp4')
    os.makedirs(os.path.dirname(mp4), exist_ok=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', rendered, '-c:v', 'libx264', '-preset', 'medium', '-crf', '23', '-maxrate', '6M',
                    '-bufsize', '12M', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', mp4], check=True)
    cover = mp4[:-4] + '-cover.png'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(min(0.8, end - start)), '-i', mp4, '-frames:v', '1', cover], check=True)
    meta = {'episode': ep['id'] if ep else None, 'score': score, 'caption': ep['caption'] if ep else '', 'cues': cs, 'src': src}
    json.dump(meta, open(mp4[:-4] + '.json', 'w'), ensure_ascii=False, indent=2)
    return {'mp4': mp4, 'cover': cover, 'episode': meta['episode'], 'score': score, 'seconds': round(end - start, 2)}


def selftest():
    eps = [{'id': 'A', 'lines': ['견적서에 이 단어 있으면, 한 번 더 물어보세요.', '일체, 등, 기타.']},
           {'id': 'B', 'lines': ['직원이 ChatGPT에 회사 자료 넣기 전에, 이 설정부터 끄세요.']}]
    segs = [{'start': 0.6, 'end': 2.8, 'text': ' 견적서에 이 단어 있으면 한번 더 물어 보세요'},
            {'start': 3.0, 'end': 4.2, 'text': ' 일체 등 기타'}, {'start': 4.3, 'end': 5.0, 'text': ' 일체 등 기타'}]
    ep, score = match_episode(segs, eps)
    assert ep['id'] == 'A' and score > 0.5, (ep, score)
    cs = cues(segs, ep['lines'])
    assert [c['text'] for c in cs] == eps[0]['lines'], cs              # 오타는 대본 문장으로
    assert cs[1]['end'] == 5.0                                         # 같은 문장 두 구간은 합침
    assert cues([{'start': 0, 'end': 1, 'text': ' 전혀 다른 말'}], eps[0]['lines'])[0]['text'] == '전혀 다른 말'
    assert match_episode([{'start': 0, 'end': 1, 'text': '오늘 날씨 좋네요'}], eps)[0] is None
    assert window(segs, 6.0) == (0.45, 6.0) and window(segs, 9.0) == (0.45, 6.2)
    print('selftest ok')


if __name__ == '__main__':
    if sys.argv[1:] == ['--selftest']:
        selftest()
    else:
        print(json.dumps(build(sys.argv[1]), ensure_ascii=False))
