# singleuser — 学生の Jupyter 環境

JupyterHub (`../hub`) が学生ごとに起動するサーバの環境。hub (root) とは別の
venv で、**share が所有する `/home/share/jupyter_tools/singleuser/.venv`** に入れる
(`../hub/jupyterhub.env` の `SINGLEUSER_VENV`)。学生全員がこの venv の python を
実行するので、全員が読める場所に置く。

中身: jupyterhub-singleuser, JupyterLab 4, Notebook 7, nbgrader, Jupyter AI,
remote_ipykernel。カーネルは python3 (taulec 上) と Python (Miyabi G)。

**jupyterhub のバージョンは `../hub/pyproject.toml` と必ず揃えること。**

## ファイル

| | |
|---|---|
| `pyproject.toml` / `uv.lock` / `.python-version` | Python 環境 (3.12) |
| `install` | venv を作り、nbgrader の共通設定とカーネルを入れる |
| `kernels/miyabi/` | Miyabi G のカーネル (全員共通)。`kernel.json` とランチャー `miyabi_kernel.py` |

## 設置・更新

share で (sudo 不要)。uv が無ければ先に入れる (`curl -LsSf https://astral.sh/uv/install.sh | sh`)。

```
cd ~/jupyter_tools/singleuser
./install
```

`install` がやること:

- `uv sync --frozen` で `.venv` を作る
- `../nbgrader/common/nbgrader_config.py` を venv の `etc/jupyter/` に symlink する
  (全学生・全教員アカウントに効く共通設定)
- `kernels/*` を `jupyter kernelspec install --sys-prefix` で venv の
  `share/jupyter/kernels/` に入れる (全員に見える)
- venv と uv の Python を全員が読めるようにする

パッケージを足すときは `pyproject.toml` を直して `uv lock` し、`./install` を流し直す。
**新しい環境は、次に起動する学生のサーバから使われる。** 起動中のサーバは
学生が一度止める (File → Hub Control Panel → Stop My Server) か、hub を再起動するまで
古い環境のまま。カーネルの追加・変更は、ランチャーを開き直せば起動中のサーバにも見える。

## Miyabi G カーネル: kernels/miyabi

自前のランチャー `kernels/miyabi/miyabi_kernel.py` (表示名 "Python (Miyabi G)") が Miyabi のログインノードで
ipykernel を動かす。以前は remote_ipykernel を使っていたが、セッションを食い潰す・失敗が遅く学生に見えない・
Miyabi 側でポートが衝突しうる、のでやめた。

各ユーザに要るもの: `~/.ssh/config` の `Host miyabig` (enroll が置く) と、`mount-miyabi` (または `ssh miyabig`)
でログインしてできた ControlMaster。

- ControlMaster に相乗りするだけで自分では認証しない (`BatchMode=yes`, `ControlMaster=no`)
- カーネル 1 つにつき Miyabi のセッションは 1 本 (カーネル本体)。ポート転送はマスターに `ssh -O forward` で
  張り (セッションを使わない)、終了時に `-O cancel` する。マスターの転送は頼んだ ssh が終わっても残るので、
  強制終了で残ったものは `~/.local/state/miyabi-kernel/forwards/` の記録から次回起動時に消す
- ポートは Miyabi 側で空いているものを選ぶ (taulec の番号をそのまま使う remote_ipykernel は Miyabi 側の
  他人のポートと衝突しうる。miyabi-g3 の実測で起動 1 回あたり約 5%)
- カーネルの鍵は ssh の標準入力で渡す (コマンドラインに出さない)。Miyabi 側の接続ファイルは
  `~/.local/share/miyabi-kernel/` に 0600 で作り、終了時に消す。taulec 側が消えると (標準入力の EOF)
  Miyabi 側のカーネルも止まる
- notebook が `~/miyabi/...` にあれば Miyabi の `/work/gt81/share/home/<user>/...` で動く (それ以外は Miyabi のホーム)
- 起動できないとき (未ログイン、セッション上限、venv が無い、起動直後に落ちた) は、理由と対処を英語で
  表示するだけの代わりのカーネルが taulec で動く。学生はセルを実行すると理由が見える。カーネルは死なない
  ので Jupyter の再起動の連鎖も起きない
- 中断は `interrupt_mode: message` (Jupyter が制御チャネルで送り、ipykernel が受ける)
- ログ: 各ユーザの `~/.local/state/miyabi-kernel/log` と、journal (`[miyabi-kernel <user> ...]` 付き)
- Miyabi 側の venv は `REMOTE_PYTHON` (`/work/gt81/share/env/.venv/bin/python`)。ipykernel が入っていればよい

## Miyabi のファイルをマウントする (mount-miyabi)

Miyabi とセットのクラスでは、学生のファイルは Miyabi の `/work/gt81/share/home/<Miyabi のユーザ>` に置き、
taulec の `~/miyabi` に sshfs でマウントして見せる。`~/notebooks/<class>` はそこへのリンク
(enroll が作る。`../enroll/README.md`)。

```
taulec$ ssh-keygen -t ed25519   # 最初の 1 回。パスフレーズを付ける。~/.ssh/id_ed25519.pub を Miyabi のポータルに登録
taulec$ mount-miyabi         # Miyabi にログイン (パスフレーズ + TOTP) してから ~/miyabi にマウント
taulec$ mount-miyabi -s      # 状態
taulec$ mount-miyabi -u      # アンマウント
```

- `bin/mount-miyabi`。`/usr/local/bin/mount-miyabi` からのリンクと sshfs の導入は ansible (`roles/jupyterhub`)
- 端末は Jupyter の端末でよい (PC から taulec に ssh する必要はない)
- マスターが無ければ、まず `ssh miyabig true` でログインさせる (パスフレーズと verification code を聞かれる)。
  `ControlMaster auto` + `ControlPersist` なので、これがそのままマスターとして残る
- 鍵は学生が taulec 上で `ssh-keygen` して作り、公開鍵を Miyabi のポータルに登録する。鍵が無ければ
  (`~/.ssh/id_*` も agent の鍵も無ければ) 作り方を英語で案内して終わる。自動では作らない。
  agent を転送して入ってきた人は、agent の鍵でもよい
- sshfs は `ssh -o BatchMode=yes -o ControlMaster=no` で ControlMaster に相乗りする (TOTP 不要)
- マウント中は sshfs がマスターの利用者なので、`ControlPersist` が切れてもマスターは残る
- Miyabi 側のディレクトリは何も作らない。自分のディレクトリが無ければエラー、`~/notebooks/*` のリンク先
  (`notebooks/<class>`) が無ければ警告 (どちらも「教員に連絡」)
- **Miyabi 側のディレクトリは教員が先に作る。** `miyabi` repo の `scripts/mk-course-dirs.sh` を t81000 で
  (`/work/gt81/share/env/miyabi` から) 流す。教員の所有で 0700、ACL でその学生と他の教員 (t81148) に rwx、
  default ACL で中に作られるものにも付く。グループ (gt81) は授業の全員なので、グループには権限を与えない:
  ```
  miyabi$ /work/gt81/share/env/miyabi/scripts/mk-course-dirs.sh -n t81149 t81150   # 確認
  miyabi$ /work/gt81/share/env/miyabi/scripts/mk-course-dirs.sh t81149 t81150
  ```
- マスターが切れると sshfs は応答しなくなる (`Transport endpoint is not connected`)。`mount-miyabi` し直せば
  ログインからやり直す (古いマウントは自動で外す)

## 既知の警告

`jupyter labextension list` で `@jupyter/nbgrader` に ✗ (incompatible) が付く。
`@jupyter/ydoc` のバージョン範囲の食い違いで、以前使っていた JupyterLab 4.3 でも
同じ表示になる。Assignments / Formgrader の画面が動けば問題ない。動かない場合は
`pyproject.toml` で `jupyterlab==4.3.*` に固定する。
