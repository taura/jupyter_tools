[1] nbgrader で submission を collect する

nbgrader list
nbgrader collect assignment_name

[2] nbgrader で autograde する (形式的)

ssh pl@taulec
cd notebooks
nbgrader autograde --assignment pl02 --no-execute

注: autograde が失敗することがある. 多くのパターンは,

  [AutogradeApp | WARNING] Cell with id 'p-003' exists multiple times!
  
みたいなWARNING (+ [AutogradeApp | WARNING] Cell 'c-002' does not exist in the database みたいのが一杯) 出て最後に,

[AutogradeApp | ERROR] One or more notebooks in the assignment use an old version
    of the nbgrader metadata format. Please **back up your class files
    directory** and then update the metadata using:

    nbgrader update .

が出る. これはどうやら学生がCell をまるごとコピーした際に起きる模様

https://github.com/jupyter/nbgrader/issues/1083

目視でも確認した. このパターンだった場合, editor で開いてduplicateしたセルの

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

注2: それ以外の理由で失敗して直せない場合,

nbgrader autograde --assignment pl02 --no-execute --CourseDirectory.student_id_exclude=...

でその学生のautogradeをしない. 
ただしこれでちゃんとそのnotebookを受け取れるのか?

[3] データをダウンロード

./work.py download --user pl # --user を適宜変える

実際にやることは

pl@taulec:notebooks 下のデータ(submitされたnotebook と gradebook.db)と
pl@taulec:/home/share/nbgrader/exchange/pl/inbound 下のデータ

[4] ./work.py export-xlsx

* dl/notebooks/gradebook.db のデータを色々join
* dl/inboundの下に提出されたipynbからsource, outputsを読む
* exec/assignment_name/prob_name/student.{ok,err} の出力を読む (-> eval_output 列)

それらをすべてgrade.xlsxに書き出す.

採点作業は grade.xlsx 上で行う

2023年度更新:

色々作業をするのにcsvよりもxlsxのほうが良さげなのでそうする

2022年度更新:

- notebookがたくさんあると, 巨大になりすぎるので, notebook ごとに分割してexportする方が実践的
- それには以下のようにする

./work.py export --sql "select * from grade_comment_cell where notebook_name=\"NOTEBOOK_NAME.sos\"" --csv grades/NOTEBOOK_NAME.csv

[OS 2021のときにやったテキストクラスタリング]

cd public_html/lecture/operating_systems/exam/2021/grading/clustering
./add_distance.py

[5] 半自動採点. プログラムを実行して採点

make -f eval.mk all

は, 全課題(pl02), 全問題(p-001, p-001, ..), 全学生(u21080, ...)に対して

assignment_name=pl02 prob_name=p-001 student=u21080 test/pl02/p-001/test.sh

みたいなコマンドを実行する. よって test/pl02/p-xxx/test.sh の中で好きなことをすれば良い.

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

なお, これをやらなくてはいけない理由の一部は, test セルの結果が export した中に入ってこないからという説もある. それが入ってくればその結果を見て信用すればわざわざプログラムを取り出して実行するほどのことはないかもしれない.

これはむしろ本格的な試験で必要な仕組みか

TODO: このやり方の代わりにあるセルに書かれた答えはすべて一度だけDLして, 問題ごとにevalようなやり方のほうがいいかもしれない. 

TODO: 学生が別途作ったファイルも評価に使いたい場合があるのでその場合は, dl/notebooks/submitted/${student_id}/os15_pipe/ からコピーする.

TODO: これをするならその中の ipynb から直接取ればいいという説がある

これをやったあとでまた

./work.py export

で grade.csv に書き出す

ただし途中まで grade.csv にscoreを書き込んだあとだとそれが失われるので, 

./work.py export --csv hoge.csv

とでもして必要な部分だけを hoge.csv -> grade.csv にコピーするのが良い

プログラムのtest方法は必ず試行錯誤(やり直し)が必要になるので,

make -f eval.mk prob_names="p-003"
./work.py export --csv g003.csv

みたいなことをやっては g003.csv の出力を grade.csv に反映させる

[6] libreoffice でできる工夫

grade.{csv,xlsx,ods} で点数をつけていくときの作業方法

* autofilter を作る
* prob_name でソートする
* eval_output が OK となっているところに1をつける

* 1つのprob_name だけを表示する
* exec_output が OK となっているところを非表示にして採点

2023年度追加:

始めから xlsx を生成することにしたので以下のコメントは大部分不要

<!--
2022年度追加: 

eval.mk を実行してはそれを取り込むということを繰り返すので, 手作業で仕事をするシートは ods/xls にしておいて一度だけautofilterなどを作っておくのが良い. 生成するのは csv にしてそこからcopy-pasteする

TODO: それをやるくらいなら既存のシートの eval_ok, eval_output, eval_err の列だけを自動で上書きするというのを work.py の機能にしたらいいのではないかという説あり

./work.py --merge-export grades.ods --keys colum_names --values eval_ok,eval_output,eval_err

export する
--keys で指定された値がマッチしている行を grades.odsから探し, --valuesで指定されたものに置き換える

おそらく ods を pandas で読み込んでまた吐き出す, だと手作業の結果 autofilter や wrap_text, alignment などの設定が失われる. xlsx + openpyxl でやるしかない?
 -->
 
=== ITC-LMSなどとの結合 ===

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
=> data/20xx....zip に保存

unar で解凍
中にExcelファイルと、テキストが入っている

UTAS [7] 同様に, WindowsのExcelでパスワードを解除?

[9] JupyterのユーザExcel (学生番号とuxxxxx の対応) 

cd ~/lectures/operating-systems/docs/jupyter
./mnt 

すると users.csv が読めるようになるのでそれを libreoffice で開き,
=> data/jupyter.xlsx
に保存.

その後で, この授業に関係ない行を削除.
削除しないと, 同じ人が複数の授業を受けていたときに取り違える可能性がある

[10] 

./join_utas_lms_jupyter_nbg.py

は, [7]-[9]のデータと, grade.xlsx をすべて結合する

[11] 最終的にutasにアップロードする際は, utasの

採点表データ出力


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

