#!/bin/bash

dst=/home/tau/jupyter_tools/sync_hist/hist
mkdir -p ${dst}

shopt -s nullglob
printf "%s\n" /home/*/notebooks/pl/*/hist.sqlite /home/*/notebooks/pl/*/problems/*/*/hist.sqlite | rsync -avR --files-from=- / "${dst}/"
shopt -u nullglob

sudo chown -R tau:tau ${dst}
