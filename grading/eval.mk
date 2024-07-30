work_dir:=exec
test_dir:=test
#assignment_name?=pl05
#notebook_name?=pl05_calculator.sos
#prob_name?=p-001

#assignment_name?=pl10
#notebook_name?=pl10_minc.sos
#prob_name?=p-002

# 課題[1]
# 無駄にデータベースを何度も引く (以下で直したつもり)
# そのために assignment_names= みたいなデータベース検索をやめさせるため
# だけのパラメータを渡しているのが汚い
#
# 課題[2]
# assignment_names assignment_name 
# notebook_names notebook_name 
# problem_names problem_name
# students student
# と色々あってややこしい.
# 複数の場合をなくして全部単数にしてもいい
#
# [2]を解決して単数の方に統一すればひとりでに[1]が解決しそう
#
# make -f eval.mk [assignment_name=] [notebook_name=] [prob_name=] [student=] _target_
#
# _target_ は なし(=all), assignment -> notebook -> problem -> student のどれか
#
# _target_ ごとに単数・複数を使い分けなくても良い
#
# その方針で直せば良い気がするが今年の途中で変えるのは嫌なのでやめておく
#
# [3] 変数名, ターゲットの統一?
# assignment_name, notebook_name, prob_name, student ->
# assignment_name, notebook_name, problem_name, student_name ??
# [4] 今は学生ごとに別フォルダを作ってはいないが作ったほうがきれいかもしれない
# [5] 実行自身をそのフォルダに cd してからやっても良い気がするがわからない
#

.DEFAULT_GOAL := all

usage :
	@echo usage:
	@echo '  make -f eval.mk assignment_name=pl02 notebook_name=pl02_ocaml.ml prob_name=p-001 problem [students="u21000 u21001 ..."]'
	@echo '  make -f eval.mk assignment_name=pl02 notebook_name=pl02_ocaml.ml notebook [prob_names="p-001 p-002 ..."]'
	@echo '  make -f eval.mk assignment_name=pl02 assignment [notebook_names="pl02_ocaml.ml ..."]'
	@echo '  make -f eval.mk all [assignment_names="pl02 pl03 ..."]'

# -------------------

# evaluate all students of all problems of all notebooks of all assignments

# echo select distinct assignment_name 1>&2; 
assignment_names?=$(shell ./work.py export-txt --sql 'select distinct(assignment_name) from grade_comment_cell order by assignment_name' --txt -)
results_all:=$(patsubst %,make-%,$(assignment_names))

$(results_all) : make-% :
	$(MAKE) -f eval.mk assignment_names= assignment_name=$* assignment

all : $(results_all)

# -------------------

# evaluate all students of all problems of all notebooks of a particular assignment

ifdef assignment_name
# echo select distinct notebook_name 1>&2; 
notebook_names?=$(shell ./work.py export-txt --sql 'select distinct(notebook_name) from grade_comment_cell where assignment_name = "$(assignment_name)" order by notebook_name' --txt -)
results_assignment:=$(patsubst %,make-$(assignment_name)-%,$(notebook_names))

$(results_assignment) : make-$(assignment_name)-% :
	$(MAKE) -f eval.mk assignment_names= assignment_name=$(assignment_name) notebook_names= notebook_name=$* notebook
endif

ifdef results_assignment
assignment : $(results_assignment)
else
assignment :
	echo "add assignment_name= to build target 'assignment'" 1>&2
	exit 1
endif

# -------------------

# evaluate all students of all problems of a particular notebook of a particular assignment
ifdef assignment_name
ifdef notebook_name
# echo select distinct prob_name 1>&2; 
prob_names?=$(shell ./work.py export-txt --sql 'select distinct(prob_name) from grade_comment_cell where assignment_name = "$(assignment_name)" and notebook_name = "$(notebook_name)" order by prob_name' --txt -)
results_notebook:=$(patsubst %,make-$(notebook_name)-%,$(prob_names))

$(results_notebook) : make-$(notebook_name)-% :
	$(MAKE) -f eval.mk assignment_names= assignment_name=$(assignment_name) notebook_names= notebook_name=$(notebook_name) prob_names= prob_name=$* problem
endif
endif

ifdef results_notebook
notebook : $(results_notebook)
else
notebook :
	echo "add assignment_name= and notebook_name= to build target 'notebook'" 1>&2
	exit 1
endif

# -------------------

# evaluate all students of a particular problem of a particular notebook of a particular assignment

ifdef assignment_name
ifdef notebook_name
ifdef prob_name
# echo select student_id 1>&2; 
students?=$(shell ./work.py export-txt --sql 'select student_id from grade_comment_cell where assignment_name = "$(assignment_name)" and notebook_name = "$(notebook_name)" and prob_name = "$(prob_name)" order by student_id' --txt -)
# results_prob:=$(patsubst %,make-$(prob_name)-%,$(students))

#$(results_prob) : make-$(prob_name)-% :
#	$(MAKE) -f eval.mk assignment_names= assignment_name=$(assignment_name) notebook_names= notebook_name=$(notebook_name) prob_names= prob_name=$(prob_name) students= student=$* student

results_prob:=$(patsubst %,$(work_dir)/$(assignment_name)/$(notebook_name)/$(prob_name)/%.ok,$(students))

# $(error "students = $(students)")
#$(error "rsults_prob = $(results_prob)")

$(results_prob) : $(work_dir)/$(assignment_name)/$(notebook_name)/$(prob_name)/%.ok : $(work_dir)/$(assignment_name)/$(notebook_name)/$(prob_name)/created
	test_dir=$(test_dir) work_dir=$(work_dir) assignment_name=$(assignment_name) notebook_name=$(notebook_name) prob_name=$(prob_name) student_id=$* $(test_dir)/$(assignment_name)/$(notebook_name)/$(prob_name)/test.sh > $(work_dir)/$(assignment_name)/$(notebook_name)/$(prob_name)/$*.out 2> $(work_dir)/$(assignment_name)/$(notebook_name)/$(prob_name)/$*.err
	touch $@
endif
endif
endif

ifdef results_prob
problem : $(results_prob)
else
problem :
	echo "add assignment_name=, notebook_name=, and prob_name= to build target 'problem'" 1>&2
	exit 1
endif

# -------------------

# evaluate a student for a particular problem of a particular notebook of a particular assignment

ifdef assignment_name
ifdef notebook_name
ifdef prob_name
ifdef student
results_student := $(work_dir)/$(assignment_name)/$(notebook_name)/$(prob_name)/$(student).ok
$(results_student) : $(work_dir)/$(assignment_name)/$(notebook_name)/$(prob_name)/created # $(test_dir)/$(assignment_name)/$(notebook_name)/$(prob_name)/test.sh 
	test_dir=$(test_dir) work_dir=$(work_dir) assignment_name=$(assignment_name) notebook_name=$(notebook_name) prob_name=$(prob_name) student_id=$* $(test_dir)/$(assignment_name)/$(notebook_name)/$(prob_name)/test.sh > $(work_dir)/$(assignment_name)/$(notebook_name)/$(prob_name)/$*.out 2> $(work_dir)/$(assignment_name)/$(notebook_name)/$(prob_name)/$*.err
	touch $@
endif
endif
endif
endif

ifdef results_student
student : $(results_student)
else
student :
	echo "add assignment_name=, notebook_name=, prob_name=, and student= to build target 'student'" 1>&2
	exit 1
endif

# -------------------

$(work_dir)/$(assignment_name)/$(notebook_name)/$(prob_name)/created :
	mkdir -p $@

.DELETE_ON_ERROR:
