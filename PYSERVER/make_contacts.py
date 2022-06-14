# ina has the structure of a list of dictionaries
# each tuple has the name of the node, the 
# number of the node, a list containing each 
# adapter and ip adress of that adapter, and a 
# lost of all neighbors' numbers and ip addresses

# def makecontactfile(ina, filename, universallinkbitrate=1024, universallinkdelay=1):
#     universallinkbitrate = 1024 if universallinkbitrate is None else universallinkbitrate
#     universallinkdelay = 1 if universallinkdelay is None else universallinkdelay
#     with open(filename, "w") as f:
#         f.write("# begin contact plan")
#         f.close()
#     with open(filename, "a") as f:
#         for node in ina:
#             f.write("a range 	+0 +40000000 " + str(node[1]) + " " + str(node[1]) + " 0")
#             f.write("a contact 	+0 +40000000 " + str(node[1]) + " " + str(node[1]) + " 40000000")

#             for neighbor in node['neighbors']:
#                 f.write("a range 	+0 +40000000 " + str(node[1]) + " " + str(neighbor[0]) + " " + str(universallinkdelay))
#                 f.write("a contact 	+0 +40000000 " + str(node[1]) + " " + str(neighbor[0]) + " " + str(universallinkbitrate))
#                 # following 2 lines are commented, handled as outgoing from other side of link.
#                 #f.write("a range 	+0 +40000000 " + str(neighbor[0]) + " " + str(node[1]) + " 0")
#                 #f.write("a contact 	+0 +40000000 " + str(neighbor[0]) + " " + str(node[1]) + " 40000000")
#         f.close()
    
def makecontactfile(ina, filename, universallinkbitrate=1024, universallinkdelay=1):
    universallinkbitrate = 1024 if universallinkbitrate is None else universallinkbitrate
    universallinkdelay = 1 if universallinkdelay is None else universallinkdelay
    result = "# begin contact plan\n"
    for node in ina:
        result += str("a range 	    +0 +40000000 " + str(node[1]) + " " + str(node[1]) + " 0\n")
        result += str("a contact 	+0 +40000000 " + str(node[1]) + " " + str(node[1]) + " 40000000\n")

        for neighbor in node['neighbors']:
            result += str("a range 	    +0 +40000000 " + str(node[1]) + " " + str(neighbor[0]) + " " + str(universallinkdelay) + "\n")
            result += str("a contact    +0 +40000000 " + str(node[1]) + " " + str(neighbor[0]) + " " + str(universallinkbitrate) + "\n")
            # following 2 lines are commented, handled as outgoing from other side of link.
            #f.write("a range 	+0 +40000000 " + str(neighbor[0]) + " " + str(node[1]) + " 0")
            #f.write("a contact 	+0 +40000000 " + str(neighbor[0]) + " " + str(node[1]) + " 40000000")

    return result