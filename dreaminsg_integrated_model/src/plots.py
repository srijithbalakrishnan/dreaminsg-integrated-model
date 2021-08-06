"""Functions to generate infrastructure network plots and result plots."""

import networkx as nx
import pandas as pd
import matplotlib.pyplot as plt

import pandapower.plotting as pandaplot

from bokeh.io import show, output_notebook
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.transform import factor_cmap
import numpy as np


# -----------------------------------------------------------#
#                      NETWORK PLOTS                        #
# -----------------------------------------------------------#


def plot_transpo_net(transpo_folder):
    """Generates the transportation network plot.

    :param transpo_folder: Location of the .tntp files.
    :type transpo_folder: string
    """
    links = pd.DataFrame(
        columns=[
            "Init node",
            "Term node",
            "Capacity",
            "Length",
            "Free Flow Time",
            "B",
            "Power",
            "Speed limit",
            "Toll",
            "Type",
        ]
    )
    with open("{}/example_net.tntp".format(transpo_folder), "r") as f:
        for line in f:
            if "~" in line:
                for line in f:
                    link_data = line.split("\t")[1:11]
                    links = links.append(
                        {
                            "Init node": link_data[0],
                            "Term node": link_data[1],
                            "Capacity": link_data[2],
                            "Length": link_data[3],
                            "Free Flow Time": link_data[4],
                            "B": link_data[5],
                            "Power": link_data[6],
                            "Speed limit": link_data[7],
                            "Toll": link_data[8],
                            "Type": link_data[9],
                        },
                        ignore_index=True,
                    )

    nodes = pd.read_csv("{}/example_node.tntp".format(transpo_folder), sep="\t")

    G = nx.Graph()
    edge_list = list(
        map(list, zip(links["Init node"].values, links["Term node"].values))
    )
    G.add_edges_from(edge_list)
    pos = {str(i + 1): (row[1], row[2]) for i, row in nodes.iterrows()}

    options = {
        "node_size": 500,
        "node_color": "lightsteelblue",
        "font_size": 14,
        "edge_color": "slategray",
        "width": 2,
    }
    plt.figure(1, figsize=(10, 7))
    nx.draw(G, pos, with_labels=True, **options)


def plot_power_net(net):
    """Generates the power systems plot.

    :param net: The power systems network.
    :type net: pandapower network object
    """
    options = {
        "bus_size": 1.5,
        "plot_loads": True,
        "library": "networkx",
        "bus_color": "lightsteelblue",
        "show_plot": True,
        "scale_size": True,
    }
    plt.figure(1, figsize=(10, 7))
    pandaplot.simple_plot(net, **options)


def plot_water_net(wn):
    """Generates the water network plot.

    :param wn: The water network.
    :type wn: wntr network object
    """
    # wn = wntr.network.WaterNetworkModel(water_net)

    coord_list = list(wn.query_node_attribute("coordinates"))
    node_coords = [list(ele) for ele in coord_list]
    node_list = wn.node_name_list
    G = wn.get_graph()
    pos = {node_list[i]: element for i, element in enumerate(node_coords)}

    options = {
        "node_size": 500,
        "node_color": "lightsteelblue",
        "font_size": 14,
        "edge_color": "slategray",
        "width": 2,
    }
    plt.figure(1, figsize=(10, 7))
    nx.draw(G, pos, with_labels=True, **options)
    # nodes, edges = wntr.graphics.plot_network(water_net, node_cmap='lightsteelblue', **options)


def plot_bokeh_from_integrated_graph(G, title, extent=[(1000, 8000), (1000, 6600)]):
    output_notebook()
    p = figure(
        background_fill_color="white",
        plot_width=700,
        height=400,
        title=title,
        x_range=extent[0],
        y_range=extent[1],
    )

    # nodes
    x, y, node_type, node_category, id = [], [], [], [], []

    for _, node in enumerate(G.nodes.keys()):
        x.append(G.nodes[node]["coord"][0])
        y.append(G.nodes[node]["coord"][1])
        node_type.append(G.nodes[node]["node_type"])
        node_category.append(G.nodes[node]["node_category"])
        id.append(node)

    plot_nodes = p.square(
        "x",
        "y",
        source=ColumnDataSource(
            dict(x=x, y=y, node_type=node_type, node_category=node_category, id=id)
        ),
        color="gainsboro",
        alpha=0.6,
        muted_color="gainsboro",
        muted_alpha=0.2,
        size=5,
    )

    # links
    x, y, link_layer, link_category, id = [], [], [], [], []
    for index, link in enumerate(G.edges.keys()):
        x.append([G.nodes[link[0]]["coord"][0], G.nodes[link[1]]["coord"][0]])
        y.append([G.nodes[link[0]]["coord"][1], G.nodes[link[1]]["coord"][1]])
        link_layer.append(G.edges[link]["link_type"])
        link_category.append(G.edges[link]["link_category"])
        id.append(link)

    plot_links = p.multi_line(
        "x",
        "y",
        source=ColumnDataSource(
            dict(x=x, y=y, link_layer=link_layer, link_category=link_category, id=id)
        ),
        line_color=factor_cmap(
            "link_layer", "Category10_3", np.unique(np.array(link_layer))
        ),
        line_alpha=1,
        line_width=1.5,
        muted_color=factor_cmap(
            "link_layer", "Category10_3", np.unique(np.array(link_layer))
        ),
        muted_alpha=0.2,
        legend_field="link_layer",
    )

    # hover tools
    node_hover = HoverTool(renderers=[plot_nodes])
    node_hover.tooltips = [
        ("Node ID", "@id"),
        ("Infrastructure", "@node_type"),
        ("Node category", "@node_category"),
    ]
    p.add_tools(node_hover)

    link_hover = HoverTool(renderers=[plot_links])
    link_hover.tooltips = [
        ("Link ID", "@id"),
        ("Infrastructure", "@link_layer"),
        ("Link category", "@link_category"),
    ]
    p.add_tools(link_hover)

    p.legend.location = "top_left"
    p.legend.click_policy = "mute"
    show(p)


#############################################################
#                      RESULT PLOTS                        #
#############################################################


def plot_repair_curves(disrupt_recovery_object, scatter=False):
    """Generates the direct impact and repair level plots for the failed components.

    :param disrupt_recovery_object: The disrupt_generator.DisruptionAndRecovery object.
    :type disrupt_recovery_object: DisasterAndRecovery object
    :param scatter: scatter plot, defaults to False
    :type scatter: bool, optional
    """
    plt.figure(figsize=(10, 7))
    sns.set_style("white")
    sns.set_context("talk")
    sns.set_palette(sns.color_palette("Set1"))

    for name in disrupt_recovery_object.network.get_disrupted_components():
        time_tracker = (
            disrupt_recovery_object.event_table[
                disrupt_recovery_object.event_table.components == name
            ].time_stamp
            / 60
        )
        # print(time_tracker)
        damage_tracker = disrupt_recovery_object.event_table[
            disrupt_recovery_object.event_table.components == name
        ].perf_level
        # print(damage_tracker)

        sns.lineplot(
            x=time_tracker,
            y=damage_tracker,
            label=name,
            drawstyle="steps-post",
        )
        if scatter == True:
            sns.scatterplot(
                x=time_tracker,
                y=damage_tracker,
                alpha=0.5,
            )
    plt.xlabel("Time (minutes)")
    plt.xlim(0, 1.01 * (disrupt_recovery_object.event_table.time_stamp.max() / 60))
    plt.ylabel("Damage level (%)")
    plt.ylim(0, 102)
    plt.title("Disrupted components and their restoration")
    plt.legend(loc="best")
    plt.show()


def plot_interdependent_effects(
    power_consump_tracker, water_consump_tracker, time_tracker, scatter=True
):
    """Generates the network-level performance plots.

    :param power_consump_tracker: A list of power consumption resilience metric values.
    :type power_consump_tracker: list of floats
    :param water_consump_tracker: A list of water consumption resilience metric values.
    :type water_consump_tracker: list of floats
    :param time_tracker: A list of time-stamps from the similation.
    :type time_tracker: list of floats
    :param scatter: scatter plot, defaults to True
    :type scatter: bool, optional
    """
    sns.set_style("white")
    sns.set_context("talk")
    sns.set_palette(sns.color_palette("Set1"))

    plt.figure(figsize=(10, 7))
    plt.title("Network-wide effects and recovery")
    sns.lineplot(
        x=time_tracker,
        y=water_consump_tracker,
        label="Water",
    )
    sns.lineplot(
        x=time_tracker,
        y=power_consump_tracker,
        label="Power",
    )
    if scatter == True:
        sns.scatterplot(
            x=time_tracker,
            y=water_consump_tracker,
            alpha=0.5,
        )
        sns.scatterplot(
            x=time_tracker,
            y=power_consump_tracker,
            alpha=0.5,
        )
    plt.xlabel("Time (minutes)")
    plt.ylabel("Consumption ratio")
    plt.xlim(0, 1.01 * max(time_tracker))
    plt.ylim(-0.01, 1.05)
    plt.legend(loc="best")
    plt.show()
