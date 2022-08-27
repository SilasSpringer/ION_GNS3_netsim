#!/bin/bash

# temporary solution. will add a top level makefile or script that packages all of this later along with installing docker and gns3 if not already installed

cd dockercontext/

NAME="sspringe/ion_node_ubuntu_latest"
VERSION="1.1"

docker build -t ${NAME}:${VERSION} .

echo "ion image built and tagged as ${NAME}:${VERSION}"