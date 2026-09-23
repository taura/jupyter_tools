# enroll — 学生を授業のサービスに登録する

**すでにある Unix (LDAP) アカウント**に、Jupyter と Open WebUI の設定を注入する。
アカウントとホームは別の手段 (ansible の `ldap_users` など) で事前に多めに作っておく前提。
LiteLLM の鍵は `../open-code/opencode_setup` が発行する (1 人 1 本)。

```
roster.csv  (user, email, class, real_name)
   │  ./enroll roster.csv          ← tau が taulec 上で実行。自分で sudo し直す
   ▼
 0. アカウントが実在するか         (なければスキップ)
 1. ~/notebooks                    なければ作る (本人所有)
 2. JupyterHub user_map            email -> user を bind
 3. Open WebUI                     いなければ事前登録 (role=user)。pending なら user に上げる
   ▼
 レポート: 各段階の件数 / スキップ・エラー (理由つき) / 名簿にない登録者
```

**何度流しても同じ結果になる**。足りないものだけを作るので、授業中に登録者が
増えたら名簿に行を足して流し直すだけでよい。**何も削除しない** (名簿から消えた人は
レポートに出るだけ)。

## 使い方

```
cp enroll.env.example enroll.env && chmod 600 enroll.env
$EDITOR enroll.env                 # OPENWEBUI_API_KEY は必須

./enroll --dry-run roster.csv      # 何が起きるかだけ見る
./enroll roster.csv
./enroll --class pl roster.csv                 # class 列が pl の行だけ
./enroll --user u26050,u26051 roster.csv       # --class と両方指定したら両方を満たす行だけ
```

名簿と `enroll.env` は sudo し直す前に tau の権限で読むので、gocryptfs の中に置いたままでよい。

## 名簿

| 列 | |
|---|---|
| `user` | Unix アカウント名 (必須)。実在しない行はスキップ |
| `email` | 学生が申告した Google (ECCS) のアドレス。`10桁@g.ecc` とは限らない。空なら 1 だけ行う |
| `class` | 授業。`--class` で絞るときに使う |
| `real_name` | Open WebUI の表示名 (任意。空なら `user`) |

ほかの列は無視するので、`opencode_setup` と同じ名簿 (`litellm_key` などの列つき) を
そのまま渡せる。`email` は小文字にそろえる。`GOOGLE_DOMAIN` (既定 `g.ecc.u-tokyo.ac.jp`)
以外、名簿内での `user` / `email` の重複、別のユーザに対応付け済みの email はスキップして
レポートに出す。

## Open WebUI

名簿の人は事前登録されるので、Google でログインすればすぐ使える。名簿にない人の
扱いは `../open-webui/oauth.env` の `ENABLE_OAUTH_SIGNUP` で切り替える
(`../open-webui/README.md` の「履修者の絞り込み」)。

管理者 API キーは、管理者パネル → 設定 → 一般 で API キーを有効にしてから、
設定 → アカウント → API キー で発行する。

## ファイル

| | |
|---|---|
| `enroll` | 本体 |
| `litellm_admin.py` | 名簿の読み込み・sudo し直し・LiteLLM の管理 API。`../open-code/opencode_setup` と共用 |
| `enroll.env.example` | 設定の雛形 |

## 前提

- user_map は JupyterHub (`ansible/roles/jupyterhub`) の `/var/lib/jupyterhub/user_map.sqlite`
  を `/opt/jupyterhub/user_map.py` で操作する
- システムの python3 だけで動く (追加のパッケージ不要)
