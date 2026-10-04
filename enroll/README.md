# enroll — 学生を授業のサービスに登録する

**すでにある Unix (LDAP) アカウント**に、Jupyter、Open WebUI、Miyabi への ssh の設定を注入する。
アカウントとホームは別の手段 (ansible の `ldap_users` など) で事前に多めに作っておく前提。
LiteLLM の鍵は `../agents/agent_setup` が発行する (1 人 1 本)。

```
roster.csv  (user, jupyter_user, webui_user, miyabi, notebooks, class, real_name)
   │  ./enroll roster.csv          ← tau が taulec 上で実行。自分で sudo し直す
   ▼
 0. アカウントが実在するか         (なければスキップ)
 1. ~/notebooks                    なければ作る (本人の権限で。列によらず常に)
 2. JupyterHub user_map            jupyter_user -> user を bind      (jupyter_user が空なら何もしない)
 3. Open WebUI                     webui_user を事前登録 (role=user)  (webui_user が空なら何もしない)
                                   pending なら user に上げる
 4. ~/.ssh/config                  ssh_config の Host miyabig / miyabic を追記 (miyabi が空なら何もしない)
 5. ~/miyabi, ~/notebooks/<class>  notebooks 列が miyabi の行だけ (下記)
   ▼
 レポート: 各段階の件数 / スキップ・エラー (理由つき) / 名簿にない登録者
```

**何度流しても同じ結果になる**。足りないものだけを作るので、授業中に登録者が
増えたら名簿に行を足して流し直すだけでよい。**何も削除しない** (名簿から消えた人は
レポートに出るだけ)。

## 使い方

```
cp enroll.env.example enroll.env && chmod 600 enroll.env
$EDITOR enroll.env                 # OPENWEBUI_API_KEY (webui_user のある行があるときだけ必要)

./enroll --dry-run roster.csv      # 何が起きるかだけ見る
./enroll roster.csv
./enroll --class pl roster.csv                 # class 列が pl の行だけ
./enroll --user u26050,u26051 roster.csv       # --class と両方指定したら両方を満たす行だけ
```

名簿と `enroll.env` は sudo し直す前に tau の権限で読むので、gocryptfs の中に置いたままでよい。

## 名簿

| 列 | |
|---|---|
`xxx_user` 列はそのサービスでのログイン ID (Google アカウント)。**空にした列のサービスは
その行では何もしない**ので、「鍵だけ」「Jupyter だけ」などを行ごとに選べる。

| 列 | |
|---|---|
| `user` | Unix アカウント名 (必須)。実在しない行はスキップ |
| `jupyter_user` | JupyterHub に Google でログインしてこの `user` に着地するアカウント。**名簿の中で一意** (Google ログインの着地先は 1 つだけ) |
| `webui_user` | Open WebUI のアカウント (= Google アカウント)。重複してよい (同じアカウントになるだけ) |
| `miyabi` | Miyabi のアカウント (`t81xxx`)。`~/.ssh/config` の `User` になる |
| `notebooks` | `~/notebooks/<class>` の置き場所。空または `local` = taulec (`~/notebooks` を作るだけ)、`miyabi` = Miyabi (下記)。それ以外の値はエラーとして報告 |
| `class` | 授業。`--class` で絞るときに使う |
| `real_name` | Open WebUI の表示名 (任意。空なら `user`) |

学生が申告した Google (ECCS) のアドレスを入れる (`10桁@g.ecc` とは限らない)。
ふつうは同じアドレスを `jupyter_user` / `webui_user` / `litellm_user` に入れる。

同じ人が 2 つのアカウントを持つ (学生と TA など) ときは、Google で着地させたいほうの行にだけ
`jupyter_user` を書く。もう一方は Local Account (パスワード) でログインする。`jupyter_user` が
重複していたら 2 行目以降の user_map だけスキップしてレポートに出す。

ほかの列は無視するので、`agent_setup` と同じ名簿 (`litellm_user`, `litellm_key` などの列つき)
をそのまま渡せる。アドレスは小文字にそろえる。`GOOGLE_DOMAIN` (既定 `g.ecc.u-tokyo.ac.jp`)
以外のアドレス、`user` の重複、別のユーザに対応付け済みの `jupyter_user` はスキップして
レポートに出す。

## ~/.ssh/config (Miyabi)

`ssh_config` (このディレクトリ) がテンプレート。`{miyabi}` が名簿の `miyabi` 列に置き換わる。
**中身を変えたいときはこのファイルを直す。** Host ごとに、まだ無いものだけを末尾に追記する:

- `~/.ssh/config` が無ければ作る (`~/.ssh` 0700, `config` 0600)
- 既に `Host miyabig` があれば (学生が自分で書いたものも) その Host は触らない。`miyabic` だけ無ければ `miyabic` だけ足す
- テンプレートを直しても、既に書かれた学生の設定は書き換わらない (直したいなら本人のものを消して流し直す)

書き込みは (`~/notebooks` も) root ではなく**そのユーザの権限**で行う (学生が `~/.ssh` をシンボリックリンクにして root に
別の場所を書かせることを防ぐ)。

鍵は学生が taulec 上で作る (`ssh-keygen -t ed25519`、パスフレーズは空にしない)。公開鍵を Miyabi の
ポータルに登録し、Jupyter の端末で `mount-miyabi` すると (パスフレーズと TOTP を入力) ControlMaster が
でき、`ControlPersist` の間、カーネル・sshfs・`ssh miyabig` はそれに相乗りする。PC から taulec への ssh や
agent の転送は要らない (PC の鍵で直接 Miyabi に入りたい人は、その公開鍵も別にポータルに登録する)。

`HostName` は `miyabi-g.jcahpc.jp` (DNS で g1/g3 に振り分け)。相乗りは ControlPath のソケット経由で
DNS を引き直さないので、ControlMaster がある限り同じノードに行き、TOTP は再要求されない。
ログインノードの host key は g1/g2/g3 で共通 (2026-10 に確認)。
Jupyter の Miyabi G カーネルは `ssh miyabig` のログイン (ControlMaster) に相乗りするので、
使う前に `mount-miyabi` (または `ssh miyabig`) でログインしておく (`../singleuser/README.md`)。

## Miyabi とセットのクラス (notebooks=miyabi)

名簿の `notebooks` 列が `miyabi` の行では、

```
~/miyabi/                                    mount-miyabi のマウントポイント (空, 0700)
~/notebooks/<class> -> ../miyabi/notebooks/<class>
```

を作る。`~/miyabi` には `mount-miyabi` が Miyabi の `/work/gt81/share/home/<miyabi>` を sshfs でマウントする
(`../singleuser/README.md`)。

- nbgrader は `~/notebooks/<course>/<assignment>` に fetch する (`path_includes_course`) ので、そのクラスの
  教材は Miyabi に置かれる。**`class` は nbgrader の course id と同じにすること**
- マウントしていないとリンク先が無いので fetch は `No such file or directory` で失敗する
  (taulec 側に黙って書かれることはない)。ほかのクラスの `~/notebooks/<course>` は普通のディレクトリのまま
- `~/notebooks` 自体は普通のディレクトリなので、マウントしていなくても JupyterHub には入れる
- 既に `~/notebooks/<class>` が普通のディレクトリとしてあると、触らずにエラーとして報告する
- Miyabi 側の `/work/gt81/share/home/<miyabi>/notebooks/<class>` は教員が先に作っておく (`../singleuser/README.md`)。
  無ければ `mount-miyabi` が警告する

Miyabi が使えない週は、`~/notebooks/<class>` を taulec 上の普通のディレクトリに付け替える (未実装)。

## Open WebUI

名簿の人は事前登録されるので、Google でログインすればすぐ使える。名簿にない人の
扱いは `../open-webui/oauth.env` の `ENABLE_OAUTH_SIGNUP` で切り替える
(`../open-webui/README.md` の「履修者の絞り込み」)。

管理者 API キーは、管理者パネル → 設定 → 一般 で API キーを有効にしてから、
設定 → アカウント → API キー で発行する。

## ファイル

| | |
|---|---|
| `enroll` | 本体 |
| `ssh_config` | `~/.ssh/config` に足す Host のテンプレート |
| `litellm_admin.py` | 名簿の読み込み・sudo し直し・LiteLLM の管理 API。`../agents/agent_setup` と共用 |
| `enroll.env.example` | 設定の雛形 |

## 前提

- user_map は同じ checkout の `../hub/state/user_map.sqlite` を `../hub/user_map.py` で操作する
  (JupyterHub が読むのと同じもの)
- システムの python3 だけで動く (追加のパッケージ不要)
