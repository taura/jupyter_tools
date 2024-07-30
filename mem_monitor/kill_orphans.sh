#!/bin/bash

kill_orphans() {
    for i in $(seq 1 10); do
        echo "--------- shot $i ---------"
        ps -e -w -w -o user,pid,ppid,vsz,rss,stat,start,time,args | awk '$3 == 1 && $9 != "/lib/systemd/systemd" && $1 ~ /(pl0|u24.)/ {print}'
        if ! sudo kill -9 $(ps -e -w -w -o user,pid,ppid,vsz,rss,stat,start,time,args | awk '$3 == 1 && $9 != "/lib/systemd/systemd" && $1 ~ /(pl0|u24.)/ {print $2}') 2> /dev/null ; then break; fi
        sleep 2
    done
}

repeat_kill_orphans() {
    while true; do
        echo "======== $(date) ========"
        kill_orphans
        sleep 60
    done
}

repeat_kill_orphans
