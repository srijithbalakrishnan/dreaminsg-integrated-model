from abc import ABC, abstractmethod

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import wntr
import re

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

    def load_networks(self, water_file, power_file, transp_folder):
        """Loads the water, power and transportation networks.

        :param water_file: The water network file (*.inp).
        :type water_file: string
        :param power_file: The power systems file (*.json).
        :type power_file: string
        :param transp_folder: The local directory that consists of required transportation network files.
        :type transp_folder: string
        """
        # load water_network model
        try:
            initial_sim_step = 60
            wn = water.load_water_network(water_file, initial_sim_step)
            self.total_base_water_demand = sum(
                [wn.get_node(node).base_demand for node in wn.junction_name_list]
            )
            self.wn = wn
        except FileNotFoundError:
            print(
                "Error: The water network file does not exist. No such file or directory: ",
                water_file,
            )

        # load power systems network
        try:
            pn = power.load_power_network(power_file)
            power.run_power_simulation(pn)
            self.total_base_power_demand = (
                pn.res_load.p_mw.sum() + pn.res_motor.p_mw.sum()
            )
            self.pn = pn
        except UserWarning:
            print(
                "Error: The power systems file does not exist. No such file or directory: ",
                power_file,
            )

        # load dynamic traffic assignment model
        try:
            tn = transpo.Network(
                f"{transp_folder}/example_net.tntp",
                f"{transp_folder}/example_trips.tntp",
                f"{transp_folder}/example_node.tntp",
            )
            print(
                f"Transportation network successfully loaded from {transp_folder}. Static traffic assignment method will be used to calculate travel times."
            )
            tn.userEquilibrium("FW", 400, 1e-4, tn.averageExcessCost)
            self.tn = tn
        except FileNotFoundError:
            print(
                f"Error: The transportation network folder does not exist. No such directory: {transp_folder}."
            )
        except AttributeError:
            print("Error: Some required network files not found.")

    def generate_integrated_graph(self, plotting=False):
        """Generates the integrated Networkx object.

        :param plotting: Generates plots, defaults to False.
        :type plotting: bool, optional
        """
        G = nx.Graph()
        node_size = 200

        # transportation network edges
        transpo_node_list = list(self.tn.node.keys())
        transpo_link_list = []
        for link in self.tn.link.keys():
            txt = re.sub(r"[^,,A-Za-z0-9]+", "", link).split(",")
            transpo_link_list.append((int(txt[0]), int(txt[1])))
        transpo_node_coords = dict()
        for index, node in enumerate(list(self.tn.node.keys())):
            transpo_node_coords[node] = list(
                zip(self.tn.node_coords.X, self.tn.node_coords.Y)
            )[index]

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
        water_junc_list = self.wn.node_name_list
        water_pipe_name_list = self.wn.pipe_name_list
        water_junc_coords = dict()
        for index, junc in enumerate(water_junc_list):
            water_junc_coords[junc] = list(self.wn.get_node(junc).coordinates)

        water_pipe_list = []
        for index, pipe in enumerate(self.wn.pipe_name_list):
            start_node = self.wn.get_link(self.wn.pipe_name_list[index]).start_node_name
            end_node = self.wn.get_link(self.wn.pipe_name_list[index]).end_node_name
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

    def get_disrupted_components(self):
        """Returns the list of disrupted components.

        :return: current list of disrupted components.
        :rtype: list of strings
        """
        return list(self.disrupted_components)

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
        self.init_water_crew_loc = init_transpo_loc
        self.power_crew_loc = self.init_power_crew_loc
        self.water_crew_loc = self.init_water_crew_loc
        self.water_crew_loc = self.init_water_crew_loc

    def reset_crew_locs(self):
        """Resets the location of infrastructure crews."""
        self.power_crew_loc = self.init_power_crew_loc
        self.water_crew_loc = self.init_water_crew_loc
        self.water_crew_loc = self.init_water_crew_loc

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

    def set_disrupted_infra_dict(self):
        """Sets the disrupted infrastructure components dictionary with infrastructure type as keys."""
        disrupted_infra_dict = {"power": [], "water": [], "transpo": []}
        for index, component in enumerate(self.disrupted_components):
            (
                compon_infra,
                compon_notation,
                compon_code,
                compon_full,
            ) = interdependencies.get_compon_details(component)

            if compon_infra == "power":
                disrupted_infra_dict["power"].append(component)
            elif compon_infra == "water":
                disrupted_infra_dict["water"].append(component)
            elif compon_infra == "transpo":
                disrupted_infra_dict["transpo"].append(component)
        self.disrupted_infra_dict = disrupted_infra_dict

    def get_disrupted_infra_dict(self):
        """Returns the  disrupted infrastructure components dictionary.

        :return: The disrupted infrastructure components dictionary.
        :rtype: dictionary
        """
        return self.disrupted_infra_dict

    def pipe_leak_node_generator(self):
        """Splits the directly affected pipes to induce leak during simulations."""
        for index, component in enumerate(self.get_disrupted_components()):
            (
                compon_infra,
                compon_notation,
                compon_code,
                compon_full,
            ) = interdependencies.get_compon_details(component)
            if compon_full == "Pipe":
                self.wn = wntr.morph.split_pipe(
                    self.wn, component, f"{component}_B", f"{component}_leak_node"
                )
