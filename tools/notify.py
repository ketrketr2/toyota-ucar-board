# -*- coding: utf-8 -*-
"""点検の結果を知らせる。GitHub の Issue（持ち主にメールで届く）と、設定があれば Slack に送る。

使い方: python3 tools/notify.py status.json <ジョブの結果 success|failure>
  - 要確認（公開を止めた）／処理の失敗 → 「【要確認】」の Issue を開く（内容が変わったときだけ追記）
  - 注意（GA4の遅れ・予定の計測が届かない）→ 「【注意】」の Issue を開く（内容が変わったときだけ追記）
  - 明日が計測の予定日 → 「【予告】」の Issue を開く（同じ日は1回だけ）
  - 正常に戻ったら、開いている【要確認】【注意】を閉じる
Slack に送るときは、リポジトリの Secrets に SLACK_WEBHOOK_URL を登録する（未登録なら送らない）。
"""
import hashlib, json, os, sys, subprocess, urllib.request

st_path, job = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else 'success')
try:
    st = json.load(open(st_path, encoding='utf-8'))
except Exception:
    st = {'level': 'fail', 'checks': [{'lv': 'fail', 'l': '点検の結果（status.json）が作られなかった'}], 'notices': []}
if job != 'success' and st.get('level') != 'fail':
    st['level'] = 'fail'
    st.setdefault('checks', []).append({'lv': 'fail', 'l': '更新の処理が途中で止まった（GitHub Actions の記録を参照）'})
URL = 'https://ketrketr2.github.io/toyota-ucar-board/'
OWNER = (os.environ.get('GITHUB_REPOSITORY') or 'ketrketr2/').split('/')[0]   # 持ち主に通知が届くようにメンションする
RUN = f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}"


def gh(*args):
    r = subprocess.run(['gh', *args], capture_output=True, text=True)
    if r.returncode:
        print('gh error:', r.stderr.strip()[:300])
    return r.stdout


def open_issues(prefix):
    out = gh('issue', 'list', '--state', 'open', '--search', f'{prefix} in:title', '--json', 'number,title', '--limit', '50')
    try:
        return [i for i in json.loads(out or '[]') if i['title'].startswith(prefix)]
    except Exception:
        return []


def slack(text):
    url = os.environ.get('SLACK_WEBHOOK_URL')
    if not url:
        return
    try:
        req = urllib.request.Request(url, data=json.dumps({'text': text}).encode('utf-8'), headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:
        print('slack error:', e)


def body(lines):
    return '\n'.join(lines + ['', f'ボード：{URL}', f'処理の記録：{RUN}', f"点検した時刻：{st.get('checked_at', '')}（日本時間）", '', '@' + OWNER])


def last_text(num):
    """開いている Issue の最後の書き込み（本文か最後のコメント）を返す。"""
    out = gh('issue', 'view', str(num), '--json', 'body,comments')
    try:
        j = json.loads(out or '{}')
    except Exception:
        return ''
    texts = [j.get('body') or ''] + [(c or {}).get('body') or '' for c in (j.get('comments') or [])]
    return texts[-1]


def post(prefix, title, head, bad, slack_text):
    """同じ内容（問題の一覧が同じ）なら追記しない。1日に何便も動くので、同じメールが何通も届かないようにする。"""
    mark = '<!-- sig:' + hashlib.sha256('\n'.join(sorted(bad)).encode('utf-8')).hexdigest()[:12] + ' -->'
    b = body(head + [f'- {x}' for x in bad]) + '\n' + mark
    ex = open_issues(prefix)
    if ex:
        if mark in last_text(ex[0]['number']):
            print('同じ内容のお知らせは済み。追記しない:', prefix)
            return
        gh('issue', 'comment', str(ex[0]['number']), '--body', b)
    else:
        gh('issue', 'create', '--title', title, '--body', b)
    slack(slack_text)


lv = st.get('level', 'ok')
bad = [c['l'] for c in st.get('checks', []) if c.get('lv') in ('fail', 'warn')]
if lv == 'fail':
    t = '【要確認】中古車ボードの更新を止めました'
    post('【要確認】', t, ['点検に通らなかったため、公開中のボードは前の版のままです。', ''], bad, t + '\n' + '\n'.join(bad) + f'\n{URL}')
elif lv == 'warn':
    t = '【注意】中古車ボードのデータに注意が必要です'
    post('【注意】', t, ['ボードは更新しました。次の項目に注意が必要です。', ''], bad, t + '\n' + '\n'.join(bad))
if lv == 'ok':
    for pre in ['【要確認】', '【注意】']:
        for i in open_issues(pre):
            gh('issue', 'close', str(i['number']), '--comment', '点検がすべて正常に戻ったため閉じます。')
for n in st.get('notices', []):
    t = '【予告】' + n.split('は計測')[0].replace('明日（', '').replace('）', '') + ' 中古車ボードの計測日'
    if not open_issues(t):
        gh('issue', 'create', '--title', t, '--body', body([n, '計測が終わると、ボードは自動で更新されます。届かないときは【注意】でお知らせします。']))
        slack('【予告】' + n)
print('notify done:', lv, len(st.get('notices', [])), 'notices')
