#!/bin/bash -x
set -eu

# this has to be done by 'share' user, on one node in the cluster

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
pip install sos jupyter_contrib_core sos-notebook jupyterlab_sos
python -m sos_notebook.install --prefix ~/venv/jupyter/
