#!/bin/bash

src=/home/u26099
dst=hist
mkdir -p ${dst}

shopt -s nullglob
printf "%s\n" ${src}/notebooks/pl/*/hist.sqlite ${src}/notebooks/pl/*/problems/*/*/hist.sqlite | rsync -avR --files-from=- / "${dst}/"
shopt -u nullglob

sudo chown -R tau:tau ${dst}
