# litellm — 授業用 LLM ゲートウェイ

学生からの全リクエストをここに通し、ユーザごとの鍵の発行・利用記録・
上流 API キーの秘匿を一手に引き受ける。

```
Open WebUI / OpenCode / aider  --->  LiteLLM  --->  UTokyo Azure
                                                    mdx MaaS
                                                    self-hosting (未)
```

待ち受けは **127.0.0.1:4000**。外からは Apache が `/litellm/v1/` だけを中継する
(`apache/litellm-subpath.conf`)。管理系 (`/ui/`, `/key/*`, `/spend/*`) は
公開しない。触るときは SSH トンネルを使う。

## ファイル

| | |
|---|---|
| `pyproject.toml` / `uv.lock` / `.python-version` | Python 環境。uv が 3.12 ごと用意する |
| `config.yaml` | モデル定義。上流の URL と実モデル名 |
| `litellm.env.example` | 秘密情報のテンプレート |
| `run_litellm` | 起動スクリプト |
| `litellm.service` | systemd user service |
| `install` | `deps` (uv sync + prisma generate) と `service` (user service の登録) |
| `apache/litellm-subpath.conf` | 443 の vhost に Include する (ansible が置く) |

## 設置

LiteLLM は **sudo 権限の無いアカウント (`pd`)** の systemd user service として動かす。
sudo が要る部分は ansible の `roles/litellm` に分けてある。

| 誰が | 何を |
|---|---|
| ansible (`roles/litellm`) | PostgreSQL の導入と LiteLLM 用のロール・DB の作成、`pd` の linger、Apache の `/litellm/v1/` 中継 |
| `pd` (`./install`) | `uv sync` + `prisma generate`、user service の登録と起動 |

1. ansible 側。DB のパスワードは `ansible/vars/litellm.yml` (実体は gocryptfs の
   `ansible/files/plain/litellm_taulec.yml`) に書く。雛形は `ansible/vars/litellm.yml.in`。

   ```
   cd ../ansible && ansible-playbook -i machines.ini litellm.yml
   ```

2. `pd` 側。`ssh pd@taulec` で**ログインして**行う (`sudo -u pd` や `su pd` からでは
   `systemctl --user` が使えない)。

   ```
   cp litellm.env.example litellm.env && chmod 600 litellm.env
   $EDITOR litellm.env
   ./install
   ```

`install` は `deps` / `service` を個別にも実行できる。

`litellm.env` に入れるもの:

| 変数 | 内容 |
|---|---|
| `OPENAI_API_KEY` | Azure のキー。`config.yaml` が `os.environ/OPENAI_API_KEY` で参照 |
| `MDX_MAAS_API_KEY` | mdx MaaS のキー |
| `LITELLM_MASTER_KEY` | プロキシの管理者キー。**学生には渡さない**。`python3 -c 'import secrets;print("sk-"+secrets.token_urlsafe(32))'` |
| `DATABASE_URL` | `postgresql://litellm:<pass>@127.0.0.1:5432/litellm` |
| `BIND_HOST` / `BIND_PORT` | `127.0.0.1` / `4000` |

`DATABASE_URL` のユーザ名・パスワード・DB 名は、ansible の `vars/litellm.yml` の
`litellm_db_user` / `litellm_db_password` / `litellm_db_name` と一致させること
(ロールと DB は ansible が作る)。

## 確認

```
curl -s http://127.0.0.1:4000/health/readiness      # {"status":"healthy","db":"connected"}
curl -s -o /dev/null -w '%{http_code}\n' https://taulec.zapto.org/litellm/v1/models   # 401 が正常
```

## 管理 (Admin UI)

127.0.0.1 でしか待ち受けていないので、手元から SSH トンネルを掘る。

```
ssh -L 4000:127.0.0.1:4000 taulec
```

→ http://localhost:4000/ui/ をブラウザで開く。
ユーザ名 `admin` / パスワードは `litellm.env` の `LITELLM_MASTER_KEY`
(`litellm/proxy/auth/login_utils.py`)。

## virtual key の発行

学生 1 人につき 1 本。**OAuth は「鍵を取りに行く一度だけ」の儀式**であって、
API 呼び出し自体は静的キーで行う (aider や opencode はブラウザリダイレクトを解さない)。

```
. ./litellm.env
curl -s http://127.0.0.1:4000/key/generate \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" -H "Content-Type: application/json" \
  -d '{
    "key_alias": "student-12345",
    "user_id":   "12345@g.ecc.u-tokyo.ac.jp",
    "team_id":   "<team id>",
    "models":    ["gpt-5.6-luna-utokyo-azure","gpt-5.3-codex-utokyo-azure","gpt-oss-20b-mdx-maas"],
    "duration":  "180d",
    "max_budget": 20
  }' | python3 -m json.tool
```

返る `key` は**一度しか表示されない** (DB にはハッシュで保存)。

`user_id` は「鍵の持ち主」。**Open WebUI のログインに使うメールと同じ文字列に
しておくと後で集計しやすい** (下記)。

その他:

```
curl -s http://127.0.0.1:4000/key/list   -H "Authorization: Bearer $LITELLM_MASTER_KEY"
curl -s http://127.0.0.1:4000/spend/logs -H "Authorization: Bearer $LITELLM_MASTER_KEY"
curl -s http://127.0.0.1:4000/key/delete -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
     -H "Content-Type: application/json" -d '{"keys":["sk-..."]}'
```

## `user_id` と `end_user` の違い

| | `user_id` | `end_user` |
|---|---|---|
| 指すもの | 鍵の持ち主 | そのリクエストを出した人 |
| 決まる時 | 鍵の発行時 (固定) | リクエストごと |
| 出所 | `/key/generate` の引数 | `X-OpenWebUI-User-Email` ヘッダ |

**Open WebUI** は鍵 1 本を全員で共有するので `end_user` で学生を識別する。
**ハーネス**は学生ごとに鍵を配るので `user_id` が本人になる。
同じ学生の利用が 2 つの列に分かれて記録されるので、集計時は両方を見る。
同じメールにしておけば単純な OR で足せる。

なお `user_id` に予算を付けても **Open WebUI 経由の利用は制限されない**
(あちらは service account の鍵で発行される)。

## Team

鍵をまとめて方針を掛ける箱。クライアントからは見えないが、クライアントの
見え方を決める。

- 使えるモデルの一覧
- 予算上限 (チーム合計)
- レート制限 (tpm / rpm)

⚠ **Team 作成時に Models を空のままにすると `["no-default-models"]` が入り、
その Team の鍵では `/v1/models` が空になる**。「未選択＝全部許可」ではない。
`All Proxy Models` を選ぶと `all-proxy-models` という予約語が一覧に混ざって
返るので、授業では使わせるモデルを明示選択する方が安全。

## モデルを追加・改名するときの手順

名前は **3 箇所に独立して保持される**。1 箇所だけ変えると静かにズレる。

### 1. `config.yaml`

```yaml
  - model_name: gpt-5.6-luna-utokyo-azure   # 外に見せる名前。ここを変える
    litellm_params:
      model: openai/gpt-5.6-luna            # 上流に送る実名。触らない
      api_base: https://tau-lecture-ai.openai.azure.com/openai/v1
      api_key: os.environ/OPENAI_API_KEY
```

上流のモデル名にスラッシュが含まれる場合は、LiteLLM が先頭のスラッシュまでを
プロバイダ名として剥がすので、プロバイダ名を重ねて書く:

```yaml
      model: openai/openai/gpt-oss-20b      # mdx MaaS の実名が "openai/gpt-oss-20b"
```

忘れると `Model gpt-oss-20b not found` になる (剥がされた後の名前がエラーに出る)。

### 2. 再起動

```
systemctl --user restart litellm     # pd でログインして
```

`config.yaml` は起動時にしか読まれない。ログに出る `periodic_reload_job` は
**モデル価格表の再取得専用**で無関係 (`litellm/proxy/proxy_server.py`)。

### 3. Team の許可リストを更新 ← 忘れやすい

```
curl -s -X POST http://127.0.0.1:4000/team/update \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" -H "Content-Type: application/json" \
  -d '{"team_id":"<id>","models":["<new>","<new>","<new>"]}'
```

### 4. Open WebUI 側

新しい名前のモデルは**アクセス制御が未設定なので管理者にしか見えない**。
管理者パネル → 設定 → モデル で **Public** にし、古い名前のレコードを削除する。

### 確認

3 経路で同じ一覧が返ること:

```
curl -s http://127.0.0.1:4000/v1/models -H "Authorization: Bearer $LITELLM_MASTER_KEY"
curl -s http://127.0.0.1:4000/v1/models -H "Authorization: Bearer <virtual key>"
# ブラウザの DevTools コンソールで
#   (await (await fetch('/api/models')).json()).data.map(m => m.id)
```

## ハマりどころ

**`prisma` は `litellm[proxy]` ではなく `extra_proxy` extra にある。**
`pyproject.toml` は `litellm[proxy,extra_proxy]` にしてある。外すと
`ModuleNotFoundError: No module named 'prisma'` で起動に失敗する。

**`prisma generate` は `.venv` を作り直すたびに必要。** スキーマはリポジトリでは
なく `.venv` 内のパッケージにある。`install deps` が両方やる。

**PostgreSQL 必須。** `schema.prisma` の datasource が `postgresql` 固定で
SQLite は使えない。

**起動ログに出る次の 2 つは無害。**
- `Error getting model info: This model isn't mapped yet` — 価格表に無いモデル。
  トークン数は記録されるが金額が出ないだけ
- `AttributeError: 'Prisma' object has no attribute '_Prisma__engine'` — 起動
  シーケンス中に握りつぶされる内部例外。その後 `db: connected` なら問題ない

**`--detailed_debug` は付けない。** リクエスト/レスポンスの本文 (学生の
プロンプトと LLM の応答) がそのままログに出る。切り分け時だけ一時的に。
