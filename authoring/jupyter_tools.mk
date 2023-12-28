#
# jupyter_tools.mk
#

this_dir:=$(dir $(lastword $(MAKEFILE_LIST)))

#
# default source files
#
nb_srcs  ?= $(wildcard nb/source/*/*.{ml,c,py,sos})
aux_srcs ?= $(wildcard nb/source/*/img/*.svg) $(wildcard nb/source/*/img/*.png)
mk_nb_flags ?= 

# users on behhalf of which we run jupyter servers
users_csv ?= users.csv
users     ?= $(shell awk '{if(NR>1) print $$1}' FS=, $(users_csv))

#
# target files
#
ipynbs        :=
ipynbs        += $(patsubst nb/source/%,notebooks/source/%.ipynb,$(nb_srcs))
ipynb_answers := 
ipynb_answers += $(patsubst nb/source/%,notebooks/source/ans_%.ans.ipynb,$(nb_srcs))
aux           := $(patsubst nb/source/%,notebooks/source/%,$(aux_srcs))
aux_answers   := $(patsubst nb/source/%,notebooks/source/ans_%,$(aux_srcs))

#
# compile
#
compile : $(ipynbs) $(ipynb_answers) $(aux) $(aux_answers)
prob : $(ipynbs) $(aux)
ans : $(ipynb_answers) $(aux_answers)

$(ipynbs) : notebooks/source/%.ipynb : nb/source/% notebooks/created
	mkdir -p $(dir $@)
	$(this_dir)mk_nb.py $(mk_nb_flags) --output $@ $< 

$(ipynb_answers) : notebooks/source/ans_%.ans.ipynb : nb/source/% notebooks/created
	mkdir -p $(dir $@)
	$(this_dir)mk_nb.py $(mk_nb_flags) --output $@ --labels ans $< 

$(aux) : notebooks/source/% : nb/source/% notebooks/created
	install --mode=0644 -D $< $@

$(aux_answers) : notebooks/source/ans_% : nb/source/% notebooks/created
	install --mode=0644 -D $< $@

notebooks/created :
	mkdir -p $@

#
# passwd (generate passwords for users)
#
passwds := $(foreach user,$(users),passwd_$(user))

$(passwds) : passwd_% :
	@echo $*,$$(slappasswd -s $(shell pwgen -H 'pwgen_secret.txt#$*' 8 1)),$(shell pwgen -H 'pwgen_secret.txt#$*' 8 1)
#	@echo $*,$(shell $(run_dir)/user_pass.py $*)

passwd : $(passwds)

#
# nbgrader_configs
#
users_sqlite := $(shell mktemp /tmp/XXXXX.sqlite)

dummy := $(shell sqlite3 $(users_sqlite) "create table a($(shell head -1 $(users_csv)))")
dummy := $(shell tail -n +2 $(users_csv) | sqlite3 -csv -separator , $(users_sqlite) ".import /dev/stdin a")

#
# ~/notebooks
#
notebooks_dirs := $(shell sqlite3 $(users_sqlite) 'select notebooks from a')

$(notebooks_dirs) : user=u$(shell sqlite3 $(users_sqlite) 'select uid from a where notebooks="$*"')
$(notebooks_dirs) : % :
	sudo -u $(user) mkdir -p $*

#
# ~/.jupyter/nbgrader_config.py
#
nbg_users := $(shell sqlite3 $(users_sqlite) 'select uid from a where class in ("pmp","pl","csi","os","pd")')
nbgrader_configs := $(foreach user,$(nbg_users),/home/$(user)/.jupyter/nbgrader_config.py)

$(nbgrader_configs) : cls=$(shell sqlite3 $(users_sqlite) 'select class from a where uid="$*"')
$(nbgrader_configs) : /home/%/.jupyter/nbgrader_config.py :
	sudo -u $* mkdir -p /home/$*/.jupyter
	sudo -u $* ln -sf /home/share/jupyter_tools/nbgrader/$(cls)/nbgrader_config.py $@

nb : $(notebooks_dirs) $(nbgrader_configs)

#
# LMS feedback
#
feedback_class ?= pl
feedback :
	sqlite3 $(users_sqlite) 'select "access https://taulec.zapto.org:8000/ with user="||user||"   passwd="||password from a where class="$(feedback_class)"'

