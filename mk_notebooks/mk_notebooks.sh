#!/bin/bash
begin=23263
end=23270
class=py

#users=$(for x in $(seq ${begin} ${end}); do echo u${x}; done) ${class} ${class}0
users=$(for x in $(seq ${begin} ${end}); do echo u${x}; done)

ECHO=

for u in ${users}; do
    ${ECHO} sudo -u ${u} mkdir -p /home/${u}/notebooks
    ${ECHO} sudo -u ${u} mkdir -p /home/${u}/.jupyter
    ${ECHO} sudo -u ${u} ln -s /home/share/jupyter_tools/nbgrader/${class}/nbgrader_config.py /home/${u}/.jupyter/
done
