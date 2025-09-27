#!/bin/bash
set -e

#begin=25000
#end=25149
#class=pl
begin=25202
end=25399
class=os

#users="${class} ${class}0"
users=$(for x in $(seq ${begin} ${end}); do echo u${x}; done) 
#users="$(for x in $(seq ${begin} ${end}); do echo u${x}; done) ${class} ${class}0"

#ECHO=echo
ECHO=

for u in ${users}; do
    echo "=== ${u} ==="
    ${ECHO} sudo -u ${u} mkdir -p /home/${u}/notebooks
    ${ECHO} sudo -u ${u} mkdir -p /home/${u}/.jupyter
    ${ECHO} sudo -u ${u} ln -s /home/share/jupyter_tools/nbgrader/${class}/nbgrader_config.py /home/${u}/.jupyter/
done
