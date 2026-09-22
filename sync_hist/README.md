# usage

- すべての hist.sqlite を taulec から download する
```
./sync_hist.sh 
```

- `ldap_users_taulec.ods` が読めるようにする

```
gocryptfs /home/tau/lectures/make_env/ansible/files/enc /home/tau/lectures/make_env/ansible/files/plain
```

的なことをして symlink を貼る

- `hist_viewer` を作る 

```
make -f hist2html.mk
```

注: 

- `dl_viewer` も作ろうとするので適宜コメントアウトする
- `hist_viewer` は hist を元に作る
- `dl_viewer` は submit されたデータ `dl/assignments/submitted/...` を元に作る

無事できたら

```
firefox hist_viewer/index.html
```

