
# common は学生全員用

* fetch したものが ~/notebooks/コース名/課題名 となる設定
* ~share/venv/jupyter/etc/jupyter/nbgrader_config.py -> common/nbgrader_config.py
  (../singleuser/install が張る)
* 課題の配布・提出の置き場 (Exchange.root) は /home/share/nbgrader/exchange
  (既定の /usr/local/share/nbgrader/exchange への symlink はホストを作り直すと消える)

* 各学生の ~/.jupyter/ 下にファイルを置く必要はない
* ただしこの状態だと関係なクラスの教材も選べてしまう

# csi, ex, os, pd, pl, pmp, py etc. は教員用

* 例えば pl であれば, 
* ~pl/.jupyter/nbgrader_config.py -> pl/nbgrader_config.py
* ~/assignments/source を読んで課題を FormGrader に表示する

