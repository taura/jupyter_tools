[1] nbgrader で submission を collect する

[2] nbgrader で autograde する (形式的)

ssh pl@taulec
cd notebooks
nbgrader autograde --assignment pl02 --no-execute

autograde が失敗することがある. 一部の学生で失敗したら

nbgrader autograde --assignment pl02 --no-execute --student xxx

nbgrader autograde --assignment pl02 --no-execute --CourseDirectory.student_id_exclude=...

[3] データをダウンロード

./work.py download --user pl # --user を適宜変える

実際にやることは

pl@taulec:notebooks 下のデータ(submitされたnotebook と gradebook.db)と
pl@taulec:/home/share/nbgrader/exchange/pl/inbound 下のデータ

[4] ./work.py export

* dl/notebooks/gradebook.db のデータを色々join
* dl/inboundの下に提出されたipynbからsource, outputsを読む
* exec/assignment_name/prob_name/student.{ok,err} の出力を読む (-> eval_output 列)

それらをすべてgrade.csvに書き出す.

採点作業は grade.csv 上で行う

[OS 2021のときにやったテキストクラスタリング]

cd public_html/lecture/operating_systems/exam/2021/grading/clustering
./add_distance.py

[5] プログラムを実行して採点

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

grade.csv で点数をつけていくときの作業方法

* autofilter を作る
* prob_name でソートする
* exec_output が OK となっているところに1をつける

* 1つのprob_name だけを表示する
* exec_output が OK となっているところを非表示にして採点

[7] ./work.py import で dl/notebooks/gradebook.db に反映

grade.csv に作業した結果を反映するのは

./work.py import

ただしこれをやる前に, gradebook.db の backup をとっておいたほうが良いだろう

[8] 無事 gradebook.db ができたと思ったら

./work.py upload --user pl # --user を適宜変える

実際にやることは以下だけ(その前に pl@taulec:notebooks/gradebook.db のバックアップを取る)

scp dl/notebooks/gradebook.db pl@taulec:notebooks/

[9] feedback を送る

$ ssh pl@taulec
taulec$ cd notebooks/
taulec$ nbgrader release_feedback --assignment plXX

