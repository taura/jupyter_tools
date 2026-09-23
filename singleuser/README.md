# singleuser — 学生の Jupyter 環境

JupyterHub (`../hub`) が学生ごとに起動するサーバの環境。hub (root) とは別の
venv で、**share が所有する `/home/share/venv/jupyter`** に入れる。学生全員が
この venv の python を実行するので、全員が読める場所に置く。

中身: jupyterhub-singleuser, JupyterLab 4, Notebook 7, nbgrader, ipywidgets,
カーネル (python3, bash, sos), numpy / pandas / matplotlib / networkx / pydot。

**jupyterhub のバージョンは `../hub/pyproject.toml` と必ず揃えること。**

## ファイル

| | |
|---|---|
| `pyproject.toml` / `uv.lock` / `.python-version` | Python 環境 (3.12) |
| `install` | venv を作り、カーネルと nbgrader の共通設定を入れる |

## 設置・更新

share で (sudo 不要)。uv は ansible (`roles/jupyterhub`) が `/usr/local/bin` に入れてある。

```
cd ~/jupyter_tools/singleuser
./install
```

`install` がやること:

- `uv sync --frozen` で `/home/share/venv/jupyter` を作る。uv が入れる Python も
  `/home/share/venv/python` に置く (どちらも全員が読める)
- bash / sos カーネルを venv の中に登録する
- `../nbgrader/common/nbgrader_config.py` を venv の `etc/jupyter/` に symlink する
  (全学生・全教員アカウントに効く共通設定)

パッケージを足すときは `pyproject.toml` を直して `uv lock` し、`./install` を流し直す。
**新しい環境は、次に起動する学生のサーバから使われる。** 起動中のサーバは
学生が一度止める (File → Hub Control Panel → Stop My Server) か、hub を再起動するまで
古い環境のまま。

以前の pip の venv (`python -m venv` で作ったもの) が同じ場所に残っていると
`install` は止まる。中身を確認して消してから流し直す。

## 既知の警告

`jupyter labextension list` で `@jupyter/nbgrader` に ✗ (incompatible) が付く。
`@jupyter/ydoc` のバージョン範囲の食い違いで、以前使っていた JupyterLab 4.3 でも
同じ表示になる。Assignments / Formgrader の画面が動けば問題ない。動かない場合は
`pyproject.toml` で `jupyterlab==4.3.*` に固定する。
