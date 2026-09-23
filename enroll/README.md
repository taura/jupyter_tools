# enroll — 学生を授業のサービスに登録する

**すでにある Unix (LDAP) アカウント**に、Jupyter と AI 関係の設定を注入する。
アカウントとホームは別の手段 (ansible の `ldap_users` など) で事前に多めに作っておく前提。

```
roster.csv  (user, email, litellm_team, real_name)
   │  ./enroll roster.csv          ← tau が taulec 上で実行。自分で sudo し直す
   ▼
 0. アカウントが実在するか         (なければスキップ)
 1. ~/notebooks                    なければ作る (本人所有)
 2. JupyterHub user_map            email -> user を bind
 3. LiteLLM                        Team (litellm_team) がなければ作る
                                   鍵ファイルがない人だけ発行 -> ~/.litellm_key (0600, 本人所有)
 4. Open WebUI                     いなければ事前登録 (role=user)。pending なら user に上げる
   ▼
 レポート: 各段階の件数 / スキップ・エラー (理由つき) / 名簿にない登録者
```

**何度流しても同じ結果になる**。足りないものだけを作るので、授業中に登録者が
増えたら名簿に行を足して流し直すだけでよい。**何も削除しない** (名簿から消えた人は
レポートに出るだけ)。

## 使い方

```
cp enroll.env.example enroll.env && chmod 600 enroll.env
$EDITOR enroll.env                 # OPENWEBUI_API_KEY と LITELLM_API_KEY は必須

./enroll --dry-run roster.csv      # 何が起きるかだけ見る
./enroll roster.csv
./enroll --only u26050,u26051 roster.csv
```

## 名簿

| 列 | |
|---|---|
| `user` | Unix アカウント名 (必須)。実在しない行はスキップ |
| `email` | 学生が申告した Google (ECCS) のアドレス。`10桁@g.ecc` とは限らない。空なら 1 だけ行う |
| `litellm_team` | LiteLLM の Team の alias。なければ作る (その時点の全モデルを許可)。空なら Team なし |
| `real_name` | Open WebUI の表示名 (任意。空なら `user`) |

ほかの列は無視するので、`ldap_users.csv` に `email` と `litellm_team` を足したものを
そのまま渡せる。`email` は小文字にそろえる。`GOOGLE_DOMAIN` (既定 `g.ecc.u-tokyo.ac.jp`)
以外、名簿内での `user` / `email` の重複、別のユーザに対応付け済みの email はスキップして
レポートに出す。

## 鍵 (~/.litellm_key)

LiteLLM は鍵を**発行時に一度しか表示しない**ので、このファイルが唯一の控え。
学生は JupyterHub に Google でログインし、ターミナルで `cat ~/.litellm_key` すれば
自分の鍵が分かる。opencode などはここから読む
(サーバで仕込むなら `"apiKey": "{file:~/.litellm_key}"`)。

鍵を作り直すときは、LiteLLM で古い鍵を消し (`/key/delete`、alias はユーザ名)、
`~/.litellm_key` を消してから流し直す。

## Open WebUI

名簿の人は事前登録されるので、Google でログインすればすぐ使える。名簿にない人の
扱いは `../open-webui/oauth.env` の `ENABLE_OAUTH_SIGNUP` で切り替える
(`../open-webui/README.md` の「履修者の絞り込み」)。

管理者 API キーは、管理者パネル → 設定 → 一般 で API キーを有効にしてから、
設定 → アカウント → API キー で発行する。

## LiteLLM の管理者キー (LITELLM_API_KEY)

Team と鍵を作れる鍵が 1 本要る。master key をコピーしても動くが、enroll 用に
別に発行するのがよい (漏れてもその鍵だけ無効にでき、master key を変えずに済む)。

```
. ../litellm/litellm.env      # LITELLM_MASTER_KEY (pd で)
curl -s http://127.0.0.1:4000/user/new -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "enroll", "user_role": "proxy_admin", "key_alias": "enroll"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["key"])'
```

返った鍵を `enroll.env` の `LITELLM_API_KEY` に書く。無効にするときは
`/key/delete` (`{"key_aliases": ["enroll"]}`)。

## 前提

- user_map は JupyterHub (`ansible/roles/jupyterhub`) の `/var/lib/jupyterhub/user_map.sqlite`
  を `/opt/jupyterhub/user_map.py` で操作する
- システムの python3 だけで動く (追加のパッケージ不要)
