#!/bin/bash

root=/sys/fs/cgroup/taulec
mkdir -p ${root}
echo +memory | sudo tee ${root}/cgroup.subtree_control

# 
for u in $(ls /home); do
    mkdir -p ${root}/${u}
    echo 256M | sudo tee ${root}/${u}/memory.high
done
