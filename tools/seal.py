# -*- coding: utf-8 -*-
"""入口ページ（index.html）を作る。

しくみ（パスワードを自動更新の環境に置かないための二重の鍵）
  - RSA の鍵の組を1回だけ作る。秘密鍵は「ID:パスワード」から作った鍵（PBKDF2-SHA256 20万回）で包み、ページに入れる。
  - 画面（HTML・CSS・JS）とデータ（数字）は、それぞれ使い捨ての鍵（AES-256-GCM）で暗号化し、その鍵を公開鍵で包む。
  - 閲覧時：ID とパスワード → 秘密鍵を開く → 使い捨ての鍵を開く → 画面とデータを開く。
  - 毎朝の自動更新は、公開鍵だけでデータを暗号化できる（パスワードも秘密鍵も要らない）。

使い方
  keygen : BOARD_ID / BOARD_PW を環境変数で渡し、gate/pub.pem と gate/wrapped.json を作る（1回だけ）
  app    : 画面のHTML（__DATA__ を残したもの）を暗号化して gate/app.json を作る（画面を直したときだけ）
  page   : データ（JSON）を公開鍵で暗号化し、入口ページ index.html を組み立てる（毎朝）
"""
import argparse, base64, gzip, json, os, sys, datetime
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
import hashlib

ITER = 200000
b64 = lambda b: base64.b64encode(b).decode('ascii')
OAEP = padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)


def seal(pub, plain_bytes):
    dek, iv = os.urandom(32), os.urandom(12)
    ct = AESGCM(dek).encrypt(iv, gzip.compress(plain_bytes, compresslevel=9, mtime=0), None)
    return {'k': b64(pub.encrypt(dek, OAEP)), 'i': b64(iv), 'c': b64(ct)}


def load_pub(gate):
    return serialization.load_pem_public_key((gate / 'pub.pem').read_bytes())


GATE_HTML = r'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<meta name="robots" content="noindex,nofollow">
<title>UCAR SIGNAL｜中古車AI検索 タイアップ効果ボード</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=BIZ+UDGothic:wght@400;700&display=swap" rel="stylesheet">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'%3E%3Crect width='48' height='48' rx='11' fill='%2305070a'/%3E%3Cpath d='M10 31 L15 21 Q16.5 17.5 20.5 17.5 L28.5 17.5 Q32.5 17.5 34 21 L39 31 Z' fill='none' stroke='%23dcbd80' stroke-width='2.2'/%3E%3Ccircle cx='17' cy='33' r='3.2' fill='none' stroke='%2362d3e2' stroke-width='2'/%3E%3Ccircle cx='31.5' cy='33' r='3.2' fill='none' stroke='%2362d3e2' stroke-width='2'/%3E%3C/svg%3E">
<style>
:root{--bg:#05070a;--panel:#0b0f15;--line:#1b222c;--line2:#262f3b;--fg:#ece8df;--fg2:#bcb7ad;--mute:#848c98;--gold:#dcbd80;--gold2:#f3e0b3;--cyan:#62d3e2;--err:#ff7a72}
@media (prefers-color-scheme: light){:root:not([data-theme="dark"]){--bg:#f2efe8;--panel:#fbfaf6;--line:#dcd5c7;--line2:#cfc6b5;--fg:#17140f;--fg2:#463f34;--mute:#776f62;--gold:#8a6422;--gold2:#6c4d16;--cyan:#0d7c8d;--err:#b02a2a}}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:var(--bg);color:var(--fg)}
body{min-height:100vh;display:grid;place-items:center;padding:24px 16px;font-family:"BIZ UDGothic","Hiragino Sans","Yu Gothic",sans-serif;
  background:radial-gradient(70% 50% at 50% 100%,color-mix(in srgb,var(--gold) 9%,transparent),transparent 70%),radial-gradient(60% 40% at 50% 0%,color-mix(in srgb,var(--cyan) 7%,transparent),transparent 70%),var(--bg)}
.card{width:100%;max-width:420px;background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:30px 28px 24px;box-shadow:0 30px 60px -40px rgba(0,0,0,.8)}
.mk{display:flex;align-items:center;gap:12px;margin-bottom:18px}
.mk svg{width:40px;height:40px;flex:none}
.mk b{display:block;font-size:14px;letter-spacing:.1em}
.mk small{display:block;font-size:10.5px;color:var(--mute);letter-spacing:.08em;margin-top:2px}
h1{font-size:19px;line-height:1.55;font-weight:700;word-break:auto-phrase}
h1 span{color:var(--gold2)}
.lead{font-size:12.5px;color:var(--fg2);line-height:1.8;margin:8px 0 18px;word-break:auto-phrase}
label{display:block;font-size:11.5px;color:var(--mute);margin:12px 0 6px;letter-spacing:.04em}
input{width:100%;font:inherit;font-size:16px;padding:11px 12px;border:1px solid var(--line2);border-radius:10px;background:var(--bg);color:var(--fg);outline:none}
input:focus{border-color:var(--gold)}
button{width:100%;margin-top:20px;font:inherit;font-weight:700;font-size:15px;padding:12px;border:none;border-radius:10px;background:linear-gradient(180deg,var(--gold2),var(--gold));color:#1a1408;cursor:pointer}
button:disabled{opacity:.6;cursor:wait}
.err{color:var(--err);font-size:12.5px;min-height:18px;margin-top:12px;text-align:center}
.ft{font-size:11px;color:var(--mute);text-align:center;margin-top:14px;line-height:1.8}
</style>
</head>
<body>
<div class="card">
  <div class="mk"><svg viewBox="0 0 48 48"><rect x="2" y="2" width="44" height="44" rx="11" fill="none" stroke="var(--line2)" stroke-width="1.5"/><path d="M10 31 L15 21 Q16.5 17.5 20.5 17.5 L28.5 17.5 Q32.5 17.5 34 21 L39 31 Z" fill="none" stroke="var(--gold)" stroke-width="1.8" stroke-linejoin="round"/><circle cx="17" cy="33" r="3.2" fill="none" stroke="var(--cyan)" stroke-width="1.6"/><circle cx="31.5" cy="33" r="3.2" fill="none" stroke="var(--cyan)" stroke-width="1.6"/><path d="M24.2 7 V13" stroke="var(--cyan)" stroke-width="1.6" stroke-linecap="round"/></svg><div><b>UCAR SIGNAL</b><small>中古車 × AI検索 × タイアップ</small></div></div>
  <h1>中古車の<span>AI検索</span>　タイアップ効果ボード</h1>
  <p class="lead">AIの答えにトヨタのお店がどれだけ出るかを、記事の掲載の前と後で測るボードです。</p>
  <form id="f" autocomplete="off">
    <label for="u">ID</label><input id="u" type="text" autocomplete="username" spellcheck="false" autocapitalize="none">
    <label for="p">パスワード</label><input id="p" type="password" autocomplete="current-password">
    <button id="b" type="submit">開く</button>
    <div class="err" id="e" role="alert"></div>
  </form>
  <div class="ft">関係者専用のページです。画面とデータは暗号化されています。<br>データの更新 __UPDATED__</div>
</div>
<script>
const G=__GATE__;
const b64d=s=>{const t=atob(s),a=new Uint8Array(t.length);for(let i=0;i<t.length;i++)a[i]=t.charCodeAt(i);return a;};
async function openBoard(u,p){
  const km=await crypto.subtle.importKey('raw',new TextEncoder().encode(u+':'+p),{name:'PBKDF2'},false,['deriveKey']);
  const kek=await crypto.subtle.deriveKey({name:'PBKDF2',salt:b64d(G.w.s),iterations:G.w.n,hash:'SHA-256'},km,{name:'AES-GCM',length:256},false,['decrypt']);
  const pk8=await crypto.subtle.decrypt({name:'AES-GCM',iv:b64d(G.w.i)},kek,b64d(G.w.c));
  const priv=await crypto.subtle.importKey('pkcs8',pk8,{name:'RSA-OAEP',hash:'SHA-256'},false,['decrypt']);
  const one=async x=>{const dek=await crypto.subtle.decrypt({name:'RSA-OAEP'},priv,b64d(x.k));const key=await crypto.subtle.importKey('raw',dek,{name:'AES-GCM'},false,['decrypt']);const z=await crypto.subtle.decrypt({name:'AES-GCM',iv:b64d(x.i)},key,b64d(x.c));return await new Response(new Blob([z]).stream().pipeThrough(new DecompressionStream('gzip'))).text();};
  const r=await Promise.all([one(G.a),one(G.d)]);
  if(r[0].indexOf('UCAR_BOARD')<0||r[0].indexOf('__DATA__')<0) throw new Error('bad');
  return r[0].split('__DATA__').join(r[1]);
}
const f=document.getElementById('f'),e=document.getElementById('e'),b=document.getElementById('b');
f.addEventListener('submit',async ev=>{
  ev.preventDefault();
  const u=document.getElementById('u').value.trim(),p=document.getElementById('p').value;
  if(!u||!p){e.textContent='IDとパスワードを入力してください';return;}
  b.disabled=true;b.textContent='開いています…';e.textContent='';
  try{const html=await openBoard(u,p);document.open();document.write(html);document.close();}
  catch(err){e.textContent='IDまたはパスワードが正しくありません';b.disabled=false;b.textContent='開く';}
});
document.getElementById('u').focus();
</script>
</body>
</html>
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['keygen', 'app', 'page'])
    ap.add_argument('--gate', default='gate')
    ap.add_argument('--html', help='app: 画面のHTML（__DATA__ を残したもの）')
    ap.add_argument('--data', help='page: データのJSON')
    ap.add_argument('--out', default='index.html')
    a = ap.parse_args()
    gate = Path(a.gate); gate.mkdir(parents=True, exist_ok=True)
    if a.mode == 'keygen':
        uid, pw = os.environ['BOARD_ID'], os.environ['BOARD_PW']
        priv = rsa.generate_private_key(public_exponent=65537, key_size=3072)
        der = priv.private_bytes(serialization.Encoding.DER, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        salt, iv = os.urandom(16), os.urandom(12)
        kek = hashlib.pbkdf2_hmac('sha256', f'{uid}:{pw}'.encode('utf-8'), salt, ITER, 32)
        (gate / 'wrapped.json').write_text(json.dumps({'s': b64(salt), 'i': b64(iv), 'n': ITER, 'c': b64(AESGCM(kek).encrypt(iv, der, None))}), encoding='utf-8')
        (gate / 'pub.pem').write_bytes(priv.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
        print('keygen: wrote', gate / 'wrapped.json', gate / 'pub.pem')
    elif a.mode == 'app':
        html = Path(a.html).read_text(encoding='utf-8')
        assert html.count('__DATA__') == 1 and 'UCAR_BOARD' in html, '画面のHTMLに __DATA__ と UCAR_BOARD が1つずつ必要'
        (gate / 'app.json').write_text(json.dumps(seal(load_pub(gate), html.encode('utf-8'))), encoding='utf-8')
        print('app: wrote', gate / 'app.json', (gate / 'app.json').stat().st_size)
    else:
        data = json.loads(Path(a.data).read_text(encoding='utf-8'))
        js = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
        g = {'w': json.loads((gate / 'wrapped.json').read_text()), 'a': json.loads((gate / 'app.json').read_text()), 'd': seal(load_pub(gate), js.encode('utf-8'))}
        upd = data.get('generated_at', '')
        page = GATE_HTML.replace('__GATE__', json.dumps(g, separators=(',', ':'))).replace('__UPDATED__', upd)
        Path(a.out).write_text(page, encoding='utf-8')
        print('page: wrote', a.out, Path(a.out).stat().st_size)


if __name__ == '__main__':
    main()
