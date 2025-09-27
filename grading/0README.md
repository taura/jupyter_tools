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

どうしても直せないものは

nbgrader autograde --assignment pl02 --no-execute --CourseDirectory.student_id_exclude=...

とするとその学生のautogradeをしないで飛ばせるがこれでちゃんとそのnotebookを受け取れるのかわからないので極力やらない

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

採点結果は grade.xlsx に記入していく

2024年度情報:

少しデータが大きくなると Libreoffice の spreadsheet は死ぬほど遅いので使わない
一つ操作をするたびに「反応なし」状態になる
Windows の Excel は何の問題もないので Windows での作業が推奨

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

2024年度に死ぬほど苦労した話

自動採点は学生が自由な形式で答えたときに, 自動実行では実はそれが正解だとわからないので, 正解と不正解の間の線引きが難しい


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

