# jupyter_tools

# FILES

* README.md
* authoring/   --- tools to convert texts (.py, .sos, .c) into .ipynb
* grading/     --- tools to grade .ipynb files
* hub/         --- JupyterHub 本体 (root, /opt/jupyterhub)。Google (ECCS) + ローカルアカウントでログイン
* singleuser/  --- 学生の Jupyter 環境 (share, /home/share/venv/jupyter)。JupyterLab, nbgrader, カーネル
* monitoring/  --- monitor, record, and visualize student activities
* nbgrader/    --- example config files for nbgrader
* ansible/     --- 新しい VM をサーバに仕立てる (ldap, nfs, apache, 証明書)
* litellm/     --- 授業用 LLM ゲートウェイ (鍵の発行・利用記録・上流 API の秘匿)
* open-webui/  --- 学生向けチャット playground (Google 認証)
* open-code/   --- コーディングエージェント (学生の手元に入れる)

These tools are mostly independent.  You can use monitoring, for example, without using any other directories

See README.md in each directory for how to use each of them.

---

# 授業用 LLM 環境

```
Client / UI                Routing                    API endpoint
-----------                -------                    ------------
Open WebUI (ブラウザ)  --> LiteLLM                --> UTokyo Azure
OpenCode / aider           認証・鍵発行・利用記録      mdx MaaS
                                                       self-hosting (未)
```

| ディレクトリ | 動く場所 | 待ち受け |
|---|---|---|
| `litellm/` | サーバ | 127.0.0.1:4000 → Apache が `https://FQDN/litellm/v1/` で中継 |
| `open-webui/` | サーバ | 127.0.0.1:8080 → Apache が `https://FQDN:3000` で中継 |
| `open-code/` | **学生の手元** | — |
| `hub/` | サーバ | JupyterHub 本体 (root, `/opt/jupyterhub`, `jupyterhub.service`) |
| `singleuser/` | サーバ | 学生の Jupyter 環境 (share, `/home/share/venv/jupyter`) |

構成要素はそれぞれ独立した uv プロジェクト。**1 つの環境に同居させられない**
(`open-webui` が `cryptography==48.0.0` を厳密固定し、`litellm[proxy]` は
`>=48.0.1` を要求する)。

## 新しいサーバを一から作る順番

前提: Ubuntu 24.04 / Apache 2.4 / 証明書がある / ドメイン名が引ける。

### 0. VM の下ごしらえ (ansible)

```
cd ansible
cp vars/cert.yml.in vars/cert.yml   && $EDITOR vars/cert.yml
cp vars/ldap.yml.in vars/ldap.yml   && $EDITOR vars/ldap.yml
cp vars/litellm.yml.in files/plain/litellm_taulec.yml && ln -s ../files/plain/litellm_taulec.yml vars/litellm.yml
$EDITOR vars/litellm.yml            # LiteLLM の DB パスワード
cp vars/jupyterhub.yml.in files/plain/jupyterhub_taulec.yml && ln -s ../files/plain/jupyterhub_taulec.yml vars/jupyterhub.yml
$EDITOR vars/jupyterhub.yml         # Google の OAuth クライアント (Open WebUI と同じ)
cp files/ldap_users.csv.in  files/ldap_users.csv  && $EDITOR files/ldap_users.csv
cp files/ldap_groups.csv.in files/ldap_groups.csv && $EDITOR files/ldap_groups.csv
$EDITOR machines.ini
ansible-playbook -i machines.ini all.yml
```

ldap / nfs / apache / 証明書に加えて、LiteLLM と Open WebUI のうち sudo が要る部分
(PostgreSQL、linger、Apache の中継) と JupyterHub 本体までがこれで整う。詳細は `ansible/README.md`。

以下の 1〜6 は **AI 関係を動かすアカウント `pd` (sudo 権限なし) で `ssh pd@taulec` して**
行う。`sudo -u pd` や `su pd` からでは `systemctl --user` が使えない。

### 1. リポジトリ

unit ファイルが `%h/jupyter_tools/...` を参照するので、**ホームの直下に
`jupyter_tools` として置く**こと。

```
cd ~ && git clone git@github.com:taura/jupyter_tools.git
```

### 2. uv

apt には無い (Ubuntu 25.04 以降を除く)。Python も uv が用意するので
pyenv や deadsnakes は不要。

```
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.local/bin/env
```

### 3. 証明書の確認

`ansible/roles/cert` が `fullchain.crt` を作っている。**リーフ単体ではいけない**
(ブラウザは AIA 補完で繋がるが curl / Python / Node は失敗する)。
Apache も JupyterHub も `fullchain.crt` を参照すること。

```
echo | openssl s_client -connect FQDN:443 -servername FQDN 2>&1 | grep "Verify return code"
# → 0 (ok)
```

### 4. LiteLLM

```
cd ~/jupyter_tools/litellm
cp litellm.env.example litellm.env && chmod 600 litellm.env
$EDITOR litellm.env
./install
```

### 5. Open WebUI

```
cd ~/jupyter_tools/open-webui
cp oauth.env.example oauth.env && chmod 600 oauth.env
$EDITOR oauth.env          # ← BASE_URL を最初から正しい https:// にすること
./install
```

⚠ **最初の起動で `BASE_URL` が DB に焼き付く。** 間違えると後から
`oauth.env` を直しても効かない (open-webui/README.md 参照)。

ブラウザで開いて **最初にログインした人が管理者**になる。その後
管理者パネルからモデル接続 (LiteLLM) を設定し、モデルを Public にする。

### 6. 常駐化

linger (これが無いとログアウトで止まる) は ansible (`roles/litellm`, `roles/open_webui`)
が設定済み。`install service` が unit の symlink と `enable --now` まで行う。
一度 `sudo reboot` して両方が自動で上がることを確認しておく。

### 7. JupyterHub

学生の環境を share で作ってから (`singleuser/README.md`)、hub を ansible で入れる
(`hub/README.md`)。

```
ssh share@taulec 'cd ~/jupyter_tools/singleuser && ./install'
cd ansible && ansible-playbook -i machines.ini jupyterhub.yml
```

Google の OAuth クライアントは Open WebUI と同じもの。リダイレクト URI に
`https://FQDN:8000/hub/google/oauth_callback` を追加しておく。

### 8. 学生への配布

1. LiteLLM で virtual key を 1 人 1 本発行 (litellm/README.md)
2. `open-code/` の使い方を案内 (open-code/README.md)
3. Open WebUI は URL を伝えるだけ。`https://` を明示するよう念を押す

## 秘密情報

`*.env.example` と `ansible/vars/*.yml.in` だけをコミットし、実値の入った `*.env` と
`ansible/vars/*.yml` (実体は gocryptfs の `ansible/files/plain/`) は `.gitignore` してある。**学生に渡すのは virtual key 1 本だけ**で、上流
プロバイダ (Azure, mdx MaaS) のキーがクライアントに出ることはない。

## 未着手

* 鍵配布の自動化 (Google OIDC でログインさせ `/key/generate` を叩く小さな Web アプリ)。
  LiteLLM 自身の SSO は 5 ユーザまで無料、それ以上は Enterprise。JWT 認証も Enterprise 限定
* 予算とレート制限 (Team の `max_budget`、鍵の `rpm_limit`) の設定
* 履修者名簿との突き合わせ
* 記録の設計 — 何を残し、教員に何を見せるか
