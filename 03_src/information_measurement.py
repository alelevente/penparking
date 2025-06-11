import traci

import numpy as np
import pandas as pd

import argparse
import sys
import os
import json

SIM_ROOT = "../01_simulation/02_scenario/"
SIMULATION = "../01_simulation/02_scenario/sim.sumocfg"
SUMO_CMD = ["sumo", "-c", SIMULATION, "--no-step-log", "--tripinfo-output", "vehicle_trips.xml"]
TIME_STEP = 15
PARKING_DEFS = "../01_simulation/02_scenario/parking_areas.add.xml"
STARTING_PRICE_DEF = "../02_data/starting_prices.json"

def create_parking_mtx(veh_destinations, parking_distance_map, parking_edges):
    answer_mtx = {}
    for veh in veh_destinations:
        new_row = {}
        for p_edge in parking_edges:
            new_row[p_edge] = parking_distance_map[veh_destinations[veh]][p_edge]
        answer_mtx[veh] = new_row
    return answer_mtx

def calc_free_parkings(free_parkings, reservations):
    for res in reservations:
        free_parkings[res] = max(0, free_parkings[res] - reservations[res])
    return free_parkings


def calculate_route_distance(vehicle):
    route = traci.vehicle.getRoute(vehicle)
    dep_pos = traci.vehicle.getLanePosition(vehicle)
    arr_pos = traci.lane.getLength(f"{route[-1]}_0")
    distance = 0
    if len(route)>1:
        distance = traci.vehicle.getDrivingDistance(vehicle, route[1], 0)
    for i in range(1, len(route)-1):
        distance += traci.simulation.getDistanceRoad(route[i], 0,
                                                     route[i+1], 0,
                                                     isDriving=True)
    distance += arr_pos
    return distance

def compute_best_parkings(destinations, num_free_spaces, parking_distance_map):
    results = []
    for veh in destinations:        
        distance_series = pd.Series(parking_distance_map[destinations[veh]])
        distance_series = distance_series.sort_values()
        i = 0
        while (num_free_spaces[f"pa{distance_series.keys()[i]}"] == 0) and (i < len(distance_series)):
            i += 1
        results.append({"veh_id": veh,
                        "new_parking_edge": distance_series.keys()[i]})
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("seed", help="seed", type=str)
    parser.add_argument("--name", help="name of the simulation", type=str)
    
    args = parser.parse_args()
    seed = args.seed
    
    parking_df = pd.read_xml(PARKING_DEFS, xpath="parkingArea")
    parking_df["id"] = parking_df["id"].astype(str)
    parking_df = parking_df.set_index("id")
    with open(STARTING_PRICE_DEF) as f:
        starting_prices = json.load(f)
    
    sumo_cmd = SUMO_CMD + ["--seed", seed, "--output-prefix", args.name]
    traci.start(sumo_cmd)
    
    #initialization:
    parking_distance_map = {}
    parking_edges = []

    for i,r in parking_df.iterrows():
        parking_edges.append(r.lane.split("_")[0])

    for p_i in parking_edges:
        parking_distance_map[p_i] = {}
        for p_j in parking_edges:
            parking_distance_map[p_i][p_j] = traci.simulation.getDistanceRoad(p_i, 0, p_j, 0, True)
        
        
    controlled_vehicles = set()
    to_auction = set()
    active_vehicles = set()
    vehicle_data = {}

    auction_outcomes = {}
    free_parkings = {}

    reservations = {}
    for pid in parking_df.index:
        reservations[pid] = 0

    p_ids, p_times, p_occups = [],[],[]
    
    #Main simulation loop:
    time = 0
    while traci.simulation.getMinExpectedNumber()>0:
        time = traci.simulation.getTime()

        #with lower frequency:
        if time%TIME_STEP == 0:  
            #parking occupancies:
            for parking_area in parking_df.index:
                occup = traci.parkingarea.getVehicleCount(parking_area)
                p_ids.append(parking_area)
                p_times.append(time)
                p_occups.append(occup/parking_df["roadsideCapacity"][parking_area])
                free_parkings[parking_area] = parking_df["roadsideCapacity"][parking_area] - occup

            #parking guidance:
            dests = {}
            for veh in to_auction:
                dests[veh] = vehicle_data[veh]["original_position"]
            free_parkings = calc_free_parkings(free_parkings, reservations)
            guidance_result = compute_best_parkings(dests, free_parkings, parking_distance_map)
            
            for ar in guidance_result:
                controlled_vehicles.add(ar["veh_id"])
                new_dest = ar["new_parking_edge"]
                vehicle_data[ar["veh_id"]]["controlled"] = True
                #flag 65: parking @ a parking area
                try:
                    next_stop = traci.vehicle.getStops(ar["veh_id"])[0]
                    traci.vehicle.replaceStop(ar["veh_id"], 0, f"pa{new_dest}", flags=65, duration=next_stop.duration)
                except:
                    controlled_vehicles.remove(ar["veh_id"])
            to_auction = set()

        #departing vehicles:
        departed_vehicles = traci.simulation.getDepartedIDList()
        for dpv in departed_vehicles:
            vehicle_data[dpv] = {
                "original_position": traci.vehicle.getNextStops(dpv)[0][0].split("_")[0],
                "original_distance": calculate_route_distance(dpv),
                "controlled": False
            }
            to_auction.add(dpv)
            active_vehicles.add(dpv)

        #stopping vehicles:
        stopping_vehicles = traci.simulation.getStopStartingVehiclesIDList()
        for spv in stopping_vehicles:
            stop_stat = traci.vehicle.getNextStops(spv)[0]
            parking_edge = stop_stat[0].split("_")[0]
            parking_driving_distance = traci.simulation.getDistanceRoad(
                                                    vehicle_data[spv]["original_position"], 0,
                                                    parking_edge, 0, True)
            vehicle_data[spv]["parking_distance"] = parking_driving_distance
            vehicle_data[spv]["original_price"] = starting_prices[vehicle_data[spv]["original_position"]]
            vehicle_data[spv]["parking_price"] = starting_prices[parking_edge]

        active_vehicles = active_vehicles - set(stopping_vehicles)     

        traci.simulation.step()
                
    traci.close()            
    
    occupancy_results = pd.DataFrame()
    occupancy_results["parking_id"] = p_ids
    occupancy_results["time"] = p_times
    occupancy_results["occupancy"] = p_occups
    
    try:
        if not os.path.exists(f"../02_data/{args.name}"):
            os.mkdir(f"../02_data/{args.name}")
        os.replace(f"{SIM_ROOT}/{args.name}detector_data.out.xml",
                   f"../02_data/{args.name}/detector_data.out.xml")
        os.replace(f"./{args.name}vehicle_trips.xml",
                   f"../02_data/{args.name}/vehicle_trips.xml")
        
        with open(f"../02_data/{args.name}/veh_results.json", "w") as f:
            json.dump(vehicle_data, f)
            
        occupancy_results.to_csv(f"../02_data/{args.name}/occupancy.csv", index=False)
    except Exception as e:
        print(e)