import networkx as nx
import pandas as pd

import wntr
import pandapower as pp
import pandapower.plotting as pandaplot

import matplotlib.pyplot as plt
import re


#############################################################
#                      NETWORK PLOTS                        #
#############################################################


def plot_transpo_net(transpo_folder):
    """Generates the transportation network plot.

    Arguments:
        transpo_folder {string} -- Location of the .tntp files.
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


def plot_power_net(power_net):
    """Generates the power systems plot.

    Arguments:
        power_net {string} -- The location of the power network .json file.
    """
    net = pp.from_json(power_net)
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


def plot_water_net(water_net):
    """Generates the water network plot.

    Arguments:
        water_net {string} -- The location of the water network .inp file.
    """
    wn = wntr.network.WaterNetworkModel(water_net)

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


def plot_integrated_network(pn, wn, tn, plotting=False):
    """Create a Networkx graph of the integrated network and plot it.

    Arguments:
        pn {pandapower model object} -- [description]
        wn {wntr model object} -- [description]
        tn {STA model object} -- [description]
    """
    G = nx.Graph()
    node_size = 200

    # transportation network edges
    transpo_node_list = list(tn.node.keys())
    transpo_link_list = []
    for link in tn.link.keys():
        txt = re.sub(r"[^,,A-Za-z0-9]+", "", link).split(",")
        transpo_link_list.append((int(txt[0]), int(txt[1])))
    transpo_node_coords = dict()
    for index, node in enumerate(list(tn.node.keys())):
        transpo_node_coords[node] = list(zip(tn.node_coords.X, tn.node_coords.Y))[index]

    node_type = {node: "transpo_node" for i, node in enumerate(transpo_node_list)}

    G.add_nodes_from(transpo_node_list)
    nx.set_node_attributes(G, transpo_node_coords, "coord")
    nx.set_node_attributes(G, node_type, "type")

    if plotting == True:
        plt.figure(1, figsize=(10, 7))
    nx.draw_networkx_edges(
        G,
        transpo_node_coords,
        edgelist=transpo_link_list,
        edge_color="green",
        width=5,
        alpha=0.25,
    )

    # power network edges
    power_bus_list = pn.bus.name
    power_bus_coords = dict()
    for index, bus in enumerate(power_bus_list):
        power_bus_coords[bus] = list(zip(pn.bus_geodata.x, pn.bus_geodata.y))[index]
    node_type = {bus: "power_node" for i, bus in enumerate(power_bus_list)}

    b2b_edge_list = [
        [pn.bus.name.values[row.from_bus], pn.bus.name.values[row.to_bus]]
        for index, row in pn.line.iterrows()
    ]
    transfo_edge_list = [
        [pn.bus.name.values[row.hv_bus], pn.bus.name.values[row.lv_bus]]
        for index, row in pn.trafo.iterrows()
    ]
    switch_edge_list = [
        [pn.bus.name.values[row.bus], pn.bus.name.values[row.element]]
        for index, row in pn.switch[pn.switch.et == "b"].iterrows()
    ]

    G.add_nodes_from(power_bus_list)
    nx.set_node_attributes(G, power_bus_coords, "coord")
    nx.set_node_attributes(G, node_type, "type")

    nx.draw_networkx_edges(
        G,
        power_bus_coords,
        edgelist=b2b_edge_list,
        edge_color="red",
        width=3,
        alpha=0.5,
        style="dotted",
    )
    nx.draw_networkx_edges(
        G,
        power_bus_coords,
        edgelist=transfo_edge_list,
        edge_color="red",
        width=3,
        alpha=0.5,
        style="dotted",
    )
    nx.draw_networkx_edges(
        G,
        power_bus_coords,
        edgelist=switch_edge_list,
        edge_color="red",
        width=3,
        alpha=0.5,
        style="dotted",
    )

    # water network edges
    water_junc_list = wn.node_name_list
    water_pipe_name_list = wn.pipe_name_list
    water_junc_coords = dict()
    for index, junc in enumerate(water_junc_list):
        water_junc_coords[junc] = list(wn.get_node(junc).coordinates)

    water_pipe_list = []
    for index, pipe in enumerate(wn.pipe_name_list):
        start_node = wn.get_link(wn.pipe_name_list[index]).start_node_name
        end_node = wn.get_link(wn.pipe_name_list[index]).end_node_name
        water_pipe_list.append((start_node, end_node))

    node_type = {node: "water_node" for i, node in enumerate(water_junc_list)}

    G.add_nodes_from(water_junc_list)
    nx.set_node_attributes(G, water_junc_coords, "coord")
    nx.set_node_attributes(G, node_type, "type")

    nx.draw_networkx_edges(
        G,
        water_junc_coords,
        edgelist=water_pipe_list,
        edge_color="blue",
        width=1,
        alpha=0.5,
        style="solid",
    )

    # plot all nodes
    nx.draw_networkx_nodes(
        G,
        transpo_node_coords,
        nodelist=transpo_node_list,
        node_color="green",
        alpha=0.25,
        node_size=node_size,
        label="transportation network",
    )
    nx.draw_networkx_labels(
        G,
        transpo_node_coords,
        {node: node for node in transpo_node_list},
        font_size=10,
        font_color="black",
    )

    nx.draw_networkx_nodes(
        G,
        power_bus_coords,
        nodelist=power_bus_list,
        node_color="red",
        alpha=0.25,
        node_size=node_size,
        label="power system",
    )
    nx.draw_networkx_labels(
        G,
        power_bus_coords,
        {node: node for node in power_bus_list},
        font_size=10,
        font_color="black",
    )

    nx.draw_networkx_nodes(
        G,
        water_junc_coords,
        nodelist=water_junc_list,
        node_color="blue",
        alpha=0.25,
        node_size=node_size,
        label="water network",
    )
    nx.draw_networkx_labels(
        G,
        water_junc_coords,
        {node: node for node in water_junc_list},
        font_size=10,
        font_color="black",
    )
    plt.title("Interdependent Water-Power-Transportation Network")
    plt.legend(scatterpoints=1, loc="upper right", framealpha=0.5)

    return G


#############################################################
#                      RESULT PLOTS                        #
#############################################################


def plot_repair_curves(disrupt_recovery_object, scatter=False):
    """Generates the direct impact and repair level plots for the failed components

    Arguments:
        disrupt_recovery_object {object} -- The disrupt_generator.DisruptionAndRecovery object
    """
    plt.figure(figsize=(10, 7))
    # fig,ax = plt.subplots()

    for name in disrupt_recovery_object.disrupted_components:
        plt.step(
            disrupt_recovery_object.event_table[
                disrupt_recovery_object.event_table.components == name
            ].time_stamp
            / 60,
            disrupt_recovery_object.event_table[
                disrupt_recovery_object.event_table.components == name
            ].perf_level,
            where="post",
            label=name,
            linewidth=3,
        )
        if scatter == True:
            plt.scatter(
                disrupt_recovery_object.event_table[
                    disrupt_recovery_object.event_table.components == name
                ].time_stamp
                / 60,
                disrupt_recovery_object.event_table[
                    disrupt_recovery_object.event_table.components == name
                ].perf_level,
            )
    plt.xlabel("Time (minutes")
    plt.xlim(0, disrupt_recovery_object.event_table.time_stamp.max() / 60)
    plt.ylabel("Damage level (%)")
    plt.legend(loc="best")
    plt.show()


def plot_interdependent_effects(
    power_consump_tracker, water_consump_tracker, time_tracker
):
    """Generates the network-level performance plots.

    Arguments:
        power_consump_tracker {list of floats} -- A list of power consumption resilience metric values
        water_consump_tracker {list of floats} -- A list of water consumption resilience metric values
        time_tracker {list of floats} -- A list of time-stamps from the similation
    """
    infra_list = ["Power", "Water"]
    color_list = ["tab:blue", "tab:orange"]
    tracker_list = [power_consump_tracker, water_consump_tracker]

    plt.figure(figsize=(10, 7))
    plt.suptitle("Network-wide effects and recovery")
    for index, column in enumerate([1, 2]):
        plt.subplot(1, 1, 1)  # row 1, column 2, count 1
        if infra_list[index] == "Power":
            plt.step(
                time_tracker,
                tracker_list[index],
                color_list[index],
                alpha=0.7,
                where="post",
                label=infra_list[index],
                linewidth=3,
            )
        else:
            plt.plot(
                time_tracker,
                tracker_list[index],
                color_list[index],
                alpha=0.7,
                label=infra_list[index],
                linewidth=3,
            )
        # plt.scatter(time_tracker, tracker_list[index])
        plt.xlabel("Time (minutes)")
        plt.ylabel("Consumption ratio")
        plt.xlim(0, max(time_tracker))
        plt.ylim(0, 1.05)
        plt.legend(loc="lower right")
    plt.show()
