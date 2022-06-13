import os
import sys
import json
import gns3fy
import subprocess
from tabulate import tabulate


# host and project name need to be specified by user/script.


# BEGIN CONFIG FILE

# TODO: add security checks to make sure illegal configuration options are 
# spit out as warnings to commandline, and default values are used instead of garbage.

with open("pyscript.conf", "r") as conffile:
	conf = json.load(conffile)

try:
	debug = conf['debug']
	if debug == "True" or debug == "true":
		debug = True
		print("debug enabled")
	else:
		debug = False
except:
	debug = False
	
try:
	netaddr = str(conf['net_address'] + ".")
except:
	netaddr = "192.168.0."

try:
	serverptcl = conf['gns3serverptcl']
except:
	serverptcl = "http"

try:
	serverport = conf['gns3serverport']
except:
	serverport = "3080"

try:
	linkprotocol = conf['link_protocol']
except:
	linkprotocol = "tcp"

try: 
	contconfpath = conf['container_config_path']
except:
	contconfpath = "/ion-open-source-4.1.0/ion_config/"

try:
	ionport = conf['ion_port']
except:
	ionport = "4556"
# END CONFIG FILE

# BEGIN COMMANDLINE INPUT
numargs = len(sys.argv)

# make sure number of given arguments is within acceptable range.
if numargs > 3 or numargs < 2:
	sys.exit(str("usage: python3 START_PY_SERVER_1.py <gns3serverhost> <projectname (optional)>\nnum args was " + str(numargs)))

serverhost = str(sys.argv[1])

if numargs == 3:
	projectname = str(sys.argv[2])
else:
	projectname = None
# END COMMANDLINE INPUT

if debug:
	print("server is: " + serverptcl + "://" + serverhost + ":" + serverport)

server	= gns3fy.Gns3Connector(serverptcl + "://" + serverhost + ":" + serverport)

# get the active project name if no project name was supplied.
if projectname is None:
	projects = server.projects_summary(is_print=False)
	for proj in projects:
		if proj[4] == "opened":
			projectname = proj[0]
			project_id = proj[1]
			break
# if the project name was supplied, find it in the list of projects on the GNS3 server and record its project ID
else: 
	projects = server.projects_summary(is_print=False)
	for proj in projects:
		if proj[0] == projectname:
			project_id = proj[1]
			break
# open project and fetch details
project = gns3fy.Project(name=projectname, connector=server)
project.get()

# get a node and link summary
nodes 	= project.nodes_summary(is_print=False)
links	= project.links_summary(is_print=False)

# now iterate through each node and link, and make an ip for each node and interface
# limited at 24 nodes, 10 adapters using current method.
# nodes go from 1 to 24, adapters from 0 to 9. (with a final address range of <netaddr>.1 to <netaddr>.249 )

# ina - ip, nodename, adapter - contains a list of all nodes, 
# where each node is represented by a pair that has the node name, 
# and an array containing pairs matching each interface to an ip address.
ina = [] 
for i, node in enumerate(project.nodes):
	ips = [] # temporary storage array for the ip-adapter pairs 
	for index, adapter in enumerate(node.ports): # for every adapter in the ports section,
		if int( str(i+1) + str(index) ) > 255:
			sys.exit("ERROR: cannot have more than 24 nodes or 10 adapters, as the ip generation method is limited in possibilities. Please reduce your network to meet requirements.")
		# TODO: use a better method or at least make the mehtod configurable for the way ips are generated to allow for larger networks.
		ips.append((adapter['name'], str(netaddr + str(i+1) + str(index))))
		# calculate a unique IP address for that adapter.	
	ina.append({
		'name' : node.name, 
		'number' : i+1, 
		'interfaces' : ips, 
		'neighbors' : [] 
		})
	


# TODO: clean this up to be more efficient, maybe use a hashmap to store the modes for faster lookup?
for link in links:
	connected=[0,0] # store node numbers of connected nodes in this link
	conn_ips=["127.0.0.1", "127.0.0.1"] # store ip addresses at each end of this link. 
	#TODO add security checks to make sure that all nodes have correct ips, rather than 
	# hoping it all works as intended. currently could recieve a loopback ip (127.0.0.1) if the correct ip isnt found.
	
	# link is name-iface-name-iface (indexes 0,2 are node names, indexes 1,3 are interfaces on their respective nodes.)
	for ix, node in enumerate(ina): # for each node
		if node['name'] == link[0]: # if we find the node that is the first node in this link,
			connected[0] = node['number'] # record its number
			for adapter in node['interfaces']: # for each interface on the node,
				if adapter[0] == link[1]:  # if it is the adapter used for this link, 
					conn_ips[0] = adapter[1] # record the ip address
					break
			
		if node['name'] == link[2]: # if we find the node that is the second node in this link,
			connected[1] = node['number'] # record its number
			for adapter in node['interfaces']: # for each interface on the node,
				if adapter[0] == link[3]: # if it is the adapter used for this link, 
					conn_ips[1] = adapter[1] # record the ip address
					break
	ina[connected[0]-1]['neighbors'].append((connected[1], conn_ips[1])) # set the ip address and number of the connected node as a neighbor for the other node
	ina[connected[1]-1]['neighbors'].append((connected[0], conn_ips[0])) # set the ip address and number of the connected node as a neighbor for the other node
			

# starts nodes and also runs commands to assign IP addresses on each node for each interface.
# TODO: potentially shift away from using docker exec to run commands on the nodes, or at least 
# shift to opening a pseudoterminal in the node and submitting commands sequentially, 
# rather than submitting each command separately through its own exec command subprocess
node_accessors = []

for j, node in enumerate(ina):
	node_accessors.append(gns3fy.Node(project_id=project.project_id, name=node['name'], connector=server))
	# temporary solution for adding the IPN numbers to the names of each node as they start. 
	# TODO: update this to read the ipn number from the title if it exists, so the user can specify ipn numbers.
	if node['name'].find('ipn:') == -1:
		node_accessors[j].update(name=str(node['name'] + "-ipn:" + str(node['number'])))
	node_accessors[j].start() # start node
	# assign ips to each interface on node.
	# for iface in node['interfaces']:
	# 	command=["docker", "exec", "-t", str(node_accessors[j].properties['container_id'])] # MARK-DOCKER-COMMAND
	# 	command.extend(['ip', 'addr', 'add', str(iface[1]+"/24"), 'dev', iface[0]])
	# 	subprocess.run(command, stdout=subprocess.DEVNULL) # MARK-SUBPROCESS

	#./conf_script.sh <nodenum> <numneighbors> <neighbors> <input files>
	# conf_script replaces all matches of <[xX]> with the node number, and all matches of <[yY]> 
	# with the line containing that match for each neighbor with the match replaced by each neighbor nodes' number.
	# TODO: move config directory up a layer to allow access regardless of ion config version.
	# command = ['docker', 'exec', '-t', '-w', contconfpath, str(node_accessors[j].properties['container_id']),
	# './conf_script.sh', str(node['number']), str(len(node['neighbors']))]  # MARK-DOCKER-COMMAND
	# neighbors = map( lambda x: str(x[0]), node['neighbors'] )
	# command.extend(neighbors)
	# command.extend(['nx.ionrc','nx.ipnrc','nx.bprc'])# currently unconfigurable files: 'nx.ionconfig' 'nx.ltprc'
	# subprocess.run(command, stdout=subprocess.DEVNULL) # MARK-SUBPROCESS

	#TODO: condense these commands together into one command or change to using a command streaming method.
	# for neighbor in node['neighbors']:
	# 	command = ['docker', 'exec', '-t', '-w', contconfpath, str(node_accessors[j].properties['container_id']), 'sed', '-i']  # MARK-DOCKER-COMMAND
	# 	command.append("/^\#OUTDUCT_TRIGGER_LINE/a" + "a outduct " + linkprotocol + " " + neighbor[1] + ":" + ionport + " " + linkprotocol + "clo")
	# 	command.append("nx.bprc")
	# 	subprocess.run(command, stdout=subprocess.DEVNULL) # MARK-SUBPROCESS
	# 	command = ['docker', 'exec', '-t', '-w', contconfpath, str(node_accessors[j].properties['container_id']), 'sed', '-i']  # MARK-DOCKER-COMMAND
	# 	command.append("/^\#PLAN_TRIGGER_LINE/a" + "a plan " + str(neighbor[0]) + " " + linkprotocol + "/" + neighbor[1] + ":" + ionport)
	# 	command.append("nx.ipnrc")
	# 	subprocess.run(command, stdout=subprocess.DEVNULL) # MARK-SUBPROCESS
	command=["docker", "exec", "-t", '-w', contconfpath, str(node_accessors[j].properties['container_id']), '/bin/bash', '-c'] # MARK-DOCKER-COMMAND
	cmds=""
	for iface in node['interfaces']:
		cmds = cmds + "ip addr add " + str(iface[1]+"/24") + " dev " + iface[0]
		cmds = cmds + " && "
	cmds = cmds + "./conf_script.sh " + str(node['number']) + " " + str(len(node['neighbors'])) + " " # MARK-DOCKER-COMMAND
	neighbors = map( lambda x: str(x[0]), node['neighbors'] )
	cmds = cmds + " ".join(neighbors)
	cmds = cmds + " nx.ionrc nx.ipnrc nx.bprc && " # currently unconfigurable files: 'nx.ionconfig' 'nx.ltprc'
	for neighbor in node['neighbors']:
		cmds = cmds + "sed -i /^\#OUTDUCT_TRIGGER_LINE/a" + "a outduct " + linkprotocol + " " + neighbor[1] + ":" + ionport + " " + linkprotocol + "clo nx.bprc"
		cmds = cmds + " && "
		cmds = cmds + "sed -i /^\#PLAN_TRIGGER_LINE/a" + "a plan " + str(neighbor[0]) + " " + linkprotocol + "/" + neighbor[1] + ":" + ionport + " nx.ipnrc"
		cmds = cmds + " && "
	cmds = cmds + "ps auxww"
	command.append(cmds)
	if not debug:
		subprocess.run(command, stdout=subprocess.DEVNULL)
	else:
		subprocess.run(command)

	
	# TEMP SOLN
	# TODO: run using a command stream solution, and get a better contact plan default fallback for if the plan is missing.
	# probably generate a permanent uptime perfect links contact file if none is given.
	command = ['docker', 'exec', '-t', '-w', contconfpath, str(node_accessors[j].properties['container_id']), '/bin/bash', '-c', 'ionadmin nx.ionrc && ionadmin contacts.ionrc && bpadmin nx.bprc && ltpadmin nx.ltprc']
	if not debug:
		subprocess.run(command, stdout=subprocess.DEVNULL)
	else:
		subprocess.run(command)
	#subprocess.run([*command, 'ionadmin', 'nx.ionrc'], stdout=subprocess.DEVNULL)	
	#subprocess.run([*command, 'ionadmin', 'contacts.ionrc'], stdout=subprocess.DEVNULL)	# assumes contact plan is supplied on the container.
	#subprocess.run([*command, 'bpadmin', 'nx.bprc'], stdout=subprocess.DEVNULL)	
	#subprocess.run([*command, 'ltpadmin', 'nx.ltprc'], stdout=subprocess.DEVNULL)	


		


# use link information and the matrix of tuples made above to configure the .bprc and .ipnrc files on each node.

# make/edit/upload contact plan file and put on each node then run it.

# start all config files in appropriate admin service (bpadmin, ionadmin, etc.)


if debug:
	print("project name: ")
	print(project.name)
	print("project id: ")
	print(project_id)
	print("node summary:")
	print(nodes)
	print("link summary:")
	print(links)

	print("\nina - node, adapter, and ip summary table:")
	print(tabulate(ina))
