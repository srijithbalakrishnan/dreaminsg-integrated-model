from abc import ABC, abstractmethod

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import wntr

import dreaminsg_integrated_model.src.network_sim_models.interdependencies as interdependencies
import dreaminsg_integrated_model.src.network_sim_models.water.water_network_model as water
import dreaminsg_integrated_model.src.network_sim_models.power.power_system_model as power
import dreaminsg_integrated_model.src.network_sim_models.transportation.network as transpo


class Network(ABC):
    """This is an abstract class of integrated infrastructure network, defining an interface to other code. This interface needs to be implemented accordingly."""

    @abstractmethod
    def load_networks(self):
        pass

    @abstractmethod
    def generate_integrated_graph(self, plotting=False):
        pass

    @abstractmethod
    def generate_dependency_table(self, dependency_file):
        pass

    @abstractmethod
    def set_disrupted_components(self, dependency_file):
        pass

    @abstractmethod
    def get_disrupted_components(self, dependency_file):
        pass


class IntegratedNetwork(Network):
    """An integrated infrastructure network class"""

    def __init__(
        self, power_sim_type="1ph", water_file=None, power_file=None, transp_folder=None
    ):
        """Initiates the IntegratedNetwork object.

        :param water_file: The water network file in inp format
        :type water_file: string
        :param power_file: The power systems file in json format
        :type power_file: string
        :param transp_folder: The local directory that consists of required transportation network files
        :type transp_folder: string
        """
        if water_file == None:
            self.wn = None
        else:
            self.load_water_network(water_file)

        if power_file == None:
            self.pn = None
        else:
            self.load_power_network(power_file, power_sim_type)

        if transp_folder == None:
            self.tn = None
        else:
            self.load_transpo_network(transp_folder)

    def load_networks(self, water_file, power_file, transp_folder, power_sim_type):
        """Loads the water, power and transportation networks.

        :param water_file: The water network file in inp format
        :type water_file: string
        :param power_file: The power systems file in json format
        :type power_file: string
        :param transp_folder: The local directory that consists of required transportation network files
        :type transp_folder: string
        :param power_sim_type: Type of power flow simulation: '1ph': single phase, '3ph': three phase.
        :type power_sim_type: string
        """
        # load water_network model
        self.load_water_network(water_file)

        # load power systems network
        self.load_power_network(power_file, power_sim_type)

        # load static traffic assignment network
        self.load_transpo_network(transp_folder)

    def load_power_network(self, power_file, power_sim_type):
        """Loads the power network.

        :param power_file: The power systems file in json format
        :type power_file: string
        """
        try:
            pn = power.load_power_network(power_file, sim_type=power_sim_type)
            power.run_power_simulation(pn)
            self.pn = pn
        except UserWarning:
            print(
                "Error: The power systems file does not exist. No such file or directory: ",
                power_file,
            )

    def load_water_network(self, water_file):
        """Loads the water network.

        :param water_file: The water network file in inp format
        :type water_file: string
        """
        try:
            initial_sim_step = 60
            wn = water.load_water_network(water_file, initial_sim_step)
            self.wn = wn
        except FileNotFoundError:
            print(
                "Error: The water network file does not exist. No such file or directory: ",
                water_file,
            )

    def load_transpo_network(self, transp_folder):
        """Loads the transportation network.

        :param transp_folder: The local directory that consists of required transportation network files
        :type transp_folder: string
        """
        try:
            tn = transpo.Network(
                f"{transp_folder}/transpo_net.tntp",
                f"{transp_folder}/transpo_trips.tntp",
                f"{transp_folder}/transpo_node.tntp",
            )
            print(
                f"Transportation network successfully loaded from {transp_folder}. Static traffic assignment method will be used to calculate travel times."
            )
            # tn.userEquilibrium("FW", 400, 1e-4, tn.averageExcessCost)
            self.tn = tn
        except FileNotFoundError:
            print(
                f"Error: The transportation network folder does not exist. No such directory: {transp_folder}."
            )
        except AttributeError:
            print("Error: Some required network files not found.")

    def generate_integrated_graph(
        self,
        plotting=False,
        legend_size=12,
        font_size=8,
        figsize=(10, 7),
        line_width=2,
    ):
        """Generates the integrated Networkx object.

        :param plotting: Generates plots, defaults to False., defaults to False
        :type plotting: bool, optional
        :param legend_size: Legend font size, defaults to 12
        :type legend_size: int, optional
        :param font_size: Text font size, defaults to 8
        :type font_size: int, optional
        :param figsize: Size of final figure, defaults to (10, 7)
        :type figsize: tuple, optional
        :param line_width: Width of lines, defaults to 2
        :type line_width: int, optional
        """
        G = nx.Graph()
        node_size = 200

        # transportation network edges
        transpo_node_list = list(self.tn.node.keys())
        transpo_link_list = []
        for link in self.tn.link.keys():
            transpo_link_list.append((self.tn.link[link].tail, self.tn.link[link].head))

        transpo_node_coords = dict()
        for index, node in enumerate(list(self.tn.node_coords.Node)):
            transpo_node_coords[node] = list(
                zip(self.tn.node_coords.X, self.tn.node_coords.Y)
            )[index]

        node_type = {node: "transpo_node" for _, node in enumerate(transpo_node_list)}

        G.add_nodes_from(transpo_node_list)
        nx.set_node_attributes(G, transpo_node_coords, "coord")
        nx.set_node_attributes(G, node_type, "type")

        if plotting == True:
            plt.figure(1, figsize=figsize)
            nx.draw_networkx_edges(
                G,
                transpo_node_coords,
                edgelist=transpo_link_list,
                edge_color="green",
                width=line_width,
                alpha=0.25,
            )

        # power network edges
        power_bus_list = self.pn.bus.name
        power_bus_coords = dict()
        for index, bus in enumerate(power_bus_list):
            power_bus_coords[bus] = list(
                zip(self.pn.bus_geodata.x, self.pn.bus_geodata.y)
            )[index]
        node_type = {bus: "power_node" for i, bus in enumerate(power_bus_list)}

        b2b_edge_list = [
            [self.pn.bus.name.values[row.from_bus], self.pn.bus.name.values[row.to_bus]]
            for index, row in self.pn.line.iterrows()
        ]
        transfo_edge_list = [
            [self.pn.bus.name.values[row.hv_bus], self.pn.bus.name.values[row.lv_bus]]
            for index, row in self.pn.trafo.iterrows()
        ]
        switch_edge_list = [
            [self.pn.bus.name.values[row.bus], self.pn.bus.name.values[row.element]]
            for index, row in self.pn.switch[self.pn.switch.et == "b"].iterrows()
        ]

        G.add_nodes_from(power_bus_list)
        nx.set_node_attributes(G, power_bus_coords, "coord")
        nx.set_node_attributes(G, node_type, "type")

        nx.draw_networkx_edges(
            G,
            power_bus_coords,
            edgelist=b2b_edge_list,
            edge_color="red",
            width=line_width,
            alpha=0.5,
            style="dotted",
        )
        nx.draw_networkx_edges(
            G,
            power_bus_coords,
            edgelist=transfo_edge_list,
            edge_color="red",
            width=line_width,
            alpha=0.5,
            style="dotted",
        )
        nx.draw_networkx_edges(
            G,
            power_bus_coords,
            edgelist=switch_edge_list,
            edge_color="red",
            width=line_width,
            alpha=0.5,
            style="dotted",
        )

        # water network edges
        water_junc_list = self.wn.node_name_list
        water_pipe_name_list = self.wn.pipe_name_list
        water_junc_coords = dict()
        for index, junc in enumerate(water_junc_list):
            water_junc_coords[junc] = list(self.wn.get_node(junc).coordinates)

        water_pipe_list = []
        for index, _ in enumerate(water_pipe_name_list):
            start_node = self.wn.get_link(water_pipe_name_list[index]).start_node_name
            end_node = self.wn.get_link(water_pipe_name_list[index]).end_node_name
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
            width=line_width,
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
            font_size=font_size,
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
            font_size=font_size,
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
            font_size=font_size,
            font_color="black",
        )
        plt.title("Interdependent Water-Power-Transportation Network")
        plt.legend(scatterpoints=1, loc="best", framealpha=0.5, fontsize=legend_size)

        self.integrated_graph = G

    def generate_dependency_table(self, dependency_file):
        """Generates the dependency table from an input file.

        :param dependency_file: The location of the dependency file in csv format.
        :type dependency_file: string
        """
        dependency_table = interdependencies.DependencyTable()

        # power-water dependencies
        dependency_table.build_power_water_dependencies(dependency_file)

        # transportation access interdependencies
        dependency_table.build_transportation_access(self.integrated_graph)

        self.dependency_table = dependency_table

    def set_disrupted_components(self, scenario_file):
        """Sets the disrupted components in the network.

        :param scenario_file: The location of the disruption scenario file in the list.
        :type scenario_file: string
        """
        try:
            self.disruptive_events = pd.read_csv(scenario_file, sep=",")
        except FileNotFoundError:
            print(
                "Error: The scenario file does not exist. No such directory: ",
                scenario_file,
            )

        self.disrupted_components = self.disruptive_events.components
        self.set_disrupted_infra_dict()

    def get_disruptive_events(self):
        """Returns the disruptive event data

        Returns:
            pandas dataframe: The table with details of disrupted components and the respective damage levels.
        """
        return self.disruptive_events

    def get_disrupted_components(self):
        """Returns the list of disrupted components.

        :return: current list of disrupted components.
        :rtype: list of strings
        """
        return list(self.disrupted_components)

    def set_disrupted_infra_dict(self):
        """Sets the disrupted infrastructure components dictionary with infrastructure type as keys."""
        disrupted_infra_dict = {"power": [], "water": [], "transpo": []}
        for _, component in enumerate(self.disrupted_components):
            # print(component)
            compon_details = interdependencies.get_compon_details(component)
            # print(compon_details)

            if compon_details[0] == "power":
                disrupted_infra_dict["power"].append(component)
            elif compon_details[0] == "water":
                disrupted_infra_dict["water"].append(component)
            elif compon_details[0] == "transpo":
                disrupted_infra_dict["transpo"].append(component)
        self.disrupted_infra_dict = disrupted_infra_dict

    def get_disrupted_infra_dict(self):
        """Returns the  disrupted infrastructure components dictionary.

        :return: The disrupted infrastructure components dictionary.
        :rtype: dictionary
        """
        return self.disrupted_infra_dict

    def set_init_crew_locs(self, init_power_loc, init_water_loc, init_transpo_loc):
        """Sets the intial location of the infrastructure crews. Assign the locations of the respective offices.

        :param init_power_loc: Location (node) of the power crew office.
        :type init_power_loc: string
        :param init_water_loc: Location (node) of the water crew office.
        :type init_water_loc: string
        :param init_transpo_loc: Location (node) of the transportation crew office.
        :type init_transpo_loc: string
        """
        self.init_power_crew_loc = init_power_loc
        self.init_water_crew_loc = init_water_loc
        self.init_transpo_crew_loc = init_transpo_loc
        self.power_crew_loc = self.init_power_crew_loc
        self.water_crew_loc = self.init_water_crew_loc
        self.transpo_crew_loc = self.init_transpo_crew_loc

    def reset_crew_locs(self):
        """Resets the location of infrastructure crews."""
        self.power_crew_loc = self.init_power_crew_loc
        self.water_crew_loc = self.init_water_crew_loc
        self.transpo_crew_loc = self.init_transpo_crew_loc

    def set_power_crew_loc(self, power_crew_loc):
        """Sets the location of the power crew.

        :param power_crew_loc: The name of the location (transportation  node)
        :type power_crew_loc: string
        """
        self.power_crew_loc = power_crew_loc

    def set_water_crew_loc(self, water_crew_loc):
        """Sets the location of the water crew.

        :param water_crew_loc: The name of the location (transportation  node)
        :type water_crew_loc: string
        """
        self.water_crew_loc = water_crew_loc

    def set_transpo_crew_loc(self, transpo_crew_loc):
        """Sets the location of the transportation crew.

        :param transpo_crew_loc: The name of the location (transportation  node)
        :type transpo_crew_loc: string
        """
        self.transpo_crew_loc = transpo_crew_loc

    def get_power_crew_loc(self):
        """Returns the current power crew location.

        :return: Power crew location
        :rtype: string
        """
        return self.power_crew_loc

    def get_water_crew_loc(self):
        """Returns the current water crew location.

        :return: Water crew location
        :rtype: string
        """
        return self.water_crew_loc

    def get_transpo_crew_loc(self):
        """Returns the current transportation crew location.

        :return: Transportation crew location
        :rtype: string
        """
        return self.transpo_crew_loc

    def pipe_leak_node_generator(self):
        """Splits the directly affected pipes to induce leak during simulations."""
        for _, component in enumerate(self.get_disrupted_components()):
            compon_details = interdependencies.get_compon_details(component)
            if compon_details[3] in [
                "Pipe",
                "Service Connection Pipe",
                "Main Pipe",
                "Hydrant Connection Pipe",
                "Valve converted to Pipe",
            ]:
                self.wn = wntr.morph.split_pipe(
                    self.wn,
                    component,
                    f"{component}_B",
                    f"{component}_leak_node",
                )
