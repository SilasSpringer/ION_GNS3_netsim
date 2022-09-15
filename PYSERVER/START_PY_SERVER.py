import os
import sys
import time
import json
import time
import gns3fy
import telnetlib
import subprocess
from tabulate import tabulate

from make_contacts import *

FILENAME="START_PY_SERVER.py"
CONFFILE="pyscript.conf"
debug = False

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

def getconf(filename):
	with open(filename, "r") as conffile: #"pyscript.conf"
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
	return (netaddr, serverptcl, serverhost, serverport, linkprotocol, contconfpath, ionport, contactfile, universallinkdelay, universallinkbitrate, tc_bandwidth_limiting)

def get_clargs():
	# BEGIN COMMANDLINE INPUT
	numargs = len(sys.argv)

	sh  = None
	spo = None
	spt = None
	pn  = None # set default projectname
	cf  = None
	rm  = None # set default running mode


	tmp = iter(sys.argv[1:])
	paired = zip(tmp,tmp)
	for pair in paired:
		# match-case is exclusive to python3.10+ 
		# should probably use something else to allow use of older python versions.
		match pair[0]:
			case "-s":
				sh = pair[1]
			case "-port":
				spo = pair[1]
			case "-ptcl":
				spt = pair[1]
			case "-proj":
				pn = pair[1]
			case "-c":
				cf = pair[1]
			case "-m":
				rm = pair[1]
			case _:
				print_help()
				sys.exit(str("invalid option: " + str(pair[0])))
	# END COMMANDLINE INPUT
	return (sh, spo, spt, pn, cf, rm)

def getserver(serverptcl, serverhost, serverport):
	if debug:
		print("server is: " + serverptcl + "://" + serverhost + ":" + serverport)
	server	= gns3fy.Gns3Connector(serverptcl + "://" + serverhost + ":" + serverport)
	return server


def getproject(server, projectname):
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
	return project


def make_ina_accessors(project, server, netaddr):
	# iterate through each node and link, and make an ip for each node and interface
	# limited at 24 nodes, 10 adapters using current method.
	# nodes go from 1 to 24, adapters from 0 to 9. (with a final address range of <netaddr>.1 to <netaddr>.249 )

	# ina - ip, nodename, adapter - contains a list of all nodes, 
	# where each node is represented by a pair that has the node name, 
	# and an array containing pairs matching each interface to an ip address.
	ina = []

	node_accessors = []

	#TODO redo the mechanism using used node numbers to find any number 
	# remaining in the allowable node number range. currently relies on 
	# having a larger number than the given number available in the range 0-255.
	# which is a bad assumption to make
	used_node_numbers = []

	for i, node in enumerate(project.nodes):
		nmbr = i+1
		node_accessors.append(gns3fy.Node(project_id=project.project_id, name=node.name, connector=server))
		# temporary solution for adding the IPN numbers to the names of each node as they start. 
		# TODO: update this to read the ipn number from the title if it exists, so the user can specify ipn numbers.
		if 'ipn:' not in node.name:
			while nmbr in used_node_numbers:
				nmbr += 1
			node_accessors[i].update(name=str(node.name + "-ipn:" + str(nmbr)))
		else:
			nmbr = int(node.name[node.name.find('ipn:')+len('ipn:'):])
		
		ips = [] # temporary storage array for the ip-adapter pairs 
		for index, adapter in enumerate(node.ports): # for every adapter in the ports section,
			if nmbr > 255 or index > 255:
				sys.exit("ERROR: cannot have more than 254 nodes or 255 adapters or nodes with ipn numbers outside the range 0-255, as the ip generation method is limited in possibilities. Please reduce network to meet requirements.")
			# TODO: add ability to exclude specific ip addresses from usable range, to allow connection to outside machines with the same first 2 octets.
			# first 2 octets of used ip addresses are user specified
			# calculate a unique IP address for that adapter.	
			ips.append((adapter['name'], str(netaddr + str(index) + "." + str(nmbr))))
		used_node_numbers.append(nmbr)
		ina.append({
			'name' : node.name, 
			'number' : nmbr, 
			'interfaces' : ips, 
			'neighbors' : [],
			'index' : i
			})
	return (ina, node_accessors)

def fill_connections(links, ina):
	# TODO: clean this up to be more efficient, maybe use a hashmap to store the nodes for faster lookup?
	for link in links:
		connected=[0,0] # store node numbers of connected nodes in this link
		indices=[0,0] # store indices of connected nodes in this link
		conn_ips=["127.0.0.1", "127.0.0.1"] # store ip addresses at each end of this link. 
		conn_ifs=["null", "null"] # store name of the interface used on each side of the link.
		#TODO add security checks to make sure that all nodes have correct ips, rather than 
		# hoping it all works as intended. currently could recieve a loopback ip (127.0.0.1) if the correct ip isnt found.
		
		# link is name-iface-name-iface (indexes 0,2 are node names, indexes 1,3 are interfaces on their respective nodes.)
		for ix, node in enumerate(ina): # for each node
			if node['name'] == link[0]: # if we find the node that is the first node in this link,
				connected[0] = node['number'] # record its number
				indices[0] = node['index']
				conn_ifs[0] = link[1] # record interface used
				for adapter in node['interfaces']: # for each interface on the node,
					if adapter[0] == link[1]:  # if it is the adapter used for this link, 
						conn_ips[0] = adapter[1] # record the ip address
						break
				
			if node['name'] == link[2]: # if we find the node that is the second node in this link,
				connected[1] = node['number'] # record its number
				indices[1] = node['index']
				conn_ifs[1] = link[3] # record interface used
				for adapter in node['interfaces']: # for each interface on the node,
					if adapter[0] == link[3]: # if it is the adapter used for this link, 
						conn_ips[1] = adapter[1] # record the ip address
						break
		ina[indices[0]]['neighbors'].append((connected[1], conn_ips[1], conn_ifs[1])) # set the ip address and number of the connected node as a neighbor for the other node
		ina[indices[1]]['neighbors'].append((connected[0], conn_ips[0], conn_ifs[0])) # set the ip address and number of the connected node as a neighbor for the other node
	return ina
	
def get_contactfile_contents(contactfile, ina, universallinkbitrate, universallinkdelay):	
	if contactfile == None:
		contactfile = "contacts.ionrc"
		contactfile_contents = makecontactfile(ina, contactfile, universallinkbitrate, universallinkdelay)
	else:
		try:
			f = open(contactfile, 'r')
			contactfile_contents = f.read() 
			if (debug):
				print(str("contactfile: " + contactfile + " contained: \n" + contactfile_contents + "\n"))
			f.close()
		except:
			pass
		try:
			match contactfile.split(" ")[0]:
				case "default":
					if (debug):
						print("making default permanent uptime contact file.")
					contactfile_contents = makecontactfile(ina, contactfile, universallinkbitrate, universallinkdelay)
				case "oscillatory": # TODO: update this to read in config for the length of oscillations and the total number of oscillations.
					if (debug):
						print("making oscillatory contact file. osc rate and cycle count config NYI.")
					contactfile_contents = makeoscillatorycontactfile(ina, contactfile, 10, 10, universallinkbitrate, universallinkdelay)
		except:
			print("could not open or read given contacts file. using default permanent uptime contact plan.")
			contactfile = "contacts.ionrc"
			contactfile_contents = makecontactfile(ina, contactfile, universallinkbitrate, universallinkdelay)
	return contactfile_contents

#TELNET_HOST="127.0.0.1"
# TELNET_HOST = serverhost
def start_and_configure(ina, node_accessors, TELNET_HOST, universallinkbitrate, tc_bandwidth_limiting, linkprotocol, contconfpath, contactfile_contents, ionport):
	# starts and configures nodes.
	for j, node in enumerate(ina):
		node_accessors[j].start() # start node
		
		# wait until node has started.
		while node_accessors[j].status == 'stopped':
			pass

		node_env = str(node_accessors[j].properties['environment'])

		# run all the commands needed to configure a node.	
		tn = telnetlib.Telnet(TELNET_HOST, str(node_accessors[j].console))
		tn.open(TELNET_HOST, str(node_accessors[j].console))
		for iface in node['interfaces']:
			tmp = node_env.find('BANDWIDTH_CAP_' + iface[0])
			if tmp == -1: # if the bandwidth cap wasnt set for this interface,
				# TODO: pull rate from contact file - may be tricky since this is dependent on contact time. 
				# should be done/updated in a daemon or server running on the host that can monitor and update 
				# all nodes as needed to have one common clock controlling the delays.
				
				# temp soln, use default rate from configuration. this is also used in creating a default contact file if one is not provided.
				rate = str(universallinkbitrate + "bit")
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

		#TODO: place this into the conf_script file to make a nx#.ltprc file regardless of whether we use ltp or not, for safety and futureproofing.
		#if (linkprotocol == 'ltp'):	# update the ltprc file to be named correctly if using ltp.
		tn.write(str("touch nx" + str(node['number']) + ".ltprc\n").encode('utf-8'))
		tn.read_until("@".encode('utf-8'))
		tn.write(str("cp nx.ltprc nx" + str(node['number']) + ".ltprc\n").encode('utf-8'))
		tn.read_until("@".encode('utf-8'))

		for neighbor in node['neighbors']:		
			if (linkprotocol == 'ltp'): # if using ltp, destination is the neighbor node's number
				dest = str(neighbor[0])
			else: # otherwise, the destination is the neighbor node's IP address.
				dest = str(neighbor[1] + ":" + ionport)

			# write outducts and plans to for each neighbor.
			tn.write(str("sed -i \"/^\#OUTDUCT_TRIGGER_LINE/a" + "a outduct " + linkprotocol + " " + dest + " " + linkprotocol + "clo\" nx" + str(node['number']) + ".bprc\n").encode('utf-8'))
			tn.read_until("@".encode('utf-8'))
			tn.write(str("sed -i \"/^\#PLAN_TRIGGER_LINE/a" + "a plan " + str(neighbor[0]) + " " + linkprotocol + "/" + dest + "\" nx" + str(node['number']) + ".ipnrc\n").encode('utf-8'))
			tn.read_until("@".encode('utf-8'))
			# output a span if using ltp.
			if (linkprotocol == 'ltp'):
				tn.write(str("sed -i \"/^\#SPAN_TRIGGER_LINE/a" + "a span " + str(neighbor[0]) + " 100 100 64000 100000 1 \'udplso " + neighbor[1] + ":1113 40000000\' \" nx" + str(node['number']) + ".ltprc\n").encode('utf-8'))
				tn.read_until("@".encode('utf-8'))

		tn.read_until("@".encode('utf-8'))
		
		# start all the configuration files on the node.
		tn.write(str("ionadmin nx" + str(node['number']) + ".ionrc\n").encode('utf-8'))
		tn.read_until("Stopping ionadmin.".encode('utf-8'))	
		
		tn.write(str("printf \"" + contactfile_contents + "\" | ionadmin\n").encode('utf-8'))
		tn.read_until("Stopping ionadmin.".encode('utf-8'))
		# tn.read_until("@".encode('utf-8'))		
		tn.write(str("bpadmin nx" + str(node['number']) + ".bprc\n").encode('utf-8'))
		tn.read_until("Stopping bpadmin.".encode('utf-8'))	
		# tn.read_until("@".encode('utf-8'))	
		tn.write(str("ltpadmin nx" + str(node['number']) + ".ltprc\n").encode('utf-8'))
		tn.read_until("Stopping ltpadmin.".encode('utf-8'))
		# tn.read_until("@".encode('utf-8'))	
	
	# close telnet terminal connection. terminal remains open for the user, however.
	tn.close()

def set_abs_ref_time(ina, node_accessors, TELNET_HOST="127.0.0.1", offset=20):
	t = int(time.time()) + offset
	t = convtoionabstimeformat(t)

	if (debug):
		print("setting absolute time or reference to ")
		print(t)

	for j, node in enumerate(ina):
		tn = telnetlib.Telnet(TELNET_HOST, str(node_accessors[j].console))
		tn.open(TELNET_HOST, str(node_accessors[j].console))
		
		tn.write(str("ionadmin\n").encode('utf-8'))
		tn.read_until(":".encode('utf-8'))
		tn.write(str("@ " + t + "\n").encode('utf-8'))	
		tn.read_until(":".encode('utf-8'))
		tn.write(str("q\n").encode('utf-8'))	
		tn.read_until("Stopping ionadmin.".encode('utf-8'))
		tn.close()


# TODO: implement running modes.




def main():
	(netaddr, serverptcl, serverhost, serverport, linkprotocol, contconfpath, ionport, contactfile, universallinkdelay, universallinkbitrate, tc_bandwidth_limiting) = getconf(CONFFILE)
	(sh, spo, spt, pn, cf, rm) = get_clargs()
	if sh is not None:
		serverhost = sh
	if spo is not None:
		serverport = spo
	if spt is not None:
		serverptcl = spt
	if cf is not None:
		contactfile = cf
	projectname = pn
	runningmode = rm

	# get open connection to server. TODO: correctly catch, retry, and warn user if server cannot be contacted.
	server = getserver(serverptcl, serverhost, serverport)	
	# get project. if no name specified, grabs first currently open project.
	project = getproject(server, projectname)
	# get a node and link summaries
	nodes 	= project.nodes_summary(is_print=False)
	links	= project.links_summary(is_print=False)

	# build ina and node_accessors arrays for future use
	(ina, node_accessors) = make_ina_accessors(project, server, netaddr)

	# update ina with neighbors and link info, and add ip addresses assigned to each side of each link.
	ina = fill_connections(links, ina)

	# get the contents of the contact file, either generatively or from given file.
	contactfile_contents = get_contactfile_contents(contactfile, ina, universallinkbitrate, universallinkdelay)

	# start all nodes in network, and configure them for use
	start_and_configure(ina, node_accessors, serverhost, universallinkbitrate, tc_bandwidth_limiting, linkprotocol, contconfpath, contactfile_contents, ionport)

	# set the absolute time as reference for relative timestamps to >now< + offset seconds
	set_abs_ref_time(ina, node_accessors, serverhost, 20)

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

if __name__ == "__main__":
    main()