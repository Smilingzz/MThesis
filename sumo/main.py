import os
import sys
import optparse

if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("declare SUMO HOME")

from sumolib import checkBinary
import sumolib
import traci

def get_options():
    opt_parser = optparse.OptionParser()
    opt_parser.add_option("--nogui", action="store_true",
                        default=False, help="run the commandline version of sumo")
    options, args = opt_parser.parse_args()
    return options

def generateRoutes():
    net = sumolib.net.readNet('map.net.xml')
    allEdges = net.getEdges() #Returns a list of xml data containing all edges.

def run():
    step = 0
    generateRoutes()
    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep()
        step += 1

        #traci.vehicle.moveToXY("carflow1.2, ")
        if step == 100:
            print(traci.vehicle.getIDList())

    traci.close()
    sys.stdout.flush()


if __name__ == "__main__":
    options = get_options()

    if options.nogui:
        sumoBinary = checkBinary('sumo')
    else:
        sumoBinary = checkBinary('sumo-gui')

    traci.start([sumoBinary, "-c", "sumo.sumocfg", "--tripinfo-output", "tripinfo.xml"])
    run()