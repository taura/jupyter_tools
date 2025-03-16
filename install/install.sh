#!/bin/bash -x
set -eu

# prerequisites

# apt install python3-pip npm libcurl4-openssl-dev libssl-dev
# npm -g install configurable-http-proxy

#python3 -m venv ~/venv/jupyter
. ~/venv/jupyter/bin/activate

# jupyter
pip install jupyterhub==4.0.2 jupyterhub-idle-culler pycurl jupyterlab

# nbgrader
pip install nbgrader
mkdir -p ~/nbgrader/exchange
chmod -R 0777 ~/nbgrader
sudo ln -sf ~/nbgrader /usr/local/share/nbgrader

# bash
pip install bash_kernel
python -m bash_kernel.install --prefix ~/venv/jupyter/

# sos
sudo apt remove sosreport
pip install sos jupyter_contrib_core sos-notebook jupyterlab_sos
python -m sos_notebook.install --prefix ~/venv/jupyter/
