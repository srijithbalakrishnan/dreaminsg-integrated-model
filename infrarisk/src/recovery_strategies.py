import networkx as nx
import infrarisk.src.network_sim_models.interdependencies as interdependencies
import infrarisk.src.network_sim_models.water.water_network_model as water
import infrarisk.src.network_sim_models.power.power_system_model as power
import infrarisk.src.network_sim_models.transportation.transpo_compons as transpo


class CentralityStrategy:
    """Based on betweenness centrality of the components multiplied by capacity. Break ties randomly."""

    def __init__(self, integrated_network):
        self.integrated_network = integrated_network

    def set_repair_order(self):
        pn_nx = self.integrated_network.power_graph
        wn_nx = self.integrated_network.water_graph
        tn_nx = self.integrated_network.transpo_graph

        disrupted_infra_dict = self.integrated_network.get_disrupted_infra_dict()

        if len(disrupted_infra_dict["power"]) > 0:
            pn_nodebc = nx.betweenness_centrality(pn_nx, normalized=True)
            pn_edgebc = nx.edge_betweenness_centrality(pn_nx, normalized=True)

        if len(disrupted_infra_dict["water"]) > 0:
            wn_nodebc = nx.betweenness_centrality(wn_nx, normalized=True)
            wn_edgebc = nx.edge_betweenness_centrality(wn_nx, normalized=True)

        if len(disrupted_infra_dict["transpo"]) > 0:
            tn_nodebc = nx.betweenness_centrality(tn_nx, normalized=True)
            tn_edgebc = nx.edge_betweenness_centrality(tn_nx, normalized=True)

        transpo_centrality_dict = dict()
        power_centrality_dict = dict()
        water_centrality_dict = dict()

        for compon in self.integrated_network.get_disrupted_components():
            compon_details = interdependencies.get_compon_details(compon)

            if compon_details[0] == "water":
                if compon_details[1] in ["R", "J", "JIN", "JVN", "JTN", "JHY", "T"]:
                    water_centrality_dict[compon] = wn_nodebc[compon]
                elif compon_details[1] in ["P", "PSC", "PMA", "PHC", "PV", "WP"]:
                    compon_key = [
                        (u, v)
                        for u, v, e in self.integrated_network.integrated_graph.edges(
                            data=True
                        )
                        if e["id"] == compon
                    ]
                    water_centrality_dict[compon] = wn_edgebc[compon_key[0]]

            elif compon_details[0] == "power":
                if compon_details[1] in [
                    "B",
                    "BL",
                    "BS",
                    "LO",
                    "LOA",
                    "LOMP",
                    "MP",
                    "AL",
                    "AS",
                    "G",
                    "SH",
                ]:
                    power_centrality_dict[compon] = pn_nodebc[compon]
                elif compon_details[1] in ["S", "L", "LS", "TF", "TH", "I", "DL"]:
                    compon_key = [
                        (u, v)
                        for u, v, e in self.integrated_network.integrated_graph.edges(
                            data=True
                        )
                        if e["id"] == compon
                    ]
                    power_centrality_dict[compon] = pn_edgebc[compon_key[0]]

            elif compon_details[0] == "transpo":
                if compon_details[1] in ["J"]:
                    transpo_centrality_dict[compon] = tn_nodebc[compon]
                elif compon_details[1] in ["L"]:
                    compon_key = [
                        (u, v)
                        for u, v, e in self.integrated_network.integrated_graph.edges(
                            data=True
                        )
                        if e["id"] == compon
                    ]
                    transpo_centrality_dict[compon] = tn_edgebc[compon_key[0]]

        water_centrality_dict = {
            k: v
            for k, v in sorted(
                water_centrality_dict.items(),
                key=lambda x: x[1],
                reverse=True,
            )
        }
        power_centrality_dict = {
            k: v
            for k, v in sorted(
                power_centrality_dict.items(),
                key=lambda x: x[1],
                reverse=True,
            )
        }
        transpo_centrality_dict = {
            k: v
            for k, v in sorted(
                transpo_centrality_dict.items(),
                key=lambda x: x[1],
                reverse=True,
            )
        }

        repair_order = (
            list(transpo_centrality_dict.keys())
            + list(power_centrality_dict.keys())
            + list(water_centrality_dict.keys())
        )
        self.repair_order = repair_order

    def get_repair_order(self):
        return self.repair_order


class CrewDistanceStrategy:
    """Based on the distance between the component and the crew location. Break ties randomly."""

    def __init__(self, integrated_network):
        self.integrated_network = integrated_network

    def set_repair_order(self):
        transpo_dist_dict = dict()
        power_dist_dict = dict()
        water_dist_dict = dict()

        for compon in self.integrated_network.get_disrupted_components():
            compon_details = interdependencies.get_compon_details(compon)

            if compon_details[0] == "water":
                connected_nodes = interdependencies.find_connected_water_node(
                    compon, self.integrated_network.wn
                )
                nearest_nodes = []
                for connected_node in connected_nodes:
                    nearest_node, _ = interdependencies.get_nearest_node(
                        self.integrated_network.integrated_graph,
                        connected_node,
                        "transpo_node",
                    )
                    nearest_nodes.append(nearest_node)

                travel_time = 1e10
                for nearest_node in nearest_nodes:
                    _, curr_tt = self.integrated_network.tn.calculateShortestTravelTime(
                        self.integrated_network.get_water_crew_loc(), nearest_node
                    )

                    if curr_tt < travel_time:
                        travel_time = curr_tt
                water_dist_dict[compon] = travel_time

            elif compon_details[0] == "power":
                connected_buses = interdependencies.find_connected_power_node(
                    compon, self.integrated_network.pn
                )
                nearest_nodes = []
                for connected_bus in connected_buses:
                    nearest_node, _ = interdependencies.get_nearest_node(
                        self.integrated_network.integrated_graph,
                        connected_bus,
                        "transpo_node",
                    )
                    nearest_nodes.append(nearest_node)

                travel_time = 1e10
                for nearest_node in nearest_nodes:
                    _, curr_tt = self.integrated_network.tn.calculateShortestTravelTime(
                        self.integrated_network.get_power_crew_loc(), nearest_node
                    )

                    if curr_tt < travel_time:
                        travel_time = curr_tt
                power_dist_dict[compon] = travel_time

            elif compon_details[0] == "transpo":
                connected_junctions = interdependencies.find_connected_transpo_node(
                    compon, self.integrated_network.tn
                )

                nearest_nodes = []
                for connected_junction in connected_junctions:
                    nearest_node = connected_junction
                    nearest_nodes.append(nearest_node)

                travel_time = 1e10
                for nearest_node in nearest_nodes:
                    _, curr_tt = self.integrated_network.tn.calculateShortestTravelTime(
                        self.integrated_network.get_transpo_crew_loc(), nearest_node
                    )

                    if curr_tt < travel_time:
                        travel_time = curr_tt
                transpo_dist_dict[compon] = travel_time

        water_dist_dict = {
            k: v
            for k, v in sorted(
                water_dist_dict.items(),
                key=lambda x: x[1],
                reverse=True,
            )
        }
        power_dist_dict = {
            k: v
            for k, v in sorted(
                power_dist_dict.items(),
                key=lambda x: x[1],
                reverse=True,
            )
        }
        transpo_dist_dict = {
            k: v
            for k, v in sorted(
                transpo_dist_dict.items(),
                key=lambda x: x[1],
                reverse=True,
            )
        }

        repair_order = (
            list(transpo_dist_dict.keys())
            + list(power_dist_dict.keys())
            + list(water_dist_dict.keys())
        )
        self.repair_order = repair_order

    def get_repair_order(self):
        return self.repair_order


class HandlingCapacityStrategy:
    """Based on the predetermined priority for different components"""

    def __init__(self, integrated_network):
        self.integrated_network = integrated_network

    def set_repair_order(self):
        transpo_capacity_dict = dict()
        power_capacity_dict = dict()
        water_capacity_dict = dict()

        for compon in self.integrated_network.get_disrupted_components():
            compon_details = interdependencies.get_compon_details(compon)
            # print(compon_details)
            if compon_details[0] == "water":
                water_dict = water.get_water_dict()
                capacity_ref = water_dict[compon_details[1]]["results"]
                if capacity_ref == "link":
                    capacity = (
                        self.integrated_network.base_water_link_flow[compon]
                        .abs()
                        .max()
                        .item()
                    )
                    water_capacity_dict[compon] = capacity
                elif capacity_ref == "node":
                    capacity = (
                        self.integrated_network.base_water_node_supply[compon]
                        .abs.max()
                        .item()
                    )
                    water_capacity_dict[compon] = capacity

            elif compon_details[0] == "power":
                power_dict = power.get_power_dict()
                capacity_ref = power_dict[compon_details[1]]["results"]
                capacity_fields = power_dict[compon_details[1]]["capacity_fields"]
                # print(compon, ": ", capacity_ref, ", ", capacity_fields)

                base_pn = self.integrated_network.base_power_supply
                base_pn_table = base_pn[compon_details[2]]
                compon_index = base_pn_table[
                    base_pn_table["name"] == compon
                ].index.item()
                capacity = sum(
                    [
                        abs(base_pn[capacity_ref][x][compon_index])
                        for x in capacity_fields
                    ]
                )
                power_capacity_dict[compon] = capacity

            elif compon_details[0] == "transpo":
                if compon_details[2] == "link":
                    base_tn_dict = getattr(
                        self.integrated_network.base_transpo_flow, "link"
                    )
                    capacity = base_tn_dict[compon].flow
                    transpo_capacity_dict[compon] = capacity
                else:
                    print(f"{compon} cannot be failed.")

        water_capacity_dict = {
            k: v
            for k, v in sorted(
                water_capacity_dict.items(),
                key=lambda x: x[1],
                reverse=True,
            )
        }
        power_capacity_dict = {
            k: v
            for k, v in sorted(
                power_capacity_dict.items(),
                key=lambda x: x[1],
                reverse=True,
            )
        }
        transpo_capacity_dict = {
            k: v
            for k, v in sorted(
                transpo_capacity_dict.items(),
                key=lambda x: x[1],
                reverse=True,
            )
        }

        repair_order = (
            list(transpo_capacity_dict.keys())
            + list(power_capacity_dict.keys())
            + list(water_capacity_dict.keys())
        )
        self.repair_order = repair_order

    def get_repair_order(self):
        return self.repair_order


class JointStrategy:
    """Optimized strategy. Capture interdependencies somehow if exist. Not an immediate priority"""

    pass
