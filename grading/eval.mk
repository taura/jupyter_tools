work_dir:=exec
test_dir:=test
#assignment_name?=pl05
#notebook_name?=pl05_calculator.sos
#prob_name?=p-001

assignment_name?=pl10
notebook_name?=pl10_minc.sos
prob_name?=p-002

.DEFAULT_GOAL := all

usage :
	@echo usage:
	@echo '  make -f eval.mk assignment_name=pl02 notebook_name=pl02_ocaml.ml prob_name=p-001 problem [students="u21000 u21001 ..."]'
	@echo '  make -f eval.mk assignment_name=pl02 notebook_name=pl02_ocaml.ml notebook [prob_names="p-001 p-002 ..."]'
	@echo '  make -f eval.mk assignment_name=pl02 assignment [notebook_names="pl02_ocaml.ml ..."]'
	@echo '  make -f eval.mk all [assignment_names="pl02 pl03 ..."]'

# -------------------

# evaluate all assignments

assignment_names?=$(shell ./work.py export-txt --sql 'select distinct(assignment_name) from grade_comment_cell order by assignment_name' --txt -)
results_all:=$(patsubst %,make-%,$(assignment_names))

$(results_all) : make-% :
	$(MAKE) -f eval.mk assignment_name=$* assignment

all : $(results_all)

# -------------------

# evaluate all notebooks of an assignment

notebook_names?=$(shell ./work.py export-txt --sql 'select distinct(notebook_name) from grade_comment_cell where assignment_name = "$(assignment_name)" order by notebook_name' --txt -)
results_assignment:=$(patsubst %,make-$(assignment_name)-%,$(notebook_names))

$(results_assignment) : make-$(assignment_name)-% :
	$(MAKE) -f eval.mk assignment_name=$(assignment_name) notebook_name=$* notebook

assignment : $(results_assignment)

# -------------------

# evaluate all problems of a notebook

prob_names?=$(shell ./work.py export-txt --sql 'select distinct(prob_name) from grade_comment_cell where assignment_name = "$(assignment_name)" and notebook_name = "$(notebook_name)" order by prob_name' --txt -)
results_notebook:=$(patsubst %,make-$(notebook_name)-%,$(prob_names))

$(results_notebook) : make-$(notebook_name)-% :
	$(MAKE) -f eval.mk assignment_name=$(assignment_name) notebook_name=$(notebook_name) prob_name=$* problem

notebook : $(results_notebook)

# -------------------

# evaluate all students of a problem

students?=$(shell ./work.py export-txt --sql 'select student_id from grade_comment_cell where assignment_name = "$(assignment_name)" and notebook_name = "$(notebook_name)" and prob_name = "$(prob_name)" order by student_id' --txt -)
results_prob:=$(patsubst %,$(work_dir)/$(assignment_name)/$(notebook_name)/$(prob_name)/%.ok,$(students))

$(results_prob) : $(work_dir)/$(assignment_name)/$(notebook_name)/$(prob_name)/%.ok : $(work_dir)/$(assignment_name)/$(notebook_name)/$(prob_name)/created # $(test_dir)/$(assignment_name)/$(notebook_name)/$(prob_name)/test.sh 
# run test.sh on a student working on a problem
	test_dir=$(test_dir) work_dir=$(work_dir) assignment_name=$(assignment_name) notebook_name=$(notebook_name) prob_name=$(prob_name) student_id=$* $(test_dir)/$(assignment_name)/$(notebook_name)/$(prob_name)/test.sh > $(work_dir)/$(assignment_name)/$(notebook_name)/$(prob_name)/$*.out 2> $(work_dir)/$(assignment_name)/$(notebook_name)/$(prob_name)/$*.err 
	touch $@

problem : $(results_prob)

# -------------------

$(work_dir)/$(assignment_name)/$(notebook_name)/$(prob_name)/created :
	mkdir -p $@

.DELETE_ON_ERROR:
