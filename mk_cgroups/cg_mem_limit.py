#!/usr/bin/python3

import getpass
import os
import sys

def check_exist(filename):
    if not os.path.exists(filename):
        sys.stderr.write("error: %s does not exist\n" % filename)
        sys.exit(1)

def main():
    cgroup_procs = "/sys/fs/cgroup/taulec/%s/cgroup.procs" % getpass.getuser()
    write_to_cgroup_procs = "/usr/local/bin/write_to_cgroup_procs"
    check_exist(cgroup_procs)
    check_exist(write_to_cgroup_procs)
    argv = sys.argv
    pid = os.getpid()
    cmd = "%s %d %s" % (write_to_cgroup_procs, pid, cgroup_procs)
    st = os.system(cmd)
    if st != 0:
        os._exit(1)
    os.execvp(argv[1], argv[1:])

def main_xxx():
    cgroup_procs = "/sys/fs/cgroup/taulec/%s/cgroup.procs" % getpass.getuser()
    write_to_cgroup_procs = "{{ wtcp }}"
    check_exist(cgroup_procs)
    check_exist(write_to_cgroup_procs)
    argv = sys.argv
    r,w = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(w)
        go = os.read(r, 2)
        if go == b"go":
            os.execvp(argv[1], argv[1:])
    else:
        os.close(r)
        cmd = "%s %d %s" % (write_to_cgroup_procs, pid, cgroup_procs)
        st = os.system(cmd)
        if st == 0:
            os.write(w, b"go")
        os.close(w)
        os.waitpid(pid, 0)

main()
