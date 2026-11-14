# -*- coding: utf-8 -*-
"""記事チェック（check/）が Claude を使うための鍵を、ボードの公開鍵で暗号化して check/key.json に置く。

  - 鍵そのものは GitHub の Settings > Secrets and variables > Actions の ANTHROPIC_API_KEY にだけ置く。
    このリポジトリにも、ページにも、平文では置かない（ログにも出さない）。
  - 暗号は入口ページ（gate）と同じ仕組み（tools/seal.py の seal）。ボードと同じ ID とパスワードで開いたときだけ読める。
  - 鍵が変わったかは、鍵の指紋（SHA-256 の先頭16字）で見る。変わっていなければ何もしない。
  - 鍵が登録されていなければ、何もしないで終わる（記事チェックは機械の点検だけで動く）。

使い方（GitHub Actions の check-key から呼ぶ）: ANTHROPIC_API_KEY=... python3 tools/seal_key.py
"""
import datetime, hashlib, json, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from seal import seal, load_pub  # noqa: E402

OUT, FP = Path('check/key.json'), Path('check/key_fp.txt')


def main():
    key = os.environ.get('ANTHROPIC_API_KEY', '').strip()
    if not key:
        print('Claude の鍵が登録されていません（Settings > Secrets and variables > Actions に ANTHROPIC_API_KEY を登録すると、次の便で入ります）')
        return 0
    if not key.startswith('sk-ant-') or len(key) < 40 or any(c.isspace() for c in key):
        print('ANTHROPIC_API_KEY の形が違います（sk-ant- で始まる1行の文字列を、前後の空白なしで登録してください）')
        return 1
    fp = hashlib.sha256(key.encode('utf-8')).hexdigest()[:16]
    if OUT.exists() and FP.exists() and FP.read_text(encoding='utf-8').strip() == fp:
        print('Claude の鍵は変わっていません（指紋', fp + '）')
        return 0
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d %H:%M')
    plain = json.dumps({'key': key, 'at': now}, separators=(',', ':')).encode('utf-8')
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(seal(load_pub(Path('gate')), plain)), encoding='utf-8')
    FP.write_text(fp + '\n', encoding='utf-8')
    print('Claude の鍵を暗号化して置きました（指紋', fp + '、', now, '）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
