import numpy as np

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.cm as cmx
import numpy as np
import pandas as pd

import json

import sys,os

SUMO_HOME = os.environ["SUMO_HOME"] #locating the simulator
sys.path.append(SUMO_HOME+"/tools")
import sumolib
from sumolib.visualization import helpers


class Option:
    #default options required by sumolib.visualization
    defaultWidth = 3
    defaultColor = (0.0, 0.0, 0.0, 0.0)
    linestyle = "solid"
    
def plot_network_probs(net_file, probabilities, cmap="YlGn",
                       title="", special_edges=None,
                       special_color=(1.0, 0.0, 0.0, 1.0),
                       fig=None, ax=None, figsize=(10,12),
                       bar_orientation="horizontal", bar_location="bottom",
                       background_color="lightgray",
                       p_min=-0.1, p_max=1.1):

    '''
        Plots a road network with edges colored according to a probabilistic distribution.
        Parameters:
            net_file: a sumo road network file path
            probabilities: a dictionary that maps edge indices to probabilities
                If an edge is not in this map, it will get a default (light gray) color.
            index_to_edge_map: a dictionary that maps edge indices to SUMO edge IDs
            cmap: the colormap to be used on the plot
            title: title of the produced plot
            special_edges: edges to be plotted with special color, given in a similar structure
                as probabilities parameter
            special_color: color of the special edges (RGBA)
            fig: if None then a new map is created; if it is given, then only special edges are overplot to the original fig
            ax: see fig

        Returns:
            a figure and axis object
    '''

    net = sumolib.net.readNet(net_file)
        
    scalar_map = None
    colors = {}
    options = Option()
    
    if fig is None:
        fig, ax = plt.subplots(figsize=figsize)
                
    c_norm = matplotlib.colors.Normalize(vmin=p_min, vmax=p_max)
    scalar_map = cmx.ScalarMappable(norm=c_norm, cmap=cmap)
    for edge in probabilities:
        colors[edge] = scalar_map.to_rgba(min(1,max(0,probabilities[edge])))
                    
    if not(special_edges is None):
        for edge in special_edges:
            colors[edge] = special_color
    
    helpers.plotNet(net, colors, [], options)
    plt.title(title)
    plt.xlabel("position [m]")
    plt.ylabel("position [m]")
    ax.set_facecolor(background_color)
    if not(scalar_map is None):
        plt.colorbar(scalar_map,
                     location = bar_location,
                     orientation = bar_orientation,
                     aspect = 50,
                     pad = .1)

    return fig, ax
