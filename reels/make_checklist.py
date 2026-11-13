"""릴스 키워드 DM 자료(체크리스트 페이지)를 만든다. docs/ai-checklist.html 을 틀로 쓰고 내용만 바꾼다.
   python3 reels/make_checklist.py reels/checklists/handover.json   -> docs/<slug>.html
스펙 JSON: slug, title(검색 제목), desc, og, crumb, h1, answer(짧은 답), intro, steps[[제목, 설명, 예시?]],
          prompt(선택, AI에게 시킬 문장), prompt_note, faq[[질문, 답]], next_h2, next_p, date
"""
import html, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, '..', 'docs')
BASE = 'https://yahr.github.io/MyTechUncle/'
ORG = {'@id': BASE + '#org'}
e = html.escape


def build(p):
    url = BASE + p['slug'] + '.html'
    tpl = open(os.path.join(DOCS, 'ai-checklist.html')).read()
    ld = {'@context': 'https://schema.org', '@graph': [
        {'@type': 'Article', '@id': url + '#article', 'headline': p['h1'], 'description': p['desc'], 'inLanguage': 'ko-KR',
         'datePublished': p['date'], 'dateModified': p['date'], 'author': ORG, 'publisher': ORG, 'mainEntityOfPage': url,
         'image': BASE + 'assets/og-image.png', 'isPartOf': {'@id': BASE + '#website'},
         'audience': {'@type': 'BusinessAudience', 'audienceType': '개발자 없는 1~10인 회사 대표'}},
        {'@type': 'HowTo', 'name': p['h1'], 'description': p['answer'], 'inLanguage': 'ko-KR',
         'step': [{'@type': 'HowToStep', 'position': i + 1, 'name': s[0], 'text': s[1]} for i, s in enumerate(p['steps'])]},
        {'@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in p['faq']]},
        {'@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': '나의 기술고문 아저씨', 'item': BASE},
            {'@type': 'ListItem', 'position': 2, 'name': p['crumb'], 'item': url}]}]}
    meta = f'''<title>{e(p['title'])}</title>
<meta name="description" content="{e(p['desc'])}">
<link rel="canonical" href="{url}">
<meta name="author" content="가볍지이지">
<meta property="og:site_name" content="My Tech Uncle">
<meta property="og:type" content="article">
<meta property="og:locale" content="ko_KR">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{e(p['og'])} · 나의 기술고문 아저씨">
<meta property="og:description" content="{e(p['desc'])}">
<meta property="og:image" content="{BASE}assets/og-image.png?v=2">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="article:published_time" content="{p['date']}">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False, indent=1)}
</script>'''
    y, m, d = p['date'].split('-')
    steps = '\n'.join(f'    <li><h3>{e(s[0])}</h3>\n      <p>{e(s[1])}</p>' + (f'\n      <p class="ex">{e(s[2])}</p>' if len(s) > 2 else '') + '</li>' for s in p['steps'])
    prompt = (f'\n  <h2>이렇게 시켜 보세요</h2>\n  <p class="prompt">{e(p["prompt"])}</p>\n  <p>{e(p["prompt_note"])}</p>\n' if p.get('prompt') else '')
    faq = '\n'.join(f'  <h3>{e(q)}</h3>\n  <p>{e(a)}</p>' for q, a in p['faq'])
    main = f'''<main>
  <div class="top">
    <a class="back" href="./">← 나의 기술고문 아저씨</a>
  </div>
  <h1>{e(p['h1'])}</h1>
  <p class="meta">개발자 없는 회사 대표님용 체크리스트 · 가볍지이지 작성 · <time datetime="{p['date']}">{int(y)}년 {int(m)}월 {int(d)}일</time> 업데이트</p>
  <p class="answer"><strong>짧은 답.</strong> {e(p['answer'])}</p>

  <div class="intro">
    <p>{e(p['intro'])}</p>
  </div>

  <ol class="check">
{steps}
  </ol>
{prompt}
  <h2>자주 묻는 질문</h2>
{faq}

  <h2>{e(p['next_h2'])}</h2>
  <p>{e(p['next_p'])}</p>
  <a class="cta" href="./#book">무료 상담 예약하기</a>
</main>'''
    out = re.sub(r'<title>.*?</script>', lambda _: meta, tpl, count=1, flags=re.S)
    out = re.sub(r'<main>.*?</main>', lambda _: main, out, count=1, flags=re.S)
    return out


if __name__ == '__main__':
    spec = json.load(open(sys.argv[1]))
    path = os.path.join(DOCS, spec['slug'] + '.html')
    open(path, 'w').write(build(spec))
    sm = os.path.join(DOCS, 'sitemap.xml'); s = open(sm).read(); loc = f'<loc>{BASE}{spec["slug"]}.html</loc>'
    if loc not in s:
        open(sm, 'w').write(s.replace('</urlset>', f'  <url>{loc}<lastmod>{spec["date"]}</lastmod></url>\n</urlset>'))
    print(path)
