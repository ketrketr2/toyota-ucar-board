# -*- coding: utf-8 -*-
"""入口ページの形を確かめる（公開の直前）。鍵・画面・データの3つが入っていて、画面が変わっていないこと。"""
import json, re, sys
from pathlib import Path
page = Path(sys.argv[1]).read_text(encoding='utf-8'); gate = Path(sys.argv[2] if len(sys.argv) > 2 else 'gate')
m = re.search(r'const G=(\{.*?\});\n', page)
assert m, '入口ページに鍵の情報がない'
g = json.loads(m.group(1))
assert set(g) == {'w', 'a', 'd'}, 'w・a・d の3つが必要'
assert g['w'] == json.loads((gate / 'wrapped.json').read_text()), '包んだ秘密鍵が gate/wrapped.json と違う'
assert g['a'] == json.loads((gate / 'app.json').read_text()), '画面が gate/app.json と違う'
assert len(g['d']['k']) > 300 and len(g['d']['i']) == 16 and len(g['d']['c']) > 100000, 'データの暗号の形が違う'
assert 'UCAR SIGNAL' in page and len(page) > 400000, '入口ページが小さすぎる'
print('verify_page: OK', len(page), 'bytes')
