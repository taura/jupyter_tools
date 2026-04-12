#!/bin/bash

src=/home
dst=hist
hist=${dst}/hist_files.txt

find ${src} -name "hist.sqlite" -type f > ${hist}
rsync -avR --files-from=${hist} / ${dst}/
sudo chown -R tau:tau ${dst}
