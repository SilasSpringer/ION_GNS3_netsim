#!/bin/bash

# can pull active project
projectname=$1

serverfile="START_PY_SERVER_1.py"

potential_configs=("$HOME/.config/GNS3/gns3_server.conf" "$HOME/.config/GNS3.conf" "/etc/xdg/GNS3/gns3_server.conf" "/etc/xdg/GNS3.conf" "./gns3_server.conf" "$HOME/.config/GNS3/2.2/gns3_server.conf")

# want to make this fixed, probably, or figure out a robust way of getting the server config.
host="132.235.3.193"

for conf_file in ${potential_configs[@]}; do
	if [ -f "$conf_file" ]; 
	then
		host = $( cat $conf_file | grep "host" | sed "s/.*= //" )
		break
	fi 
	
done

echo "server host: $host"
if [ ${1:-'-'} = '-' ];
then
	python3 $serverfile "$host"
else
	echo "project name: $projectname"	
	python3 $serverfile "$host" "$projectname"
fi




