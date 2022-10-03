#!/bin/bash

function monitor() {
    while true; do
        echo "=== date before ==="
        date
        echo "=== uptime ==="
        uptime
        echo "=== free ==="
        free
        echo "=== vmstat ==="
        vmstat
        echo "=== processes ==="
        ps -e -w -w -o user,pid,ppid,vsz,rss,stat,start,time,args
        echo "=== date after ==="
        date
        sleep 600
    done
}

monitor
