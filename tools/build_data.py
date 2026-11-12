# -*- coding: utf-8 -*-
"""中古車GEO タイアップ効果ボード：表示用データ（board_data.json）を作る。
入力：toyota-geo-board の data/ucar（84問）・data/ucar_signal（1,761本）・data/ga4（toyota.jp）
数え方：classify.py（261022 実態調査 v9 付録 P.42 に合わせて検証済み）"""
import json, sys, re, collections, csv, datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import yaml
from classify import judge, norm, host, ENT

R = Path(__file__).parent.parent / 'toyota-geo-board'
U = R / 'data' / 'ucar'
SURF = ['aio', 'aimode', 'chatgpt', 'gemini']
SURF_JA = {'aio': 'AI Overviews', 'aimode': 'AI Mode', 'chatgpt': 'ChatGPT', 'gemini': 'Gemini'}

# ------------------------------------------------------------------ 質問
P = yaml.safe_load(open(R / 'config/ucar_prompts.yaml', encoding='utf-8'))['prompts']
PI = {p['id']: p for p in P}
VOL = json.load(open(U / 'volumes_2026-10-26.json'))['volumes']
STAGE_MEDIA = {'Ask': 'livedoor', 'Interest': 'bestcar', 'Confirm': 'goonet_mag', 'Action': 'official'}
GROUP_KEY = {'重点': 'focus', '比較用': 'comp', 'トヨタ指名': 'named'}

def qorder(q):
    g = {'重点': 0, '比較用': 1, 'トヨタ指名': 2}[q['group']]
    m = re.match(r'([A-Z]+)(\d+)', q['id'])
    pre = {'A': 0, 'I': 1, 'C': 2, 'X': 3, 'B': 4, 'T': 5}.get(m.group(1), 9)
    return (g, pre, int(m.group(2)))

QUESTIONS = []
for p in sorted(P, key=qorder):
    QUESTIONS.append({
        'id': p['id'], 'g': GROUP_KEY[p['group']], 'named': bool(p['named']),
        'stage': p.get('stage'), 'theme': p.get('theme') or '', 'kw': p['kw'], 'chat': p['chat'],
        'vol': VOL.get(p['kw']),
        'media': STAGE_MEDIA.get(p.get('stage')) if p['group'] == '重点' else None,
    })

G = {
    'focus31': [q['id'] for q in QUESTIONS if q['g'] == 'focus' and not q['named']],
    'focus34': [q['id'] for q in QUESTIONS if q['g'] == 'focus'],
    'comp30': [q['id'] for q in QUESTIONS if q['g'] == 'comp'],
    'named20': [q['id'] for q in QUESTIONS if q['g'] == 'named'],
}
G['nonnamed61'] = G['focus31'] + G['comp30']
G['named23'] = [q['id'] for q in QUESTIONS if q['named']]
for st in ['Ask', 'Interest', 'Confirm', 'Action']:
    G['st_' + st] = [q for q in G['focus31'] if PI[q]['stage'] == st]
for m in ['livedoor', 'bestcar', 'goonet_mag']:
    G['m_' + m] = [q['id'] for q in QUESTIONS if q['media'] == m]          # 担当10問（名前入りを含む）
    G['m31_' + m] = [q for q in G['m_' + m] if not PI[q]['named']]        # 率の計算（名前入りを除く）

# ------------------------------------------------------------------ 25年度の記事と今年度の記事
ART25 = [
    # No, 媒体, 公開日, タイトル（先頭）, 25年度PV, 既知のURL（参考元に出たもの）
    (1, 'グーネットマガジン', '2026-02-06', '安心の中古車選び！中古車もトヨタのお店がおすすめな３つ…', None, 'goo-net.com/magazine/contents/purchase/271840'),
    (2, 'グーネットマガジン', '2026-02-17', '隅々までこだわった点検整備で“状態が見える”。中古車も…', None, None),
    (3, 'グーネットマガジン', '2026-02-19', 'アフターサービスの充実ぶりも嬉しい！中古車もトヨタのお…', None, None),
    (4, 'グーネットマガジン', '2026-02-24', 'ハイブリッドの中古車もやっぱりトヨタのお店で！在庫が豊…', None, None),
    (5, 'グーネットマガジン', '2026-02-27', '自宅にいながら相談や注文も！トヨタの中古車はオンライン…', None, None),
    (6, '車選びドットコム', '2026-03-18', '初めてのクルマは信頼と安心のトヨタの中古車がおすすめ', None, 'kurumaerabi.com/magazine/articles/1215'),
    (7, '車選びドットコム', '2026-03-23', 'ハイブリッド保証で安心感UP！中古車もトヨタのお店で', None, 'kurumaerabi.com/magazine/articles/1216'),
    (8, '車選びドットコム', '2026-03-25', '中古車もトヨタのお店で｜トヨタ中古車のオンライン購入サ…', None, None),
    (9, 'MOBY', '2026-03-30', '『中古車もトヨタのお店で』。「トヨタの中古車」ならば、…', None, None),
    (10, 'MOBY', '2026-03-30', '中古車もオンラインで購入する時代へ。トヨタならではの信…', None, None),
    (11, 'MOBY', '2026-03-31', '中古ハイブリッドカーを買う前に知っておくべき3つの基準…', None, None),
    (12, 'Motor-Fan', '2026-03-30', '【第1回】中古車選びもトヨタのお店にお任せ！安心できる…', None, None),
    (13, 'Motor-Fan', '2026-03-30', '【第2回】「中古車もトヨタのお店で」パイオニアならでは…', None, None),
    (14, 'Motor-Fan', '2026-03-31', '【第3回】「中古車もトヨタのお店で」。利便性と安心を兼…', None, None),
    (15, 'Car Watch', '2026-03-24', '中古車選びもトヨタのお店にお任せ！購入からアフターサー…', None, None),
    (16, 'Car Watch', '2026-03-25', '中古ハイブリッド車もトヨタのお店で！専用診断や保証など…', None, None),
    (17, 'Car Watch', '2026-03-26', '中古車もトヨタのお店で！トヨタ中古車の新しい買い方「オ…', None, 'car.watch.impress.co.jp/docs/topic/special/2088508'),
    (18, 'CAMP HACK', '2026-03-30', '予算内で“納得して選べる一台”を。タフに走るキャンパー…', None, None),
    (19, '男の隠れ家', '2026-03-31', '【男の道具選び】趣味を深く、遠くへ。トヨタのお店で選ぶ…', None, None),
]
ART25_DOMAINS = ['goo-net.com', 'kurumaerabi.com', 'car-moby.jp', 'motor-fan.jp', 'car.watch.impress.co.jp', 'camp-hack.jp', 'otokonokakurega.com']

MEDIA_DOM25 = {'グーネットマガジン': 'goo-net.com', '車選びドットコム': 'kurumaerabi.com', 'MOBY': 'car-moby.jp', 'Motor-Fan': 'motor-fan.jp',
               'Car Watch': 'car.watch.impress.co.jp', 'CAMP HACK': 'camp-hack.jp', '男の隠れ家': 'otokonokakurega.com'}
_P = r'[\s　！!？?。、・｜|「」『』【】“”"…]'
def art25_hits(cits):
    """その回答で参考元に出た25年度の記事の番号（集合）。既知のURLは完全一致、それ以外は媒体のドメイン＋タイトル先頭14文字で照合"""
    out = set()
    for c in cits or []:
        u = (c.get('url') or '').lower()
        t = re.sub(_P, '', c.get('title') or '')
        h = host(u)
        for no, media, d, title, pv, url in ART25:
            if url:
                if url in u:
                    out.add(no)
                continue
            dom = MEDIA_DOM25.get(media)
            key = re.sub(_P, '', title)[:14]
            if dom and h.endswith(dom) and len(key) >= 10 and key in t:
                out.add(no)
    return out

# 今年度のタイアップ記事（掲載後にURLを登録する。登録すると記事引用率が自動で入る）
ARTICLES = [
    {'media': 'livedoor', 'kind': 'WEB記事', 'title': '（企画中）', 'url': None, 'date': None},
    {'media': 'livedoor', 'kind': '動画（X含む）', 'title': '（企画中）', 'url': None, 'date': None},
    {'media': 'bestcar', 'kind': 'WEB記事①', 'title': '（企画中）', 'url': None, 'date': None},
    {'media': 'bestcar', 'kind': 'WEB記事②', 'title': '（企画中）', 'url': None, 'date': None},
    {'media': 'bestcar', 'kind': 'YouTube', 'title': '（企画中）', 'url': None, 'date': None},
    {'media': 'bestcar', 'kind': 'ショート動画', 'title': '（企画中）', 'url': None, 'date': None},
    {'media': 'goonet_mag', 'kind': 'WEB記事', 'title': '（企画中）', 'url': None, 'date': None},
    {'media': 'goonet_mag', 'kind': 'ショート動画①', 'title': '（企画中）', 'url': None, 'date': None},
    {'media': 'goonet_mag', 'kind': 'ショート動画②', 'title': '（企画中）', 'url': None, 'date': None},
]
ART_URLS = [a['url'].lower() for a in ARTICLES if a['url']]

# ------------------------------------------------------------------ 計測回
def load(files):
    rows = []
    for f in files:
        rows += json.load(open(U / f, encoding='utf-8'))
    return rows

def valid(r):
    if not (r.get('text') or '').strip():
        return False
    if r['surface'] == 'aio' and r.get('has_ai') is False:
        return False
    return True

KNOWN = {'responses_2026-10-19T1539.json', 'responses_2026-10-19T1602.json', 'responses_2026-10-19T1632.json',
         'responses_2026-10-26T0832.json', 'responses_2026-10-21T0907.json'}
ROUNDS = [
    {'id': 'R1', 'label': '掲載前①', 'date': '2026-10-19', 'runs': 3,
     'rows': [r for r in load(['responses_2026-10-19T1539.json', 'responses_2026-10-19T1632.json']) if r['surface'] != 'gemini']
             + load(['responses_2026-10-19T1602.json'])},
    {'id': 'R2', 'label': '掲載前②', 'date': '2026-10-26', 'runs': 3, 'rows': load(['responses_2026-10-26T0832.json'])},
]
DAILY = [{'id': 'D1', 'label': '日ごとの確認', 'date': '2026-10-21', 'runs': 1, 'rows': load(['responses_2026-10-21T0907.json'])}]
# 新しい計測（掲載後など）：同じ日のファイルをまとめ、同じ問・AI・回は新しいファイルの値を使う。3回以上なら「回」、1回なら「日ごとの確認」
CFG = json.load(open(Path(__file__).parent / 'rounds.json', encoding='utf-8')) if (Path(__file__).parent / 'rounds.json').exists() else {}
PUB = CFG.get('publish_start')   # 最初の記事の掲載日（決まったら rounds.json に書く）
_by_date = collections.defaultdict(list)
for f in sorted(U.glob('responses_*.json')):
    if f.name in KNOWN:
        continue
    d = f.name[len('responses_'):len('responses_') + 10]
    if d > '2026-10-26':
        _by_date[d].append(f.name)
_npre, _npost = len(ROUNDS), 0
for d, files in sorted(_by_date.items()):
    best = {}
    for fn in files:
        for r in json.load(open(U / fn, encoding='utf-8')):
            best[(r['qid'], r['surface'], r.get('run', 0))] = r
    rows = list(best.values())
    runs = 1 + max((r.get('run', 0) for r in rows), default=0)
    post = bool(PUB and d >= PUB)
    if runs >= 3:
        if post:
            _npost += 1; lab = '掲載後' + '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳'[min(_npost, 20) - 1]
        else:
            _npre += 1; lab = '掲載前' + '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳'[min(_npre, 20) - 1]
        ROUNDS.append({'id': f'R{len(ROUNDS) + 1}', 'label': lab, 'date': d, 'runs': runs, 'rows': rows, 'post': post})
    else:
        DAILY.append({'id': f'D{len(DAILY) + 1}', 'label': '日ごとの確認', 'date': d, 'runs': runs, 'rows': rows, 'post': post})

def enrich(rows):
    out = []
    for r in rows:
        if not valid(r):
            continue
        j = judge(r['text'], r.get('citations'))
        j['art25'] = sorted(art25_hits(r.get('citations')))
        j['art'] = any(any(a in (c.get('url') or '').lower() for a in ART_URLS) for c in (r.get('citations') or [])) if ART_URLS else False
        out.append((r, j))
    return out

def pooled(E, qids, fn):
    res = {}
    qs = set(qids)
    for s in SURF:
        rr = [j for r, j in E if r['surface'] == s and r['qid'] in qs]
        res[s] = round(100 * sum(1 for j in rr if fn(j)) / len(rr), 2) if rr else None
    v = [x for x in res.values() if x is not None]
    res['avg'] = round(sum(v) / len(v), 2) if v else None
    res['n'] = sum(1 for r, j in E if r['qid'] in qs)
    return res

ENTS = ENT  # toyota, goonet, carsensor, honda, nissan, nextage, gulliver, wecars
SUBS = ['nintei', 'light', 'gazoo', 'store', 'online']

def first_share(E, qids):
    qs = set(qids)
    per = {}
    for s in SURF:
        rr = [j for r, j in E if r['surface'] == s and r['qid'] in qs and j['first']]
        cnt = collections.Counter(j['first'] for j in rr)
        per[s] = {e: 100 * cnt[e] / len(rr) for e in ENTS} if rr else None
    ok = [s for s in SURF if per[s]]
    return {e: round(sum(per[s][e] for s in ok) / len(ok), 1) for e in ENTS}

def round_metrics(E):
    M = {}
    for gname in ['focus31', 'focus34', 'comp30', 'named20', 'nonnamed61', 'named23', 'st_Ask', 'st_Interest', 'st_Confirm', 'st_Action',
                  'm31_livedoor', 'm31_bestcar', 'm31_goonet_mag', 'm_livedoor', 'm_bestcar', 'm_goonet_mag']:
        q = G[gname]
        M[gname] = {
            'appear': pooled(E, q, lambda j: j['a']['toyota']),
            'mention': pooled(E, q, lambda j: j['m']['toyota']),
            'cite': pooled(E, q, lambda j: j['c']['toyota']),
            'comp': {e: pooled(E, q, lambda j, e=e: j['a'][e])['avg'] for e in ENTS if e != 'toyota'},
        }
    # 比較表（10/14の形）：非指名61問と指名23問
    tbl = {}
    for gname in ['nonnamed61', 'named23']:
        q = G[gname]
        t = {}
        for e in ENTS + SUBS:
            t[e] = {k: pooled(E, q, lambda j, e=e, k=k: (j[k].get(e, False)))['avg'] for k in ['m', 'c', 'a']}
        t['rec'] = {'m': pooled(E, q, lambda j: j['rec'])['avg'], 'c': 0.0, 'a': pooled(E, q, lambda j: j['rec'])['avg']}
        t['goomag'] = {'m': None, 'c': pooled(E, q, lambda j: j['c']['goomag'])['avg'], 'a': pooled(E, q, lambda j: j['c']['goomag'])['avg']}
        tbl[gname] = t
    M['table'] = tbl
    M['first61'] = first_share(E, G['nonnamed61'])
    # 記事・媒体の引用（重点34問の回答で数える）
    f34 = set(G['focus34'])
    M['article_rate'] = pooled(E, G['focus34'], lambda j: j['art'])
    M['media_cite'] = {m: {
        'focus34': pooled(E, G['focus34'], lambda j, m=m: j['c']['goomag' if m == 'goonet_mag' else m]),
        'own10': pooled(E, G['m_' + m], lambda j, m=m: j['c']['goomag' if m == 'goonet_mag' else m]),
        'all84_count': sum(1 for r, j in E if j['c']['goomag' if m == 'goonet_mag' else m]),
    } for m in ['livedoor', 'bestcar', 'goonet_mag']}
    # 25年度の記事
    c25 = collections.Counter(); s25 = collections.defaultdict(collections.Counter)
    for r, j in E:
        for no in j['art25']:
            c25[no] += 1; s25[no][r['surface']] += 1
    M['art25'] = {str(no): {'n': c25[no], 'by': dict(s25[no])} for no in c25}
    M['art25_answers'] = sum(1 for r, j in E if j['art25'])
    M['n_answers'] = len(E)
    return M

def per_question(E):
    out = {}
    by = collections.defaultdict(list)
    for r, j in E:
        by[(r['qid'], r['surface'])].append(j)
    for q in QUESTIONS:
        d = {}
        for s in SURF:
            js = by.get((q['id'], s), [])
            if not js:
                d[s] = None
                continue
            n = len(js)
            comp = {e: sum(1 for j in js if j['a'][e]) for e in ENTS if e != 'toyota'}
            top = max(comp.items(), key=lambda x: x[1])
            d[s] = {'n': n, 'a': sum(1 for j in js if j['a']['toyota']), 'm': sum(1 for j in js if j['m']['toyota']),
                    'c': sum(1 for j in js if j['c']['toyota']), 'top': top[0] if top[1] else None, 'topn': top[1],
                    'first': collections.Counter(j['first'] for j in js if j['first']).most_common(1)[0][0] if any(j['first'] for j in js) else None}
        out[q['id']] = d
    return out

def samples(E, maxlen=2400):
    """各問×AIの1回目の答え（読む用）。t=答えの文（長いときは先頭 maxlen 字）、len=全体の字数、
    c=参考元（先頭10件：[サイト, 題名, URL]）、n=参考元の数、a/m/k=トヨタのお店が出た（出現／本文の名前／参考元のサイト）、f=最初に名前が出た店"""
    out = {}
    for r, j in E:
        if r['run'] != 0:
            continue
        txt = (r.get('text') or '').strip()
        txt = re.sub(r'\n{3,}', '\n\n', txt)
        cut = len(txt) > maxlen
        cits = []
        seen = set()
        for c in (r.get('citations') or []):
            h = host(c.get('url'))
            if not h or (h, c.get('title')) in seen:
                continue
            seen.add((h, c.get('title')))
            cits.append([h, (c.get('title') or '')[:70], c.get('url') or ''])
            if len(cits) >= 10:
                break
        out.setdefault(r['qid'], {})[r['surface']] = {'t': txt[:maxlen] + ('…' if cut else ''), 'len': len(txt), 'c': cits, 'n': len(r.get('citations') or []),
                                                      'a': 1 if j['a']['toyota'] else 0, 'm': 1 if j['m']['toyota'] else 0, 'k': 1 if j['c']['toyota'] else 0, 'f': j['first']}
    return out

data = {'generated_at': datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d %H:%M'),
        'questions': QUESTIONS, 'groups': {k: v for k, v in G.items()}, 'rounds': [], 'daily': []}
for rd in ROUNDS:
    E = enrich(rd['rows'])
    data['rounds'].append({'id': rd['id'], 'label': rd['label'], 'date': rd['date'], 'runs': rd['runs'], 'post': rd.get('post', False),
                           'm': round_metrics(E), 'q': per_question(E)})
    if rd['id'] == ROUNDS[-1]['id']:
        data['samples'] = samples(E)
        data['samples_round'] = rd['label'] + '（' + rd['date'] + '）'
for rd in DAILY:
    E = enrich(rd['rows'])
    m = round_metrics(E)
    data['daily'].append({'id': rd['id'], 'label': rd['label'], 'date': rd['date'], 'post': rd.get('post', False), 'focus31': m['focus31']['appear'], 'comp30': m['comp30']['appear']})
data['art25'] = [{'no': a[0], 'media': a[1], 'date': a[2], 'title': a[3]} for a in ART25]
data['articles'] = ARTICLES

# ------------------------------------------------------------------ 1,761本（10/19）
SP = yaml.safe_load(open(R / 'config/ucar_signal_prompts.yaml', encoding='utf-8'))['prompts']
SPI = {p['id']: p for p in SP}
exec(open(Path(__file__).parent / 'wide_names.py', encoding='utf-8').read())  # OTHER, other_named
SV = json.load(open(R / 'data/ucar_signal/volumes_2026-10-19.json'))
SV = SV.get('volumes', SV)
wrows = json.load(open(R / 'data/ucar_signal/responses_2026-10-19T2250.json', encoding='utf-8'))
WE = [(r, judge(r['text'], r.get('citations'))) for r in wrows if valid(r)]
def wclass(p):
    if p['named']:
        return 'toyota'
    return 'other' if other_named(p['kw']) else 'general'
WCL = {p['id']: wclass(p) for p in SP}
GEN = {q for q, c in WCL.items() if c == 'general'}
CAT_JA = {'車種指名': '車種名', '用途・ライフステージ': '用途', '新車 vs 中古': '新車 vs 中古', '地域・店舗': '地域・店舗', '売却・乗り換え': '売却',
          '予算帯': '予算帯', '品質・保証': '品質・保証', '手続き・費用': '手続き・費用', '年式・走行距離': '年式・距離', '相場・値ごろ': '相場・値ごろ',
          'どこで買うか': 'どこで買う', '買い方（EC・オンライン）': '買い方'}
cat_n = collections.Counter(SPI[q]['kubun'] for q in GEN)

def wrate(qset, fn, s):
    rr = [(r, j) for r, j in WE if r['surface'] == s and r['qid'] in qset]
    if not rr:
        return None
    if s in ('aio', 'aimode'):
        return 100 * sum(1 for r, j in rr if fn(j)) / len(rr)
    by = collections.defaultdict(list)
    for r, j in rr:
        by[SPI[r['qid']]['kubun']].append(1 if fn(j) else 0)
    w = collections.Counter(SPI[q]['kubun'] for q in qset)
    num = sum(w[c] * sum(v) / len(v) for c, v in by.items())
    den = sum(w[c] for c in by)
    return 100 * num / den

def wavg(qset, fn):
    v = {s: wrate(qset, fn, s) for s in SURF}
    ok = [x for x in v.values() if x is not None]
    v['avg'] = sum(ok) / len(ok) if ok else None
    return {k: (round(x, 1) if x is not None else None) for k, x in v.items()}

wide = {'n': len(SP), 'n_general': len(GEN), 'n_toyota': sum(1 for c in WCL.values() if c == 'toyota'),
        'n_other': sum(1 for c in WCL.values() if c == 'other'), 'date': '2026-10-19'}
wide['general'] = {e: wavg(GEN, lambda j, e=e: j['a'][e]) for e in ENTS}
wide['toyota_named'] = wavg({q for q, c in WCL.items() if c == 'toyota'}, lambda j: j['a']['toyota'])
wide['other_named'] = wavg({q for q, c in WCL.items() if c == 'other'}, lambda j: j['a']['toyota'])
# 検索数で重みをつけた値（AIO・AI Mode は全本、ChatGPT・Gemini は抜き取り）
def vol_weighted():
    tot = {}
    for s in SURF:
        rr = [(r, j) for r, j in WE if r['surface'] == s and r['qid'] in GEN]
        num = sum((SV.get(SPI[r['qid']]['kw']) or 0) * (1 if j['a']['toyota'] else 0) for r, j in rr)
        den = sum((SV.get(SPI[r['qid']]['kw']) or 0) for r, j in rr)
        tot[s] = 100 * num / den if den else None
    ok = [x for x in tot.values() if x is not None]
    return round(sum(ok) / len(ok), 1)

# 第一想起（一般の語）
def wfirst(qset):
    per = {}
    for s in SURF:
        rr = [j for r, j in WE if r['surface'] == s and r['qid'] in qset and j['first']]
        cnt = collections.Counter(j['first'] for j in rr)
        per[s] = {e: 100 * cnt[e] / len(rr) for e in ENTS} if rr else None
    ok = [s for s in SURF if per[s]]
    return {e: round(sum(per[s][e] for s in ok) / len(ok), 1) for e in ENTS}
wide['first'] = wfirst(GEN)
cats = []
for k, ja in CAT_JA.items():
    qs = {q for q in GEN if SPI[q]['kubun'] == k}
    allq = [p for p in SP if p['kubun'] == k]
    ent = {e: wavg(qs, lambda j, e=e: j['a'][e])['avg'] for e in ENTS}
    comp = {e: v for e, v in ent.items() if e != 'toyota' and v is not None}
    top = max(comp.items(), key=lambda x: x[1]) if comp else (None, None)
    vol = sum((SV.get(p['kw']) or 0) for p in allq if p['id'] in GEN)
    aio_shown = [r for r in wrows if r['surface'] == 'aio' and SPI[r['qid']]['kubun'] == k]
    shown = 100 * sum(1 for r in aio_shown if r.get('has_ai') is not False and (r.get('text') or '').strip()) / len(aio_shown) if aio_shown else None
    media = {}
    for m, key in [('livedoor', 'livedoor'), ('bestcar', 'bestcar'), ('goonet_mag', 'goomag')]:
        rr = [j for r, j in WE if SPI[r['qid']]['kubun'] == k]
        media[m] = round(100 * sum(1 for j in rr if j['c'][key]) / len(rr), 1) if rr else None
    fr = wfirst(qs)['toyota'] if qs else None
    by_ai = wavg(qs, lambda j: j['a']['toyota'])
    cats.append({'cat': ja, 'n': len(allq), 'n_general': len(qs), 'vol': vol, 'toyota': ent['toyota'], 'top': top[0], 'top_v': top[1],
                 'first': fr, 'aio_shown': round(shown) if shown is not None else None, 'media': media, 'by_ai': by_ai})
tv = sum(c['vol'] for c in cats)
for c in cats:
    c['vol_share'] = round(100 * c['vol'] / tv, 1) if tv else None
wide['cats'] = sorted(cats, key=lambda c: -c['vol'])
# トヨタのお店が どのAIでも出ない一般の語（検索数順）
by_q = collections.defaultdict(list)
for r, j in WE:
    by_q[r['qid']].append((r['surface'], j))
miss = []
for q in GEN:
    lst = by_q.get(q, [])
    if lst and not any(j['a']['toyota'] for s, j in lst):
        firsts = collections.Counter(j['first'] for s, j in lst if j['first'])
        miss.append({'kw': SPI[q]['kw'], 'cat': CAT_JA.get(SPI[q]['kubun'], SPI[q]['kubun']), 'vol': SV.get(SPI[q]['kw']) or 0,
                     'ais': len(lst), 'first': firsts.most_common(1)[0][0] if firsts else None})
miss.sort(key=lambda x: -x['vol'])
wide['miss_n'] = len(miss)
wide['miss_vol'] = sum(m['vol'] for m in miss)
wide['miss_top'] = miss[:40]
wide['media_total'] = {m: sum(1 for r, j in WE if j['c'][key]) for m, key in [('livedoor', 'livedoor'), ('bestcar', 'bestcar'), ('goonet_mag', 'goomag')]}
wide['answers'] = len(WE)
data['wide'] = wide

# ------------------------------------------------------------------ GA4（toyota.jp）
GA = R / 'data' / 'ga4'
def rcsv(p):
    with open(p, encoding='utf-8') as f:
        return list(csv.DictReader(f))
mon = rcsv(GA / 'toyota_jp_ga4_monthly.csv')
ai = rcsv(GA / 'ai_referrals_daily.csv')
ga = {'source': 'GA4実測（Toyota.jp【本格移行用】- GA4）', 'until': ai[-1]['date']}
ga['monthly_sessions'] = [{'ym': r['year_month'], 's': int(float(r['sessions'])), 'partial': r.get('partial_until') or ''} for r in mon]
aim = collections.defaultdict(lambda: collections.Counter())
for r in ai:
    ym = r['date'][:7]
    for k in ['chatgpt', 'gemini', 'copilot', 'perplexity', 'claude', 'grok', 'deepseek', 'doubao', 'other_ai']:
        aim[ym][k] += int(float(r.get(k) or 0))
ga['ai_monthly'] = [{'ym': ym, **dict(c), 'total': sum(c.values())} for ym, c in sorted(aim.items())]
ga['ai_daily'] = [{'d': r['date'], 't': int(float(r['total'])), 'g': int(float(r['chatgpt']))} for r in ai[-120:]]
# 中古車関連ページ（toyota.jp 側）と U-Car からの流れ（10/26 取得分）
gu = json.load(open(U / 'ga4_ucar_2026-10-26.json', encoding='utf-8'))
pd = collections.defaultdict(int)
grp = collections.defaultdict(lambda: collections.defaultdict(int))
def pgroup(p):
    if p.startswith('/service/estimate/ucar'):
        return '中古車の見積り（toyota.jp）'
    if '/ucar/support' in p:
        return 'U-Car サポート'
    if p.startswith('/information/ucar'):
        return '中古車の案内ページ'
    return 'その他の中古車関連'
for r in gu['pages_daily_90']['rows']:
    pd[r['date']] += int(r['sessions'])
    grp[pgroup(r['page_path'])][r['date']] += int(r['sessions'])
ga['ucar_pages_daily'] = [{'d': d, 's': s} for d, s in sorted(pd.items())]
ga['ucar_pages_groups'] = {g: sum(v.values()) for g, v in grp.items()}
fu = collections.defaultdict(int)
for r in gu['from_ucar_daily_90']['rows']:
    fu[r['date']] += int(r['sessions'])
ga['from_ucar_daily'] = [{'d': d, 's': s} for d, s in sorted(fu.items())]
ga['range90'] = gu['range90']
lc = collections.defaultdict(lambda: [0, 0])
for r in gu['landing_conv1_28']['rows']:
    g = pgroup(r['landing_page'])
    lc[g][0] += int(r['sessions']); lc[g][1] += int(r.get('conversions') or 0)
ga['landing28'] = {g: {'s': v[0], 'cv': v[1]} for g, v in lc.items()}
ga['range28'] = gu['range28']
aiu = collections.Counter()
for r in gu['site_ai_pages_90']['rows']:
    if any(k in r['page_path'] for k in ['ucar', 'u-car', '/usedcar']):
        aiu[pgroup(r['page_path'])] += int(r['sessions'])
ga['ai_to_ucar_pages_90'] = dict(aiu)
data['ga4'] = ga

# ------------------------------------------------------------------ 参考元のURLの索引（画面「2-4 記事のURLで探す」）
import cindex
data['cix'] = cindex.build(
    [(rd['id'], rd['date'], rd['label'], rd.get('post', False), rd['runs'], rd['rows']) for rd in ROUNDS],
    [(rd['id'], rd['date'], rd['label'], rd.get('post', False), rd['runs'], rd['rows']) for rd in DAILY],
    ('W1', wide['date'], '検索1,761本', wrows, SP, SV),
    {q['id']: i for i, q in enumerate(QUESTIONS)}, valid, judge, ART25, art25_hits)

out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / 'board_data.json'
json.dump(data, open(out, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('wrote', out, out.stat().st_size)
