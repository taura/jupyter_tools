#!/bin/bash

root=/sys/fs/cgroup/taulec
sudo mkdir -p ${root}
echo +memory | sudo tee ${root}/cgroup.subtree_control

# 
for u in $(ls /home); do
    echo "=== ${u} ==="
    sudo mkdir -p ${root}/${u}
    echo 256M | sudo tee ${root}/${u}/memory.high
done
