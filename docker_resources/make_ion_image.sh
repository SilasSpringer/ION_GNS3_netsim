#!/bin/bash

# temporary solution. will add a top level makefile or script that packages all of this later along with installing docker and gns3 if not already installed

docker build -t ion_base_image:0.1 - < DOCKERFILE_COMP

cd dockercontext/

docker build -t ion_2node:1.0 .

echo "2-node image built and tagged as ion_2node:1.0"
echo "base ion image built and tagged as ion_base_image:0.1"