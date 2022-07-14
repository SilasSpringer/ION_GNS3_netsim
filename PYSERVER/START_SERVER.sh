#!/bin/bash

pyversion="python3.10"

# can pull active project, so this is optional.
projectname=$1

# name of python script file to run
serverfile="START_PY_SERVER.py"

# common locations for gns3 server configs. first option is most likely
potential_configs=("${HOME}/.config/GNS3/$(ls -At "${HOME}/.config/GNS3/" | head -1)/gns3_server.conf" "${HOME}/.config/GNS3/gns3_server.conf" "${HOME}/.config/GNS3.conf" "/etc/xdg/GNS3/gns3_server.conf" "/etc/xdg/GNS3.conf" "./gns3_server.conf")

host="" # set default host to none.
port="" # set default port to none.
ptcl="" # set default protocol to none.
for conf_file in ${potential_configs[@]}; do
	if [ -f "${conf_file}" ]; 
	then
		host="$( grep host ${conf_file} | sed "s/.*= //" )"
		port="$( grep ^port ${conf_file} | sed "s/.*= //" )"
		ptcl="$( grep protocol ${conf_file} | sed "s/.*= //" )" 
		break
	fi 
done

echo "server host: ${host}"

# build command to run
cmd="${pyversion} ${serverfile}"

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

if [ ${1:-'-'} != '-' ];
then
	echo "project name: ${projectname}"	
	cmd="${cmd} -p ${projectname}"
fi

# run command
${cmd}

