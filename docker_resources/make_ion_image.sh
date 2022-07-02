#!/bin/bash

# temporary solution. will add a top level makefile or script that packages all of this later along with installing docker and gns3 if not already installed

cd dockercontext/

docker build -t sspringe/ion_node_ubuntu_latest:1.1 .

echo "2-node image built and tagged as ion_2node:1.0"
echo "base ion image built and tagged as ion_base_image:0.1"