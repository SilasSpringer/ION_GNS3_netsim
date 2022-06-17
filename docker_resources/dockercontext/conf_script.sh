#!/bin/bash

# first argument is the name of the node
# second argument (X) is the number of other nodes
# the following X  arguments are the names of the other nodes
# the remaining arguments are the input files

#
# this script is intended and should work if we choose to configure all nodes at runtime when the
# user has finished building their network, it requires knowledge of it's neighbors and their names

# need to reset config to default before running this script (e.g. restart the node)

DEBUG="true"

ARGS=("$@")
NODENAME=${ARGS[0]}
NUM_OTHERNODES=${ARGS[1]}
OTHERNODES=()

#if the nodename is -, then take the name of the node from the hostname environment variable.
if [ $NODENAME = "-" ] 
then
	NODENAME=$(cut -d "-" -f2- <<< "$(printenv HOSTNAME)")
	echo "node name set to HOSTNAME: $NODENAME"
fi

# extract array of the names of the other nodes given.
for NUM in $(seq 2 $(expr $NUM_OTHERNODES + 1 ) ); do
	OTHERNODES+=("${ARGS[$NUM]}")
done

# debug
if [ $DEBUG = "true" ] 
then
	echo "full args list: ${ARGS[@]}"
	echo "node name: $NODENAME"
	echo "num other nodes known: $NUM_OTHERNODES"
	echo "names of other nodes known: ${OTHERNODES[@]}"
	echo "ARG numbers that are files to change: $(seq $(expr 2 + $NUM_OTHERNODES) $(expr ${#ARGS[@]} - 1 ))"
fi

# fix the files given.
for NUM in $(seq $(expr 2 + $NUM_OTHERNODES) $(expr ${#ARGS[@]} - 1 )); do
	sed -i "s/<[xX]>/$NODENAME/g" ${ARGS[$NUM]}
	for I in ${OTHERNODES[@]}; do
		awk  "1; gsub(/<[yY]>/,"$I")" ${ARGS[$NUM]} > tmp && mv -f tmp ${ARGS[$NUM]}
	done
	sed -i "s/<[yY]>/$NODENAME/g" ${ARGS[$NUM]}
	
done

echo "conf_script complete"