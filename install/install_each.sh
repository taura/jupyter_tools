#!/bin/bash -x
set -eu

# this has to be done by any sudoer on each node in the cluster

# Jupyter prerequisites
sudo apt install python3-pip npm libcurl4-openssl-dev libssl-dev
sudo npm -g install configurable-http-proxy
# Jupyter SoS prerequisites
sudo apt remove sosreport
# OCaml prerequisite
sudo apt install unzip bubblewrap libgmp-dev libzmq3-dev pkg-config npm
