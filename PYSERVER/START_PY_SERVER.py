import os
import sys
import json
import gns3fy
import telnetlib
import subprocess
from tabulate import tabulate

from make_contacts import makecontactfile

FILENAME="START_PY_SERVER.py"

def print_help():
	print("usage: python[3.X] " + FILENAME + " -[s|c|m|port|ptcl|proj] [ARGUMENT]...")
	print("		m   	| Use following argument as the running mode. For more info, see the help for START_SERVER.sh")
	print("		c   	| Use following argument as the path to the contact file")
	print("		s   	| Use following argument as server hostname")
	print("		proj 	| Use following argument as the GNS3 project name")
	print("		port	| Use following argument as the server port number")
	print("		ptcl 	| Use following argument as the server protocol.")

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
	netaddr = "192.168."

try:
	serverptcl = conf['gns3serverptcl']
except:
	serverptcl = "http"

try:
	serverhost = conf['gns3server']
except:
	serverhost = "localhost"

try:
	serverport = conf['gns3serverport']
except:
	serverport = "3080"

try:
	linkprotocol = conf['link_protocol']
except:
	linkprotocol = "udp"

try: 
	contconfpath = conf['container_config_path']
except:
	contconfpath = "/root/ion_config/"

try:
	ionport = conf['ion_port']
except:
	ionport = "4556"

try: 
	contactfile = conf['contactfile']
except:
	contactfile = None

try:
	universallinkdelay = conf['universallinkdelay']
except:
	universallinkdelay = None

try:
	universallinkbitrate = conf['universallinkbitrate']
except:
    universallinkbitrate = None

try:
	tc_bandwidth_limiting = conf['tc_bandwidth_limiting']
except:
	tc_bandwidth_limiting = "default"
# END CONFIG FILE

# BEGIN COMMANDLINE INPUT
numargs = len(sys.argv)

projectname = None # set default projectname
runningmode = None # set default running mode

tmp = iter(sys.argv[1:])
paired = zip(tmp,tmp)
for pair in paired:
	# match-case is exclusive to python3.10+ 
	# should probably use something else to allow use of older python versions.
	match pair[0]:
		case "-s":
			serverhost = pair[1]
		case "-port":
			serverport = pair[1]
		case "-ptcl":
			serverptcl = pair[1]
		case "-proj":
			projectname = pair[1]
		case "-c":
			contactfile = pair[1]
		case "-m":
			runningmode = pair[1]
		case _:
			print_help()
			sys.exit(str("invalid option: " + str(pair[0])))

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
		if i+1 > 255 or index > 255:
			sys.exit("ERROR: cannot have more than 254 nodes or 255 adapters, as the ip generation method is limited in possibilities. Please reduce network to meet requirements.")
		# TODO: add ability to exclude specific ip addresses from usable range, to allow connection to outside machines with the same first 2 octets.
		# first 2 octets of used ip addresses are user specified
		# calculate a unique IP address for that adapter.	
		ips.append((adapter['name'], str(netaddr + str(index) + "." + str(i+1))))
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
	conn_ifs=["null", "null"]
	#TODO add security checks to make sure that all nodes have correct ips, rather than 
	# hoping it all works as intended. currently could recieve a loopback ip (127.0.0.1) if the correct ip isnt found.
	
	# link is name-iface-name-iface (indexes 0,2 are node names, indexes 1,3 are interfaces on their respective nodes.)
	for ix, node in enumerate(ina): # for each node
		if node['name'] == link[0]: # if we find the node that is the first node in this link,
			connected[0] = node['number'] # record its number
			conn_ifs[0] = link[1] # record interface used
			for adapter in node['interfaces']: # for each interface on the node,
				if adapter[0] == link[1]:  # if it is the adapter used for this link, 
					conn_ips[0] = adapter[1] # record the ip address
					break
			
		if node['name'] == link[2]: # if we find the node that is the second node in this link,
			connected[1] = node['number'] # record its number
			conn_ifs[1] = link[3] # record interface used
			for adapter in node['interfaces']: # for each interface on the node,
				if adapter[0] == link[3]: # if it is the adapter used for this link, 
					conn_ips[1] = adapter[1] # record the ip address
					break
	ina[connected[0]-1]['neighbors'].append((connected[1], conn_ips[1], conn_ifs[1])) # set the ip address and number of the connected node as a neighbor for the other node
	ina[connected[1]-1]['neighbors'].append((connected[0], conn_ips[0], conn_ifs[0])) # set the ip address and number of the connected node as a neighbor for the other node
	
if contactfile == None:
	contactfile = "contacts.ionrc"
	contactfile_contents = makecontactfile(ina, contactfile, universallinkbitrate, universallinkdelay)
else:
	try:
		f = open(contactfile, 'r')
		contactfile_contents = f.read() 
		f.close()
	except:
		print("could not open or read given contacts file. using default permanent uptime contact plan.")
		contactfile = "contacts.ionrc"
		contactfile_contents = makecontactfile(ina, contactfile, universallinkbitrate, universallinkdelay)


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
	
	# wait until node has started.
	while node_accessors[j].status == 'stopped':
		pass

	node_env = str(node_accessors[j].properties['environment'])

	# run all the commands needed to configure a node.	
	tn = telnetlib.Telnet('127.0.0.1', str(node_accessors[j].console))
	tn.open('127.0.0.1', str(node_accessors[j].console))
	for iface in node['interfaces']:
		tmp = node_env.find('BANDWIDTH_CAP_' + iface[0])
		if tmp == -1: # if the bandwidth cap wasnt set for this interface,
			# TODO: pull rate from contact file - may be tricky since this is dependent on contact time. 
			# should be done/updated in a daemon or server running on the host that can monitor and update all nodes as needed to have one common clock controlling the delays.
			
			# temp soln, use default rate
			rate = str(universallinkbitrate + "bps")
		else:	# if it was found, extract value.
			rate = str(node_env[(tmp+len(str('BANDWIDTH_CAP_' + iface[0])) + 1):])
			rate = rate.splitlines()[0]
		
		address = "127.0.0.1"

		for neighbor in node['neighbors']:
			if iface[0] == neighbor[2]: # find the neighbor connected on this interface
				address = neighbor[1] # save the ip address of that neighbor
				break # exit loop.
		
		tn.read_until("@".encode('utf-8'))
		if address != "127.0.0.1": # only set an ip address and add qdiscs to interfaces that are being used. 
			if debug:
				print(rate)
				print(address)
			tn.write(str("ip addr add " + str(iface[1]+"/24") + " dev " + iface[0] + "\n").encode('utf-8'))
			tn.read_until("@".encode('utf-8'))
			if tc_bandwidth_limiting == "default":
				tn.write(str("tc qdisc add dev " + iface[0] + " root handle 1:0 htb default 30\n").encode('utf-8'))
				tn.read_until("@".encode('utf-8'))
				tn.write(str("tc class add dev " + iface[0] + " parent 1:0 classid 1:1 htb rate " + rate + "\n").encode('utf-8'))
				tn.read_until("@".encode('utf-8'))
				tn.write(str("tc filter add dev " + iface[0] + " protocol ip parent 1:0 prio 1 u32 match ip dst " + address + " flowid 1:1\n").encode('utf-8'))
				tn.read_until("@".encode('utf-8'))
		
	tn.write(str("cd " + contconfpath +"\n").encode('utf-8'))
	tn.read_until(contconfpath.encode('utf-8'))
	tn.write(str("./conf_script.sh "+ str(node['number']) + " " + str(len(node['neighbors'])) +" " + " ".join( map( lambda x: str(x[0]), node['neighbors'] ) ) + " nx.ionrc nx.ipnrc nx.bprc\n" ).encode('utf-8'))
	tn.read_until("conf_script complete".encode('utf-8'))

	for neighbor in node['neighbors']:		
		if( linkprotocol == 'ltp' ):
			tn.write(str("sed -i \"/^\#OUTDUCT_TRIGGER_LINE/a" + "a outduct " + linkprotocol + " " + str(neighbor[0]) + " " + linkprotocol + "clo\" nx" + str(node['number']) + ".bprc\n").encode('utf-8'))
			tn.read_until("@".encode('utf-8'))

			#TEMP - add LTP outbound loopback
			tn.write(str("sed -i \"/^\#OUTDUCT_TRIGGER_LINE/a" + "a outduct " + linkprotocol + " " + str(node['number']) + " " + linkprotocol + "clo\" nx" + str(node['number']) + ".bprc\n").encode('utf-8'))
			tn.read_until("@".encode('utf-8'))
			
			tn.write(str("sed -i \"/^\#PLAN_TRIGGER_LINE/a" + "a plan " + str(neighbor[0]) + " " + linkprotocol + "/" + str(neighbor[0]) + "\" nx" + str(node['number']) + ".ipnrc\n").encode('utf-8'))
		else:
			tn.write(str("sed -i \"/^\#OUTDUCT_TRIGGER_LINE/a" + "a outduct " + linkprotocol + " " + neighbor[1] + ":" + ionport + " " + linkprotocol + "clo\" nx" + str(node['number']) + ".bprc\n").encode('utf-8'))
			tn.read_until("@".encode('utf-8'))
			tn.write(str("sed -i \"/^\#PLAN_TRIGGER_LINE/a" + "a plan " + str(neighbor[0]) + " " + linkprotocol + "/" + neighbor[1] + ":" + ionport + "\" nx" + str(node['number']) + ".ipnrc\n").encode('utf-8'))
		tn.read_until("@".encode('utf-8'))
		
		tn.write(str("touch nx" + str(node['number']) + ".ltprc\n").encode('utf-8'))
		tn.read_until("@".encode('utf-8'))
		tn.write(str("cp nx.ltprc nx" + str(node['number']) + ".ltprc\n").encode('utf-8'))
		tn.read_until("@".encode('utf-8'))
		tn.write(str("sed -i \"/^\#SPAN_TRIGGER_LINE/a" + "a span " + str(neighbor[0]) + " 100 100 64000 100000 1 \'udplso " + neighbor[1] + ":1113 40000000\' \" nx" + str(node['number']) + ".ltprc\n").encode('utf-8'))
		tn.read_until("@".encode('utf-8'))

	tn.read_until("@".encode('utf-8'))
	
	tn.write(str("ionadmin nx" + str(node['number']) + ".ionrc\n").encode('utf-8'))
	tn.read_until("Stopping ionadmin.".encode('utf-8'))	
	tn.write(str("printf \"" + contactfile_contents + "\" | ionadmin\n").encode('utf-8'))
	tn.read_until("Stopping ionadmin.".encode('utf-8'))	
	tn.write(str("bpadmin nx" + str(node['number']) + ".bprc\n").encode('utf-8'))
	tn.read_until("Stopping bpadmin.".encode('utf-8'))
	tn.write(str("ltpadmin nx" + str(node['number']) + ".ltprc\n").encode('utf-8'))
	tn.read_until("Stopping ltpadmin.".encode('utf-8'))
	tn.close()

# TODO: implement running modes.


if debug:
	print("project name: ")
	print(project.name)
	print("project id: ")
	print(project.project_id)
	print("node summary:")
	print(nodes)
	print("link summary:")
	print(links)

	print("\nina - node, adapter, and ip summary table:")
	print(ina)
