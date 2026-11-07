# -*- coding: utf-8 -*-
"""中古車GEO：回答1件ごとの判定（言及・引用・ブランド出現・第一想起・推奨文）。
数え方は 261022 実態調査 v9 の付録「数え方」（P.42）に合わせる。"""
import re, unicodedata
from urllib.parse import urlparse

def norm(s):
    return unicodedata.normalize('NFKC', s or '').lower()

PREFS = ("北海道 青森 岩手 宮城 秋田 山形 福島 茨城 栃木 群馬 埼玉 千葉 東京 神奈川 新潟 富山 石川 福井 山梨 長野 岐阜 静岡 愛知 三重 "
         "滋賀 京都 大阪 兵庫 奈良 和歌山 鳥取 島根 岡山 広島 山口 徳島 香川 愛媛 高知 福岡 佐賀 長崎 熊本 大分 宮崎 鹿児島 沖縄 "
         "札幌 名古屋 横浜 神戸 仙台 北九州 浜松 岐阜 四国 九州 東海 北陸 西四国 南国 中京 徳島 埼玉 千葉").split()
PREF_RE = '|'.join(sorted(set(PREFS), key=len, reverse=True))

# ---------------- トヨタのお店（本文）
T_SUB = {
    'nintei': [r'トヨタ(の)?[「『"]?認定中古車', r'トヨタ認定u-car', r'トヨタ(の)?認定 ?u-car'],
    'light':  [r'認定中古車ライト'],
    'gazoo':  [r'gazoo(?! ?racing)', r'ガズー(?!レーシング)'],
    'store':  [r'中古車オンラインストア', r'トヨタ中古車オンライン'],
    'online': [r'オンライン購入サービス', r'トヨタ[^。\n]{0,20}オンラインで(の)?(購入|契約)', r'トヨタ[^。\n]{0,20}オンライン(購入|契約)'],
}
T_DEALER = [
    r'トヨタ(系)?(の)?(正規)?(販売店|ディーラー|お店|販売会社|店舗|中古車販売店|中古車店|系列店|直営店)',
    r'トヨタ(系)?(の)?(正規)?(ディーラー|販売店)系',
    r'トヨペット', r'トヨタカローラ', r'カローラ店', r'ネッツトヨタ', r'ネッツ店', r'トヨタモビリティ',
    r'(%s)トヨタ' % PREF_RE,
    r'トヨタ[^。\n]{0,3}u-car', r'u-car店', r'トヨタ[^。\n]{0,3}ユーカー',
]
T_ALL = [p for v in T_SUB.values() for p in v] + T_DEALER

# ---------------- 比較相手（本文）
C_MENTION = {
    'goonet':   [r'グーネット', r'goo-net', r'goonet'],
    'carsensor':[r'カーセンサー', r'carsensor', r'car sensor'],
    'honda':    [r'honda cars', r'ホンダカーズ', r'ホンダ(系)?(の)?(正規)?(販売店|ディーラー|お店)', r'honda(の)?(正規)?(販売店|ディーラー)',
                 r'(honda|ホンダ)認定中古車', r'u-select', r'ユーセレクト'],
    'nissan':   [r'日産(系)?(の)?(正規)?(販売店|ディーラー|お店)', r'日産プリンス', r'日産サティオ', r'日産(の)?認定中古車', r'日産 ?u-cars', r'日産(の)?「?u-cars'],
    'nextage':  [r'ネクステージ', r'nextage'],
    'gulliver': [r'ガリバー', r'gulliver'],
    'wecars':   [r'wecars', r'ウィーカーズ'],
}
ENT = ['toyota'] + list(C_MENTION)

def _first(pats, t):
    best = None
    for p in pats:
        m = re.search(p, t)
        if m and (best is None or m.start() < best):
            best = m.start()
    return best

# ---------------- 引用（参考元）
import fnmatch
DEALER_GLOBS = ["toyota-mobi-*.jp","toyota-mobi-*.co.jp","toyota-mobility-*.jp","toyota-mobility-*.co.jp","toyota-united*.co.jp",
 "*-toyota.jp","*-toyota.co.jp","*toyota.jp","*toyota.co.jp","gtoyota.com","corolla-*.jp","corolla-*.net","corolla-*.co.jp",
 "*.corolla.co.jp","*corolla*.jp","t-corolla.co.jp","*toyopet*.co.jp","*toyopet*.jp","*.toyopet-dealer.jp","netz*.com","netz*.jp",
 "*netz*.jp","*.toyota-dealer.jp","weins-toyota-*.co.jp","k-toyota.co.jp"]
def is_dealer(h):
    return any(fnmatch.fnmatch(h, g) for g in DEALER_GLOBS)
def host(u):
    try:
        h = urlparse(u).hostname or ''
    except Exception:
        h = ''
    return h.lower().removeprefix('www.')

def cite_flags(cits):
    f = {k: False for k in ['toyota','nintei','light','gazoo','store','online','goonet','goomag','carsensor','honda','nissan','nextage','gulliver','wecars','livedoor','bestcar']}
    for c in cits or []:
        u = (c.get('url') or '')
        h = host(u) or (c.get('domain') or '').lower().removeprefix('www.')
        ul = u.lower()
        path = urlparse(ul).path if ul else ''
        if h.endswith('toyota.jp'):
            f['toyota'] = True
            if h == 'toyota.jp' and (path.startswith('/ucar') or path.startswith('/u-car')):
                f['nintei'] = True
                if 'light' in path:
                    f['light'] = True
                if '/ucar/guide/online-purchase' in path:
                    f['online'] = True
        elif h == 'toyota-outlet.gazoo.com':
            f['toyota'] = f['store'] = True
        elif h.endswith('gazoo.com'):
            f['toyota'] = f['gazoo'] = True
        elif h in ('toyota.co.jp', 'global.toyota'):
            pass
        elif is_dealer(h) and 'nissan' not in h and 'honda' not in h:
            f['toyota'] = True
        if h.endswith('goo-net.com'):
            f['goonet'] = True
            if path.startswith('/magazine'):
                f['goomag'] = True
        if h.endswith('carsensor.net'): f['carsensor'] = True
        if h.endswith('honda.co.jp') or h.startswith('hondacars') or h.startswith('honda-cars') or 'hondacars' in h: f['honda'] = True
        if 'nissan' in h: f['nissan'] = True
        if h.endswith('nextage.jp'): f['nextage'] = True
        if h.endswith('221616.com'): f['gulliver'] = True
        if h.endswith('wecars.co.jp'): f['wecars'] = True
        if h.endswith('livedoor.com') or h.endswith('livedoor.jp'): f['livedoor'] = True
        if h.endswith('bestcarweb.jp') or h.endswith('bestcar.jp'): f['bestcar'] = True
    return f

REC = r'(おすすめ|オススメ|お勧め|候補|安心)'

def judge(text, cits):
    t = norm(text)
    out = {}
    # 言及
    sub = {k: _first(v, t) is not None for k, v in T_SUB.items()}
    tpos = _first(T_ALL, t)
    out['m'] = {'toyota': tpos is not None, **{k: sub[k] for k in sub}}
    pos = {'toyota': tpos}
    for e, pats in C_MENTION.items():
        p = _first(pats, t)
        out['m'][e] = p is not None
        pos[e] = p
    # 引用
    cf = cite_flags(cits)
    out['c'] = cf
    # 出現
    out['a'] = {e: out['m'][e] or cf.get(e, False) for e in ENT}
    for k in ['nintei','light','gazoo','store','online']:
        out['a'][k] = out['m'][k] or cf[k]
    # 第一想起
    present = {e: p for e, p in pos.items() if p is not None}
    out['first'] = min(present, key=present.get) if present else None
    # 推奨の文（中古車もトヨタのお店で）
    rec = False
    if tpos is not None:
        for s in re.split(r'[。！？!?]', t):
            if _first(T_ALL, s) is not None and re.search(REC, s):
                rec = True; break
    out['rec'] = rec
    return out
