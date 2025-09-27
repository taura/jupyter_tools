#!/bin/bash
set -e

#begin=25000
#end=25149
#class=pl
begin=25150
end=25199
class=csi

#users="${class} ${class}0"
users=$(for x in $(seq ${begin} ${end}); do echo u${x}; done) 
#users="$(for x in $(seq ${begin} ${end}); do echo u${x}; done) ${class} ${class}0"

#ECHO=echo
ECHO=

for u in ${users}; do
    ${ECHO} sudo -u ${u} mkdir -p /home/${u}/notebooks
    ${ECHO} sudo -u ${u} mkdir -p /home/${u}/.jupyter
    ${ECHO} sudo -u ${u} ln -s /home/share/jupyter_tools/nbgrader/${class}/nbgrader_config.py /home/${u}/.jupyter/
done
