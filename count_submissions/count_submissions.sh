#!/bin/bash
while :; do
    echo "=== $(date) ==="
    sudo bash -c 'ls -d /home/share/nbgrader/exchange/os/inbound/*+os2025_exam_practice+*' | ./count_submissions.py os os2025_exam_practice 2026-01-14-10-00 > submissions.csv
    echo "=== END ==="
    sleep 10
done
