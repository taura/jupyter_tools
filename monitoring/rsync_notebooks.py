#!/usr/bin/python3

"""
rsync notebooks and put file info into db
"""

import argparse
import csv
import os
import pwd
import grp
import subprocess
import sys
import time

import make_database

def do_rsync(srcs, dest, suffix, log, owner, no_sudo):
    """
    run rsync to copy all dirs in SRCS under DEST, making a back up of
    overwritten files with SUFFIX; a line saying suffix=SUFFIX and
    all outputs from rsync are put into a file named LOG.  It will
    be read by read_copied_files to update the database
    """
    assert(len(srcs) > 0)
    sudo = "" if no_sudo else "sudo"
    cmd = '(echo suffix={suffix}; {sudo} rsync --itemize-changes --out-format="%i|%n|" --relative --recursive --update --perms --owner --group --times --links --safe-links --super --one-file-system --backup --max-size=10m --suffix={suffix} {srcs} {dest}/) > {log}; {sudo} chmod -R +rX {dest}'.format(srcs=" ".join(srcs), dest=dest, suffix=suffix, log=log, owner=owner, sudo=sudo)
    print(cmd)
    return subprocess.run(cmd, check=False, shell=True)

def update_database(log, users_csv, dest, db, no_sudo):
    sudo = "" if no_sudo else "sudo"
    cmd = ('{sudo} ./make_database.py --users-csv {users_csv} --log {log} --dest {dest} --db {db}'
           .format(users_csv=users_csv, log=log, dest=dest, db=db, sudo=sudo))
    print(cmd)
    return subprocess.run(cmd, shell=True)

def read_user_csv(a_csv):
    """
    read user csv and collect values in "notebooks" column
    """
    with open(a_csv) as a_fp:
        csv_fp = csv.DictReader(a_fp)
        srcs = [row["notebooks"] for row in csv_fp]
    return srcs

def get_user_group():
    uid = os.geteuid()
    pw = pwd.getpwuid(uid)
    user = pw.pw_name
    gr = grp.getgrgid(pw.pw_gid)
    group = gr.gr_name
    return "{}:{}".format(user, group)

def do_rsync_and_update_db(opt):
    """
    run rsync, read the log and update database
    """
    now = time.strftime("%Y-%m-%dT%H:%M:%S",
                        time.localtime(time.time()))
    print("======== {} ========".format(now))
    log = "{log_dir}/sync_{now}.log".format(log_dir=opt.log_dir, now=now)
    suffix = ".bak_{}".format(now)
    srcs = read_user_csv(opt.users_csv)
    os.makedirs(opt.log_dir, exist_ok=True)
    os.makedirs(opt.dest, exist_ok=True)
    if len(srcs) > 0:
        owner = get_user_group()
        do_rsync(srcs, opt.dest, suffix, log, owner, opt.no_sudo)
        update_database(log, opt.users_csv, opt.dest, opt.db, opt.no_sudo)

def replay_log_and_update_db(opt):
    """
    run rsync, read the log and update database
    """
    os.makedirs(opt.log_dir, exist_ok=True)
    os.makedirs(opt.dest, exist_ok=True)
    for log_ in sorted(os.listdir(opt.log_dir)):
        log = "{}/{}".format(opt.log_dir, log_)
        update_database(log, opt.dest, opt.db, opt.no_sudo)

def parse_argv(argv):
    """
    parse argv
    """
    psr = argparse.ArgumentParser(prog=argv[0])
    psr.add_argument("--users-csv", default="users.csv",
                     help=("a csv file describing directories to monitor, which at minimum must have a column 'notebooks'."
                           " they are typically notebooks/ directories of students (default: users.csv)."))
    psr.add_argument("--dest", default="sync_dest",
                     help=("the directory into which directories are copied (default: ./sync_dest)"))
    psr.add_argument("--log-dir", default="sync_logs",
                     help=("the directory into which rsync logs are stored (default: ./sync_logs)"))
    psr.add_argument("--db", default="sync.sqlite",
                     help=("sqlite3 database to which all file histories are stored (default: sync.sqlite)"))
    psr.add_argument("--repeat", default=-1, type=int,
                     help=("the number of times directories are copied."
                           " after this number of times, the program quits."
                           " negative numbers indicate forever (default: -1)."))
    psr.add_argument("--overhead", default=0.05, type=float,
                     help=("the maximum CPU usage of this program (default: 0.05)."
                           " if this value is 0.05, it makes sure the program uses 5%% worth of a single core."
                           " it adjusts the overhead by adjusting the interval between two consecutive copies."))
    psr.add_argument("--min-sleep", default=300.0, type=float,
                     help=("the minimum interval between two consecutive copies."))
    psr.add_argument("--no-sudo", action="store_true",
                     help=("if given, sudo is not used"))
    psr.add_argument("--replay-log", action="store_true",
                     help=("mainly used for debugging.  if given, it does not look"
                           " at the actual user files.  it instead looks at the log directory (--log-dir) and"
                           " and reconstruct the database solely based on the log."))
    opt = psr.parse_args(argv[1:])
    return opt

def main():
    """
    main
    """
    opt = parse_argv(sys.argv)
    if opt.replay_log:
        replay_log_and_update_db(opt)
    else:
        i = 0
        repeat = opt.repeat
        while repeat < 0 or i < repeat:
            t0 = time.time()
            do_rsync_and_update_db(opt)
            t1 = time.time()
            dt = t1 - t0
            sleep_time = max(opt.min_sleep, dt / opt.overhead)
            print("took {:.2} sec to update, sleep {:.2} sec until next updte"
                  .format(dt, sleep_time), flush=True)
            time.sleep(sleep_time)
            i = i + 1

main()

# >f..t......|gp/libitrace/test/f.cc|
