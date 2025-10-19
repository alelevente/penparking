import numpy as np
import argparse
import json
import xml.etree.ElementTree as ET
import xml.dom.minidom

ZONE_1_PRICE = 1.00 #Euro
ZONE_2_PRICE = 0.50 #Euro

N_VEHICLES = 100000 #for sampling


def get_distance_from_center(edge):
    cc, cd = ord('C'), ord('D')
    
    def get_distance_horizontal(edge):
        row = int(edge[1])
        c1, c2 = ord(edge[0]), ord(edge[2])
        row_dist = max(2-row, row-3)
        col_dist = max(cc-c1, c1-cd,
                       cc-c2, c2-cd)
        return row_dist + col_dist
    def get_distance_vertical(edge):
        c = ord(edge[0])
        r1, r2 = int(edge[1]), int(edge[3])
        col_dist = max(cc-c, c-cd)
        row_dist = max(2-r1, r1-3,
                       2-r2, r2-3)
        return row_dist + col_dist
    
    if edge[1] == edge[3]:
        return get_distance_horizontal(edge)
    if edge[0] == edge[2]:
        return get_distance_vertical(edge)
    

def get_distance(edge1, edge2):
    cols = [ord(edge1[0]), ord(edge1[2]),
            ord(edge2[0]), ord(edge2[2])]
    rows = [int(edge1[1]), int(edge1[3]),
            int(edge2[1]), int(edge2[3])]
    col_dist = max(abs(cols[0]-cols[2]),
                   abs(cols[0]-cols[3]),
                   abs(cols[1]-cols[2]),
                   abs(cols[1]-cols[3]))
    row_dist = max(abs(rows[0]-rows[2]),
                   abs(rows[0]-rows[3]),
                   abs(rows[1]-rows[2]),
                   abs(rows[1]-rows[3]))
    return col_dist + row_dist - 1


def get_cost(destination, distances, prices, beta):
    d_max = max(distances.values())
    p_max = max(prices.values())
    
    costs = {}
    for e in all_edges:
        d = distances[destination, e]
        p = prices[e]
        costs[e] = beta*p/p_max + (1-beta)*d/d_max
    
    return costs

def get_new_dest(destination, beta, distances, prices):
    def list_mins(costs):
        min_v, min_idx = 2, []
        for c in costs:
            if costs[c] < min_v:
                min_v = costs[c]
                min_idx = [c]
            elif costs[c] == min_v:
                min_idx.append(c)
        return min_idx
    
    costs = get_cost(destination, distances, prices, beta)
    return np.random.choice(list_mins(costs))


def create_dst_xml(dest_probabilities):
    answer = ET.Element("edgedata")
    interval = ET.SubElement(answer, "interval")
    interval.set("begin", "0")
    interval.set("end", "14400")
    
    for edge in dest_probabilities:
        new_edge_elem = ET.SubElement(interval, "edge")
        new_edge_elem.set("id", edge)
        new_edge_elem.set("value", f"{dest_probabilities[edge]}")
        
    return answer


if __name__ == "__main__":
    #argparser:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=str)
    parser.add_argument("--betaconfig", type=str)
    args = parser.parse_args()
    
    #setup:
    rows = [0, 1, 2, 3, 4, 5]
    columns = ['A', 'B', 'C', 'D', 'E', 'F']
    all_edges = []

    for row in rows:
        for col in range(len(columns)-1):
            all_edges.append(f"{columns[col]}{row}{columns[col+1]}{row}")
            all_edges.append(f"{columns[col+1]}{row}{columns[col]}{row}")

    for column in columns:
        for row in range(len(rows)-1):
            all_edges.append(f"{column}{row}{column}{row+1}")
            all_edges.append(f"{column}{row+1}{column}{row}")

    zone1 = ["C2C1", "C1C2", "D2D1", "D1D2",
                    "B2C2", "C2B2", "C2D2", "D2C2", "D2E2", "E2D2",
                    "C2C3", "C3C2", "D2D3", "D3D2",
                    "B3C3", "C3B3", "C3D3", "D3C3", "D3E3", "E3D3",
                    "C3C4", "C4C3", "D3D4", "D4D3"]
    zone2 = list(set(all_edges).difference(set(zone1)))
    
    prob_dist = []
    for e in all_edges:
        prob_dist.append(get_distance_from_center(e))

    prob_dist = np.array(prob_dist)
    prob_dist = (np.max(prob_dist)+1 - prob_dist)
    prob_dist = prob_dist/np.sum(prob_dist)
    
    if args.betaconfig is not None:
        distances = {}
        for e1 in all_edges:
            for e2 in all_edges:
                distances[(e1,e2)] = get_distance(e1,e2)
                
        prices = {}
        for p in all_edges:
            prices[p] = ZONE_1_PRICE if p in zone1 else ZONE_2_PRICE
            
        with open(args.betaconfig) as f:
            beta_conf = json.load(f)
        
        betas = np.random.choice(beta_conf["values"],
                                 N_VEHICLES,
                                 p=beta_conf["probabilities"])
        destinations = np.random.choice(all_edges, size=N_VEHICLES, p=prob_dist)
        park_dest = []
        for i in range(len(destinations)):
            park_dest.append(get_new_dest(destinations[i],
                                          betas[i],
                                          distances, prices))
        
        probabilities = {}
        for p in park_dest:
            if not (p in probabilities):
                probabilities[p] = 0
            probabilities[p] += 1
        for p in probabilities:
            probabilities[p] /= N_VEHICLES
    
    else:
        probabilities = {}
        for i in range(len(all_edges)):
            probabilities[all_edges[i]] = prob_dist[i]
        
    output_xml = ET.tostring(
        create_dst_xml(probabilities)
    )
    #pretty printing:
    temp = xml.dom.minidom.parseString(output_xml)
    pretty_xml = temp.toprettyxml()
    with open(args.output, "w") as f:
        f.write(pretty_xml)
        