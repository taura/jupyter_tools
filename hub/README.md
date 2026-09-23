# hub — JupyterHub

```
ブラウザ --https:8000--> JupyterHub (root, /opt/jupyterhub)
                           |  Google (ECCS) / Local (PAM) でログイン
                           v
                         学生のサーバ (学生の uid, /home/share/venv/jupyter)
                           jupyterhub-singleuser + JupyterLab + nbgrader + カーネル
```

venv は 2 つに分けてある。

| | 場所 | 所有 | 中身 | 作る人 |
|---|---|---|---|---|
| hub | `/opt/jupyterhub/venv` | root | jupyterhub, oauthenticator, multiauthenticator | ansible (`roles/jupyterhub`) |
| 学生 | `/home/share/venv/jupyter` | share | jupyterhub-singleuser, jupyterlab, nbgrader, カーネル, numpy 等 | share (`../singleuser/install`) |

hub は root で動くので、hub が実行するものは root 所有にしてある (share が書き換え
られると root 権限を取られる)。学生の環境は share が sudo なしで更新できる。

**jupyterhub のバージョンは `pyproject.toml` と `../singleuser/pyproject.toml` で
必ず揃えること。**

## ファイル

| | |
|---|---|
| `pyproject.toml` / `uv.lock` / `.python-version` | hub の venv。ansible が `/opt/jupyterhub` にコピーして `uv sync --frozen` する |
| `jupyterhub_config.py` | 設定。ansible が `/opt/jupyterhub/` にコピーする |
| `user_map.py` | Google のメール → ローカルユーザの対応表。config から import される + CLI |

systemd unit と環境変数ファイルは ansible の `roles/jupyterhub/templates/` にある。

サーバ上の配置:

| | |
|---|---|
| `/opt/jupyterhub/` | venv, uv の Python, `jupyterhub_config.py`, `user_map.py` |
| `/etc/jupyterhub/jupyterhub.env` | `FQDN`, Google のクライアント ID/シークレット等 (0600) |
| `/var/lib/jupyterhub/` | 作業ディレクトリ。`jupyterhub.sqlite`, cookie secret, `user_map.sqlite` |
| `/etc/systemd/system/jupyterhub.service` | unit |

## 設置・更新

1. `ansible/vars/jupyterhub.yml` に Google の OAuth クライアント (Open WebUI と同じ) を書く。
   雛形は `ansible/vars/jupyterhub.yml.in`
2. Google Cloud Console の「承認済みのリダイレクト URI」に
   `https://taulec.zapto.org:8000/hub/google/oauth_callback` を追加 (完全一致)
3. share で学生の環境を作る (`../singleuser/README.md`)
4. hub:
   ```
   cd ../ansible && ansible-playbook -i machines.ini jupyterhub.yml
   ```

設定 (`jupyterhub_config.py`) や依存 (`pyproject.toml`) を変えたら、手元で
`uv lock` してから 4. を流し直す。**変更があると hub を再起動するので、起動中の
学生のサーバも止まる** (授業中に流さない)。

```
sudo systemctl status  jupyterhub
sudo systemctl restart jupyterhub
journalctl -u jupyterhub -f
```

## ログイン

ログインページに 2 つのボタンが出る。

| ボタン | 誰が | ユーザ名 |
|---|---|---|
| Google (ECCS) | 学生 | `10桁@g.ecc.u-tokyo.ac.jp` を `user_map` でローカルユーザ (`u26000` 等) に変換 |
| Local Account | 教員, TA, 授業用アカウント | LDAP のユーザ名とパスワード (PAM, sssd 経由) |

Google では `g.ecc.u-tokyo.ac.jp` 以外のアカウントは弾く (`hosted_domain`)。

## user_map

Google のメールアドレスとローカルユーザの対応表 (`/var/lib/jupyterhub/user_map.sqlite`)。
初回ログイン時に、登録済みなら対応するローカルユーザになり、未登録なら
`self_register` が on のときだけ空いているローカルユーザ (`user` が空の行) を割り当てる。

作業ディレクトリで root として操作する:

```
cd /var/lib/jupyterhub
sudo /opt/jupyterhub/venv/bin/python /opt/jupyterhub/user_map.py show
sudo /opt/jupyterhub/venv/bin/python /opt/jupyterhub/user_map.py binds users.csv   # user,local 列
sudo /opt/jupyterhub/venv/bin/python /opt/jupyterhub/user_map.py local u26000      # 割り当て候補に追加
sudo /opt/jupyterhub/venv/bin/python /opt/jupyterhub/user_map.py register on       # 自己登録を許す
```

**キーは Google のメールアドレス (`10桁@g.ecc.u-tokyo.ac.jp`)。** 以前の UTokyo Account
(`10桁@utac.u-tokyo.ac.jp`) の表は使えないので作り直す。LDAP のユーザ CSV の
`10桁` 列から作れる。

## 証明書

`jupyterhub_config.py` は `fullchain.crt` を参照する。リーフ単体だと
ブラウザは AIA 補完で繋がるが curl / Python / Node は
"unable to get local issuer certificate" で失敗する。
生成は ansible の `roles/cert` (`fullchain_dest` + `select_chain`)。
