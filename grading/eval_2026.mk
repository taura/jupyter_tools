#
# eval_pl.mk : run the per-problem test script for every
#              (topic, problem, user, lang) combination
#
# usage:
#   make -f eval_pl.mk -j 8            # run everything (incrementally)
#   make -f eval_pl.mk list            # show the (topic problem user lang) list
#   make -f eval_pl.mk clean
#
# knobs:
#   topics=...  restrict topics       (default: the list below)
#   langs=...   restrict languages    (default: go jl ml rs)
#
# each run leaves, in out/<topic>/<problem>/<user>/<lang>/ :
#   log.txt ... everything the test script printed (stdout and stderr)
#   ok.txt  ... the certificate of success; it exists iff the test passed
#
# use -k to keep going past failures (there are a lot of them for now)
#

# never let make's builtin rules touch anything under the submission dirs
MAKEFLAGS += -rR
.SUFFIXES:

topics :=
#topics += recursion
#topics += tail_recursion
#topics += typedef
#topics += recursive_type
#topics += oop_basics
topics += how_compiled
#topics += minc

langs     := go jl ml rs
ps        := ps
pr        := problems
submitted := dl/assignments/submitted
out       := out

# the generated rules come first in this file, so say what the default is
# .DEFAULT_GOAL := all

all : 

# ---------------------------------------------------------------- accessors
# in a path <submitted>/<user>/<assignment>/problems/<topic>/<problem>,
# the user is the field just after <submitted>
user_field := $(words $(subst /, ,$(submitted)) x)

# problems_of(topic)
problems_of = $(notdir $(patsubst %/,%,$(wildcard $(ps)/$(topic)/*/)))

# users_of(topic, problem) : students who have a directory for it
# (the assignment name, e.g. pl02_recursion, is unknown here, hence the */)
users_of = $(sort $(foreach d,$(wildcard $(submitted)/*/*/problems/$(topic)/$(problem)), $(word $(user_field),$(subst /, ,$d))))
# users_of = u26017


# langs_of(topic, problem, user) : always all four; the log says which ones
# the student actually worked on
langs_of = $(langs)

# dir_of(topic, problem, user, lang) : the student's directory, if any
submission_dir_of  = $(firstword $(wildcard $(submitted)/$(user)/*/problems/$(topic)/$(problem)/$(lang)))

# files_of : what the student put there; guarded, as $(wildcard /*) would
# otherwise list the whole root directory when submission_dir_of is empty
files_of = $(if $(submission_dir_of),$(wildcard $(submission_dir_of)/*))

# skel_of(topic, problem, lang) : the skeleton I handed out, if any
skel_dir_of = $(firstword $(wildcard $(pr)/$(topic)/$(problem)/$(lang)))

# test_of(topic, problem) : the test script (a prerequisite, so make itself
# reports it and fails when it does not exist)
test_of = $(ps)/$(topic)/$(problem)/$(problem)_test.sh

# log_of / ok_of / out_dir_of (topic, problem, user, lang)
out_dir_of = $(out)/$(topic)/$(problem)/$(user)/$(lang)
log_of     = $(out_dir_of)/log.txt
ok_of      = $(out_dir_of)/ok.txt

# --------------------------------------------------------------- rule maker
# one rule per (topic, problem, user, lang); the log depends on the student's
# files, so a re-run only redoes what changed.
# the .ok file is touched only after the test script returns zero; when it
# fails the recipe stops before the touch, so no certificate is left behind
# (the .log is kept either way -- .DELETE_ON_ERROR only removes the target)

.DELETE_ON_ERROR:

define rule_for
all : $(ok_of)
$(out_dir_of) :
	mkdir -p $$@
$(ok_of) : $(test_of) $(files_of) | $(out_dir_of)
	topic=$(topic) problem=$(problem) user=$(user) lang=$(lang) skel_dir=$(skel_dir_of) submission_dir=$(submission_dir_of) out_dir=$(out_dir_of) $(test_of) > $(log_of) 2>&1
	touch $$@
endef

#EVAL:=info
EVAL:=eval

$(foreach topic,$(topics), \
  $(foreach problem,$(problems_of), \
    $(foreach user,$(users_of), \
      $(foreach lang,$(langs_of), \
        $(eval $(call rule_for))))))

clean:
	rm -rf $(out)

.PHONY: all clean
