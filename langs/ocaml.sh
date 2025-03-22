#!/bin/bash
# must be executed on each host
bash -c "sh <(curl -fsSL https://opam.ocaml.org/install.sh)"
sudo apt install unzip bubblewrap libgmp-dev libzmq3-dev pkg-config
