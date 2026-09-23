# open-code — コーディングエージェントから LiteLLM を使う

OpenCode を LiteLLM 経由で使うための設定。**学生の手元 (PC / ECCS 端末) に
入れるもの**で、サーバに置くものではない。

```
OpenCode --https://taulec.zapto.org/litellm/v1--> Apache(443) --127.0.0.1:4000--> LiteLLM
```

LiteLLM の 4000 番は外に開いていない。Apache が `/litellm/v1/` だけを中継する。
管理系 (`/ui/`, `/key/*`, `/spend/*`) は公開されていない。

## ファイル

| | |
|---|---|
| `opencode.jsonc` | OpenCode の設定 (接続先とモデル一覧)。**鍵は書かない** (全員共通) |
| `opencode_setup` | 名簿のユーザの鍵を発行し、auth.json と opencode.jsonc を置く (サーバ用) |
| `opencode_setup.env.example` | `opencode_setup` の設定 (鍵を発行するときだけ要る) |
| `install` | 自分で設定する人 (ラップトップなど) 用。symlink を張る |

## 鍵と設定の関係

OpenCode はプロバイダ `litellm` に送るとき、接続先を `opencode.jsonc` から、
鍵を `~/.local/share/opencode/auth.json` の `"litellm"` の行から取る (ID が名前で対応する)。

```
~/.config/opencode/opencode.jsonc          "provider": { "litellm": { baseURL, models } }
~/.local/share/opencode/auth.json          { "litellm": { "type": "api", "key": "sk-..." }, ...ほかのプロバイダ }
```

`opencode.jsonc` の `options.apiKey` に鍵を書くとそちらが優先される (auth.json は見ない)。
ここでは書かない。

**鍵は 1 人 1 本。** 発行は `opencode_setup` が行い、学生への連絡は LMS で行う
(`opencode_setup` が鍵を埋めた名簿を出力する)。LiteLLM は鍵を**確認するだけ**で、
学生のアカウントを持たない。鍵を持っている人がその学生として扱われる。

## サーバで仕込む (opencode_setup)

名簿 (`user`, `email`, `litellm_key`, `litellm_team`, `class`) の選んだ行について、

1. 鍵: `litellm_key` 列の鍵を使う。空なら LiteLLM で発行する (`key_alias` = user)
2. `{prefix}/share/opencode/auth.json` の `"litellm"` の行をその鍵にする (ほかの行は残す)
3. `{config}/opencode/opencode.jsonc` に `--config-src` をコピー (または symlink) する

発行した鍵は **`-o` の CSV** に出す。入力の名簿そのままに `litellm_key` 列を埋めたもので、
それ以外のセルは変えない。入力も既存のファイルも上書きしない (鍵を発行する行があるのに
`-o` がなければ、発行する前に止まる)。この CSV は実行したユーザの権限で書くので
gocryptfs の中に置ける。

何度流しても同じ結果になる (鍵が埋まった名簿で流し直せば発行しない)。

### taulec

```
cp opencode_setup.env.example opencode_setup.env && chmod 600 opencode_setup.env
$EDITOR opencode_setup.env                    # LITELLM_API_KEY (下記)

./opencode_setup --sudo --class pl --dry-run roster.csv
./opencode_setup --sudo --class pl -o roster_keys.csv roster.csv
```

`--config` / `--prefix` の既定は `~{user}/.config` / `~{user}/.local` (本人のホーム)。
`--sudo` で root として流し直し、作ったものを本人の所有にする (名簿と設定ファイルは
sudo の前に実行したユーザの権限で読む)。学生は taulec にログインして `opencode` と打つだけ。

`roster_keys.csv` の `litellm_key` を LMS で各学生に返す。

### 別のクラスタ (ホーム非共有、root なし)

鍵は taulec で発行済みのものを使う (1 人 1 本)。そのクラスタのアカウント名で作った名簿の
`litellm_key` 列に、taulec の出力の鍵を貼っておく。鍵が埋まっていれば LiteLLM には繋がない。

```
./opencode_setup --config /shared/opencode/{user}/config \
    --prefix /shared/opencode/{user}/local sc_roster.csv
```

- root がないので所有者は変えない。**学生だけが自分の auth.json を読めるようにするのは
  その場所の仕組み (ACL など) 次第**。`--dir-mode` で作るディレクトリのモードを指定できる
- 学生は自分のものを所定の場所にコピーする (既存の auth.json があるなら `"litellm"` の行だけ足す):
  ```
  mkdir -p ~/.config/opencode ~/.local/share/opencode
  cp /shared/opencode/$USER/config/opencode/opencode.jsonc ~/.config/opencode/
  cp /shared/opencode/$USER/local/share/opencode/auth.json ~/.local/share/opencode/
  ```
- OpenCode 本体は共有ディレクトリに 1 つ置き (単体のバイナリ)、PATH に足してもらう
- 使うのはログインノードから (`https://taulec.zapto.org/litellm/v1` に届けばよい)

鍵の列が空の行があってそのクラスタで発行したい場合は、taulec の管理 API を port forward して
`--litellm-server http://localhost:4000 --site sc -o ...` を付ける (alias は `user@sc`)。
1 人 1 本を保つなら、発行は taulec でまとめて行う。

### LiteLLM の管理者キー (LITELLM_API_KEY)

Team と鍵を作れる鍵が 1 本要る。master key をコピーしても動くが、別に発行するのがよい
(漏れてもその鍵だけ無効にでき、master key を変えずに済む)。LiteLLM の管理画面で
Owned By = You (admin) で作るか、

```
. ../litellm/litellm.env      # LITELLM_MASTER_KEY (pd で)
curl -s http://127.0.0.1:4000/user/new -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "opencode_setup", "user_role": "proxy_admin", "key_alias": "opencode_setup"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["key"])'
```

### モデルを足したとき

- コピーなら `--force-config` を付けて流し直す (古いものは `.bak` に残る)。学生が自分で
  コピーした先は各自で取り直してもらう
- `--config-mode symlink` なら元ファイルを直すだけで全員に効く。元ファイルは学生が読める
  場所に置くこと (スクリプトが確かめる)

## 自分で設定する (ラップトップなど)

```
npm i -g opencode-ai            # OpenCode 本体 (未導入なら)
./install                       # ~/.config/opencode/opencode.jsonc -> このディレクトリの opencode.jsonc
opencode auth login             # Other → provider id に litellm → LMS で受け取った鍵を貼る
opencode
```

`opencode auth login` は鍵を auth.json に保存するだけで、何も確認しない (確認は LiteLLM が
リクエストごとに行う)。ブラウザは要らない。`opencode auth list` で保存を確かめられる。

**プロバイダ (Azure, mdx MaaS) のキーは手元に置かない。** すべて LiteLLM が
代理で持つ。学生に渡すのは virtual key 1 本。

## 使い方

| キー | 動作 |
|---|---|
| `Ctrl+X` `m` | モデル一覧を開く (leader は既定 `Ctrl+X`) |
| `F2` | 直前に使ったモデルへ切り替え |

既定モデルは `opencode.jsonc` の末尾 `"model"` で決まる。コーディング向けかどうかを
自動判定する仕組みは無く、**単に文字列で指定しているだけ**。

## 切り分け

設定をいじる前に curl で確かめると早い。

```
KEY=sk-...                      # 自分の鍵
curl -s https://taulec.zapto.org/litellm/v1/models -H "Authorization: Bearer $KEY" \
  | python3 -c 'import sys,json;print([m["id"] for m in json.load(sys.stdin)["data"]])'
```

| 結果 | 原因 |
|---|---|
| モデル一覧が返る | サーバ側は正常。`opencode.jsonc` の問題 |
| 401 | 鍵が違う、または Team / `models` の制限で弾かれている |
| 404 | `baseURL` の綴り。`/litellm/v1` まで、末尾スラッシュ無し |
| 接続エラー | ネットワーク側 |

`opencode models litellm` でも OpenCode 側から見えているモデルを確認できる。

## ⚠ モデル名は完全一致

`opencode.jsonc` の `models` のキーは、LiteLLM の `config.yaml` の `model_name` と
**完全一致**させること。サーバ側で改名したらここも直す。`name` は表示用ラベルなので自由。

## TUI なので端末を選ぶ

Emacs の `shell` buffer (`TERM=dumb`) ではまともに描画できない。
`M-x term` / `M-x vterm` か、普通の端末エミュレータから使うこと。
止めたいだけなら `C-c C-c`、効かなければ別端末から `pkill -f opencode`。

## 他のハーネス

aider など OpenAI SDK 互換のツールは環境変数で渡す:

```
export OPENAI_API_BASE=https://taulec.zapto.org/litellm/v1
export OPENAI_API_KEY=sk-...    # 自分の鍵
```

continue.dev は別で、`~/.continue/config.yaml` の `apiBase` を
`https://taulec.zapto.org/litellm/v1` に、`apiKey` を
`${{ secrets.LITELLM_API_KEY }}` にして `~/.continue/.env` に鍵を置く。
