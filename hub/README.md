
# systemd で常駐させる

ホスト起動時に自動で上がるようにする。従来の `./run_hub FQDN` の代わり。

```
sudo ln -sf /home/tau/jupyter_tools/hub/jupyterhub@.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now jupyterhub@taulec.zapto.org
```

`@` の後ろはサイトのディレクトリ名 (= FQDN)。`cfg.sh` と `jupyterhub.sqlite` が
置いてあるディレクトリを指す。

```
sudo systemctl status jupyterhub@taulec.zapto.org
sudo systemctl restart jupyterhub@taulec.zapto.org
journalctl -u jupyterhub@taulec.zapto.org -f
```

ログは `hub.log` ではなく journal に入る。ローテーションも journald が面倒を見る。
従来どおりファイルにも残したい場合は unit に

```
StandardOutput=append:/home/tau/jupyter_tools/hub/taulec.zapto.org/hub.log
```

を足す (肥大化は自分で管理すること)。

## 証明書

`jupyterhub_config.py` は `fullchain.crt` を参照する。リーフ単体だと
ブラウザは AIA 補完で繋がるが curl / Python / Node は
"unable to get local issuer certificate" で失敗する。
生成は ansible の `roles/cert` (`fullchain_dest` + `select_chain`)。
