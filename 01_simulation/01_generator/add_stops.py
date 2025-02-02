import argparse
import re

import numpy as np
import pandas as pd

import xml.etree.ElementTree as ET
from xml.dom import minidom

import sumolib

def prettify(elem):
    """Return a pretty-printed XML string for the Element.
    """
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def read_trips_df(file_path, random_regex):
    def not_filter_regex(text):
        '''Returns *True* if the regex cannot be matched to the text,
         else otherwise.'''
        
        if re.findall(random_regex, file_path):
            return False
        else:
            return True
        
    trips = pd.read_xml(file_path, xpath="trip")
    trips = trips[trips["id"].apply(not_filter_regex)]
    trips["veh_id"] = trips["id"].transform(lambda x: x.split(":")[0])
    trips["move_id"] = trips["id"].transform(lambda x: int(x.split(":")[1]))
    return trips

def get_inverse_edge(edge_id):
    edge = net.getEdge(edge_id)
    from_e = edge.getFromNode().getID()
    to_e = edge.getToNode().getID()
    return edge_dict[(to_e, from_e)]

if __name__ == "__main__":
    net = sumolib.net.readNet("../02_scenario/grid.net.xml")
    
    edge_dict = {}
    for e in net.getEdges():
        from_e = e.getFromNode().getID()
        to_e = e.getToNode().getID()
        edge_dict[(from_e, to_e)] = e.getID()
        
    trips_tree = ET.parse("../02_scenario/trips.trips.xml")

    for trip_e in trips_tree.findall("trip"):
        new_destination = get_inverse_edge(trip_e.get("from"))
        park_at = trip_e.get("to")
        new_stop = ET.SubElement(trip_e, "stop")
        new_stop.set("parkingArea", f"pa{park_at}")
        new_stop.set("duration", str(int(np.random.uniform(15*60, 45*60))))
        
    with open("../02_scenario/trips_with_stops.trips.xml", "wb") as f:
        trips_tree.write(f)
