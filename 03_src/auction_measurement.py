import traci

import numpy as np
import pandas as pd

import argparse
import sys
import os
import json
import re

sys.path.append("auctions")
import helper
import auction

SIM_ROOT = "../01_simulation/02_scenario/"
SIMULATION = "../01_simulation/02_scenario/sim.sumocfg"
SUMO_CMD = ["sumo", "-c", SIMULATION, "--no-step-log"]
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

def make_auctions(free_parkings: dict, veh_destinations: dict, parking_distance_map: dict,
                  starting_prices: dict, parking_edges: list, beta_values, beta_probabilities):
    
    p_mtx = create_parking_mtx(veh_destinations, parking_distance_map, parking_edges)        
    betas_ = np.random.choice(beta_values, size=len(veh_destinations), p=beta_probabilities)
    beta_per_vehicle = {}
    for i, bi in enumerate(veh_destinations):
        beta_per_vehicle[bi] = betas_[i]
        
    fp_ = {}
    for pa in free_parkings:
        fp_[pa.split("pa")[-1]] = free_parkings[pa]
        
    auctions, buyers = auction.init_auction_method(fp_, veh_destinations, starting_prices,
                                                   p_mtx, betas=beta_per_vehicle)
    if len(buyers)>0:
        print(f"{len(auctions)} auctions started with {len(buyers)} buyers")
    auction_results = auction.run_auctions(auctions, buyers, r_max=100)
    return auction_results

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("seed", help="seed", type=str)
    parser.add_argument("--penetration", help="penetration level", type=int, default=10)
    parser.add_argument("--name", help="name of the simulation", type=str)
    parser.add_argument("--mix_config", help="path to mix configuration", type=str)
    
    args = parser.parse_args()
    seed = args.seed
    
    parking_df = pd.read_xml(PARKING_DEFS, xpath="parkingArea").set_index("id")
    with open(STARTING_PRICE_DEF) as f:
        starting_prices = json.load(f)
        
    if not os.path.exists(f"../02_data/{args.name}"):
        os.makedirs(f"../02_data/{args.name}")
        
    sim_name = args.name.split("/")[-1]
    sumo_cmd = SUMO_CMD + ["--seed", seed, "--output-prefix",
                           f"{sim_name}",
                           "--tripinfo-output", f"vehicle_trips.xml"]
    mix_config = None
    if args.mix_config is not None:
        with open(args.mix_config) as f:
            mix_config = json.load(f)
            
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

            #auctions:
            dests = {}
            for veh in to_auction:
                dests[veh] = vehicle_data[veh]["original_position"]
            free_parkings = calc_free_parkings(free_parkings, reservations)
            
            if len(dests)>0:
                auction_result = make_auctions(free_parkings, dests, parking_distance_map,
                                               starting_prices.copy(), parking_edges,
                                               mix_config["values"],
                                               mix_config["probabilities"])
                
                for ar in auction_result:
                    veh = auction_result[ar]["winner"]
                    if veh!="":
                        print(ar, auction_result[ar])
                        controlled_vehicles.add(veh)
                        #print(controlled_vehicles)
                        new_dest = re.sub("_[0-9]*$", "", ar)
                        auction_outcomes[veh] = {
                            "parking_edge": new_dest,
                            "auction_id": ar,
                            "price": auction_result[ar]["price"],
                            "vehicle": veh,
                            "distance": traci.simulation.getDistanceRoad(
                                                            dests[veh], 0,
                                                            new_dest.split("pa")[-1], 0, True),
                            "time": time
                        }
                        vehicle_data[veh]["controlled"] = True
                        #flag 65: parking @ a parking area
                        try:
                            next_stop = traci.vehicle.getStops(veh, 1)[0]
                            traci.vehicle.replaceStop(veh, 0, f"pa{new_dest}", flags=65, duration=next_stop.duration)
                            reservations[f"pa{new_dest}"] += 1
                        except Exception as e:
                            print(e)
                            if auction_result[ar]["winner"] != "":
                                controlled_vehicles.remove(auction_result[ar]["winner"])
            to_auction = set()

        #departing vehicles:
        departed_vehicles = traci.simulation.getDepartedIDList()
        for dpv in departed_vehicles:
            next_stop = traci.vehicle.getStops(dpv)
            if len(next_stop)>0: #not through vehicle
                pos = next_stop[0].stoppingPlaceID.split("pa")[-1]
                vehicle_data[dpv] = {
                    "original_position": pos,
                    "controlled": False,
                    "occupied_reserved": False
                }
            r_int = np.random.randint(0, 10)
            if r_int<args.penetration:
                to_auction.add(dpv)
            active_vehicles.add(dpv)
            
        #parkEndingVehicles:
        park_ends = traci.simulation.getParkingEndingVehiclesIDList()

        #stopping vehicles:
        stopping_vehicles = traci.simulation.getStopStartingVehiclesIDList()
        #if len(stopping_vehicles)>0:
        #    print("stopping", stopping_vehicles)
        #if len(controlled_vehicles)>0:
        #    print("controlled", controlled_vehicles)
        for spv in stopping_vehicles:
            stop_stat = traci.vehicle.getNextStops(spv)[0]
            parking_edge = stop_stat[0].split("_")[0]
            parking_driving_distance = traci.simulation.getDistanceRoad(
                                                    vehicle_data[spv]["original_position"], 0,
                                                    parking_edge, 0, True)
            vehicle_data[spv]["parking_distance"] = parking_driving_distance
            vehicle_data[spv]["original_price"] = starting_prices[vehicle_data[spv]["original_position"]]
            vehicle_data[spv]["parking_price"] = starting_prices[parking_edge] 
            vehicle_data[spv]["paid_price"] = starting_prices[parking_edge] #for uncontrolled or occupied
            if spv in controlled_vehicles:
                reserved_edge = auction_outcomes[spv]["parking_edge"]
                reservations[f"pa{reserved_edge}"] -= 1
                vehicle_data[spv]["auction_price"] = auction_outcomes[spv]["price"]
                #print(reserved_edge, parking_edge)
                if reserved_edge == parking_edge:
                    vehicle_data[spv]["paid_price"] = auction_outcomes[spv]["price"] #if controlled and successfully reserved
                    vehicle_data[spv]["occupied_reserved"] = True
        active_vehicles = active_vehicles - set(stopping_vehicles)     

        traci.simulation.step()
                
    traci.close()            
    
    occupancy_results = pd.DataFrame()
    occupancy_results["parking_id"] = p_ids
    occupancy_results["time"] = p_times
    occupancy_results["occupancy"] = p_occups
    
    try:
        
        os.replace(f"{SIM_ROOT}/{sim_name}detector_data.out.xml",
                   f"../02_data/{args.name}/detector_data.out.xml")
        os.replace(f"./{sim_name}vehicle_trips.xml",
                   f"../02_data/{args.name}/vehicle_trips.xml")
        
        with open(f"../02_data/{args.name}/veh_results.json", "w") as f:
            json.dump(vehicle_data, f)
        with open(f"../02_data/{args.name}/auction_results.json", "w") as f:
            json.dump(auction_outcomes, f)
            
        occupancy_results.to_csv(f"../02_data/{args.name}/occupancy.csv", index=False)
    except Exception as e:
        print(e)