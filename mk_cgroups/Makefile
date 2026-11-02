
CC:=gcc
CFLAGS:=-Wall -Wextra -O3

all : /usr/local/bin/cg_mem_limit /usr/local/bin/write_to_cgroup_procs

/usr/local/bin/cg_mem_limit : cg_mem_limit.py
	sudo install -m 755 $< $@

/usr/local/bin/write_to_cgroup_procs : write_to_cgroup_procs
	sudo install -m 4755 $< $@

write_to_cgroup_procs : write_to_cgroup_procs.c
	$(CC) $(CFLAGS) -o $@ $<
