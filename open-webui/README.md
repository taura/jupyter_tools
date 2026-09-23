# open-webui — 授業用チャット playground

学生が Google (ECCS) アカウントでログインして使う Web UI。
モデルは直接叩かず、必ず同じホストの LiteLLM を経由する。

```
ブラウザ --https:3000--> Apache --http://127.0.0.1:8080--> Open WebUI
                                                             |
                                          http://127.0.0.1:4000/v1 (LiteLLM)
```

**Open WebUI 自身は TLS を張れない**。`open_webui/__init__.py` の `uvicorn.run()`
に `ssl_keyfile` / `ssl_certfile` が渡されておらず、CLI にも環境変数にも口がない。
前段に Apache を置く。

## ファイル

| | |
|---|---|
| `pyproject.toml` / `uv.lock` / `.python-version` | Python 環境 (3.12 固定) |
| `oauth.env.example` | 秘密情報とホスト固有設定のテンプレート |
| `run_open_webui` | 起動スクリプト |
| `open-webui.service` | systemd user service |
| `install` | `deps` (uv sync) と `service` (user service の登録) |
| `apache/open-webui-tls.conf.j2` | 3000 番の SSL vhost。ansible の template (`roles/open_webui`) |

Python は **3.12 固定**。`open-webui` が `>=3.11,<3.13` を要求するため。
また **`litellm[proxy]` と同居できない** (`cryptography==48.0.0` と `>=48.0.1` が
衝突する) ので、litellm とは別の uv プロジェクトにしてある。

## 設置

### 1. Google OAuth クライアントを作る

[console.cloud.google.com](https://console.cloud.google.com) を **g.ecc アカウント**で開く。

1. プロジェクトを作る
2. **OAuth 同意画面** → User Type は **内部 (Internal)**。
   選べない場合は外部になり、未審査だとテストユーザー 100 人が上限
   (授業規模で詰まる)。組織配下でプロジェクトを作り直せないか要相談
3. **認証情報 → OAuth クライアント ID → ウェブ アプリケーション**
   - 承認済みのリダイレクト URI: `https://example.org:3000/oauth/google/login/callback`
     **完全一致**。末尾スラッシュ、`localhost` と `127.0.0.1` も別物
   - JavaScript 生成元はパスも末尾スラッシュも書けない。そもそも Open WebUI は
     サーバサイドのリダイレクトフローなのでこの欄は使われない

### 2. 導入

Open WebUI は **sudo 権限の無いアカウント (`pd`)** の systemd user service として動かす。
sudo が要る部分は ansible の `roles/open_webui` に分けてある。

| 誰が | 何を |
|---|---|
| ansible (`roles/open_webui`) | `pd` の linger、Apache の 3000 番 vhost (TLS 終端 → 127.0.0.1:8080) |
| `pd` (`./install`) | `uv sync`、user service の登録と起動 |

ポート (3000 / 8080) は `roles/open_webui/defaults/main.yml` にある。変えるときは
`oauth.env` の `BASE_URL` / `BIND_PORT` も揃えること。

1. `pd` 側。`ssh pd@taulec` で**ログインして**行う (`sudo -u pd` や `su pd` からでは
   `systemctl --user` が使えない)。**先に `BASE_URL` と `BIND_PORT` を入れておく**
   (下の「環境変数は初回起動時だけ DB に焼き付く」)。

   ```
   cp oauth.env.example oauth.env && chmod 600 oauth.env
   $EDITOR oauth.env      # BASE_URL=https://taulec.zapto.org:3000, BIND_PORT=8080
   ./install
   ```

2. ansible 側。3000 番を Apache 以外が掴んでいると止まる。

   ```
   cd ../ansible && ansible-playbook -i machines.ini open_webui.yml
   ```

### 3. モデル接続を設定 (初回のみ、ブラウザから)

環境変数では設定できない。**管理者パネル → 設定 → 接続** の
「Manage OpenAI API Connections」で:

| 項目 | 値 |
|---|---|
| URL | `http://127.0.0.1:4000/v1` |
| Key | LiteLLM で発行した service account の virtual key |

`/v1` を忘れない。既定で入っている `https://api.openai.com/v1` の接続は無効に
しておく (残すと LiteLLM を通らない経路が生き続け、記録が漏れる)。

モデルは接続に付いてくる。**モデルごとに接続先を指定する設定は無い**。
Open WebUI は有効な接続それぞれに `GET /models` を投げ、返ってきた ID を
その接続のものとして扱う。

### 4. モデルを Public にする

取得したモデルは**アクセス制御が未設定なので管理者にしか見えない**
(`utils/models.py` "only admins can see unconfigured models")。
管理者パネル → 設定 → モデル で Public にする。

## 最初のユーザが管理者になる

`utils/oauth.py` の `user_count == 1` のときだけ `admin` が付く。
以後の新規ユーザは `DEFAULT_USER_ROLE` (既定 `pending` = 承認待ち)。
**後から勝手に管理者が増えることはない**。

昇格経路が塞がっていることの確認:

| 経路 | 状態 |
|---|---|
| パスワードでの新規登録 | `ENABLE_SIGNUP` 既定 false |
| Google からの新規登録 | 有効。ただしロールは `pending` |
| IdP のグループで admin 付与 | `ENABLE_OAUTH_ROLE_MANAGEMENT` 既定 false。**有効にしない** |
| ドメイン外 | `OAUTH_ALLOWED_DOMAINS` で拒否 |

## 履修者の絞り込み

`ALLOWED_DOMAIN` はドメインまでしか絞れず、`g.ecc.u-tokyo.ac.jp` は東大の全構成員。
ただし `DEFAULT_USER_ROLE` が `pending` なので、**新規ユーザは何も使えない**。
素通しではない。

履修者だけを摩擦なく通すには、名簿からアカウントを**事前に作っておく**。
`OAUTH_MERGE_ACCOUNTS_BY_EMAIL=true` により初回ログイン時に新規作成ではなく
事前登録済みアカウントへ紐づく (`utils/oauth.py`)。名簿に無い人は `pending` に落ちる。

- 管理者パネル → ユーザー の **Add User** (CSV インポートもある)
- API なら `POST /api/v1/auths/add`

`DEFAULT_USER_ROLE` は `pending` のまま変えないこと。

## ⚠ 環境変数は「初回起動時だけ」DB に焼き付く

設定の多くは **PersistentConfig**。`models/config.py` の `seed_defaults` が起動時に
「DB にまだ無いキーだけ」を環境変数で埋め、以後は **DB の値が優先**される
("Existing DB values take precedence over defaults")。

**最初の起動から正しい `BASE_URL` にしておくこと。** 一度間違った URL で起動すると
`oauth.env` を直しても効かず、DB を書き換えるしかなくなる。

実際に踏んだ例: Apache 導入前に `BASE_URL=http://...` で起動 → `webui.url` に
http が保存され、その後 https に直しても **Google ログイン後のリダイレクトだけ
http に飛んでエラー** (`utils/oauth.py` が `Config.get('webui.url')` を見るため。
パスワードログインはこの経路を通らないので再現しない)。

直し方 (停止してから):

```
python3 -c "
import sqlite3, json, os
db = os.path.expanduser('~/open-webui-data/webui.db')
c = sqlite3.connect(db)
c.execute('update config set value=? where key=?',
          (json.dumps('https://example.org:3000'), 'webui.url'))
c.commit()"
```

管理者パネルの **設定 → インターフェース** にも WebUI URL の欄はあるが、説明が
「通知のリンク生成用」となっていて見つけにくい。

## データの置き場

`run_open_webui` が `DATA_DIR=~/open-webui-data` を設定する。
**既定は `.venv` の中**なので、そのままだと `uv sync` のやり直しや `.venv` 削除で
全ユーザ・全チャットが消える。

既存の DB を引き継ぐ場合:

```
mkdir -p ~/open-webui-data
cp -a .venv/lib/python3.12/site-packages/open_webui/data/. ~/open-webui-data/
```

## ハマりどころ

**Apache reload の前に Open WebUI を 8080 に移す。** 3000 番を掴んだままだと
Apache が bind できない。`roles/open_webui` は 3000 番を Apache 以外が使っていたら
止まるようにしてある。

**`/ws/socket.io/` を `/` より先にプロキシする。** 順序が逆だと画面は出るのに
応答が流れてこない。

**`ProxyTimeout` は `<Location>` の中では使えない。** `ProxyPass` の
`timeout=600` パラメータで書く。既定 60 秒だと長い生成が途中で切れる。

**`X-Forwarded-Proto https` を渡す。** 無いと OAuth のリダイレクト URL を
`http://` で組み立てて Google に弾かれる。

**平文 HTTP で 3000 を叩くと** `You're speaking plain HTTP to an SSL-enabled
server port.` になる。`https://` を明示すること。

**構成を変えた直後の不可解な挙動は Service Worker を疑う。** Open WebUI は PWA で
オフラインキャッシュを持つ。サーバのログに何も出ないのにエラーが出る場合、
DevTools → アプリケーション → Service Workers を登録解除し、サイトデータを削除する。
スーパーリロードでは直らない。

## 起動時の警告

| 出力 | 判断 |
|---|---|
| `AuthlibDeprecationWarning` | 無視。Open WebUI 自身のコード |
| `USER_AGENT environment variable not set` | 無視 |
| `embeddings.position_ids UNEXPECTED` | 無視。ログ自身が "can be ignored" と言っている |
| `CORS_ALLOW_ORIGIN IS SET TO '*'` | `run_open_webui` が `$BASE_URL` に設定するので出ないはず |

起動のたびに Hugging Face へ埋め込みモデルの確認通信が出る。外向き通信が
制限された環境では `HF_HUB_OFFLINE=1` を足す。
