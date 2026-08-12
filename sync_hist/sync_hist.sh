#!/bin/bash

ssh taulec sudo -S jupyter_tools/sync_hist/sync_hist_on_remote.sh
rsync -avz taulec:jupyter_tools/sync_hist/hist ./
