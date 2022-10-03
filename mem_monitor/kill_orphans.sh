#!/bin/bash

kill_orphans() {
    for i in $(seq 1 3); do
        echo "--------- shot $i ---------"
        ps -e -w -w -o user,pid,ppid,vsz,rss,stat,start,time,args | awk '$3 == 1 && $1 ~ /(pl|pmp|u22.)/ {print}'
        if ! sudo kill -9 $(ps -e -w -w -o user,pid,ppid,vsz,rss,stat,start,time,args | awk '$3 == 1 && $1 ~ /(pl|pmp|u22.)/ {print $2}') 2> /dev/null ; then break; fi
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
