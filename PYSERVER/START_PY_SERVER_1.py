import sys
import gns3fy

from tabulate import tabulate
import subprocess

# host and project name need to be specified by user/script.

subnet="192.168.0."

numargs = len(sys.argv)

if numargs > 3 or numargs < 2:
	sys.exit(str("usage: python3 START_PY_SERVER_1.py <gns3serverhost> <projectname (optional)>\nnum args was " + str(numargs)))

serverhost = str(sys.argv[1])
if numargs == 3:
	projectname = str(sys.argv[2])
else:
	projectname = None

print("server is: " + "http://" + serverhost + ":3080")

server	= gns3fy.Gns3Connector("http://" + serverhost + ":3080")

if projectname is None:
	projects = server.projects_summary(is_print=False)
	for proj in projects:
		if proj[4] == "opened":
			projectname = proj[0]
			project_id = proj[1]
			break
else:
	projects = server.projects_summary(is_print=False)
	for proj in projects:
		if proj[0] == projectname:
			project_id = proj[1]
			break

project = gns3fy.Project(name=projectname, connector=server)
project.get()
nodes 	= project.nodes_summary(is_print=False)#project.nodes
links	= project.links_summary(is_print=False)#project.links

'''
now iterate through each node and link, and make an ip for each node and interface
proferably base the ips off the interface number and node number in some way to be able to engineer them inside the containers too to configure ION. if not, will directly conf ion using docker exec in the .sh script.
'''
# limited at 24 nodes, 10 adapters
# nodes go from 1 to 25, adapters from 0 to 9.
'''ina = [] # ina - ip, nodename, adapter - contains a list of all nodes, where each node is represented by a pair that has the node name, and an array containing pairs matching each interface to an ip address.
for i, node in enumerate(project.nodes):
	ips = [] # temporary storage array for the ip-adapter pairs 
	for index, adapter in enumerate(node.ports): # for every adapter in the ports section,
		if int( str(i+1) + str(index) ) > 255:
			sys.exit("ERROR: cannot have more than 24 nodes or 10 adapters, as the ip generation method is limited in possibilities. Please reduce your network to meet requirements.")
		ips.append((adapter['name'], str(subnet + str(i+1) + str(index) + "/24")))
		# calculate a unique IP address for that adapter.	
	ina.append((node.name, i+1, ips, [(i+1, 127.0.0.1)]))
'''
ina = [] # ina - ip, nodename, adapter - contains a list of all nodes, where each node is represented by a pair that has the node name, and an array containing pairs matching each interface to an ip address.
for i, node in enumerate(project.nodes):
	ips = [] # temporary storage array for the ip-adapter pairs 
	for index, adapter in enumerate(node.ports): # for every adapter in the ports section,
		if int( str(i+1) + str(index) ) > 255:
			sys.exit("ERROR: cannot have more than 24 nodes or 10 adapters, as the ip generation method is limited in possibilities. Please reduce your network to meet requirements.")
		ips.append((adapter['name'], str(subnet + str(i+1) + str(index))))
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
	conn_ips=["127.0.0.1", "127.0.0.1"] # store ip addresses at each end of this link
	
	# link is name-iface-name-iface
	for ix, node in enumerate(ina):
		if node['name'] == link[0]: # if we find the node that is the first node in this link,
			connected[0] = node['number']
			for adapter in node['interfaces']:
				if adapter[0] == link[1]:
					conn_ips[0] = adapter[1]
					break
			
		if node['name'] == link[2]:
			connected[1] = node['number']
			for adapter in node['interfaces']:
				if adapter[0] == link[3]:
					conn_ips[1] = adapter[1]
					break
	ina[connected[0]-1]['neighbors'].append((connected[1], conn_ips[1]))
	ina[connected[1]-1]['neighbors'].append((connected[0], conn_ips[0]))
			
# start nodes ( need to remove entrypoint configurator )
# also runs commands to assign IP addresses on each node for each interface.
node_accessors = []
for j, node in enumerate(ina):
	node_accessors.append(gns3fy.Node(project_id=project.project_id, name=node['name'], connector=server))
	node_accessors[j].start() # start node
	# assign ips to each interface on node.
	for iface in node['interfaces']:
		command=["docker", "exec", "-t", str(node_accessors[j].properties['container_id'])]
		command.extend(['ip', 'addr', 'add', str(iface[1]+"/24"), 'dev', iface[0]])
		subprocess.run(command)
	
	#./conf_script.sh <nodenum> <numneighbors> <neighbors> nx.ionrc nx.ionconfig nx.ltprc
	# TODO: move config directory up a layer to allow access regardless of ion config version.
	# TODO: remove debug print, or at least disable debug print in container conf_script.
	command = ['docker', 'exec', '-t', '-w', '/ion-open-source-4.1.0/ion_config/', str(node_accessors[j].properties['container_id']),
	'./conf_script.sh', str(node['number']), str(len(node['neighbors']))]
	neighbors = map( lambda x: str(x[0]), node['neighbors'] )
	command.extend(neighbors)
	command.extend(['nx.ionrc','nx.ionconfig','nx.ltprc'])
	subprocess.run(command)

# use link information and the matrix of tuples made above to configure the .bprc and .ipnrc files on each node.

# make/edit/upload contact plan file and put on each node then run it.

# start all config files in appropriate admin service (bpadmin, ionadmin, etc.)



print(project.name)
print(project_id)
print(nodes)
print(links)

print("\n\n")
print(tabulate(ina))
