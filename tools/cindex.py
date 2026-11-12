# -*- coding: utf-8 -*-
"""参考元のURLの索引（画面「2-4 記事のURLで探す」で使う）。

答え1件ごとに、参考元に出たURL（正規化したもの）と、本文に名前が出た媒体・サイトを記録する。
画面では、入れたURL（このページ／この階層／サイト全体）に合う答えを、計測の日・質問・AIごとに数える。
計測が増えると（掲載後・3月の事後計測）、毎回の自動更新で索引も作り直す。

URLの正規化（画面の JavaScript の nurl() と同じ決まり。片方を直すときは両方を直す）
  - http/https・www.・ポート番号・#以降・末尾の「/」と index.html などを無視する
  - パスの %xx を元の文字に戻す（日本語を含むURLを、エンコードの有無に関係なく同じページとして扱う）
  - ?以降は、ページを区別する名前（KEEP_Q）だけを残す（utm_ や padid などの追跡用は捨てる）
  - youtu.be/XXXX は youtube.com/watch?v=XXXX に、m.youtube.com は youtube.com に寄せる

出力（data['cix']）
  h     : サイト（ホスト）の一覧
  u     : URL の一覧 [サイトの番号, パス（?以降を含む）]
  t     : URL の題名（参考元に付いていたもの・先頭60字。u と同じ順）
  sets  : 計測ごと {id, kind(r=84問の回 / d=日ごとの確認 / w=検索1,761本), date, label, post, runs, n(AIごとの答えの数)}
  a     : 計測ごとの答え [質問の番号, AIの番号, 何回目, トヨタの印, 本文に出た名前の印, URLの番号…]
          質問の番号は、84問なら data['questions'] の順、1,761本なら wq の順
          トヨタの印：1=出現 2=言及（本文に名前）4=引用（参考元にトヨタのサイト）の和
          本文に出た名前の印：names の順に 1,2,4,8…の和
  wq    : 1,761本の検索の語 [語, 月の検索数]
  names : 本文の名前で数える媒体・サイト [キー, 表示名, サイト（ホスト／パスの頭）]
  art25 : 前年の記事の番号 → 参考元に出たURLの番号（題名とサイトで照らしたもの）
"""
import re, unicodedata
from urllib.parse import unquote

KEEP_Q = ('v', 'id', 'p', 'page_id', 'aid', 'article_id', 'no', 'qid')
SURF = ['aio', 'aimode', 'chatgpt', 'gemini']


def nurl(u):
    u = (u or '').strip()
    if not u:
        return ''
    u = re.sub(r'^[a-zA-Z][a-zA-Z0-9+.\-]*://', '', u)
    u = re.sub(r'^//', '', u)
    m = re.match(r'([^/?#]*)([^#]*)', u)
    h, rest = m.group(1).lower(), m.group(2)
    h = h.rsplit('@', 1)[-1]
    h = re.sub(r':\d+$', '', h).rstrip('.')
    if h.startswith('www.'):
        h = h[4:]
    if h == 'm.youtube.com':
        h = 'youtube.com'
    path, _, query = rest.partition('?')
    path = unquote(path)
    path = re.sub(r'/{2,}', '/', path)
    path = re.sub(r'/index\.(?:html?|php|aspx?)$', '', path, flags=re.I)
    path = path.rstrip('/')
    q = []
    for kv in query.split('&'):
        if not kv:
            continue
        k, _, v = kv.partition('=')
        k = unquote(k).lower()
        if k in KEEP_Q and v:
            q.append((k, unquote(v)))
    if h == 'youtu.be' and path:
        q = [('v', path.lstrip('/').split('/')[0])]
        h, path = 'youtube.com', '/watch'
    if h == 'youtube.com' and path != '/watch':
        q = [x for x in q if x[0] != 'v']
    q.sort()
    return h + path + ('?' + '&'.join(f'{k}={v}' for k, v in q) if q else '')


# 本文の名前で数える媒体・サイト（キー, 表示名, 本文の言い方, 大文字小文字を区別するか, サイト）
NAMES = [
    ('livedoor', 'livedoor ニュース', r'ライブドア|livedoor', False, ['news.livedoor.com', 'livedoor.com', 'livedoor.jp']),
    ('bestcar', 'ベストカー', r'ベストカー|bestcar', False, ['bestcarweb.jp', 'bestcar.jp']),
    ('goomag', 'グーネットマガジン', r'グーネット\s*マガジン|goo-?net\s*magazine', False, ['goo-net.com/magazine']),
    ('goonet', 'グーネット', r'グーネット(?!\s*マガジン)|goo-?net(?!\s*magazine)', False, ['goo-net.com']),
    ('carsensor', 'カーセンサー', r'カーセンサー|carsensor', False, ['carsensor.net']),
    ('nextage', 'ネクステージ', r'ネクステージ|nextage', False, ['nextage.jp']),
    ('gulliver', 'ガリバー', r'ガリバー|gulliver', False, ['221616.com']),
    ('gazoo', 'GAZOO', r'gazoo|ガズー', False, ['gazoo.com']),
    ('kurumaerabi', '車選びドットコム', r'車選び\s*(?:ドットコム|\.com)|kurumaerabi', False, ['kurumaerabi.com']),
    ('moby', 'MOBY', r'(?<![A-Za-z])MOBY(?![A-Za-z])|モビー', True, ['car-moby.jp']),
    ('motorfan', 'Motor-Fan', r'motor-?fan|モーターファン', False, ['motor-fan.jp']),
    ('carwatch', 'Car Watch', r'car\s?watch|カーウォッチ', False, ['car.watch.impress.co.jp']),
    ('camphack', 'CAMP HACK', r'camp\s?hack|キャンプハック', False, ['camp-hack.jp']),
    ('kakurega', '男の隠れ家', r'男の隠れ家', False, ['otokonokakurega.com']),
    ('youtube', 'YouTube', r'youtube|ユーチューブ', False, ['youtube.com', 'youtu.be']),
    ('kakaku', '価格.com', r'価格\.com|価格コム', False, ['kakaku.com']),
    ('chiebukuro', 'Yahoo!知恵袋', r'知恵袋', False, ['chiebukuro.yahoo.co.jp']),
    ('carview', 'carview!', r'carview|カービュー', False, ['carview.yahoo.co.jp']),
    ('autocone', 'オートックワン', r'オートックワン|autoc-?one', False, ['autoc-one.jp']),
    ('kinto', 'KINTO', r'(?<![A-Za-z])KINTO(?![A-Za-z])|キント(?!ン)', True, ['kinto-jp.com']),
]
_NRE = [re.compile(p, 0 if cs else re.I) for _, _, p, cs, _ in NAMES]


def names_mask(text):
    raw = unicodedata.normalize('NFKC', text or '')
    low = raw.lower()
    m = 0
    for i, (k, ja, p, cs, hs) in enumerate(NAMES):
        if _NRE[i].search(raw if cs else low):
            m |= 1 << i
    return m


def build(rounds, daily, wide, qindex, valid, judge, art25, art25_hits):
    """rounds/daily: [(id, date, label, post, runs, rows)], wide: (id, date, label, rows, prompts, volumes) か None"""
    hosts, hidx = [], {}
    urls, uidx, titles = [], {}, []
    a25 = {}

    def uid(c):
        raw = c.get('url') or ''
        k = nurl(raw) if raw else nurl(c.get('domain') or '')
        if not k:
            return None
        if k not in uidx:
            h, _, p = k.partition('/')
            hq = h.split('?')[0]
            p = ('/' + p) if p else k[len(hq):]
            if hq not in hidx:
                hidx[hq] = len(hosts); hosts.append(hq)
            uidx[k] = len(urls); urls.append([hidx[hq], p]); titles.append('')
        i = uidx[k]
        t = (c.get('title') or '').strip()
        if t and not titles[i]:
            titles[i] = re.sub(r'\s+', ' ', t)[:60]
        return i

    sets, ans = [], {}

    def add(sid, kind, date, label, post, runs, rows, qi_of):
        n = [0, 0, 0, 0]
        out = []
        for r in rows:
            if not valid(r):
                continue
            qi = qi_of(r['qid'])
            if qi is None or r['surface'] not in SURF:
                continue
            si = SURF.index(r['surface'])
            n[si] += 1
            j = judge(r['text'], r.get('citations'))
            fl = (1 if j['a']['toyota'] else 0) | (2 if j['m']['toyota'] else 0) | (4 if j['c']['toyota'] else 0)
            us = []
            for c in r.get('citations') or []:
                i = uid(c)
                if i is not None and i not in us:
                    us.append(i)
                for no in art25_hits([c]):
                    if i is not None:
                        a25.setdefault(no, [])
                        if i not in a25[no]:
                            a25[no].append(i)
            out.append([qi, si, r.get('run', 0), fl, names_mask(r.get('text'))] + us)
        sets.append({'id': sid, 'kind': kind, 'date': date, 'label': label, 'post': bool(post), 'runs': runs, 'n': n})
        ans[sid] = out

    for sid, date, label, post, runs, rows in rounds:
        add(sid, 'r', date, label, post, runs, rows, lambda q: qindex.get(q))
    for sid, date, label, post, runs, rows in daily:
        add(sid, 'd', date, label, post, runs, rows, lambda q: qindex.get(q))
    wq = []
    if wide:
        sid, date, label, rows, prompts, vols = wide
        wi = {p['id']: i for i, p in enumerate(prompts)}
        wq = [[p['kw'], vols.get(p['kw']) or 0] for p in prompts]
        add(sid, 'w', date, label, False, 1, rows, lambda q: wi.get(q))
    return {'v': 1, 'h': hosts, 'u': urls, 't': titles, 'sets': sets, 'a': ans, 'wq': wq,
            'names': [[k, ja, hs] for k, ja, p, cs, hs in NAMES],
            'art25': {str(no): v for no, v in sorted(a25.items())}}
