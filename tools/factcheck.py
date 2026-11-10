# -*- coding: utf-8 -*-
"""AIの答えに出てくる「トヨタ認定中古車」の説明を、トヨタの公式の説明と照らす（ハルシネーションの点検）。

答えを1文ずつ読み、決まった7つの項目だけを見る（それ以外の文は判定しない）。
  ok  : 公式の説明と合う
  ng  : 公式の説明と違う（誤り）
  old : 以前は公式の説明だったが、いまは違う（古い情報）
公式の説明は 2026-11-10 に各ページで確かめた内容。ページが変わったら FACTS を直す。
"""
import re

FACTS = {
    'lr_term': {'t': 'ロングラン保証の期間', 's': '1年（有料で最長3年）', 'fact': '1年間（有料のロングラン保証αで、さらに1年か2年を足せる）',
                'ng': '「2年」「3年」の保証と書く（αの説明がない）', 'src': ['ロングラン保証｜トヨタ認定中古車', 'https://toyota.jp/ucar/about/longrun/']},
    'lr_km': {'t': 'ロングラン保証の走行距離', 's': '走行距離は無制限', 'fact': '走行距離は無制限',
              'ng': '「◯万kmまで」と上限を書く', 'src': ['ロングラン保証｜トヨタ認定中古車', 'https://toyota.jp/ucar/about/longrun/']},
    'stores': {'t': '保証修理を受けられる拠点の数', 's': '全国約4,500か所', 'fact': '全国約4,500か所（トヨタユーゼックの店舗なども含む）',
               'ng': '約4,500か所と違う数を書く', 'old': '「約5,000か所」（以前の数。GAZOO の購入ガイドにまだ残っている）',
               'src': ['ロングラン保証｜トヨタ認定中古車', 'https://toyota.jp/ucar/about/longrun/'],
               'src_old': ['GAZOO 中古車購入のポイント', 'https://gazoo.com/U-Car/Info/PurchaseTips.html']},
    'hv': {'t': '中古車ハイブリッド保証', 's': '10年目までか3年の長い方・20万kmまで', 'fact': 'ロングラン保証が終わった後、初度登録から10年目まで、または3年間の長い方。累計20万kmまで',
           'ng': '走行距離を「無制限」と書く', 'old': '「初度登録から9年以内」（2020年の発表時の条件）',
           'src': ['こんな安心もプラス｜トヨタ認定中古車', 'https://toyota.jp/ucar/about/plus/'],
           'src_old': ['トヨタ ニュースリリース（2020年4月1日）', 'https://global.toyota/jp/newsroom/corporate/32138917.html']},
    'cert': {'t': '車両検査証明書を作る人', 's': 'トヨタの認定検査員', 'fact': 'トヨタの認定検査員が検査して作る（自動車公正取引協議会が監修、日本自動車査定協会が定期的に監査）',
             'ng': '「第三者機関が検査・発行する」と書く', 'src': ['車両検査証明書｜トヨタ認定中古車', 'https://toyota.jp/ucar/about/certificate/index.html']},
    'tvalue': {'t': 'ブランドの名前', 's': '2020年に「T-Value」から「トヨタ認定中古車」へ', 'fact': '「T-Value」は2020年4月1日に「トヨタ認定中古車」に統一された',
               'old': '「T-Value」を、いまの名前として書く', 'src': ['トヨタ ニュースリリース（2020年4月1日）', 'https://global.toyota/jp/newsroom/corporate/32138917.html']},
    'clean': {'t': 'クリーニングの工程の数', 's': '数は出していない（56工程は2020年の表記）', 'fact': 'いまの公式の説明は工程の数を出していない（「16項目56工程」は2020年の発表時の表記）',
              'old': '「16項目56工程」と書く', 'src': ['トヨタ ニュースリリース（2020年4月1日）', 'https://global.toyota/jp/newsroom/corporate/32138917.html']},
}
ORDER = ['stores', 'lr_term', 'lr_km', 'hv', 'cert', 'tvalue', 'clean']

ALPHA = re.compile(r'α|アルファ|延長|有料|有償|追加|プラス|オプション|最長|最大')
PAST = re.compile(r'旧|以前|かつて|統一|改称|名称変更|2020|現在は|今は|廃止|終了|変わ|変更|呼ばれていた|でした|現：|現・|現在の')
NUM_STORE = re.compile(r'全国(?:の)?(?:約|およそ)?\s*([0-9０-９,，]+)\s*(?:か所|ヶ所|カ所|箇所|拠点|店舗|店|ケ所)')
TOY = re.compile(r'トヨタ|ロングラン|認定中古車')
OTHER_MAKER = re.compile(r'Honda|ホンダ|日産|スバル|マツダ|メルセデス|BMW|レクサス以外|スズキ|ダイハツ|三菱')


def norm_num(s):
    return s.translate(str.maketrans('０１２３４５６７８９，', '0123456789,')).replace(',', '')


def sents(t):
    """答えの文を1文ずつに分ける（見出しや箇条書きの記号は外す）"""
    t = re.sub(r'\*\*|__|#+ ', '', t or '')
    out = []
    for line in t.split('\n'):
        for s in re.split(r'(?<=[。！？])', line):
            s = s.strip(' 　-*・|')
            if len(s) > 4:
                out.append(s)
    return out


def check(s):
    """1文から、トヨタ認定中古車についての主張を取り出し、[(項目, 判定, 根拠の語)] を返す。"""
    out = []
    has_lr = 'ロングラン保証' in s
    hv_ctx = bool(re.search(r'ハイブリッド|初度登録|10年目', s))
    # ロングラン保証の期間と走行距離（ハイブリッド保証の説明は除く。年数はロングラン保証の近くだけを見る）
    if has_lr and not hv_ctx:
        near = ''.join(s[max(0, m.start() - 20):m.end() + 30] for m in re.finditer('ロングラン保証', s))
        yrs = set(norm_num(m) for m in re.findall(r'([0-9０-９]+)\s*年', near))
        km = re.search(r'([0-9０-９,，.]+)\s*万?\s*(?:km|ｋｍ|キロ)', near)
        if km and '無制限' not in s:
            out.append(('lr_km', 'ng', km.group(0)))
        elif '1' in yrs:
            out.append(('lr_term', 'ok', '1年'))
        elif yrs & {'2', '3'} and not ALPHA.search(near):
            out.append(('lr_term', 'ng', '・'.join(sorted(yrs)) + '年'))
        elif '無制限' in s and not yrs:
            out.append(('lr_km', 'ok', '走行距離無制限'))
    # 保証修理を受けられる拠点の数
    for m in NUM_STORE.finditer(s):
        if not TOY.search(s) or OTHER_MAKER.search(s):
            continue
        n = int(norm_num(m.group(1)) or 0)
        if '以上' in s[m.end():m.end() + 3]:
            continue
        if n == 4500:
            out.append(('stores', 'ok', m.group(0)))
        elif n == 5000:
            out.append(('stores', 'old', m.group(0)))
        elif 1000 <= n <= 10000:
            out.append(('stores', 'ng', m.group(0)))
    # 中古車ハイブリッド保証
    if re.search(r'ハイブリッド(?:機構)?(?:の)?(?:特別)?保証', s) and not OTHER_MAKER.search(s) and 'U-Select' not in s:
        if re.search(r'無制限', s) and not has_lr:
            out.append(('hv', 'ng', '走行距離無制限'))
        elif re.search(r'9年(?:以内|まで)', s) and '10年' not in s:
            out.append(('hv', 'old', '初度登録から9年'))
        elif '10年' in s and ('3年' in s or '20万' in s):
            out.append(('hv', 'ok', '10年目／3年・20万km'))
    # 車両検査証明書を作る人
    if '車両検査証明書' in s or ('認定中古車' in s and 'トヨタ' in s and '検査' in s):
        bad = None   # 誤りの語（印をつける部分）
        for cl in re.split(r'[、。,]', s):
            m3 = re.search(r'第三者(?:機関|検査)?(?:（[^）]{0,12}）)?|JAAA|日本自動車査定協会|査定協会|AIS', cl)
            if m3 and not re.search(r'監修|監査|基準', cl) \
               and re.search(r'トヨタ|車両検査証明書', cl + s[:s.find(cl)][-25:]) and not OTHER_MAKER.search(cl):
                bad = bad or m3.group(0)
        if bad and 'トヨタ' in s:
            out.append(('cert', 'ng', bad))
        elif '車両検査証明書' in s and re.search(r'検査員', s):
            out.append(('cert', 'ok', '認定検査員'))
    # ブランドの名前（T-Value）
    if re.search(r'T-Value|Ｔ-Value|Tバリュー|ティーバリュー', s):
        out.append(('tvalue', 'ok' if PAST.search(s) else 'old', 'T-Value'))
    # まるごとクリーニングの工程（2020年の表記）
    if re.search(r'56工程|16項目', s) and 'クリーニング' in s:
        out.append(('clean', 'old', '16項目56工程'))
    return out


SEV = {'ng': 2, 'old': 1, 'ok': 0}


def clean(s):
    """表の記号や改行のタグを、読める形に直す（引用として見せる文）"""
    s = re.sub(r'<br\s*/?>', ' ', s)
    s = re.sub(r'\s*\|\s*', '｜', s).strip('｜ ')
    return re.sub(r'\s{2,}', ' ', s)


def run(rounds, valid, dates, qids_named, host_of, surf_order, max_items=400):
    """rounds: 回ごとの答えの行。dates: 回の日付。戻り値は board_extra.json の facts。"""
    n = n_claim = 0
    rule = {k: {'ok': 0, 'ng': 0, 'old': 0} for k in ORDER}
    by_ai = {s: [0, 0, 0, 0] for s in surf_order}            # 答え・主張のある答え・誤り・古い
    by_round = []
    by_q = {}
    items, ok_ex = [], {}
    bad_hosts = {}
    bad_urls = {k: {} for k in ORDER}      # 誤り・古い情報の答えが参考元に挙げたページ（項目ごと）
    for ri, rows in enumerate(rounds):
        rn = rc = rb = 0
        for r in rows:
            if not valid(r):
                continue
            n += 1; rn += 1
            s_ai = r['surface']
            by_ai[s_ai][0] += 1
            found = {}
            for s in sents(r.get('text')):
                for k, v, ev in check(s):
                    if k not in found or SEV[v] > SEV[found[k][0]]:
                        found[k] = (v, ev, s)
            if not found:
                continue
            n_claim += 1; rc += 1
            by_ai[s_ai][1] += 1
            worst = max(SEV[v] for v, _, _ in found.values())
            if worst == 2:
                by_ai[s_ai][2] += 1
            elif worst == 1:
                by_ai[s_ai][3] += 1
            if worst:
                rb += 1
            q = by_q.setdefault(r['qid'], [0, 0])
            q[0] += 1
            if worst:
                q[1] += 1
            hosts, urls = [], []
            for c in r.get('citations') or []:
                h = host_of(c)
                if h and h not in hosts:
                    hosts.append(h)
                u = (c.get('url') or '').split('#')[0]
                if u and u not in urls:
                    urls.append(u)
            for k, (v, ev, s) in found.items():
                rule[k][v] += 1
                if v == 'ok':
                    if k not in ok_ex or len(s) < len(ok_ex[k]['q']):
                        ok_ex[k] = {'q': clean(s)[:160], 's': s_ai, 'qid': r['qid']}
                    continue
                for h in hosts[:6]:
                    bad_hosts[h] = bad_hosts.get(h, 0) + 1
                for u in urls[:8]:
                    bad_urls[k][u] = bad_urls[k].get(u, 0) + 1
                items.append({'k': k, 'v': v, 'ev': ev, 'q': clean(s)[:220], 's': s_ai, 'qid': r['qid'], 'r': ri,
                              'run': r.get('run', 0), 'h': hosts[:5], 'named': r['qid'] in qids_named})
        by_round.append([dates[ri] if ri < len(dates) else '', rn, rc, rb])
    items.sort(key=lambda x: (-SEV[x['v']], ORDER.index(x['k']), x['qid'], x['s'], x['r'], x['run']))
    return {
        'checked_on': '2026-11-10', 'n': n, 'n_claim': n_claim,
        'n_bad': len(set((i['r'], i['qid'], i['s'], i['run']) for i in items)),
        'n_ng': len(set((i['r'], i['qid'], i['s'], i['run']) for i in items if i['v'] == 'ng')),
        'rules': [dict(FACTS[k], k=k, **rule[k]) for k in ORDER],
        'by_ai': by_ai, 'by_round': by_round, 'by_q': by_q,
        'items': items[:max_items], 'n_items': len(items), 'ok_ex': ok_ex,
        'bad_hosts': sorted(bad_hosts.items(), key=lambda x: -x[1])[:12],
        'bad_urls': {k: sorted(v.items(), key=lambda x: -x[1])[:6] for k, v in bad_urls.items() if v},
    }
