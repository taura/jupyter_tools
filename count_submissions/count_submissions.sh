#!/bin/bash
while :; do
    echo "=== $(date) ==="
    sudo bash -c 'ls -d /home/share/nbgrader/exchange/os/inbound/*+os2023_exam+*' | ./count_submissions.py os os2023_exam > submissions.csv
    echo "=== END ==="
    sleep 10
done
