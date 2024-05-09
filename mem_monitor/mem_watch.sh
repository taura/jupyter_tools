#!/bin/bash

count_vscode() {
    ps auxww | egrep -e '(vscode-server.*command-shell)' | grep -v grep | wc -l
}

count_jupyter() {
    ps auxww | egrep -e '(jupyterhub-singluser)' | grep -v grep | wc -l
}

main() {
    while :; do
        echo "=========="
        echo "date : $(date)"
        echo "vscode : $(count_vscode)"
        echo "jupyter : $(count_jupyter)"
        free
        sleep 60
    done
}

main
