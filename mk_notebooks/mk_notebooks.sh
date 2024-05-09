#!/bin/bash
begin=24000
end=24099
class=pl

users="$(for x in $(seq ${begin} ${end}); do echo u${x}; done) ${class} ${class}0"
#users=$(for x in $(seq ${begin} ${end}); do echo u${x}; done) 

#ECHO=echo
ECHO=

for u in ${users}; do
    ${ECHO} sudo -u ${u} mkdir -p /home/${u}/notebooks
    ${ECHO} sudo -u ${u} mkdir -p /home/${u}/.jupyter
    ${ECHO} sudo -u ${u} ln -sf /home/share/jupyter_tools/nbgrader/${class}/nbgrader_config.py /home/${u}/.jupyter/
done
