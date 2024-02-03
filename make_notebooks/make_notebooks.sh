#!/bin/bash
class=pmp
start=23000
end=23029
#class=os
#start=23300
#end=23509
#class=pl
#start=23100
#end=23249

echo=

for u in ${class} ${class}0; do
    echo "=== ${u} ==="
    ${echo} sudo -u ${u} mkdir -p /home/${u}/notebooks /home/${u}/.jupyter
    ${echo} sudo -u ${u} ln -sf /home/share/jupyter_tools/nbgrader/${class}/nbgrader_config.py /home/${u}/.jupyter/
done

for x in $(seq ${start} ${end}); do
    u=u${x}
    echo "=== ${u} ==="
    ${echo} sudo -u ${u} mkdir -p /home/${u}/notebooks /home/${u}/.jupyter
    ${echo} sudo -u ${u} ln -sf /home/share/jupyter_tools/nbgrader/${class}/nbgrader_config.py /home/${u}/.jupyter/
done
