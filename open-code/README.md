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
| `opencode.jsonc` | OpenCode の設定。`~/.config/opencode/opencode.jsonc` へ symlink する |
| `client.env.example` | base URL と virtual key のテンプレート |
| `run_opencode` | `client.env` を読んで opencode を起動する |
| `install` | symlink を張る |

## 設置

```
# OpenCode 本体 (未導入なら)
npm i -g opencode-ai

./install
cp client.env.example client.env && chmod 600 client.env
$EDITOR client.env      # 配られた virtual key を入れる
./run_opencode
```

`client.env` に入れるのは 2 つだけ。

```
export LITELLM_BASE_URL=https://taulec.zapto.org/litellm/v1   # 末尾 /v1 まで
export LITELLM_API_KEY=sk-...
```

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
. ./client.env
curl -s "$LITELLM_BASE_URL/models" -H "Authorization: Bearer $LITELLM_API_KEY" \
  | python3 -c 'import sys,json;print([m["id"] for m in json.load(sys.stdin)["data"]])'
```

| 結果 | 原因 |
|---|---|
| モデル一覧が返る | サーバ側は正常。`opencode.jsonc` の問題 |
| 401 | 鍵が違う、または Team / `models` の制限で弾かれている |
| 404 | `LITELLM_BASE_URL` の綴り。`/litellm/v1` まで、末尾スラッシュ無し |
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

`client.env` は `OPENAI_API_BASE` / `OPENAI_API_KEY` も export するので、
aider など OpenAI SDK 互換のツールはそのまま使える。

continue.dev は別で、`~/.continue/config.yaml` の `apiBase` を
`https://taulec.zapto.org/litellm/v1` に、`apiKey` を
`${{ secrets.LITELLM_API_KEY }}` にして `~/.continue/.env` に鍵を置く。
