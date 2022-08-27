#!/bin/bash
FILENAME="START_SERVER.sh"

# name of python script file to run
serverfile="START_PY_SERVER.py"

# python version to use.
# currently 3.10 since this is the minimum for pattern matching case statements in python
pyversion="python3.10"

# build base command to run
cmd="${pyversion} ${serverfile}"

# process commandline inputs.
# valid options are -[p|m|h] to set project name, running mode, and help menu respectively.
while getopts ":p:m:c:h:" option; do
   case $option in
      p) cmd="${cmd} -proj ${OPTARG}";;
      m) cmd="${cmd} -m ${OPTARG}";;
	  c) cmd="${cmd} -c ${OPTARG}";;
	  h) help;;
   esac
done

# common locations for gns3 server configs. first option is most likely
potential_configs=("${HOME}/.config/GNS3/$(ls -At "${HOME}/.config/GNS3/" | head -1)/gns3_server.conf" "${HOME}/.config/GNS3/gns3_server.conf" "${HOME}/.config/GNS3.conf" "/etc/xdg/GNS3/gns3_server.conf" "/etc/xdg/GNS3.conf" "./gns3_server.conf")

host="" # set default host to none.
port="" # set default port to none.
ptcl="" # set default protocol to none.
for conf_file in ${potential_configs[@]}; do
	if [ -f "${conf_file}" ]; 
	then
		# extract host, port, and protocol from config file.
		host="$( grep host ${conf_file} | sed "s/.*= //" )"
		port="$( grep ^port ${conf_file} | sed "s/.*= //" )"
		ptcl="$( grep protocol ${conf_file} | sed "s/.*= //" )" 
		break
	fi 
done

# add host, port, and protocol to arguments to python script if theyre found.
if [ ${host} != "" ];
then
	cmd="${cmd} -s ${host}"	
fi

if [ ${port} != "" ];
then
	cmd="${cmd} -port ${port}"	
fi

if [ ${ptcl} != "" ];
then
	cmd="${cmd} -ptcl ${ptcl}"	
fi

# run command
${cmd}



help(){
	echo "usage: ./${FILENAME} -[h|p|m] [ARGUMENT]... "
	echo "	h | display this help message"
	echo "	p | use the immediately following argument as the name of the GNS3 project to open"
	echo "	m | use the immediately following argument as the running mode for the script. "
	echo "		Valid options:"
	echo "			\"none\"  	| no automatically started applications or processes on the nodes"
	echo "			\"bping\" 	| NYI"
	echo "			\"bpfile\" 	| NYI"
	echo "			\"bptrace\"	| NYI"
}