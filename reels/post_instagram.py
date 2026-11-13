"""완성된 릴스를 Aside 브라우저로 @mytechuncle 에 올린다 (Claude 없이 맥에서 실행).
   python3 reels/post_instagram.py <mp4> [--dry-run]     -> 성공하면 마지막 줄에 {"link": ...}
   python3 reels/post_instagram.py --comment <릴스 링크> [문구]   -> 댓글 유도 문구(기본 COMMENT)를 단다
같은 이름의 .json(대본·캡션)과 -cover.png 를 같이 쓴다. --dry-run 은 '공유하기' 직전에 멈춘다.
파일은 잠깐 띄운 로컬 서버(127.0.0.1)로 브라우저에 넘긴다.
"""
import http.server, json, os, re, socketserver, subprocess, sys, threading

ACCOUNT = 'mytechuncle'

JS = r'''
const pg = await openTab('https://www.instagram.com/');
const snap = async () => (await snapshot(pg, { interactive: true })).tree;
await sleep(2500);
let t = await snap();
const later = t.match(/button "나중에 하기" \[ref=(e\d+)\]/);  // '알림 설정' 같은 팝업이 화면을 가리면 닫는다
if (later) { await pg.locator(later[1]).click(); await sleep(1000); t = await snap(); }
if (!t.includes('__ACCOUNT__님의 프로필 사진')) throw new Error('인스타가 __ACCOUNT__ 계정이 아니에요');
await pg.locator(t.match(/link \[ref=(e\d+)\]:\n\s+- img "새로운 게시물"/)[1]).click();
await sleep(1200);
t = await snap();
const sub = t.match(/link \[ref=(e\d+)\]:\n\s+- text: "게시물"/);
if (sub) { await pg.locator(sub[1]).click(); await sleep(1200); }
const save = async (url, name) => { const r = await fetch(url); await fs.writeFile(name, Buffer.from(await r.arrayBuffer())); return name; };
await pg.locator('[role="dialog"] input[type="file"]').first().setInputFiles(await save('__BASE__/reel.mp4', './reel.mp4'));
await sleep(6000);
t = await snap();
const cropBtn = t.match(/button \[ref=(e\d+)\]:\n\s+- img "자르기 선택"/);
if (cropBtn) { await pg.locator(cropBtn[1]).click(); await sleep(600); await pg.getByText('9:16', { exact: true }).first().click(); await sleep(600); }
await pg.locator((await snap()).match(/button "다음" \[ref=(e\d+)\]/)[1]).click();
await sleep(2500);
await pg.locator('[role="dialog"] input[type="file"]').last().setInputFiles(await save('__BASE__/cover.png', './cover.png'));
await sleep(2000);
await pg.locator((await snap()).match(/button "다음" \[ref=(e\d+)\]/)[1]).click();
await sleep(2500);
await pg.locator((await snap()).match(/textbox "캡션 추가\.\.\." \[ref=(e\d+)\]/)[1]).click();
const lines = __CAPTION__;
for (let i = 0; i < lines.length; i++) { if (lines[i]) await pg.keyboard.insertText(lines[i]); if (i < lines.length - 1) await pg.keyboard.press('Shift+Enter'); }
t = await snap();
if (__AI__) {  // AI로 만든 사실적인 배경 영상이면 'AI 레이블 추가'를 켠다(인스타 규칙)
  const ai = t.match(/text: "AI 레이블 추가"\n\s+- switch \[ref=(e\d+)\]/);
  if (!ai) throw new Error('AI 레이블 스위치를 찾지 못했어요');
  await pg.locator(ai[1]).click(); await sleep(800);
  if (await pg.locator(ai[1]).getAttribute('aria-checked') !== 'true') throw new Error('AI 레이블이 켜지지 않았어요');
  t = await snap();
}
const share = t.match(/button "공유하기" \[ref=(e\d+)\]/);
if (!share) throw new Error('공유하기 버튼을 찾지 못했어요');
if (__DRY__) { console.log(JSON.stringify({ dry: true, caption: (t.match(/button "(\d+\/2200)"/) || [])[1] })); }
else {
  await pg.locator(share[1]).click();
  let ok = false;
  for (let i = 0; i < 16 && !ok; i++) { await sleep(5000); ok = /공유되었습니다/.test((await snapshot(pg)).tree); }
  if (!ok) throw new Error('공유 완료를 확인하지 못했어요');
  await pg.goto('https://www.instagram.com/__ACCOUNT__/reels/');
  await sleep(3500);
  const href = await pg.evaluate(() => (document.querySelector('a[href*="/reel/"]') || {}).getAttribute?.('href'));
  console.log(JSON.stringify({ link: href ? 'https://www.instagram.com' + href : '' }));
}
'''

# 게시 직후 계정 이름으로 다는 첫 댓글(댓글 유도). 웹에는 댓글·게시물 고정 메뉴가 없어 고정은 앱에서 한다
COMMENT = '회사 상황 한 줄 남겨 주시면 어디부터 손대면 좋을지 답해 드려요 🙌'
COMMENT_JS = r'''
const pg = await openTab('__LINK__');
await sleep(4000);
const later = (await snapshot(pg, { interactive: true })).tree.match(/button "나중에 하기" \[ref=(e\d+)\]/);
if (later) { await pg.locator(later[1]).click(); await sleep(1000); }
const box = (await snapshot(pg, { interactive: true })).tree.match(/textbox "댓글 달기\.\.\." \[ref=(e\d+)\]/);
if (!box) throw new Error('댓글 입력창을 찾지 못했어요');
await pg.locator(box[1]).click();
await pg.keyboard.insertText(__TEXT__);
await sleep(800);
const btn = (await snapshot(pg, { interactive: true })).tree.match(/button "게시" \[ref=(e\d+)\]/);  // Enter 로는 안 올라갈 때가 있다
if (btn) await pg.locator(btn[1]).click(); else await pg.keyboard.press('Enter');
const head = __TEXT__.slice(0, 12);
let ok = false;  // 입력창 글자가 아니라, 날짜가 붙은 댓글 목록에 생겼는지로 확인
for (let i = 0; i < 8 && !ok; i++) { await sleep(1500); ok = (await snapshot(pg)).tree.split('\n').some((l, j, a) => l.includes('- text: "' + head) && /link "\d{4}년/.test(a[j - 1] || '')); }
console.log(JSON.stringify({ commented: ok }));
'''


def comment(link, text=COMMENT):
    js = COMMENT_JS.replace('__LINK__', link).replace('__TEXT__', json.dumps(text, ensure_ascii=False))
    r = subprocess.run(['aside', 'repl', js], capture_output=True, text=True, timeout=120)
    out = [l for l in r.stdout.splitlines() if l.startswith('{')]
    if not out or not json.loads(out[-1])['commented']:
        raise RuntimeError((r.stdout + r.stderr).strip()[-300:])


COMMENTS_JS = r'''
const pg = await openTab('__LINK__');
await sleep(4000);
console.log(JSON.stringify({ tree: (await snapshot(pg)).tree }));
'''
COMMENT_RE = re.compile(r'link "([\w.]+)" \[ref=e\d+\]\n\s+- link "\d{4}년[^"]*" \[ref=e\d+\]: "[^"]*"\n\s+- text: "(.*)"')


def parse_comments(tree):
    """릴스 화면 스냅샷에서 (아이디, 댓글) 목록. 캡션은 날짜 링크가 없어 빠진다"""
    return COMMENT_RE.findall(tree)


def comments(link):
    r = subprocess.run(['aside', 'repl', COMMENTS_JS.replace('__LINK__', link)], capture_output=True, text=True, timeout=120)
    out = [l for l in r.stdout.splitlines() if l.startswith('{"tree"')]
    if not out:
        raise RuntimeError((r.stdout + r.stderr).strip()[-300:])
    return parse_comments(json.loads(out[-1])['tree'])


def serve(files):
    """mp4·cover 를 임시 로컬 서버로 내놓는다"""
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            path = files.get(self.path)
            if not path:
                self.send_response(404); self.end_headers(); return
            data = open(path, 'rb').read()
            self.send_response(200); self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data)
        def log_message(self, *a):
            pass
    srv = socketserver.TCPServer(('127.0.0.1', 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f'http://127.0.0.1:{srv.server_address[1]}'


def post(mp4, dry=False):
    meta = json.load(open(mp4[:-4] + '.json')) if os.path.exists(mp4[:-4] + '.json') else {}
    caption = meta.get('caption', '')
    if len(re.findall(r'#\S+', caption)) > 5:  # 2025-12부터 인스타 해시태그는 글 하나에 5개까지
        raise RuntimeError('해시태그가 5개를 넘어요. episodes.json 캡션을 줄여 주세요')
    srv, base = serve({'/reel.mp4': mp4, '/cover.png': mp4[:-4] + '-cover.png'})
    try:
        js = (JS.replace('__ACCOUNT__', ACCOUNT).replace('__BASE__', base)
                .replace('__CAPTION__', json.dumps(caption.split('\n'), ensure_ascii=False)).replace('__DRY__', 'true' if dry else 'false')
                .replace('__AI__', 'true' if meta.get('ai_generated') else 'false'))
        r = subprocess.run(['aside', 'repl', js], capture_output=True, text=True, timeout=170)
    finally:
        srv.shutdown()
    out = [l for l in r.stdout.splitlines() if l.startswith('{')]
    if not out:
        raise RuntimeError((r.stdout + r.stderr).strip()[-400:])
    return json.loads(out[-1])


if __name__ == '__main__':
    if sys.argv[1] == '--selftest':
        t = '''      - link "kim.ceo" [ref=e32]
      - link "2026년 10월 9일" [ref=e33]: "3분"
      - text: "보고서 부탁드려요"
      - link "mytechuncle" [ref=e38]
      - link "2026년 10월 9일" [ref=e39]: "12분"
      - text: "회사 상황 한 줄 🙌"'''
        assert parse_comments(t) == [('kim.ceo', '보고서 부탁드려요'), ('mytechuncle', '회사 상황 한 줄 🙌')], parse_comments(t)
        print('selftest ok')
    elif sys.argv[1] == '--comments':  # python3 reels/post_instagram.py --comments <릴스 링크>
        print(json.dumps(comments(sys.argv[2]), ensure_ascii=False))
    elif sys.argv[1] == '--comment':  # python3 reels/post_instagram.py --comment <릴스 링크>
        comment(sys.argv[2], *sys.argv[3:4]); print('{"commented": true}')  # 3번째 인자로 문구를 줄 수 있다
    else:
        print(json.dumps(post(sys.argv[1], '--dry-run' in sys.argv), ensure_ascii=False))
