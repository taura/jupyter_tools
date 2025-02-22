work_dir:=exec
test_dir:=test

ifndef assignment_names
test_scripts:=$(shell find $(test_dir) -name test.sh)
else
ifndef notebook_names
test_scripts:=$(foreach a,$(assignment_names),$(shell find $(test_dir)/$(a) -name test.sh))
else
ifndef prob_names
test_scripts:=$(foreach a,$(assignment_names),$(foreach n,$(notebook_names),$(shell find $(test_dir)/$(a)/$(n) -name test.sh)))
else
test_scripts:=$(foreach a,$(assignment_names),$(foreach n,$(notebook_names),$(foreach p,$(prob_names),$(shell find $(test_dir)/$(a)/$(n)/$(p) -name test.sh))))
endif
endif
endif

ifndef students
students:=$(shell ./work.py export-txt --sql 'select distinct(student_id) from grade_comment_cell order by student_id' --txt -)
endif

all :

define compile
all : $(work_dir)/$(assignment_name)/$(notebook_name)/$(prob_name)/$(student)/ok.txt
$(work_dir)/$(assignment_name)/$(notebook_name)/$(prob_name)/$(student)/dir :
	mkdir -p $$@
$(work_dir)/$(assignment_name)/$(notebook_name)/$(prob_name)/$(student)/ok.txt : $(test_dir)/$(assignment_name)/$(notebook_name)/$(prob_name)/test.sh $(work_dir)/$(assignment_name)/$(notebook_name)/$(prob_name)/$(student)/dir
	test_dir=$(test_dir) work_dir=$(work_dir) assignment_name=$(assignment_name) notebook_name=$(notebook_name) prob_name=$(prob_name) student_id=$(student) $(test_dir)/$(assignment_name)/$(notebook_name)/$(prob_name)/test.sh > $(work_dir)/$(assignment_name)/$(notebook_name)/$(prob_name)/$(student)/out.txt 2>&1
	touch $$@
endef

anps:=$(patsubst $(test_dir)/%/test.sh,%,$(test_scripts))

$(foreach anp,$(anps),\
$(foreach assignment_name,$(shell echo $(anp) | awk '{print $$1}' FS=/),\
$(foreach notebook_name,$(shell echo $(anp) | awk '{print $$2}' FS=/),\
$(foreach prob_name,$(shell echo $(anp) | awk '{print $$3}' FS=/),\
$(foreach student,$(students),$(eval $(call compile)))))))

.DELETE_ON_ERROR:
