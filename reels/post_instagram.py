"""완성된 릴스를 Aside 브라우저로 @mytechuncle 에 올린다 (Claude 없이 맥에서 실행).
   python3 reels/post_instagram.py <mp4> [--dry-run]     -> 성공하면 마지막 줄에 {"link": ...}
같은 이름의 .json(대본·캡션)과 -cover.png 를 같이 쓴다. --dry-run 은 '공유하기' 직전에 멈춘다.
파일은 잠깐 띄운 로컬 서버(127.0.0.1)로 브라우저에 넘긴다.
"""
import http.server, json, os, socketserver, subprocess, sys, threading

ACCOUNT = 'mytechuncle'

JS = r'''
const pg = await openTab('https://www.instagram.com/');
const snap = async () => (await snapshot(pg, { interactive: true })).tree;
let t = await snap();
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
    srv, base = serve({'/reel.mp4': mp4, '/cover.png': mp4[:-4] + '-cover.png'})
    try:
        js = (JS.replace('__ACCOUNT__', ACCOUNT).replace('__BASE__', base)
                .replace('__CAPTION__', json.dumps(caption.split('\n'), ensure_ascii=False)).replace('__DRY__', 'true' if dry else 'false'))
        r = subprocess.run(['aside', 'repl', js], capture_output=True, text=True, timeout=170)
    finally:
        srv.shutdown()
    out = [l for l in r.stdout.splitlines() if l.startswith('{')]
    if not out:
        raise RuntimeError((r.stdout + r.stderr).strip()[-400:])
    return json.loads(out[-1])


if __name__ == '__main__':
    print(json.dumps(post(sys.argv[1], '--dry-run' in sys.argv), ensure_ascii=False))
