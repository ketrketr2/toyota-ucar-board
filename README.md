# UCAR SIGNAL｜中古車AI検索 タイアップ効果ボード

公開URL：https://ketrketr2.github.io/toyota-ucar-board/ （ID とパスワードで開きます）
9月の版：https://ketrketr2.github.io/toyota-ucar-board/v05/

## 毎朝の自動更新（.github/workflows/ucar-refresh.yml）
- 07:12（予備の便 08:40）に、計測データ（ketrketr2/toyota-geo-board）からボードのデータを作り直します。
- 点検（tools/check.py）に通った版だけを公開します。通らないときは公開せず、前の版を残したまま Issue でお知らせします。
- 18:05 に翌日の計測の予定を確かめ、予定日の前日に【予告】の Issue を出します。
- お知らせは GitHub の通知（メール）で届きます。Slack にも送るときは、Settings > Secrets and variables > Actions に SLACK_WEBHOOK_URL を登録します。

## 鍵のしくみ
- 画面（gate/app.json）とデータは暗号化してあり、閲覧時の ID とパスワードで開きます。
- 自動更新は公開鍵（gate/pub.pem）だけでデータを暗号化します。パスワードと秘密鍵は、このリポジトリにも自動更新の環境にも置きません。

## 掲載が始まったら
- tools/rounds.json の publish_start に、最初の記事の掲載日（YYYY-MM-DD）を書きます。その日以降の計測を「掲載後」として数え、ボードの見出しと判定が自動で掲載後の比較に切り替わります。
