import time


# ina has the structure of a list of dictionaries
# each tuple has the name of the node, the 
# number of the node, a list containing each 
# adapter and ip adress of that adapter, and a 
# lost of all neighbors' numbers and ip addresses
def makecontactfile(ina, filename, universallinkbitrate=1024, universallinkdelay=1):
    universallinkbitrate = 1024 if universallinkbitrate is None else universallinkbitrate
    universallinkdelay = 1 if universallinkdelay is None else universallinkdelay
    result = "# begin contact plan\n"
    for node in ina:
        result += str("a range 	    +0 +40000000 " + str(node['number']) + " " + str(node['number']) + " 0\n")
        result += str("a contact 	+0 +40000000 " + str(node['number']) + " " + str(node['number']) + " 40000000\n")

        for neighbor in node['neighbors']:
            result += str("a range 	    +0 +40000000 " + str(node['number']) + " " + str(neighbor[0]) + " " + str(universallinkdelay) + "\n")
            result += str("a contact    +0 +40000000 " + str(node['number']) + " " + str(neighbor[0]) + " " + str(universallinkbitrate) + "\n")
            # following 2 lines are commented, handled as outgoing from other side of link.
            #f.write("a range 	+0 +40000000 " + str(neighbor[0]) + " " + str(node[1]) + " 0")
            #f.write("a contact 	+0 +40000000 " + str(neighbor[0]) + " " + str(node[1]) + " 40000000")

    return result
def makeoscillatorycontactfile(ina, filename, osc_interval=10, cycle_count=10, universallinkbitrate=1024, universallinkdelay=1):
    universallinkbitrate = 1024 if universallinkbitrate is None else universallinkbitrate
    universallinkdelay = 1 if universallinkdelay is None else universallinkdelay
    result = "# begin contact plan\n"
    for node in ina:
        # loopback
        result += str("a range 	    +0 +40000000 " + str(node['number']) + " " + str(node['number']) + " 0\n")
        result += str("a contact 	+0 +40000000 " + str(node['number']) + " " + str(node['number']) + " 40000000\n")

        # cyclical communication with neighbors.
        i = 0
        while i < cycle_count*2:
            for neighbor in node['neighbors']:
                result += str("a range 	    +" + str(osc_interval*i) + " +" + str(osc_interval*(i+1)) + " " + str(node['number']) + " " + str(neighbor[0]) + " " + str(universallinkdelay) + "\n")
                result += str("a contact    +" + str(osc_interval*i) + " +" + str(osc_interval*(i+1) + osc_interval) + " " + str(node['number']) + " " + str(neighbor[0]) + " " + str(universallinkbitrate) + "\n")
            i += 2
    return result

def convtoionabstimeformat(t):
	t = time.ctime(t)
	t = time.strptime(str(t))
	return str(time.strftime("%Y/%m/%d-%H:%M:%S", t))
	