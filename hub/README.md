# hub — JupyterHub

```
ブラウザ --https:8000--> JupyterHub (root, このディレクトリから直接動く)
                           |  Google (ECCS) / Local (PAM) でログイン
                           v
                         学生のサーバ (学生の uid, /home/share/venv/jupyter)
                           jupyterhub-singleuser + JupyterLab + nbgrader + カーネル
```

**hub はこの checkout (`~tau/jupyter_tools/hub`) から直接動く。** 設定やプログラムの
変更は `git pull` して再起動するだけ。ansible (`roles/jupyterhub`) がやるのは
configurable-http-proxy と systemd unit を置く最初の 1 回だけ。

venv は 2 つに分けてある。

| | 場所 | 所有 | 中身 | 作る人 |
|---|---|---|---|---|
| hub | `hub/.venv` | tau | jupyterhub, oauthenticator, multiauthenticator | tau (`uv sync`) |
| 学生 | `/home/share/venv/jupyter` | share | jupyterhub-singleuser, jupyterlab, nbgrader, カーネル, numpy 等 | share (`../singleuser/install`) |

hub は root で動くが、tau はもともと sudoer なので、tau のファイルを root が実行しても
権限が広がることはない。学生の環境は share が sudo なしで更新できる (share は sudoer
ではないので、root はこちらを実行しない)。

**jupyterhub のバージョンは `pyproject.toml` と `../singleuser/pyproject.toml` で
必ず揃えること。**

## ファイル

| | |
|---|---|
| `pyproject.toml` / `uv.lock` / `.python-version` | hub の venv (`uv sync` で `.venv`) |
| `jupyterhub_config.py` | 設定 |
| `user_map.py` | Google のメール → ローカルユーザの対応表。config から import される + CLI |
| `jupyterhub.env.example` | 秘密情報 (`jupyterhub.env`) の雛形 |
| `jupyterhub.env` | `FQDN`, Google のクライアント ID/シークレット等。commit しない (0600) |
| `state/` | 作業ディレクトリ (tau 所有 0700, commit しない)。`jupyterhub.sqlite`, cookie secret (root 所有 0600), `user_map.sqlite` (tau 所有) |

systemd unit は `../ansible/roles/jupyterhub/templates/jupyterhub.service.j2`。
`state/` は起動時に unit が作る。

## 設置

1. hub の venv と秘密情報 (tau で)
   ```
   cd ~/jupyter_tools/hub
   uv sync
   cp jupyterhub.env.example jupyterhub.env && chmod 600 jupyterhub.env
   $EDITOR jupyterhub.env        # Google の OAuth クライアント (Open WebUI と同じ)
   ```
2. Google Cloud Console の「承認済みのリダイレクト URI」に
   `https://taulec.zapto.org:8000/hub/google/oauth_callback` を追加 (完全一致)
3. share で学生の環境を作る (`../singleuser/README.md`)
4. configurable-http-proxy と unit (最初の 1 回だけ)
   ```
   cd ../ansible && ansible-playbook -i machines.ini jupyterhub.yml
   ```

## 更新

```
git pull
uv sync                         # pyproject.toml / uv.lock が変わったときだけ
sudo systemctl restart jupyterhub
```

**再起動すると起動中の学生のサーバも止まる** (授業中にやらない)。依存を変えるときは
`uv lock` してから commit する。

```
sudo systemctl status  jupyterhub
journalctl -u jupyterhub -f
```

## ログイン

ログインページに 2 つのボタンが出る。

| ボタン | 誰が | ユーザ名 |
|---|---|---|
| Google (ECCS) | 学生 | 申告された g.ecc のアドレスを `user_map` でローカルユーザ (`u26000` 等) に変換 |
| Local Account | 教員, TA, 授業用アカウント | LDAP のユーザ名とパスワード (PAM, sssd 経由) |

Google では `g.ecc.u-tokyo.ac.jp` 以外のアカウントは弾く (`hosted_domain`)。

## user_map

Google のメールアドレスとローカルユーザの対応表 (`state/user_map.sqlite`)。
**ふだんの登録は `../enroll` が名簿から行う。** 以下は個別に見たり直したりするとき。

`state/` で tau として操作する (`user_map.py` はカレントディレクトリの `user_map.sqlite`
を開く。標準ライブラリだけなので venv は要らない)。`state/` と `user_map.sqlite` は tau
所有にしてあるので sudo は要らない (hub が root で書き込んでも所有者は変わらない):

```
cd ~/jupyter_tools/hub/state
python3 ../user_map.py show
python3 ../user_map.py binds users.csv   # user,local 列
python3 ../user_map.py local u26000      # 割り当て候補に追加
python3 ../user_map.py register on       # 自己登録を許す
```

**別のディレクトリで実行すると、そこに空の `user_map.sqlite` ができる** (hub が見ている
ものとは別物) ので注意。

**キーは Google のメールアドレス。** 以前の UTokyo Account (`10桁@utac.u-tokyo.ac.jp`)
の表は使えないので作り直す。

## 証明書

`jupyterhub_config.py` は `fullchain.crt` を参照する。リーフ単体だと
ブラウザは AIA 補完で繋がるが curl / Python / Node は
"unable to get local issuer certificate" で失敗する。
生成は ansible の `roles/cert` (`fullchain_dest` + `select_chain`)。
