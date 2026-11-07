# -*- coding: utf-8 -*-
"""作り直したデータを点検し、公開してよいかを決める。

使い方: python3 tools/check.py <作業フォルダ> <リポジトリのルート>
  入力 : <作業>/board_data.json, <作業>/board_extra.json, <ルート>/status.json（前回の状態）
  出力 : <作業>/board_full.json（画面に渡すデータ。点検の結果を含む）, <ルート>/status.json（公開の状態）
  終了コード : 0＝公開してよい（正常・注意）, 1＝公開しない（要確認）, 0 かつ status.unchanged＝データに変化なし
"""
import json, sys, hashlib, datetime, math, re
from pathlib import Path

W, ROOT = Path(sys.argv[1]), Path(sys.argv[2] if len(sys.argv) > 2 else '.')
JST = datetime.timezone(datetime.timedelta(hours=9))
now = datetime.datetime.now(JST)
today = now.date()
D = json.load(open(W / 'board_data.json', encoding='utf-8'))
X = json.load(open(W / 'board_extra.json', encoding='utf-8'))
prev = {}
if (ROOT / 'status.json').exists():
    try:
        prev = json.load(open(ROOT / 'status.json', encoding='utf-8'))
    except Exception:
        prev = {}
checks = []
def add(lv, l, s=''):
    checks.append({'lv': lv, 'l': l, 's': s})
md = lambda d: f'{int(d[5:7])}/{int(d[8:10])}'

# 1. 計測の回
rounds = D.get('rounds', [])
pre = [r for r in rounds if not r.get('post')]
add('ok' if len(pre) >= 2 else 'fail', f'掲載前の計測：{len(pre)}回（' + '・'.join(md(r['date']) for r in pre) + '）', '基準に必要な回数は2回')
post = [r for r in rounds if r.get('post')]
if post:
    add('ok', f'掲載後の計測：{len(post)}回（' + '・'.join(md(r['date']) for r in post) + '）')
# 2. 各回の答えの数（84問×4つのAI×回数のうち、AI Overviews の要約が出なかった分を除く）
for r in rounds:
    n = (r.get('m') or {}).get('n_answers') or 0
    exp = 84 * 4 * int(r.get('runs') or 3)
    lv = 'ok' if n >= 0.85 * exp else ('warn' if n >= 0.6 * exp else 'fail')
    add(lv, f"{md(r['date'])}の答え：{n:,}件（予定 {exp:,}件）", '' if lv == 'ok' else '予定より少ない。計測が途中で止まった可能性')
# 3. 数字が壊れていないか
bad = []
for r in rounds:
    for g in ['focus31', 'comp30', 'named20', 'nonnamed61']:
        for k in ['appear', 'mention', 'cite']:
            v = (((r.get('m') or {}).get(g) or {}).get(k) or {}).get('avg')
            if v is None or not (0 <= v <= 100) or (isinstance(v, float) and math.isnan(v)):
                bad.append(f"{r['id']}:{g}:{k}")
add('ok' if not bad else 'fail', '指標の値：すべて0〜100%の範囲' if not bad else f'指標の値が壊れている：{len(bad)}か所', '、'.join(bad[:6]))
# 4. 答えの文（ドロワーで読むもの）
ns = len(D.get('samples') or {})
add('ok' if ns >= 80 else 'warn', f'答えの文：{ns}問ぶん', '')
# 5. 1,761本
wa = (D.get('wide') or {}).get('answers') or 0
add('ok' if wa >= 4000 else 'fail', f"1,761本：答え {wa:,}件（{md((D.get('wide') or {}).get('date', '0000-00-00'))}）", '')
# 6. GA4 の鮮度
until = (D.get('ga4') or {}).get('until')
if until:
    lag = (today - datetime.date.fromisoformat(until)).days
    add('ok' if lag <= 3 else 'warn', f'GA4（toyota.jp）：{md(until)} までのデータ', f'今日との差 {lag}日' + ('' if lag <= 3 else '。GA4の取り込みが止まっている可能性'))
else:
    add('fail', 'GA4：データがない')
# 7. 前回より後退していないか（データの消失を防ぐ）
if prev:
    if len(rounds) < prev.get('n_rounds', 0):
        add('fail', f"計測の回が減った：前回 {prev.get('n_rounds')}回 → 今回 {len(rounds)}回", '元データの読み込みに失敗した可能性')
    if until and prev.get('ga4_until') and until < prev['ga4_until']:
        add('fail', f"GA4の最終日が前回より古い：{prev['ga4_until']} → {until}", '')
# 8. 計測の予定（toyota-geo-board の triggers）
sched = set()
for name in ['ucar-round.json', 'ucar-wide.json']:
    p = ROOT / 'toyota-geo-board' / 'triggers' / name
    if p.exists():
        try:
            t = json.load(open(p, encoding='utf-8'))
            for k, v in t.items():
                if k in ('requested_at', 'note'):
                    continue
                for d in re.findall(r'\d{4}-\d{2}-\d{2}', str(v)):
                    sched.add(d)
        except Exception:
            pass
try:
    cfg = json.load(open(ROOT / 'tools' / 'rounds.json', encoding='utf-8'))
    sched |= set(cfg.get('schedule') or [])
except Exception:
    pass
have = {r['date'] for r in rounds} | {d['date'] for d in D.get('daily', [])}
notices = []
tomorrow = (today + datetime.timedelta(days=1)).isoformat()
for d in sorted(sched):
    if d == tomorrow:
        notices.append(f'明日（{md(d)}）は計測の予定日です。朝6時40分ごろに計測が始まります。')
    if d == today.isoformat() and now.hour >= 10 and d not in have:
        add('warn', f'今日（{md(d)}）の計測のデータが、まだ届いていない', '計測の処理が止まっている可能性')
    if today.isoformat() > d >= (today - datetime.timedelta(days=3)).isoformat() and d not in have:
        add('warn', f'予定の計測（{md(d)}）のデータが届いていない', '')
nxt = [d for d in sorted(sched) if d > today.isoformat()]

level = 'fail' if any(c['lv'] == 'fail' for c in checks) else ('warn' if any(c['lv'] == 'warn' for c in checks) else 'ok')
D['extra'] = X
D['checks'] = checks
body = json.dumps({k: v for k, v in D.items() if k not in ('generated_at', 'checks')}, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
h = hashlib.sha256(body.encode('utf-8')).hexdigest()[:16]
unchanged = bool(prev) and prev.get('data_hash') == h
if unchanged:
    D['generated_at'] = prev.get('data_generated_at', D.get('generated_at'))
status = {
    'checked_at': now.strftime('%Y-%m-%d %H:%M'), 'level': level, 'unchanged': unchanged, 'data_hash': h,
    'data_generated_at': D.get('generated_at'), 'n_rounds': len(rounds),
    'rounds': [{'label': r['label'], 'date': r['date'], 'post': bool(r.get('post'))} for r in rounds],
    'ga4_until': until, 'wide_date': (D.get('wide') or {}).get('date'),
    'next_measure': nxt[:5], 'notices': notices, 'checks': [{'lv': c['lv'], 'l': c['l']} for c in checks],
}
if level == 'fail':
    status['published'] = prev.get('published') or prev.get('data_generated_at')
else:
    status['published'] = D.get('generated_at')
(W / 'board_full.json').write_text(json.dumps(D, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
(ROOT / 'status.json').write_text(json.dumps(status, ensure_ascii=False, indent=1), encoding='utf-8')
for c in checks:
    print({'ok': 'OK  ', 'warn': 'WARN', 'fail': 'FAIL'}[c['lv']], c['l'], c['s'])
print('LEVEL', level, 'UNCHANGED' if unchanged else 'CHANGED', h)
sys.exit(1 if level == 'fail' else 0)
