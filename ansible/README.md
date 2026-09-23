# ansible — サーバの下ごしらえ

新しい VM を授業用サーバに仕立てるところまで。LLM 環境そのもの
(`../litellm`, `../open-webui`) はこの後に手で入れる。

`~/lectures/make_env/ansible` から**このサーバ構成に要る役割だけ**を移したもの。
slurm / cuda / pytorch / xrdp / lustre / jupyter 系の role は持ってきていない
(元の `all.yml` でも `hosts: none` で無効化されていた)。

## 使い方

```
cp vars/cert.yml.in vars/cert.yml && $EDITOR vars/cert.yml
cp vars/ldap.yml.in vars/ldap.yml && $EDITOR vars/ldap.yml
cp files/ldap_users.csv.in  files/ldap_users.csv  && $EDITOR files/ldap_users.csv
cp files/ldap_groups.csv.in files/ldap_groups.csv && $EDITOR files/ldap_groups.csv
$EDITOR machines.ini          # ホスト名・IP を新しい VM に合わせる

ansible-playbook -i machines.ini all.yml
```

`vars/*.yml` と `files/*.csv` は**秘密・個人情報を含むのでコミットしない**
(`.gitignore` 済み)。`.in` がテンプレート。

## playbook

| | |
|---|---|
| `all.yml` | 全部。新しい VM にはこれを流す |
| `cert.yml` | 証明書だけ取り直したいとき |
| `users.yml` | LDAP のユーザだけ入れ直したいとき |

## role

| role | 役割 | hosts |
|---|---|---|
| `basics` | timezone, hostname, /etc/hosts, apt upgrade, 基本パッケージ | default |
| `nfs_server` + `attach_home` | /home のボリュームを mount して NFS export | nfs_server |
| `nfs_client` | NFS の /home を mount | nfs_client |
| `mv_home_ansible_user` | `ansible_user` の HOME を /home.local へ退避 (nfs_{server,client} が include) | — |
| `ldap_server` | slapd。ドメインと管理者パスワードを設定 | ldap_server |
| `ldap_client` | sssd。LDAP を名前解決に使う | ldap_client |
| `ldap_users` | csv からユーザとグループを作る | ldap_server |
| `sss_invalidate` | sss のキャッシュを飛ばす | ldap_client |
| `ldap_sudo` | LDAP グループに sudo 権限を与える | ldap_client |
| `apache` | apache2 と userdir / ssl / headers モジュール | web_server |
| `cert` | Let's Encrypt の証明書取得と apache への設定 | web_server |

## 証明書について

`cert` role は **`fullchain.crt`** を作り、Apache にはそちらを使わせる。
リーフ証明書単体だとブラウザは AIA 補完で繋がるが、**curl / Python / Node は
`unable to get local issuer certificate` で失敗する**。コーディングエージェントは
これらの上に乗っているので、リーフだけでは学生の手元から使えない。

さらに `select_chain` で、新ルート (ISRG Root YR) を既存の ISRG Root X1 が
クロス署名したチェーンを選ぶ。新ルートはまだ OS のトラストストアに配布されて
いないため、これが無いと同じく検証に失敗する。

移行が終わって代替チェーンが提供されなくなると `select_chain` は警告なく既定の
チェーンに戻るので、その後に `openssl verify` で検証するタスクを入れてある。
壊れたら**学生の環境ではなく playbook の実行時に**気づける。

JupyterHub も `fullchain.crt` を参照する (`../hub/jupyterhub_config.py`)。

## この後にやること

`../README.md` の「新しいサーバを一から作る順番」を参照。
uv の導入 → LiteLLM → Open WebUI → 常駐化 → JupyterHub と続く。
