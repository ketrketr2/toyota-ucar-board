# -*- coding: utf-8 -*-
"""ボード用の追加データ（board_extra.json）。
board_data.json と同じ元データ・同じ判定（classify.py）から作る。
  flow   : 名前を含まない61問の答え1件ずつの行き先（キービジュアル）
  cites  : 参考元に出たサイトの顔ぶれ（61問の答え）
  wideq  : 1,761本のうち一般の語1,417本の1本ずつの結果
  ga4x   : toyota.jp 全体と中古車関連ページの比率（全体との比較）
"""
import json, sys, collections, csv, re
from pathlib import Path

B = Path(__file__).resolve().parent
sys.path.insert(0, str(B))
import yaml
from classify import judge, host, ENT, cite_flags, is_dealer, norm

R = B.parent / 'toyota-geo-board'
U = R / 'data' / 'ucar'
GA = R / 'data' / 'ga4'
SURF = ['aio', 'aimode', 'chatgpt', 'gemini']
D = json.load(open(sys.argv[1] if len(sys.argv) > 1 else B.parent / 'build' / 'board_data.json', encoding='utf-8'))
G = D['groups']
QI = {q['id']: i for i, q in enumerate(D['questions'])}


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


ROUNDS = [
    [r for r in load(['responses_2026-10-19T1539.json', 'responses_2026-10-19T1632.json']) if r['surface'] != 'gemini']
    + load(['responses_2026-10-19T1602.json']),
    load(['responses_2026-10-26T0832.json']),
]
# 掲載前②より後の計測（掲載後など）：board_data.json と同じ決まりで「回」を見つけ、同じ順に並べる（3回以上聞いた日だけ）
KNOWN = {'responses_2026-10-19T1539.json', 'responses_2026-10-19T1602.json', 'responses_2026-10-19T1632.json',
         'responses_2026-10-26T0832.json', 'responses_2026-10-21T0907.json'}
_by_date = collections.defaultdict(list)
for _f in sorted(U.glob('responses_*.json')):
    _d = _f.name[len('responses_'):len('responses_') + 10]
    if _f.name not in KNOWN and _d > '2026-10-26':
        _by_date[_d].append(_f.name)
_extra = []
for _d, _files in sorted(_by_date.items()):
    _best = {}
    for _fn in _files:
        for _r in json.load(open(U / _fn, encoding='utf-8')):
            _best[(_r['qid'], _r['surface'], _r.get('run', 0))] = _r
    _rows = list(_best.values())
    if 1 + max((_r.get('run', 0) for _r in _rows), default=0) >= 3:
        _extra.append((_d, _rows))
if [d for d, _ in _extra] == [r['date'] for r in D['rounds'][2:]]:
    ROUNDS += [rows for _, rows in _extra]
else:
    print('注意：掲載前②より後の回が board_data.json と合わないため、行き先の図には入れません', [d for d, _ in _extra], [r['date'] for r in D['rounds'][2:]])

# ------------------------------------------------------------------ flow：答え1件ずつの行き先
DEST = ['toyota', 'carsensor', 'goonet', 'nextage', 'gulliver', 'other', 'none']
NN = set(G['nonnamed61'])
CITE_HOST = [('carsensor.net', 1), ('goo-net.com', 2), ('nextage.jp', 3), ('221616.com', 4)]


def cite_dest(cits):
    """参考元の並び順で、最初に出た他社（4社）のサイト。4社がなく参考元があれば「ほか」、参考元がなければ「なし」"""
    if not cits:
        return 6
    for c in cits:
        h = host(c.get('url')) or (c.get('domain') or '').lower().removeprefix('www.')
        for suf, i in CITE_HOST:
            if h.endswith(suf):
                return i
    return 5
flow = []
cite_rows = []
for ri, rows in enumerate(ROUNDS):
    for r in rows:
        if r['qid'] not in NN or not valid(r):
            continue
        j = judge(r['text'], r.get('citations'))
        if j['a']['toyota']:
            d = 0
        elif j['first']:
            d = DEST.index(j['first']) if j['first'] in DEST else 5
        else:
            d = 6
        f = j['first']
        fc = 6 if not f else (DEST.index(f) if f in DEST else 5)
        # 言及：本文にトヨタのお店の名前が出たか。出ないときは本文で最初に名前が出た店
        dm = 0 if j['m']['toyota'] else fc
        # 引用：参考元にトヨタのサイトが出たか。出ないときは参考元で最初に出た他社のサイト（他社がなければ、ほかのサイト・参考元なし）
        dc = 0 if j['c']['toyota'] else cite_dest(r.get('citations'))
        flow.append([ri, SURF.index(r['surface']), QI[r['qid']], d, r.get('run', 0), fc, dm, dc])
        cite_rows.append((ri, r))

# ------------------------------------------------------------------ cites：参考元の顔ぶれ
NAME = {
    'goo-net.com': 'グーネット', 'carsensor.net': 'カーセンサー', 'nextage.jp': 'ネクステージ', '221616.com': 'ガリバー',
    'youtube.com': 'YouTube', 'toyota.jp': 'トヨタ（toyota.jp）', 'kakaku.com': '価格.com', 'kurumaerabi.com': '車選びドットコム',
    'aftc.or.jp': '自動車公正取引協議会', 'hanamaru870.net': 'はなまる', 'carseven.co.jp': 'カーセブン',
    'detail.chiebukuro.yahoo.co.jp': 'Yahoo!知恵袋', 'autoc-one.jp': 'オートックワン', 'gazoo.com': 'GAZOO',
    'ucar.carview.yahoo.co.jp': 'carview! 中古車', 'carview.yahoo.co.jp': 'carview!', 'kokusen.go.jp': '国民生活センター',
    'jucda.or.jp': '日本中古自動車販売協会連合会', 'navikuru.jp': 'ナビクル', 'google.com': 'Google', 'caniva.jp': 'カニバ',
    'life.oricon.co.jp': 'オリコン顧客満足度', 'insweb.co.jp': 'インズウェブ', 'u-car.nissan.co.jp': '日産 U-Cars',
    'mlit.go.jp': '国土交通省', 'bestcarweb.jp': 'ベストカーWeb', 'motor-fan.jp': 'Motor-Fan', 'note.com': 'note',
    'tiktok.com': 'TikTok', 'orixcar.jp': 'オリックス中古車', 'jaf.or.jp': 'JAF', 'honda.co.jp': 'Honda',
    'toyota-outlet.gazoo.com': 'トヨタ中古車オンラインストア', 'manual.toyota.jp': 'トヨタ（取扱説明書）',
    'global.toyota': 'トヨタ（企業サイト）', 'wecars.co.jp': 'WECARS', 'car-moby.jp': 'MOBY', 'kinto-jp.com': 'KINTO',
}
MAKER = ['nissan', 'honda', 'daihatsu', 'suzuki', 'mazda', 'subaru', 'mitsubishi', 'lexus', 'yanase', 'bmw', 'audi', 'mercedes', 'volkswagen', 'kia', 'hyundai', 'isuzu']
CHAIN = ['nextage.jp', '221616.com', 'carseven.co.jp', 'hanamaru870.net', 'wecars.co.jp', 'orixcar.jp', 'atm-car.co.jp', 'carmo-kun.jp',
         'goodspeed.ne.jp', 'buddica.direct', 'ucarpac.com', 'flexnet.co.jp', 'applenet.co.jp', 'activecollection.co.jp', 'carnext.jp',
         'kuruma-terrace.com', 'keinomori.com', 'kurumanomori.com', 'life-cars.com', 'ekuruma.co.jp', 'cars-enjoy.com', 'car-premium.net',
         'bande-gi.co.jp', 'blog.cartown.jp', 'mobilico.jp', 'ah.j-carnet.co.jp', 'car-byebuy.com', 'idom.co.jp', 'big-motor.co.jp', 'carchs.com']
PORTAL = ['goo-net.com', 'carsensor.net', 'carview.yahoo.co.jp', 'kakaku.com', 'kurumaerabi.com', 'kurumaerabi.co.jp', 'autoc-one.jp',
          'car-me.jp', 'navikuru.jp', 'car-match.jp', 'chukosha-data.jp', 'resalevalue.jp']
SNS = ['youtube.com', 'tiktok.com', 'x.com', 'twitter.com', 'instagram.com', 'chiebukuro.yahoo.co.jp', 'note.com', 'bbs.kakaku.com',
       'ameblo.jp', 'hatenablog.com', 'facebook.com', 'reddit.com', 'google.com']
CAT = ['toyota', 'portal', 'chain', 'maker', 'public', 'sns', 'media']
CAT_JA = {'toyota': 'トヨタのサイト', 'portal': '中古車の検索サイト', 'chain': '大手の販売・買取店', 'maker': 'ほかのメーカー・販売店',
          'public': '公的機関・業界団体', 'sns': '動画・SNS・Q&A', 'media': '記事・情報サイトほか'}


def ends(h, lst):
    return any(h == x or h.endswith('.' + x) for x in lst)


def ccat(h, url):
    if cite_flags([{'url': url}])['toyota'] or h.endswith('toyota.jp') or h.endswith('gazoo.com') or h == 'global.toyota':
        return 'toyota'
    if ends(h, SNS):
        return 'sns'
    if ends(h, PORTAL):
        return 'portal'
    if ends(h, CHAIN):
        return 'chain'
    if any(m in h for m in MAKER):
        return 'maker'
    if h.endswith('.go.jp') or h.endswith('.lg.jp') or h.endswith('.or.jp'):
        return 'public'
    return 'media'


def shown_host(h):
    for k in ['detail.chiebukuro.yahoo.co.jp', 'ucar.carview.yahoo.co.jp', 'carview.yahoo.co.jp', 'bbs.kakaku.com']:
        if h == k or h.endswith('.' + k):
            return k
    if h.endswith('mlit.go.jp'):
        return 'mlit.go.jp'
    if h.endswith('goo-net.com'):
        return 'goo-net.com'
    if h.endswith('carsensor.net'):
        return 'carsensor.net'
    if h.endswith('kakaku.com'):
        return 'kakaku.com'
    return h


def puny(h):
    try:
        return h.encode('ascii').decode('idna') if 'xn--' in h else h
    except Exception:
        return h


cnt = collections.Counter()
by = collections.defaultdict(lambda: [0, 0, 0, 0])
hcat = {}
cat_by = {c: [0, 0, 0, 0] for c in CAT}
n_by = [0, 0, 0, 0]
nocite_by = [0, 0, 0, 0]
media_mag = [0, 0, 0, 0]   # グーネットマガジン（goo-net.com/magazine）
for ri, r in cite_rows:
    si = SURF.index(r['surface'])
    n_by[si] += 1
    hs = {}
    for c in r.get('citations') or []:
        u = c.get('url') or ''
        h = host(u) or (c.get('domain') or '').lower().removeprefix('www.')
        if not h:
            continue
        sh = shown_host(h)
        hs[sh] = ccat(h, u)
        if 'goo-net.com/magazine' in u.lower():
            hs['__mag'] = 'x'
    if not [k for k in hs if k != '__mag']:
        nocite_by[si] += 1
    if '__mag' in hs:
        media_mag[si] += 1
        hs.pop('__mag')
    cats_here = set()
    for sh, cc in hs.items():
        cnt[sh] += 1
        by[sh][si] += 1
        hcat[sh] = cc
        cats_here.add(cc)
    for cc in cats_here:
        cat_by[cc][si] += 1
top = []
for h, n in cnt.most_common(40):
    top.append({'h': puny(h), 'name': NAME.get(h, ''), 'cat': hcat[h], 'n': n, 'by': by[h]})
cites = {'n_answers': len(cite_rows), 'n_by': n_by, 'nocite_by': nocite_by, 'top': top,
         'cat_by': cat_by, 'cat_ja': CAT_JA, 'cat_order': CAT, 'mag_by': media_mag, 'hosts': len(cnt)}

# ------------------------------------------------------------------ wideq：1,417本の1本ずつ
SP = yaml.safe_load(open(R / 'config/ucar_signal_prompts.yaml', encoding='utf-8'))['prompts']
SPI = {p['id']: p for p in SP}
exec(open(B / 'wide_names.py', encoding='utf-8').read())  # other_named
SV = json.load(open(R / 'data/ucar_signal/volumes_2026-10-19.json'))
SV = SV.get('volumes', SV)
wrows = json.load(open(R / 'data/ucar_signal/responses_2026-10-19T2250.json', encoding='utf-8'))
CAT_W = {'車種指名': '車種名', '用途・ライフステージ': '用途', '新車 vs 中古': '新車 vs 中古', '地域・店舗': '地域・店舗', '売却・乗り換え': '売却',
         '予算帯': '予算帯', '品質・保証': '品質・保証', '手続き・費用': '手続き・費用', '年式・走行距離': '年式・距離', '相場・値ごろ': '相場・値ごろ',
         'どこで買うか': 'どこで買う', '買い方（EC・オンライン）': '買い方'}
CAT_ORDER = [c['cat'] for c in D['wide']['cats']]


def wclass(p):
    if p['named']:
        return 'toyota'
    return 'other' if other_named(p['kw']) else 'general'


WCL = {p['id']: wclass(p) for p in SP}
GEN = {q for q, c in WCL.items() if c == 'general'}
per = collections.defaultdict(dict)
WE = []
for r in wrows:
    if r['qid'] not in SPI:
        continue
    if r['surface'] == 'aio' and (r.get('has_ai') is False or not (r.get('text') or '').strip()):
        per[r['qid']][r['surface']] = None   # 要約が出なかった
        continue
    if not valid(r):
        continue
    j = judge(r['text'], r.get('citations'))
    WE.append((r, j))
    per[r['qid']][r['surface']] = j


def wrate(qset, fn, s):
    rr = [(r, j) for r, j in WE if r['surface'] == s and r['qid'] in qset]
    if not rr:
        return None
    if s in ('aio', 'aimode'):
        return 100 * sum(1 for r, j in rr if fn(j)) / len(rr)
    byk = collections.defaultdict(list)
    for r, j in rr:
        byk[SPI[r['qid']]['kubun']].append(1 if fn(j) else 0)
    w = collections.Counter(SPI[q]['kubun'] for q in qset)
    num = sum(w[c] * sum(v) / len(v) for c, v in byk.items())
    den = sum(w[c] for c in byk)
    return 100 * num / den


def wavg(qset, fn):
    v = {s: wrate(qset, fn, s) for s in SURF}
    ok = [x for x in v.values() if x is not None]
    v['avg'] = sum(ok) / len(ok) if ok else None
    return {k: (round(x, 2) if x is not None else None) for k, x in v.items()}


wide_rates = {k: wavg(GEN, (lambda j, k=k: j[k]['toyota'])) for k in ['a', 'm', 'c']}
wide_rates['first'] = None
FE = ['toyota', 'carsensor', 'goonet', 'nextage', 'gulliver']
wq = []
for q in sorted(GEN, key=lambda q: -(SV.get(SPI[q]['kw']) or 0)):
    p = SPI[q]
    code = ''
    firsts = collections.Counter()
    for s in SURF:
        if s not in per[q]:
            code += '-'          # 測っていない（ChatGPT・Geminiは抜き取り）
        elif per[q][s] is None:
            code += 'x'          # AI Overviews の要約が出なかった
        else:
            j = per[q][s]
            code += '1' if j['a']['toyota'] else '0'
            if j['first']:
                firsts[j['first']] += 1
    f = firsts.most_common(1)[0][0] if firsts else None
    wq.append([p['kw'], CAT_ORDER.index(CAT_W.get(p['kubun'], p['kubun'])), SV.get(p['kw']) or 0, code,
               FE.index(f) if f in FE else (5 if f else 6)])
wideq = {'rows': wq, 'cats': CAT_ORDER, 'rates': wide_rates, 'first_codes': FE + ['other', 'none']}

# 1,761本の答えの例（総覧の「中古車の検索全体」の例で読む）：カテゴリごとに検索数が最も多い語＋主な車名の語
_bycat = collections.defaultdict(list)
for _r in wq:
    _bycat[_r[1]].append(_r)
WS_KW = [sorted(_bycat[_c], key=lambda r: -r[2])[0][0] for _c in range(len(CAT_ORDER)) if _bycat.get(_c)]
for _kw in ['シエンタ 中古', 'ヴォクシー 中古', 'ライズ 中古']:
    if _kw not in WS_KW:
        WS_KW.append(_kw)
_kw2q = {SPI[q]['kw']: q for q in GEN}
_wsamp = {}
for _kw in WS_KW:
    _q = _kw2q.get(_kw)
    if not _q:
        continue
    _ent = {}
    for r in wrows:
        if r['qid'] != _q or not (r.get('text') or '').strip():
            continue
        if r['surface'] == 'aio' and r.get('has_ai') is False:
            continue
        j = judge(r['text'], r.get('citations'))
        _t = re.sub(r'\n{3,}', '\n\n', r['text'].strip())
        _c, _seen = [], set()
        for c in (r.get('citations') or []):
            h = host(c.get('url'))
            if not h or h in _seen:
                continue
            _seen.add(h)
            _c.append([h, (c.get('title') or '')[:70], c.get('url') or ''])
            if len(_c) >= 10:
                break
        _ent[r['surface']] = {'t': _t[:2400] + ('…' if len(_t) > 2400 else ''), 'len': len(_t), 'c': _c, 'n': len(r.get('citations') or []),
                              'a': 1 if j['a']['toyota'] else 0, 'm': 1 if j['m']['toyota'] else 0, 'k': 1 if j['c']['toyota'] else 0, 'f': j['first']}
    _wsamp[_kw] = {'cat': CAT_W.get(SPI[_q]['kubun'], SPI[_q]['kubun']), 'vol': SV.get(_kw) or 0, 's': _ent}
wideq['samples'] = _wsamp

# ------------------------------------------------------------------ ga4x：全体との比較
def rcsv(p):
    with open(p, encoding='utf-8') as f:
        return list(csv.DictReader(f))


daily = rcsv(GA / 'toyota_jp_ga4_daily.csv')
aid = {r['date']: r for r in rcsv(GA / 'ai_referrals_daily.csv')}
site_daily = []
for r in daily:
    a = aid.get(r['date'])
    site_daily.append([r['date'], int(float(r['sessions'])), int(float(a['total'])) if a else None,
                       int(float(a['chatgpt'])) if a else None, int(float(r.get('conversions') or 0))])
chm = collections.defaultdict(dict)
for r in rcsv(GA / 'toyota_jp_ga4_channel_monthly.csv'):
    chm[r['year_month']][r['channel']] = int(float(r['sessions']))
gu = json.load(open(U / 'ga4_ucar_2026-10-26.json', encoding='utf-8'))
lch = collections.defaultdict(lambda: [0, 0, 0])
for r in gu['landing_source_28']['rows']:
    c = r['session_default_channel_group']
    lch[c][0] += int(r['sessions']); lch[c][1] += int(r.get('newusers') or 0); lch[c][2] += int(r.get('conversions') or 0)
MODELS = set('aqua yaris yariscross corolla corollatouring corollasport corollacross corollaaxio corollafielder prius crown crownsport crownestate '
             'crowncrossover crownsedan camry mirai sienta noah voxy alphard vellfire granace roomy raize rav4 harrier landcruiser250 '
             'landcruiser300 landcruiser70 landcruiserprado hilux bz4x gr86 grsupra grcorolla gryaris hiacevan hiacewagon hiacecommuter '
             'townacevan townacetruck probox chr c-hr century passo pixisvan pixisjoy pixisepoch pixistruck liteacevan dynamic tank '
             'esquire coaster jpntaxi supra copen landcruiserfj bz4xtouring centurynewbt highlander tundra landhopper dynacargo1t dynacargo2t welcab series e-palette'.split())


def pcat(p):
    p = (p or '').split('?')[0]
    if p in ('/', '/index.html', ''):
        return 'トップ'
    seg = p.strip('/').split('/')[0]
    if p.startswith('/carlineup'):
        return '車種の一覧'
    if p.startswith('/service/estimate/ucar'):
        return '中古車の見積り'
    if p.startswith('/service/estimate') or 'simulation' in p:
        return '新車の見積り'
    if p.startswith('/service/store-search') or seg in ('dealer', 'store'):
        return '販売店をさがす'
    if p.startswith('/site-search'):
        return 'サイト内検索'
    if seg in ('member', 'api', 'webregist_tsc', 'register_submitmail.html', 'mytoyota', 'clogin', 'pwreset', 'pwresetComplete', 'session', 'webregist_18TC', 'webregist_common') or seg.startswith('webregist'):
        return '会員・ログイン'
    if seg in ('faq', 'help', 'support', 'sitemap', 'search.html'):
        return 'よくある質問'
    if seg in ('tconnectservice', 'digital_key', 'function-guide', 'dop', 'after_service', 'maintenance_note', 'user', 'task', 'contract', 'service', 'services', 'spapp', 'appcatalog', 'sp', 'guide', 'safety', 'technology', 'ecocar', 'kyuden', 'bousai'):
        return 'オーナー向け'
    if seg in ('store-detail', 'madoguchi'):
        return '販売店をさがす'
    if seg == 'request':
        return 'カタログ・試乗'
    if seg in ('news', 'topics', 'information', 'info', 'recall', 'toyota_news', 'newscast', 'spotlights', 'toyotatimes_live', 'whatsnew', 'latest_stories.html', 'view'):
        return 'お知らせ'
    if seg in ('ucar', 'u-car', 'usedcar'):
        return '中古車の案内'
    if seg in MODELS:
        return '車種のページ'
    return 'ほか'


PC = ['車種の一覧', '車種のページ', 'トップ', '新車の見積り', '中古車の見積り', '販売店をさがす', 'サイト内検索', 'カタログ・試乗', 'よくある質問', 'オーナー向け', '会員・ログイン', 'お知らせ', '中古車の案内', 'ほか']
ai_pages = collections.Counter()
for r in gu['site_ai_pages_90']['rows']:
    ai_pages[pcat(r['page_path'])] += r['sessions']
from_ucar = collections.Counter()
for r in gu['from_ucar_28']['rows']:
    from_ucar[pcat(r['page_path'])] += r['sessions']
r90 = gu['range90']
site90 = [r for r in gu['site_daily_90']['rows']]
ai365 = collections.defaultdict(float)
for r in gu['site_ai_daily_365']['rows']:
    ai365[r['date']] += r['sessions']
ga4x = {
    'site_daily': site_daily,                       # [日付, 全体セッション, AIから, うちChatGPT, キーイベント]
    'channel_monthly': {k: chm[k] for k in sorted(chm)},
    'ucar_landing_ch28': {k: v for k, v in sorted(lch.items(), key=lambda x: -x[1][0])},
    'range28': gu['range28'], 'range90': r90,
    'ai_pages90': {k: int(ai_pages.get(k, 0)) for k in PC},
    'from_ucar28': {k: int(from_ucar.get(k, 0)) for k in PC},
    'page_cats': PC,
    'site90_sessions': int(sum(r['sessions'] for r in site90)),
    'site90_ai': int(sum(v for d, v in ai365.items() if r90[0] <= d <= r90[1])),
    'ucar90_sessions': int(sum(x['s'] for x in D['ga4']['ucar_pages_daily'])),
    'ucar90_ai': int(sum(D['ga4']['ai_to_ucar_pages_90'].values())),
}

try:
    ga4x['check'] = [ln.strip() for ln in open(GA / 'last_check.txt', encoding='utf-8') if ln.strip()]
except Exception:
    ga4x['check'] = []
# 計測の記録（使ったモデル）
models = {}
for f in sorted(U.glob('models_*.json')):
    try:
        u = json.load(open(f, encoding='utf-8')).get('used') or {}
        for k, v in u.items():
            if v:
                models[k] = v
    except Exception:
        pass
# ------------------------------------------------------------------ facts：答えの中のトヨタ認定中古車の説明を、公式の説明と照らす
import factcheck


def _chost(c):
    return host(c.get('url')) or (c.get('domain') or '').lower().removeprefix('www.')


facts = factcheck.run(ROUNDS, valid, [r['date'] for r in D['rounds']], set(G.get('named23', [])), _chost, SURF)
out = {'flow': flow, 'flow_dest': DEST, 'cites': cites, 'wideq': wideq, 'ga4x': ga4x, 'models': models, 'facts': facts,
       'n_rows': [len(rows) for rows in ROUNDS], 'n_valid': [sum(1 for r in rows if valid(r)) for rows in ROUNDS],
       'aio_shown': [round(100 * sum(1 for r in rows if r['surface'] == 'aio' and valid(r)) / max(1, sum(1 for r in rows if r['surface'] == 'aio')), 1) for rows in ROUNDS]}
p = Path(sys.argv[2]) if len(sys.argv) > 2 else B / 'board_extra.json'
json.dump(out, open(p, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('wrote', p, p.stat().st_size, 'flow', len(flow), 'cites', len(cite_rows), 'wideq', len(wq))
