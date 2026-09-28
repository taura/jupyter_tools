# agents — コーディングエージェント (OpenCode, Codex CLI) から LiteLLM を使う

```
OpenCode / Codex CLI --https://taulec.zapto.org/litellm/v1--> Apache(443) --127.0.0.1:4000--> LiteLLM
```

LiteLLM の 4000 番は外に開いていない。Apache が `/litellm/v1/` だけを中継する。
管理系 (`/ui/`, `/key/*`, `/spend/*`) は公開されていない。

サーバ (taulec や別のクラスタ) では `agent_setup` が鍵と設定を仕込む。学生の手元 (PC) では
各自が設定する。

## ファイル

| | |
|---|---|
| `opencode.jsonc` | OpenCode の設定 (接続先とモデル一覧)。**鍵は書かない** (全員共通) |
| `codex.toml` | Codex CLI の `config.toml` (接続先と既定のモデル)。**鍵は書かない** (全員共通) |
| `agent_setup` | 名簿のアカウントの鍵を発行し、各エージェントの鍵と設定を置く (サーバ用) |
| `agent_setup.env.example` | `agent_setup` の設定 (鍵を発行するときだけ要る) |
| `install` | OpenCode を自分で設定する人 (ラップトップなど) 用。symlink を張る |

## 鍵と設定の関係

どちらのエージェントも、接続先は設定ファイルに、鍵は資格情報のファイルに置く。

| | 設定 (共通) | 鍵 |
|---|---|---|
| OpenCode | `~/.config/opencode/opencode.jsonc` の `"provider": { "litellm": ... }` | `~/.local/share/opencode/auth.json` の `"litellm"` の行 (ID が名前で対応。ほかのプロバイダの行と同居) |
| Codex CLI | `~/.codex/config.toml` (`model_provider = "litellm"`, `requires_openai_auth = true`) | `~/.codex/auth.json` (`{"auth_mode": "apikey", "OPENAI_API_KEY": ...}`。**ログイン情報 1 つだけのファイル**) |

- OpenCode は `options.apiKey` を書くとそちらが優先される (auth.json は見ない)。ここでは書かない
- Codex は `requires_openai_auth = true` のプロバイダに auth.json の鍵を送る。自分で入れるなら
  `printf %s "$KEY" | codex login --with-api-key`

**鍵は 1 アカウント 1 本** (両方のエージェントで同じ鍵)。発行は `agent_setup` が行い、学生への連絡は
LMS で行う (`agent_setup` が鍵を埋めた名簿を出力する)。LiteLLM は鍵を**確認するだけ**で、
学生のアカウントを持たない。鍵を持っている人がその学生として扱われる。

## サーバで仕込む (agent_setup)

名簿 (`user`, `litellm_user`, `litellm_key`, `litellm_team`, `class`) の選んだ行について、

| 段階 | |
|---|---|
| `key` | `litellm_key` 列の鍵を使う。空なら `litellm_user` を持ち主 (LiteLLM の `user_id`) として発行する (`key_alias` = user)。**両方とも空の行は何もしない** |
| `oc_auth` | `{prefix}/share/opencode/auth.json` の `"litellm"` の行をその鍵にする (ほかの行は残す) |
| `oc_config` | `{config}/opencode/opencode.jsonc` に `--opencode-config` をコピー (または symlink) |
| `codex_auth` | `{codex_home}/auth.json` を作る |
| `codex_config` | `{codex_home}/config.toml` に `--codex-config` をコピー (または symlink) |

**設定ファイルと Codex の auth.json は上書きしない。** すでにあって中身が違えば、そのまま残して
警告に出す (学生が自分で書いた設定や、ChatGPT でのログインを壊さないため)。`--agents opencode` /
`--agents codex` で片方だけにできる。

発行した鍵は **`-o` の CSV** に出す。入力の名簿そのままに `litellm_key` 列を埋めたもので、
それ以外のセルは変えない。入力も既存のファイルも上書きしない (鍵を発行する行があるのに
`-o` がなければ、発行する前に止まる)。この CSV は実行したユーザの権限で書くので
gocryptfs の中に置ける。

何度流しても同じ結果になる (鍵が埋まった名簿で流し直せば発行しない)。

### taulec

```
cp agent_setup.env.example agent_setup.env && chmod 600 agent_setup.env
$EDITOR agent_setup.env                       # LITELLM_API_KEY (下記)

./agent_setup --sudo --class pl --dry-run roster.csv
./agent_setup --sudo --class pl -o roster_keys.csv roster.csv
```

`--config` / `--prefix` / `--codex-home` の既定は `~{user}/.config` / `~{user}/.local` /
`~{user}/.codex` (本人のホーム)。`--sudo` で root として流し直し、作ったものを本人の所有にする
(名簿と設定ファイルは sudo の前に実行したユーザの権限で読む)。学生は taulec にログインして
`opencode` / `codex` と打つだけ。

`roster_keys.csv` の `litellm_key` を LMS で各学生に返す。

### 別のクラスタ (ホーム非共有、root なし)

鍵は taulec で発行済みのものを使う (1 アカウント 1 本)。そのクラスタのアカウント名で作った名簿の
`litellm_key` 列に、taulec の出力の鍵を貼っておく。鍵が埋まっていれば LiteLLM には繋がない。

```
./agent_setup --config /shared/agents/{user}/config --prefix /shared/agents/{user}/local \
    --codex-home /shared/agents/{user}/codex sc_roster.csv
```

- root がないので所有者は変えない。**学生だけが自分の auth.json を読めるようにするのは
  その場所の仕組み (ACL など) 次第**。`--dir-mode` で作るディレクトリのモードを指定できる
- 学生は自分のものを所定の場所にコピーする (既存の OpenCode の auth.json があるなら `"litellm"`
  の行だけ足す。Codex の auth.json は置き換わる):
  ```
  mkdir -p ~/.config/opencode ~/.local/share/opencode ~/.codex
  cp /shared/agents/$USER/config/opencode/opencode.jsonc ~/.config/opencode/
  cp /shared/agents/$USER/local/share/opencode/auth.json ~/.local/share/opencode/
  cp /shared/agents/$USER/codex/config.toml /shared/agents/$USER/codex/auth.json ~/.codex/
  ```
- エージェントの本体は共有ディレクトリに置き (どちらも単体のバイナリ)、PATH に足してもらう
- 使うのはログインノードから (`https://taulec.zapto.org/litellm/v1` に届けばよい)

鍵の列が空の行があってそのクラスタで発行したい場合は、taulec の管理 API を port forward して
`--litellm-server http://localhost:4000 --site sc -o ...` を付ける (alias は `user@sc`)。
1 アカウント 1 本を保つなら、発行は taulec でまとめて行う。

### LiteLLM の管理者キー (LITELLM_API_KEY)

Team と鍵を作れる鍵が 1 本要る。master key をコピーしても動くが、別に発行するのがよい
(漏れてもその鍵だけ無効にでき、master key を変えずに済む)。LiteLLM の管理画面で
Owned By = You (admin) で作るか、

```
. ../litellm/litellm.env      # LITELLM_MASTER_KEY (pd で)
curl -s http://127.0.0.1:4000/user/new -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "agent_setup", "user_role": "proxy_admin", "key_alias": "agent_setup"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["key"])'
```

### モデルを足したとき

- コピーした設定は上書きしないので、雛形を直しても配り直されない。学生の設定を消してから流し直すか、
  各自で取り直してもらう
- `--config-mode symlink` なら雛形を直すだけで全員に効く。雛形は学生が読める場所に置くこと
  (スクリプトが確かめる)

## 自分で設定する (ラップトップなど)

OpenCode:

```
npm i -g opencode-ai            # OpenCode 本体 (未導入なら)
./install                       # ~/.config/opencode/opencode.jsonc -> このディレクトリの opencode.jsonc
opencode auth login             # Other → provider id に litellm → LMS で受け取った鍵を貼る
opencode
```

Codex CLI:

```
npm i -g @openai/codex          # Codex CLI 本体 (未導入なら)
mkdir -p ~/.codex && cp codex.toml ~/.codex/config.toml
printf %s "$KEY" | codex login --with-api-key      # LMS で受け取った鍵
codex
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

GPT-6 は Chat Completions の `max_tokens` を受け付けないため、`opencode.jsonc` ではモデルごとの
`provider.npm` を `@ai-sdk/openai` にして LiteLLM の `/v1/responses` を使う。ほかのモデルは
`@ai-sdk/openai-compatible` のまま `/v1/chat/completions` を使う。

## ⚠ モデル名は完全一致

`opencode.jsonc` の `models` のキーと `codex.toml` の `model` は、LiteLLM の `config.yaml` の
`model_name` と **完全一致**させること。サーバ側で改名したらここも直す。`name` は表示用ラベルなので自由。

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
