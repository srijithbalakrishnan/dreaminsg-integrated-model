from io import StringIO
import pandas as pd
import networkx as nx
import wntr
import math
import os
import numpy as np

import infrarisk.src.physical.interdependencies as interdependencies
import infrarisk.src.physical.water.water_network_model as water
import infrarisk.src.physical.power.power_system_model as power
import infrarisk.src.physical.transportation.network as transpo
import infrarisk.src.plots as model_plots

import infrarisk.src.repair_crews as repair_crews


class IntegratedNetwork:
    """An integrated infrastructure network class"""

    def __init__(
        self,
        name,
        water_folder=None,
        power_folder=None,
        transp_folder=None,
        power_sim_type=None,
        water_sim_type=None,
    ):
        """Initiates the IntegratedNetwork object.

        :param name: The name of the network.
        :type name: string
        :param water_folder: The directory that consists of required water network files, defaults to None
        :type water_folder: pathlib.Path object, optional
        :param power_folder: The directory that consists of required power network files, defaults to None
        :type power_folder: pathlib.Path object, optional
        :param transp_folder: The directory that consists of required traffic network files, defaults to None
        :type transp_folder: pathlib.Path object, optional
        :param power_sim_type: Power simulation type ("1ph" for single phase networks, "3ph" for three phase networks), defaults to "1ph"
        :type power_sim_type: string, optional
        :param water_sim_type: Type of water simulation: 'PDA' for pressure-dependent driven analysis, 'DDA' for demand driven analysis
        :type water_sim_type: string
        """
        self.name = name

        if water_folder is None:
            self.wn = None
        else:
            self.load_water_network(water_folder, water_sim_type=water_sim_type)

        if power_folder is None:
            self.pn = None
        else:
            self.load_power_network(power_folder, power_sim_type=power_sim_type)

        if transp_folder is None:
            self.tn = None
        else:
            self.load_transpo_network(transp_folder)

    def load_networks(
        self,
        water_folder,
        power_folder,
        transp_folder,
        power_sim_type="1ph",
        water_sim_type="PDA",
    ):
        """Loads the water, power and transportation networks.

        :param water_folder: The directory that consists of required water network files, defaults to None
        :type water_folder: pathlib.Path object, optional
        :param power_folder: The directory that consists of required power network files, defaults to None
        :type power_folder: pathlib.Path object, optional
        :param transp_folder: The directory that consists of required traffic network files, defaults to None
        :type transp_folder: pathlib.Path object, optional
        :param power_sim_type: Power simulation type ("1ph" for single phase networks, "3ph" for three phase networks), defaults to "1ph"
        :type power_sim_type: string, optional
        :param water_sim_type: Type of water simulation: 'PDA' for pressure-dependent driven analysis, 'DDA' for demand driven analysis
        :type water_sim_type: string
        """
        # load water_network model
        if water_folder is not None:
            self.load_water_network(water_folder, water_sim_type)

        # load power systems network
        if power_folder is not None:
            self.load_power_network(power_folder, power_sim_type)

        # load static traffic assignment network
        if transp_folder is not None:
            self.load_transpo_network(transp_folder)

    def load_power_network(self, power_folder, power_sim_type):
        """Loads the power network.

        :param power_file: The power systems file in json format
        :type power_file: string
        """
        try:
            pn = power.load_power_network(
                power_folder / "power.json", sim_type=power_sim_type
            )
            power.run_power_simulation(pn)
            self.pn = pn
            self.power_sim_time = power_sim_type
            self.base_power_supply = power.generate_base_supply(pn)
        except UserWarning:
            print(
                "Error: The power systems file does not exist. No such file or directory: ",
                power_folder / "power.json",
            )

        if os.path.exists(power_folder / "line_to_switch_map.csv"):
            line_switch_df = pd.read_csv(
                power_folder / "line_to_switch_map.csv", sep=","
            )

            self.line_switch_dict = dict()
            for _, row in line_switch_df.iterrows():
                line = row["line"]
                switch_list = [x for x in row[1:] if x is not np.nan]
                self.line_switch_dict[line] = switch_list

    def load_water_network(self, water_folder, water_sim_type):
        """Loads the water network.

        :param water_folder: The directory that consists of required water network files
        :type water_folder: pathlib.Path object
        :param water_sim_type: Type of water simulation: 'PDA' for pressure-dependent driven analysis, 'DDA' for demand driven analysis
        :type water_sim_type: string
        """
        initial_sim_step = 60
        self.wn = water.load_water_network(
            f"{water_folder}/water.inp", water_sim_type, initial_sim_step
        )
        self.water_sim_type = water_sim_type

        if water_sim_type == "DDA":
            self.base_water_node_supply = pd.read_csv(
                water_folder / "base_water_node_supply.csv"
            )
            self.base_water_link_flow = pd.read_csv(
                water_folder / "base_water_link_flow.csv"
            )
        elif self.water_sim_type == "PDA":
            self.base_water_node_supply = pd.read_csv(
                water_folder / "base_water_node_supply_pda.csv"
            )
            self.base_water_link_flow = pd.read_csv(
                water_folder / "base_water_link_flow_pda.csv"
            )

        if os.path.exists(water_folder / "pipe_to_valve_map.csv"):
            pipe_valve_df = pd.read_csv(water_folder / "pipe_to_valve_map.csv", sep=",")

            self.pipe_valve_dict = dict()
            for _, row in pipe_valve_df.iterrows():
                pipe = row["pipe"]
                valve_list = [x for x in row[1:] if x is not np.nan]
                self.pipe_valve_dict[pipe] = valve_list

    def load_transpo_network(self, transp_folder):
        """Loads the transportation network.

        :param transp_folder: The directory that consists of required transportation network files
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
            self.base_transpo_flow = tn
        except FileNotFoundError:
            print(
                f"Error: The transportation network folder does not exist. No such directory: {transp_folder}."
            )
        except AttributeError:
            print("Error: Some required network files not found.")

    def generate_integrated_graph(self):
        """Generates the integrated network as a Networkx graph."""
        self.power_graph = self.generate_power_networkx_graph()
        print("Successfully added power network to the integrated graph...")
        self.water_graph = self.generate_water_networkx_graph()
        print("Successfully added water network to the integrated graph...")
        self.transpo_graph = self.generate_transpo_networkx_graph()
        print("Successfully added transportation network to the integrated graph...")

        G = nx.compose(
            self.power_graph, nx.compose(self.water_graph, self.transpo_graph)
        )

        self.integrated_graph = G
        self.set_map_extends()
        print("Integrated graph successffully created.")

        title = f"{self.name} integrated network"

        self.generate_betweenness_centrality()
        model_plots.plot_bokeh_from_integrated_graph(
            G, title=title, extent=self.map_extends
        )

    def generate_betweenness_centrality(self):
        """Generates the betweenness centrality of the integrated graph."""
        print("Generating betweenness centrality...")
        pn_nx = self.power_graph
        wn_nx = self.water_graph
        tn_nx = self.transpo_graph

        self.pn_nodebc = nx.betweenness_centrality(pn_nx, normalized=True)
        self.pn_edgebc = nx.edge_betweenness_centrality(pn_nx, normalized=True)

        self.wn_nodebc = nx.betweenness_centrality(wn_nx, normalized=True)
        self.wn_edgebc = nx.edge_betweenness_centrality(wn_nx, normalized=True)

        self.tn_nodebc = nx.betweenness_centrality(tn_nx, normalized=True)
        self.tn_edgebc = nx.edge_betweenness_centrality(tn_nx, normalized=True)

    def set_map_extends(self):
        """Sets the extents of the map in the format ((xmin, ymin), (xmax, ymax))."""
        x, y = [], []
        for node in self.integrated_graph.nodes:
            x_coord, y_coord = self.integrated_graph.nodes[node]["coord"]
            x.append(x_coord)
            y.append(y_coord)

        self.map_extends = [
            (math.floor(min(x)), math.floor(min(y))),
            (math.floor(max(x)), math.floor(max(y))),
        ]

    def get_map_extends(self):
        """Returns the extents of the map in the format ((xmin, ymin), (xmax, ymax)).

        :return: The extent of the integrated graph (coordinates)
        :rtype: list of tuples
        """
        return self.map_extends

    def generate_power_networkx_graph(self, plot=False):
        """Generates the power network as a networkx object.

        :param plot: To generate the network plot, defaults to False.
        :type plot: bool, optional
        :return: The power network as a networkx object.
        :rtype: Networkx object
        """
        G_power = nx.Graph()

        # power network nodes
        power_nodes = pd.DataFrame(
            columns=["id", "node_type", "node_category", "x", "y"]
        )

        for index, row in self.pn.bus.iterrows():
            power_nodes = power_nodes.append(
                {
                    "id": row["name"],
                    "node_type": "power_node",
                    "node_category": "Bus",
                    "x": self.pn.bus_geodata.x[index],
                    "y": self.pn.bus_geodata.y[index],
                },
                ignore_index=True,
            )

        # power network links
        power_links = pd.DataFrame(
            columns=["id", "link_type", "link_category", "from", "to"]
        )

        for _, row in self.pn.line.iterrows():
            power_links = power_links.append(
                {
                    "id": row["name"],
                    "link_type": "Power",
                    "link_category": "Power line",
                    "from": self.pn.bus.name.values[row["from_bus"]],
                    "to": self.pn.bus.name.values[row["to_bus"]],
                },
                ignore_index=True,
            )

        for _, row in self.pn.trafo.iterrows():
            power_links = power_links.append(
                {
                    "id": row["name"],
                    "link_type": "Power",
                    "link_category": "Transformer",
                    "from": self.pn.bus.name.values[row["hv_bus"]],
                    "to": self.pn.bus.name.values[row["lv_bus"]],
                },
                ignore_index=True,
            )

        for _, row in self.pn.switch[self.pn.switch.et == "b"].iterrows():
            power_links = power_links.append(
                {
                    "id": row["name"],
                    "link_type": "Power",
                    "link_category": "Switch",
                    "from": self.pn.bus.name.values[row["bus"]],
                    "to": self.pn.bus.name.values[row["element"]],
                },
                ignore_index=True,
            )

        G_power = nx.from_pandas_edgelist(
            power_links,
            source="from",
            target="to",
            edge_attr=True,
        )

        for _, row in power_nodes.iterrows():
            G_power.nodes[row["id"]]["node_type"] = row["node_type"]
            G_power.nodes[row["id"]]["node_category"] = row["node_category"]
            G_power.nodes[row["id"]]["coord"] = (row["x"], row["y"])

        for graph in [G_power]:
            for _, link in enumerate(graph.edges.keys()):
                start_node, end_node = link
                start_coords = graph.nodes[link[0]]["coord"]
                end_coords = graph.nodes[link[1]]["coord"]
                graph.edges[link]["length"] = round(
                    math.sqrt(
                        ((start_coords[0] - end_coords[0]) ** 2)
                        + ((start_coords[1] - end_coords[1]) ** 2)
                    ),
                    3,
                )

        if plot == True:
            pos = {node: G_power.nodes[node]["coord"] for node in power_nodes.id}
            nx.draw(G_power, pos, node_size=1)

        return G_power

    def generate_water_networkx_graph(self, plot=False):
        """Generates the water network as a networkx object.

        :param plot: To generate the network plot, defaults to False., defaults to False.
        :type plot: bool, optional
        :return: The water network as a networkx object.
        :rtype: Networkx object
        """
        G_water = nx.Graph()

        # water network nodes
        water_nodes = pd.DataFrame(
            columns=["id", "node_type", "node_category", "x", "y"]
        )

        water_junc_list = self.wn.junction_name_list
        water_tank_list = self.wn.tank_name_list
        water_reserv_list = self.wn.reservoir_name_list

        for _, node_name in enumerate(water_junc_list):
            water_nodes = water_nodes.append(
                {
                    "id": node_name,
                    "node_type": "water_node",
                    "node_category": "Junction",
                    "x": list(self.wn.get_node(node_name).coordinates)[0],
                    "y": list(self.wn.get_node(node_name).coordinates)[1],
                },
                ignore_index=True,
            )
        for _, node_name in enumerate(water_tank_list):
            water_nodes = water_nodes.append(
                {
                    "id": node_name,
                    "node_type": "water_node",
                    "node_category": "Tank",
                    "x": list(self.wn.get_node(node_name).coordinates)[0],
                    "y": list(self.wn.get_node(node_name).coordinates)[1],
                },
                ignore_index=True,
            )
        for _, node_name in enumerate(water_reserv_list):
            water_nodes = water_nodes.append(
                {
                    "id": node_name,
                    "node_type": "water_node",
                    "node_category": "Reservoir",
                    "x": list(self.wn.get_node(node_name).coordinates)[0],
                    "y": list(self.wn.get_node(node_name).coordinates)[1],
                },
                ignore_index=True,
            )

        # water network links
        water_links = pd.DataFrame(
            columns=["id", "link_type", "link_category", "from", "to"]
        )

        water_pipe_name_list = self.wn.pipe_name_list
        water_pump_name_list = self.wn.pump_name_list

        for _, link_name in enumerate(water_pipe_name_list):
            water_links = water_links.append(
                {
                    "id": link_name,
                    "link_type": "Water",
                    "link_category": "Water pipe",
                    "from": self.wn.get_link(link_name).start_node_name,
                    "to": self.wn.get_link(link_name).end_node_name,
                },
                ignore_index=True,
            )
        for _, link_name in enumerate(water_pump_name_list):
            water_links = water_links.append(
                {
                    "id": link_name,
                    "link_type": "Water",
                    "link_category": "Water pump",
                    "from": self.wn.get_link(link_name).start_node_name,
                    "to": self.wn.get_link(link_name).end_node_name,
                },
                ignore_index=True,
            )

        G_water = nx.from_pandas_edgelist(
            water_links, source="from", target="to", edge_attr=True
        )

        for _, row in water_nodes.iterrows():
            G_water.nodes[row["id"]]["node_type"] = row["node_type"]
            G_water.nodes[row["id"]]["node_category"] = row["node_category"]
            G_water.nodes[row["id"]]["coord"] = self.wn.get_node(row["id"]).coordinates

        for graph in [G_water]:
            for _, link in enumerate(graph.edges.keys()):
                start_node, end_node = link
                start_coords = graph.nodes[link[0]]["coord"]
                end_coords = graph.nodes[link[1]]["coord"]
                graph.edges[link]["length"] = round(
                    math.sqrt(
                        ((start_coords[0] - end_coords[0]) ** 2)
                        + ((start_coords[1] - end_coords[1]) ** 2)
                    ),
                    3,
                )

        if plot == True:
            pos = {node: G_water.nodes[node]["coord"] for node in water_nodes.id}
            nx.draw(G_water, pos, node_size=1)

        return G_water

    def generate_transpo_networkx_graph(self, plot=False):
        """Generates the transportation network as a networkx object.

        :param plot: To generate the network plot, defaults to False., defaults to False.
        :type plot: bool, optional
        :return: The transportation network as a networkx object.
        :rtype: Networkx object
        """
        G_transpo = nx.Graph()

        # transportation network nodes
        transpo_nodes = pd.DataFrame(
            columns=["id", "node_type", "node_category", "x", "y"]
        )

        transpo_node_list = list(self.tn.node.keys())
        for _, node_name in enumerate(list(transpo_node_list)):
            transpo_nodes = transpo_nodes.append(
                {
                    "id": node_name,
                    "node_type": "transpo_node",
                    "node_category": "Junction",
                    "x": self.tn.node_coords[
                        self.tn.node_coords["Node"] == node_name
                    ].X,
                    "y": self.tn.node_coords[
                        self.tn.node_coords["Node"] == node_name
                    ].Y,
                },
                ignore_index=True,
            )

        # transportation network links
        transpo_links = pd.DataFrame(
            columns=["id", "link_type", "link_category", "from", "to"]
        )
        transpo_link_list = list(self.tn.link.keys())
        for _, link_name in enumerate(list(transpo_link_list)):
            transpo_links = transpo_links.append(
                {
                    "id": link_name,
                    "link_type": "Transportation",
                    "link_category": "Road link",
                    "from": self.tn.link[link_name].tail,
                    "to": self.tn.link[link_name].head,
                },
                ignore_index=True,
            )

        G_transpo = nx.from_pandas_edgelist(
            transpo_links,
            source="from",
            target="to",
            edge_attr=True,
        )

        for _, node_name in enumerate(transpo_node_list):
            G_transpo.nodes[node_name]["node_type"] = "transpo_node"
            G_transpo.nodes[node_name]["node_category"] = transpo_nodes[
                transpo_nodes.id == node_name
            ]["node_category"].item()
            G_transpo.nodes[node_name]["coord"] = [
                self.tn.node_coords[self.tn.node_coords["Node"] == node_name].X.item(),
                self.tn.node_coords[self.tn.node_coords["Node"] == node_name].Y.item(),
            ]

        for graph in [G_transpo]:
            for _, link in enumerate(graph.edges.keys()):
                start_node, end_node = link
                start_coords = graph.nodes[link[0]]["coord"]
                end_coords = graph.nodes[link[1]]["coord"]
                graph.edges[link]["length"] = round(
                    math.sqrt(
                        ((start_coords[0] - end_coords[0]) ** 2)
                        + ((start_coords[1] - end_coords[1]) ** 2)
                    ),
                    3,
                )

        if plot == True:
            pos = {node: G_transpo.nodes[node]["coord"] for node in transpo_nodes.id}
            nx.draw(G_transpo, pos, node_size=1)

        return G_transpo

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

        self.disruption_time_dict = {}  # self.disruptive_events["time_stamp"].min()

        power_list = self.disrupted_infra_dict["power"]
        water_list = self.disrupted_infra_dict["water"]
        transpo_list = self.disrupted_infra_dict["transpo"]

        self.disruption_time_dict["power"] = self.disruptive_events[
            self.disruptive_events["components"].isin(power_list)
        ]["time_stamp"].min()
        self.disruption_time_dict["water"] = self.disruptive_events[
            self.disruptive_events["components"].isin(water_list)
        ]["time_stamp"].min()
        self.disruption_time_dict["transpo"] = self.disruptive_events[
            self.disruptive_events["components"].isin(transpo_list)
        ]["time_stamp"].min()

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

    def deploy_crews(
        self,
        init_power_crew_locs=None,
        power_crews_size=None,
        init_water_crew_locs=None,
        water_crews_size=None,
        init_transpo_crew_locs=None,
        transpo_crews_size=None,
    ):
        """Deploys the infrastructure crews for performing recovery actions.

        :param init_power_crew_locs: Initial locations (nearest transportation nodes) of the power crews.
        :type init_power_crew_locs: list of strings
        :param init_water_crew_locs: Initial locations (nearest transportation nodes) of the water crews.
        :type init_water_crew_locs: list of strings
        :param init_transpo_crew_locs: Initial locations (nearest transportation nodes) of the transportation crews.
        :type init_transpo_crew_locs: list of strings
        """
        self.power_crews = {}
        self.water_crews = {}
        self.transpo_crews = {}

        try:
            for i in range(len(init_power_crew_locs)):
                crew_size = None if power_crews_size is None else power_crews_size[i]
                self.power_crews[i + 1] = repair_crews.PowerRepairCrew(
                    name=i + 1,
                    init_loc=init_power_crew_locs[i],
                    crew_size=crew_size,
                )
                self.power_crews[i + 1].set_next_trip_start(
                    self.disruption_time_dict["power"]
                )
            print("Power repair crews successfully deployed.")
        except TypeError:
            print(
                "TypeError: The initial locations of the power crews are not specified or not valid."
            )

        try:
            for i in range(len(init_water_crew_locs)):
                crew_size = None if water_crews_size is None else water_crews_size[i]
                self.water_crews[i + 1] = repair_crews.WaterRepairCrew(
                    name=i + 1,
                    init_loc=init_water_crew_locs[i],
                    crew_size=crew_size,
                )
                self.water_crews[i + 1].set_next_trip_start(
                    self.disruption_time_dict["water"]
                )
            print("Water repair crews successfully deployed.")
        except TypeError:
            print(
                "TypeError: The initial locations of the water crews are not specified or not valid."
            )

        try:
            for i in range(len(init_transpo_crew_locs)):
                crew_size = (
                    None if transpo_crews_size is None else transpo_crews_size[i]
                )
                self.transpo_crews[i + 1] = repair_crews.TranspoRepairCrew(
                    name=i + 1,
                    init_loc=init_transpo_crew_locs[i],
                    crew_size=crew_size,
                )
                self.transpo_crews[i + 1].set_next_trip_start(
                    self.disruption_time_dict["transpo"]
                )
            print("Transportation repair crews successfully deployed.")
        except TypeError:
            print(
                "TypeError: The initial locations of the transportation crews are not specified or not valid."
            )

    def get_idle_crew(self, crew_type):
        """Returns the idle crew of the given type.

        :param crew_type: Type of the crew.
        :type crew_type: string
        :return: The idle crew of the given type.
        :rtype: repair_crews.RepairCrew
        """
        if crew_type == "power":
            crews = self.power_crews

            idle_crew = crews[list(crews.keys())[0]]
            for crew_name in crews.keys():
                if crews[crew_name].next_trip_start < idle_crew.next_trip_start:
                    idle_crew = crews[crew_name]
            return idle_crew
        elif crew_type == "water":
            crews = self.water_crews
            idle_crew = crews[list(crews.keys())[0]]
            for crew_name in crews.keys():
                if crews[crew_name].next_trip_start < idle_crew.next_trip_start:
                    idle_crew = crews[crew_name]
            return idle_crew
        elif crew_type == "transpo":
            crews = self.transpo_crews
            idle_crew = crews[list(crews.keys())[0]]
            for crew_name in crews.keys():
                if crews[crew_name].next_trip_start < idle_crew.next_trip_start:
                    idle_crew = crews[crew_name]
            return idle_crew

    def reset_crew_locs(self):
        """Resets the location of infrastructure crews."""
        for crew_type in [self.power_crews, self.water_crews, self.transpo_crews]:
            for crew in crew_type.keys():
                crew_type[crew].reset_locs()

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

    def get_node_link_dict(self):
        node_link_dict = {
            "water": {
                "node": ["R", "J", "JIN", "JVN", "JTN", "JHY", "T"],
                "link": ["P", "PSC", "PMA", "PHC", "PV", "WP"],
            },
            "power": {
                "node": ["B", "BL", "BS", "LO", "MP", "AL", "AS", "G"],
                "link": ["S", "L", "LS", "TF", "TH", "I", "DL"],
            },
            "transpo": {"node": ["J"], "link": ["L"]},
        }
        return node_link_dict
