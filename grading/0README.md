※ 2026 年度のプログラミング言語で数々の変更が行われた。よく読んでから作業をすべし。

[0] nbgrader が使えるように (必要ならば)
ssh pl@taulec
mkdir -p venv
python3 -m venv venv/jupyter 
. venv/jupyter/bin/activate
pip install nbgrader

[1] nbgrader で submission を collect する

nbgrader list
nbgrader collect assignment_name

[2] nbgrader で autograde する (形式的)

ssh pl@taulec
cd notebooks
nbgrader autograde --assignment pl02 --no-execute

注: autograde が失敗することがある. 多くのパターンは,

```
  [AutogradeApp | INFO] Converting notebook /home/os/notebooks/submitted/u25274/os02_process/os02_process.sos.ipynb
  [AutogradeApp | WARNING] Cell with id 'p-001' exists multiple times!
```
  
みたいなWARNING (+ [AutogradeApp | WARNING] Cell 'c-002' does not exist in the database みたいのが一杯) 出て最後に,

[AutogradeApp | ERROR] One or more notebooks in the assignment use an old version
    of the nbgrader metadata format. Please **back up your class files
    directory** and then update the metadata using:

    nbgrader update .

が出る. これはどうやら学生がCell をまるごとコピーした際に起きる模様

https://github.com/jupyter/nbgrader/issues/1083

目視でも確認した. このパターンだった場合, 一行上に, `Converting notebook /home/os/notebooks/submitted/u25274/os02_process/os02_process.sos.ipynb` みたいにファイル名が書いてあるのでそれを editor で開いてduplicateしたセルの

  "metadata": {
    "kernel": "Bash",
    "nbgrader": {
     "cell_type": "code",
     "checksum": "5047123777f5f50e378cd58b247d06eb",
     "grade": true,
     "grade_id": "p-003",
     "locked": false,
     "points": 1,
     "schema_version": 3,
     "solution": true,
     "task": false
    }
   },

の "nbgader" をまるごと削除してこんな感じにする. "Bash", の , も忘れず削除

  "metadata": {
    "kernel": "Bash"
   },

これをやるためのツール `fix_broken_ipynb.py` を作った

```
./fix_broken_ipynb.py a.ipynb
```

で `a.ipynb` を直す. 元ファイルは `a.ipynb.bak` にcp

もともと`a.ipynb.bak` があったら上書きされるので, 事故のときにオリジナルを失わないようにするには, 

```
cp a.ipynb a.ipynb.org
```

とでもしてから作業を始めるのが良い

注2: それ以外の理由で失敗して直せない場合, エラーメッセージを見ながらマニュアルで直す
よくあるエラー:

 * [AutogradeApp | WARNING] Attribute 'cell_type' for cell p-001 has changed! (should be: markdown, got: raw)
 * [AutogradeApp | ERROR] Notebook JSON is invalid: 'outputs' is a required property
 
2025年度の新傾向: 

```
[AutogradeApp | INFO] Converting notebook /home/os/notebooks/submitted/u25269/os2025_exam/problem_4.sos.ipynb
[AutogradeApp | WARNING] Attribute 'cell_type' for cell p-002 has changed! (should be: markdown, got: raw)
[AutogradeApp | ERROR] There was an error processing assignment: /home/os/notebooks/submitted/u25278/os2025_exam
[AutogradeApp | ERROR] Traceback (most recent call last):

                            ...

    File "/home/os/venv/jupyter/lib/python3.12/site-packages/nbformat/validator.py", line 509, in validate
        raise error
    nbformat.validator.NotebookValidationError: 'id' is a required property
    
    Failed validating 'required' in notebook:
    
    On instance:
    {'cell_type': 'markdown',
     'metadata': {'deletable': False,
                  'kernel': 'SoS',
                  'nbgrader': {'cell_type': 'markdown',
                               'checksum': '3c9ebad55b38098c52a27e75a384c6f9',
                               'grade': True,
                               'grade_id': 'p-002',
                               'locked': False,
                               'points': 1,
                               'schema_version': 3,
                               'solution': True,
                               'task': False}},
     'source': 'send_transactionファイルに実行権限を付与する。'}
```

修正するための有用情報は [AutogradeApp | ERROR] の一行上の WARNING:

  `Attribute 'cell_type' for cell p-002 has changed! (should be: markdown, got: raw)` 
  
にあるとおり, どうやらあるセルのtypeを変えてしまうことにあるらしい.
壊れたファイル名はその一行上の INFO にでている

   Converting notebook /home/os/notebooks/submitted/u25269/os2025_exam/problem_4.sos.ipynb

ファイルをEmacsで開いて該当するセルをエラーメッセージの文字列から見つけて, "cell_type" を直す

どうしても直せないものは

```
nbgrader autograde --assignment pl02 --no-execute --CourseDirectory.student_id_exclude=...
```

とするとその学生のautogradeをしないで飛ばせるがこれでちゃんとそのnotebookを受け取れるのかわからないので極力やらない

[2026 年度 update]

プログラミング言語の授業で、本体の .ipynb ではほとんどなにもさせない方式を採用。
get_problem とすると1問だけの .ipynb が cp される方式。
その結果、直接 .ipynb のセルをいじることがなくなったので autograde できないという事故はなくなった。
cp された .ipynb は提出はされるが autograde ではなにも行われない。
採点は .ipynb のセルに対してではなく別途提出されたファイルに対して行なうので特に問題はない。

[3] データをダウンロード

```
./work.py download --user pl # --user を適宜変える
```

実際にやることは

#[2025まで]
#pl@taulec:notebooks 下のデータ(submitされたnotebook と gradebook.db)と
#pl@taulec:/home/share/nbgrader/exchange/pl/inbound 下のデータ

pl@taulec:assignments 下のデータ(submitされたassignments と gradebook.db)と
pl@taulec:/home/share/nbgrader/exchange/pl/inbound 下のデータ


[4] ./work.py export-xlsx
(以下の[4']も参照)

* dl/notebooks/gradebook.db のデータを色々join
* dl/inboundの下に提出されたipynbからsource, outputsを読む
* exec/assignment_name/prob_name/student.{ok,err} の出力を読む (-> eval_output 列)

それらをすべてgrade.xlsxに書き出す.

採点結果は grade.xlsx に記入していく

2024年度情報:

少しデータが大きくなると Libreoffice の spreadsheet は死ぬほど遅いので使わない
一つ操作をするたびに「反応なし」状態になる
Windows の Excel は何の問題もないので Windows での作業が推奨

[4'] `./work.py export-xlsx` でできる Excel は作業のために色々修正が必要

* 列の幅を揃える
* 罫線
* フィルダーを備える
* 左寄せ、上寄せ、はみ出た文字は折返し、にする
* manual score に条件付き書式(色を付けるなど)

毎回やるのもアレなので中身が空の Excel を作ってそれにデータを追加するという方法もある.
その空のExcel がこのフォルダの grade_template.xlsx

したがって

```
cp ~/lectures/jupyter_tools/grading/grade_template.xlsx grade.xlsx 
./work.py update-xlsx
```

としてもよい.

ただし「左寄せ、上寄せ、はみ出た文字は折返し」の書式、罫線は追加された行には適用されてくれない模様

* TIPS: 条件付き書式
  * 採点漏れを防ぐため, かつ行の高さが大きいところに数字だけのセルは目視が難しいため, 色を付けるのが良い
  * 1 -> Good, "" -> Default, 0 -> Bad, !="" Note とするのが基本だが注意
    * "" は 0 扱いされるらしく, 0 -> Bad を "" -> Default の前に置くと 空のセルも Bad になってしまう. かならず "" -> Default を先に書く
    * 上記の書式には, vertical alignment が bottom ということが含まれているので実際にはそのまま適用してはならず, New Style で それぞれを Inherit した新しい書式を作り, その中で vertical alignment を修正して Top にしないとだめ
      * aGood, aDefault, aBad, aNote などとするのがおすすめ

* TIPS: 素早く採点
  * 短い答えを採点する場合, 同じ答えは固まるようにするのが*圧倒的に*速い
  * そのために source でソートして1問題だけを表示すると良い

[2026年度 update]

新しい 2026年度プログラミング言語の方式では、本体の .ipynb には本当の課題の問題はないので、 ./work.py export-xlsx とやっても何もでてこない。
つまり上記のようにしてできた grade.xlsx は空になる。
したがってこの[4]に書いてある事自体、必要が無くなる。

[5] 半自動採点. プログラムを実行して採点

## 2025/02/23 eval.mk がおそすぎるのを改良して eval2.mk に

make -f eval2.mk all

は, `test/assignment_name/notebook_name/prob_name/test.sh`

が存在するすべての `assignent_name`, `notebook_name`, `prob_name` の組とすべての学生に対して, 

`assignment_name=os02_process notebook_name=os02_process.sos prob_name=p-001 student=u24xxx test/os02_process/os02_process.sos/p-001/test.sh` 

みたいなコマンドを実行する. よって test/os02_process/os02_process.sos/p-001/test.sh の中で好きなことをすれば良い.

「好きなこと」ではいくつかのセルから書かれたプログラムを読み出してテストを実行するみたいなことをする.
複雑なケースでは前に遡って読み出さないといけない (p-012 の答えが p-011 の答えに依存している).
単純に全部としてしまうと, 前の方の問題でエラーが出ると先が実行できなくなってしまうので,
マニュアルで取り出す必要がある.

学生によっては勝手にセルを追加してプログラムを書く人がいるがそういう人の分まで対処はできていない.

例: 必要に応じて prob_name のところに p-009,p-010,p-011 みたいなことを書く
必要に応じて prologue に事前に必要な定義を追加

#!/bin/bash
test -e

ext=ml
cmd=ocaml

prologue=
epilogue=${test_dir}/${assignment_name}/${notebook_name}/${prob_name}/test.${ext}
test_prog=${work_dir}/${assignment_name}/${notebook_name}/${prob_name}/${student_id}.${ext} # exec/pl02/pl02-ocaml.sos/p-001/test.ml

./work.py export-source --student-id ${student_id} --assignment-name ${assignment_name} --notebook-name ${notebook_name} --prob-name ${prob_name} --txt - | cat ${prologue} - ${epilogue} > ${test_prog}

${cmd} ${test_prog} 2>&1

test を走らせたら

```
./work.py update-xlsx
```

するとコマンドの出力や, 成功したかどうか (ok.txt と言うファイルの存在で確認) が grade.xlsx に書き込まれる

注: update-xlsx は grade.xlsx を更新するので間違い防止のために, grade.xlsx に元々入っている行数と結果として書き込むことになる行数が一致していないと動かない. したがってあとから追加で download したりして提出物が増えてから行うと動かない

2024年度に死ぬほど苦労した話

自動採点は学生が自由な形式で答えたときに, 自動実行では実はそれが正解だとわからないので, 正解と不正解の間の線引きが難しい

[2026年度 update]

grade.xlsx 自身が空にしかならないので、grade.xlsx に採点を書き込んでいくというやり方自身がなくなった。
dl/assignments/submitted/ の中身をみてそこから必要なファイルを見て採点する --- eval.mk の変種のような --- やり方。
セルの値を gradebook.db から引き抜くというプロセスが不要になったのはむしろ単純化。

採点スクリプトを各問題と同じディレクトリ (e.g., `ps/recursion/fast_power/fast_power_test.sh` ) におくことにして、それを走らせる新しい makefile  `eval_pl.mk` を claude が書いた。 -> `jupyter_tools/grading/eval_2026.mk` として commit

それらの出力を 2次元の表にするプログラムを claude が書いた。 out2xlsx.py -> status.xlsx

[6] Excel に仕込んでいおくと良い仕掛け

* autofilter を作る
* prob_name でソートする
* eval_ok が --- ok --- となっているところに1をつける

* 1つのprob_name だけを表示する
* exec_output が OK となっているところを非表示にして採点

=== UTAS, LMSなどとの結合 ===

[7] UTASのデータをダウンロード

   UTAS 
-> 成績・定期試験
-> 成績登録 
-> 講義を選ぶ 
-> Excel出力 
=> data/utas.xlsx という名前で保存

そのままではパスワード付きで, libreofficeで開けない.

   WindowsのExcel
-> 情報 
-> ブックの保護 
-> パスワードによる暗号化
=> data/utas.xlsx という名前のまま保存


<!--
[8] ITC-LMSデータのダウンロード
   ITC-LMS 
-> 課題 
-> 全体提出状況確認 
-> ダウンロード
=> data/lms.xlsx に保存

UTAS [7] 同様に, WindowsのExcelでパスワードを解除
-->

[8] UTOLデータのダウンロード

   UTOL
-> 課題 
-> 全履修者の提出物確認
-> zipダウンロード
=> data/20xx..xx.zip に保存

```
cd data
unar 20xx..xx.zip
```

`data/20xx..xx/授業名.xlsx` というファイルがあるので, UTAS 同様に, WindowsのExcelで開いてパスワードを解除したものを --> `data/utol.xlsx` として保存

zip を解凍してできたフォルダは `utol` に改名

```
mv 20xx..xx utol
```

=> 最終的に以下のような状態にする (`data/utol.xlsx`, `data/utol/` がある状態)

```
data/
  utol.xlsx
  utol/
    3124xxxx/
    3124xxxx/
    3124xxxx/
      ...
```


[9] JupyterのユーザExcel (学生番号とuxxxxx の対応) 

    ssh -t taulec-ansible gocryptfs make_env/ansible/files/enc make_env/ansible/files/plain
    sshfs taulec-ansible: taulec-ansible
    ln -s taulec-ansible/make_env/ansible/files/plain/taulec_ldap_users.csv users.csv

すると users.csv が読めるようになるのでそれを libreoffice で開き,
=> data/jupyter.xlsx
に保存.

*その後で, この授業に関係ない行を削除.*
削除しないと, 同じ人が複数の授業を受けていたときに取り違える可能性がある

[10] 

./join_utas_lms_jupyter_nbg.py

は, [7]-[9]のデータと, grade.xlsx をすべて結合する

utas_lms_jupyter_nbgrader.xlsx

というファイルができる

2025/02/25 更新

これまでは必ず utas_lms_jupyter_nbgrader.xlsx を作り直していたが同ファイルへ施した種々の調整(列の太さ, autofilterなど)が失われる不便を解消。utas_lms_jupyter_nbgrader.xlsx が存在していたらそのデータ部分だけを更新することにした

[2026年度 update]

grade.xlsx が空でしかなくなったのでこれを merge することがありえなくなった。
`join_utas_lms_jupyter_nbg.py` は grade.xlsx の代わりに status.xlsx を merge するようにした。
grade.xlsx は データベースぽい形式 (user x 問題の2次元表ではなく、user, assignment, notebook, cell, ... の並び)の表だったので、マージする際にそれを2次元表ぽくする処理を挟んでいた。それは status.xlsx を作る時点で行われており不要になったのでむしろ全体は単純になった。
grade.xlsx 方式も --grade オプションでサポートする。

なおこの新 `join_utas_lms_jupyter_nbg_new.py` では、`utas_lms_jupyter_nbgrader.xlsx` が存在していたらそれを update する方式にした。

※検討事項[1]: すべての join するというこのステップが最後に一度だけ行われるという前提で作業をしていたのがよくなかった説。
実際に採点結果を一つに統合するのはこの Excel で行われる。
であれば最初にそれを作り、eval_pl.mk を走らせるたびにその Excel に結果が書き込まれていくというスタイルも考えるに値する。

また、このExcel表でたくさんのマニュアル作業をしているがそれらは結局のところ、

Reflection提出の回数
各課題の点数
各課題の締め切り
各課題の配点

などを調節して総合点をだすことだけである。
ある程度ややこしくなるとExcel上でやることが苦痛になる。
Excel の数式をエラーと格闘しながら書くのは苦痛（数式の字があまりに小さい）。
ある列の値を元にある列の値を計算するようなDSL的なものをつくり、マージ処理自身をプログラム化したほうがきっとよい。
どんなDSL? Python dictionary で十分という説もある  t[row][col] の形式を与えられそれを元に Python で計算。

大事なことは utas, lms, jupyter までをマージしたファイル（あとから変更されることはあまりない）をつくり、それに対して施した、見やすさのための変更（列の太さや条件付き書式など）を保存したまま eval_pl.mk の結果を書き足して行けるようにすること。

※検討事項[2]: 遅れ提出の扱い

Jupyterのsubmission には timestamp.txt というファイルがついているのでこれを元に遅れ提出か否かを判定できる。
今回それを使って check_timestamp.py というスクリプトで timestamp を取り出したところ、かなりの締切後提出が見つかった。
これまで提出日付をろくに見ていなかったが見なくてはダメだと判明。

複数回の提出ができること、 dl/inbound には過去の投稿も残っているのでどれを見るのが良いのと言う話になる。
それは遅れ提出へのペナルティの与え方にもよる。
一瞬でも遅刻したら 1/10 になるのであれば、改良して再提出したら不利になることになる。
一方、締め切り前の提出物しか見ないのだとすると、遅れ提出を認めないのと同じことになる。
(a) 締め切り前にクズを提出してその後遅れて改良版を提出する。
(b) 締め切り前に提出せずに、その後遅れて提出する。
(a)の方が不利になるのは違う気がする。
とは言え全部採点していい方を取るなどという面倒なことはやりたくない。
結局、新しい版を提出する＝その方が良いと信じて提出する、という意味だと解釈して「最後の版しか見ない」という風にするしかない。
それを宣言すると、遅れた際のペナルティがどのくらいかを公表してという話になりそうなので面倒だ。

[11] 最終的にutasにアップロードする際は, utasの

採点表データ [出力] でDLする

暗号化されていてWindowsじゃないと開けないので
utas_lms_jupyter_nbgrader.xlsx を A列 でソートして
Windows上でコピペする

[12] 電気系(池田先生)の成績報告

2024年度冬学期(A1A2) 成績入力のお願い( FEN-EE3d16L1 オペレーティングシステム)

以下のパスワードをご利用いただきますようお願いいたします。
また、7zを展開するパスワードは学科で日頃用いているものになります。

成績担当　　池田　誠

科目名: オペレーティングシステム
成績プログラムのダウンロード:
http://www.mos.t.u-tokyo.ac.jp/~ikeda/EEScore/2024_FEN-EE3d16L1_Drc.7z

成績ファイルのアップロード:
http://www.mos.t.u-tokyo.ac.jp/ikeda-cgi/EEScore/EEScore.cgi?Lec=2024_FEN-EE3d16L1_Drc

田浦健次朗先生
ユーザ名:   24A_tau@eidos.ic.i.u-tokyo.ac.jp
パスワード:  ndZirkSpfBFoekst

みたいなメールがやってくる.
ダウンロードリンクを開くと上記のユーザ名, パスワードを要求されるので入れて, xxxxx.7z みたいなファイルをDLする
apt install 7zip 
して
7za e xxxxx.7z
でパスワードは「いつもの」(メールで送られてきたやつではなく) で解凍
-> usb.tar ができる

tar usb.tar

するとファイルがその場にぶちまけられるので注意

utas_lms_jupyter_nbgrader.xlsx の成績を100点満点で10段階に変換

学生証番号 -> 下5桁を取り出す
10段階成績 -> 10x して 100点満点にする
ヘッダなし, indexなし, sep=" " で csv 保存


2025年度, ファイル入力すると RATEDATA.TXT という提出ファイルが一切保存されない (0 byteのまま) というバグに悩まされた
ファイル入力して10点法/100点法に移ると成績は反映されているが終了すると RATEDATA.TXT が0バイト

ファイル入力してからそのへんでいくつかの成績を手動でいじって元に戻す?
最初に手動で入力してからファイル入力する?
最初に手動で入力してからファイル入力してまた少し手動でいじる?

色々やっているうちに直ってしまった

A1 ... 100
A  ... 90, 80, 70
B  ... 60, 50
C  ... 40, 30

でつける. 学生証番号の列と上記の点数2列をテキストファイルにコピー(Excelでは間の列を非表示にするとできる).
学生証番号は下5桁のみ(6桁以上有ると全部見つからないとなる)にする.
それを data.txt とでも名付けてぶちまけられた場所にでも保存

rate.exe を Windows から起動して, 
(3) ファイルから入力
をおしてファイル名を指定する.

終了すると ratedata.txt というファイルができるのでそれを上記のアップロードリンクからアップロード

=== これ以降の作業はfeedbackを学生に返さないのなら不要 ===

[11] ./work.py import で dl/notebooks/gradebook.db に反映

grade.csv に作業した結果を反映するのは

./work.py import

ただしこれをやる前に, gradebook.db の backup をとっておいたほうが良いだろう


[12] 無事 gradebook.db ができたと思ったら

./work.py upload --user pl # --user を適宜変える

実際にやることは以下だけ(その前に pl@taulec:notebooks/gradebook.db のバックアップを取る)

scp dl/notebooks/gradebook.db pl@taulec:notebooks/

[13] feedback を送る

$ ssh pl@taulec
taulec$ cd notebooks/
taulec$ nbgrader release_feedback --assignment plXX

--------------------------------------

[2026年度 update]

理想の workflow 

採点の早い段階で UTAS, LMS, Jupyter のデータを統合
eval_2026.mk を実行 -> 統合したデータに書き込む（カラムを追加したり既存セルを上書きしたり）。
提出遅れも同様に書き込む。
主観評価をするようなものについては統合されたExcelに書き込んでいく形式。

最終的に点数に落とし込むところをDSLで、Excel上でややこしい作業なしに行なう。
