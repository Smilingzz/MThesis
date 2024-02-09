import os
import sys
import optparse
import xml.etree.ElementTree as ET
from sumolib import checkBinary
import sumolib
import traci
import copy
from datetime import datetime

# ":2108758057_0"
# "-24634517#16"
# "201963533#5"
# "233675413#7"
# "27920078#1"
START_EDGE = "23184143#2"


# "22690206#1"
# "124812857#0"
# "-25145013#0"
END_EDGE = "26339189"

amount = 1000
PERIMITER_OFFSET = 100
COR_NAME = "CourierVehicle"
COR_TYPE = "Courier"
STEP_COUNT = 0
SIM = True
TRAVEL_DISTANCE = 0.0
TRAVEL_TIME = 0
EDGES_VISITED = 0
CURRENT_EDGE = ""
current_datetime = datetime.now()
current_date_time = current_datetime.strftime("%m_%d_%Y_%H_%M_%S")




if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("declare SUMO HOME")

def get_options():
    opt_parser = optparse.OptionParser()
    opt_parser.add_option("--nogui", action="store_true",
                        default=False, help="run the commandline version of sumo")
    options, args = opt_parser.parse_args()
    return options

def startCourier():
    global START_EDGE, END_EDGE, COR_NAME, COR_TYPE
    traci.route.add("trip", [START_EDGE, END_EDGE])
    traci.vehicle.add(COR_NAME, "trip", typeID=COR_TYPE)
    
# Improve with this: https://sumo.dlr.de/docs/Tools/Sumolib.html
def initializeDictionaries(graph):
    edge_weights = {}
    visited_edges = {}
    tentative_distance = {}
    for edge in graph:
        edge_weights[edge] = 0
        visited_edges[edge] = False
        tentative_distance[edge] = float('inf')
    return edge_weights, visited_edges, tentative_distance
        
def initializeVehicles():
    vehicle_dict = {}
    tree = ET.parse('MCS\\users.xml')
    root = tree.getroot()

    for users in root.findall('users'):
        for ID in users.findall('items'):
            vehicle_dict[ID] = True
    return vehicle_dict

def getEdgeAverageSpeed(Edge, vehicle_dict):
    laneAmount = traci.edge.getLaneNumber(Edge)
    averageSpeed = 0
    for lane in range(laneAmount):
        laneID = Edge + "_" + str(lane)
        vehicleIDs = traci.lane.getLastStepVehicleIDs(laneID)
        amountInLane = len(vehicleIDs)
        maxSpeed = traci.lane.getMaxSpeed(laneID)
        if amountInLane == 0:
            averageSpeed += maxSpeed
        else:
            laneSpeed = 0
            none_found = True
            for ID in vehicleIDs:
                if ID in vehicle_dict.keys():
                    none_found = False
                    laneSpeed += traci.vehicle.getSpeed(ID)
            if none_found:
                averageSpeed += maxSpeed
            else:
                averageSpeed += (laneSpeed / amountInLane )
    return ( averageSpeed / laneAmount )
    
def updateEdgeWeights(graph, edge_lengths, edge_weights, vehicle_dict):
    for edge in graph:
        edge_weights[edge] = ( (edge_lengths[edge] ) / getEdgeAverageSpeed(edge, vehicle_dict) )
    return edge_weights

def expandPerimiter(xy_start, xy_end):
    global PERIMITER_OFFSET
    x_start = xy_start[0]
    y_start = xy_start[1]

    x_end = xy_end[0]
    y_end = xy_end[1]

    box = None
    if x_start > x_end:
        x_start += PERIMITER_OFFSET
        if x_end < PERIMITER_OFFSET:
            x_end = 0
        else:
            x_end -= PERIMITER_OFFSET
        if y_start > y_end:
            y_start += PERIMITER_OFFSET
            if y_end < PERIMITER_OFFSET:
                y_end = 0
            else:
                y_end -= PERIMITER_OFFSET
            box = ((x_end, y_end),(x_start, y_start))
        else:
            y_end += PERIMITER_OFFSET
            if y_start < PERIMITER_OFFSET:
                y_start = 0
            else:
                y_start -= PERIMITER_OFFSET
            box = ((x_end, y_start),(x_start, y_end))
    else:
        x_end += PERIMITER_OFFSET
        if x_start < PERIMITER_OFFSET:
            x_start = 0
        else:
            x_start -= PERIMITER_OFFSET
        if y_start > y_end:
            y_start += PERIMITER_OFFSET
            if y_end < PERIMITER_OFFSET:
                y_end = 0
            else:
                y_end -= PERIMITER_OFFSET
            box = ((x_start, y_end),(x_end, y_start))
        else:
            y_end += PERIMITER_OFFSET
            if y_start < PERIMITER_OFFSET:
                y_start = 0
            else:
                y_start -= PERIMITER_OFFSET
            box = ((x_start, y_start),(x_end, y_end))
    return box

def inPerimiter(box, xy):
    if xy[0] > box[0][0] and box[1][0] > xy[0] and xy[1] > box[0][1] and box[1][1] > xy[1]:
        return True
    return False
    
def createCompleteGraph():
    global START_EDGE, END_EDGE
    graph = {}
    edge_lengths = {}
    
    tree = ET.parse('ingolstadt.net.xml')
    root = tree.getroot()

    xy_start = (0.0,0.0)
    xy_end = (0.0,0.0)
    for junction in root.findall('junction'):
        incLanes = junction.get('incLanes')
        if START_EDGE in incLanes:
            xy_start = (float(junction.get('x')), float(junction.get('y')))
        if END_EDGE in incLanes:
            xy_end = (float(junction.get('x')), float(junction.get('y')))

    box = expandPerimiter(xy_start, xy_end)


    for connection in root.findall('connection'):
        fromID = connection.get('from')
        for junction in root.findall('junction'):
            if fromID in junction.get('incLanes') or fromID in junction.get('intLanes'):
                if inPerimiter(box, (float(junction.get('x')), float(junction.get('y'))) ):
                    if fromID[0:1] != ":":
                        for anotherJunction in root.findall('junction'):
                            if junction.get('id') != anotherJunction.get('id'):
                                otherID = ""
                                if fromID[0:1] == "-":
                                    otherID == fromID[1:]
                                else:
                                    otherID = "-" + fromID
                                if otherID in anotherJunction.get('incLanes') or otherID in anotherJunction.get('intLanes'):
                                    if inPerimiter(box, (float(anotherJunction.get('x')), float(anotherJunction.get('y'))) ):
                                        graph[fromID] = []
                    else:
                        graph[fromID] = []
    for connection in root.findall('connection'):
        fromID = connection.get('from')
        toID = connection.get('to')
        viaInternal = connection.get('via')
        if fromID in graph.keys() and toID in graph.keys():
            if viaInternal == None:
                graph[fromID].append(toID)
            else:
                graph[fromID].append(viaInternal[0:-2])
                edge_lengths[viaInternal[0:-2]] = traci.lane.getLength(viaInternal)
        edge_lengths[fromID] = traci.lane.getLength(fromID + "_0")
        edge_lengths[toID] = traci.lane.getLength(toID + "_0")
        
    total_nodes = len(graph)
    print("\n\n\n\n", total_nodes)
    return graph, edge_lengths, total_nodes
            
        
         

# Inspiration from: https://bogotobogo.com/python/python_Dijkstras_Shortest_Path_Algorithm.php
def djikstrasAlgorithm(graph, visited_edges, tentative_distance, edge_weights, total_nodes):
    
    visited = copy.deepcopy(visited_edges)

    getPrevious = {}
    currentPos = getVehicleEdge()
    tentative_copy = copy.deepcopy(tentative_distance)
    tentative_copy[currentPos] = 0
    for i in range(total_nodes):
        current_min = None
        current_node = None
        for node in tentative_copy:
            if current_min == None:
                current_min = tentative_copy[node]
                current_node = node
            else:
                if tentative_copy[node] < current_min and visited[node] == False:
                    current_min = tentative_copy[node]
                    current_node = node
        visited[current_node] = True

        for neighbour in graph[current_node]:
            new_distance = tentative_copy[current_node] + edge_weights[neighbour]
            if new_distance < tentative_copy[neighbour]:
                tentative_copy[neighbour] = new_distance
                getPrevious[neighbour] = current_node
    route = []
    curr = END_EDGE
    route = [END_EDGE] + route
    while curr != currentPos:
        route = [getPrevious[curr]] + route
        curr = getPrevious[curr]

    for entry in route:
        if entry[0:1] == ":":
            route.remove(entry)
    return route

def getVehicleEdge():
    return traci.vehicle.getRoadID(COR_NAME)
        
def updateRoute(graph, edge_lengths, total_nodes, edge_weights, visited_edges, tentative_distance, vehicle_dict):
    edge_weights = updateEdgeWeights(graph, edge_lengths, edge_weights, vehicle_dict)
    updatedRouting = djikstrasAlgorithm(graph, visited_edges, tentative_distance, edge_weights, total_nodes)
    print("Current edge: ", getVehicleEdge())
    print("\nMCS Route:")
    print(updatedRouting)
    traci.vehicle.setRoute(COR_NAME, updatedRouting)
    
def checkEndCondition(edge_lengths):
    global CURRENT_EDGE, TRAVEL_DISTANCE, EDGES_VISITED, TRAVEL_TIME
    newEdge = traci.vehicle.getRoadID(COR_NAME)
    if newEdge != CURRENT_EDGE:
        EDGES_VISITED += 1
        TRAVEL_DISTANCE += edge_lengths[newEdge]
        CURRENT_EDGE = newEdge
    if traci.vehicle.getRoadID(COR_NAME) == END_EDGE:
        return True
    return False

def getResults(step_count):
    global TRAVEL_TIME, TRAVEL_DISTANCE, EDGES_VISITED, START_EDGE, END_EDGE, current_date_time
        
    print("\n\n")
    print("Car traveled from ", START_EDGE, " to ", END_EDGE)
    print("Total time: ", step_count)
    print("Total distance: ", TRAVEL_DISTANCE)
    print("Total edges: ", EDGES_VISITED) 

    ## Inspiration from user unutbu: https://stackoverflow.com/questions/2869564/xml-filtering-with-python 
    tree = ET.parse('Results\output.xml')
    root = tree.getroot()

    for timestep in root.findall('timestep'):
        for person in timestep.findall('person'):
            timestep.remove(person)
        for vehicle in timestep.findall('vehicle'):
            id = vehicle.get('id')
            if id != COR_NAME:
                timestep.remove(vehicle)

    tree.write('Results\output_filtered_' + current_date_time + '.xml')

def initializeRun():
    graph, edge_lengths, total_nodes = createCompleteGraph()
    edge_weights, visited_edges, tentative_distance = initializeDictionaries(graph)
    vehicle_dict = initializeVehicles()
    startCourier()
    return graph, edge_lengths, total_nodes, edge_weights, visited_edges, tentative_distance, vehicle_dict

def setPreconditions(amount):
    for i in range(amount):
        traci.simulationStep()

def run(graph, edge_lengths, total_nodes, edge_weights, visited_edges, tentative_distance, vehicle_dict, step_count):

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        step_count += 1
        
        updateRoute(graph, edge_lengths, total_nodes, edge_weights, visited_edges, tentative_distance, vehicle_dict)
        if checkEndCondition(edge_lengths):
            break

    traci.close()
    sys.stdout.flush()
    return step_count

if __name__ == "__main__":
    options = get_options()

    if SIM:
        sumoBinary = "sumo"
    else:
        sumoBinary = "sumo-gui"

    traci.start([sumoBinary, "-c", "InTAS_buildings.sumocfg", "--fcd-output", "Results\output_" + current_date_time + ".xml", "--fcd-output.geo"])
    setPreconditions(amount)
    graph, edge_lengths, total_nodes, edge_weights, visited_edges, tentative_distance, vehicle_dict = initializeRun()
    step_count = 0
    step_count = run(graph, edge_lengths, total_nodes, edge_weights, visited_edges, tentative_distance, vehicle_dict, step_count)
    getResults(step_count)