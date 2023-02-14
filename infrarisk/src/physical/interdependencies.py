"""Classes and functions to manage dependencies in the integrated infrastructure network."""

import pandas as pd
from scipy import spatial
import re
import infrarisk.src.physical.water.water_network_model as water
import infrarisk.src.physical.power.power_system_model as power
import infrarisk.src.physical.transportation.transpo_compons as transpo_compons

import infrarisk.src.network_recovery as network_recovery

water_dict = water.get_water_dict()
power_dict = power.get_power_dict()
transpo_dict = transpo_compons.get_transpo_dict()

water_control_dict = water.get_water_control_dict()
power_control_dict = power.get_power_control_dict()

# ---------------------------------------------------------------------------- #
#                      DEPENDENCY TABLE CLASS AND METHODS                      #
# ---------------------------------------------------------------------------- #
class DependencyTable:
    """A class to store information related to dependencies among power, water and transportation networks."""

    def __init__(self):
        """Initiates an empty dataframe to store node-to-node dependencies."""
        self.wp_table = pd.DataFrame(
            columns=["water_id", "power_id", "water_type", "power_type"]
        )
        self.access_table = pd.DataFrame(
            columns=[
                "origin_id",
                "transp_id",
                "origin_cat",
                "origin_type",
                "access_dist",
            ]
        )

    def build_power_water_dependencies(self, dependency_file):
        """Adds the power-water dependency table to the DependencyTable object.

        :param dependency_file: The location of the dependency file containing dependency information.
        :type dependency_file: string
        """
        try:
            dependency_data = pd.read_csv(dependency_file, sep=",")
            for _, row in dependency_data.iterrows():
                water_id = row["water_id"]
                power_id = row["power_id"]

                water_details = get_compon_details(water_id)
                power_details = get_compon_details(power_id)

                if (power_details["name"] == "Motor") & (
                    water_details["name"] == "Pump"
                ):
                    self.add_pump_motor_coupling(
                        water_id=water_id,
                        power_id=power_id,
                    )
                elif (power_details["name"] == "Motor as Load") & (
                    water_details["name"] == "Pump"
                ):
                    self.add_pump_loadmotor_coupling(
                        water_id=water_id,
                        power_id=power_id,
                    )
                elif (water_details["name"] == "Reservoir") & (
                    power_details["name"] == "Generator"
                ):
                    self.add_gen_reserv_coupling(
                        water_id=water_id,
                        power_id=power_id,
                    )
                else:
                    print(
                        f"Cannot create dependency between {water_id} and {power_id}. Check the component names and types."
                    )
        except FileNotFoundError:
            print(
                "Error: The infrastructure dependency data file does not exist. No such file or directory: ",
                dependency_file,
            )

    def build_transportation_access(self, integrated_graph):
        """Adds the transportatio naccess table to the DependencyTable object.

        :param integrated_graph: The integrated network as Networkx object.
        :type integrated_graph: networkx.Graph
        """
        self.add_transpo_access(integrated_graph)

    def add_pump_motor_coupling(self, water_id, power_id):
        """Creates a pump-on-motor dependency entry in the dependency table.

        :param water_id: The name of the pump in the water network model.
        :type water_id: string
        :param power_id: The name of the motor in the power systems model.
        :type power_id: string
        """
        self.wp_table = self.wp_table.append(
            {
                "water_id": water_id,
                "power_id": power_id,
                "water_type": "Pump",
                "power_type": "Motor",
            },
            ignore_index=True,
        )

    def add_pump_loadmotor_coupling(self, water_id, power_id):
        """Creates a pump-on-motor dependency entry in the dependency table when motor is modled as a load.

        :param water_id: The name of the pump in the water network model.
        :type water_id: string
        :param power_id: The name of the motor (modeled as load in three phase pandapower networks) in the power systems model.
        :type power_id: string
        """
        self.wp_table = self.wp_table.append(
            {
                "water_id": water_id,
                "power_id": power_id,
                "water_type": "Pump",
                "power_type": "Motor as Load",
            },
            ignore_index=True,
        )

    def add_gen_reserv_coupling(self, water_id, power_id):
        """Creates a generator-on-reservoir dependency entry in the dependency table.

        :param water_id: The name of the reservoir in the water network model.
        :type water_id: string
        :param power_id: The name of the generator in the power systems model.
        :type power_id: string
        """
        self.wp_table = self.wp_table.append(
            {
                "water_id": water_id,
                "power_id": power_id,
                "water_type": "Reservoir",
                "power_type": "Generator",
            },
            ignore_index=True,
        )

    def add_transpo_access(self, integrated_graph):
        """Creates a mapping to nearest road link from every water/power network component.

        :param integrated_graph: The integrated network as networkx object.
        :type integrated_graph: networkx.Graph
        """
        nodes_of_interest = [
            x
            for x, y in integrated_graph.nodes(data=True)
            if y["node_type"] == "power" or y["node_type"] == "water"
        ]
        for node in nodes_of_interest:
            comp_details = get_compon_details(node)
            near_node, near_dist = get_nearest_node(
                integrated_graph,
                node,
                "transpo",
            )
            self.access_table = self.access_table.append(
                {
                    "origin_id": node,
                    "transp_id": near_node,
                    "origin_cat": comp_details["infra"],
                    "origin_type": comp_details["name"],
                    "access_dist": near_dist,
                },
                ignore_index=True,
            )

    def update_dependencies(self, network, time_stamp, next_time_stamp):
        """Updates the operational performance of all the dependent components in the integrated network.

        :param network: The integrated infrastructure network object.
        :type network: networkx.Graph
        :param time_stamp: The start time of the current iteration in seconds.
        :type time_stamp: integer
        :param next_time_stamp: The end tiem of the iteration.
        :type next_time_stamp: integer
        """
        time_stamp = int(time_stamp)
        next_time_stamp = int(next_time_stamp)
        for _, row in self.wp_table.iterrows():
            if (row.water_type == "Pump") & (row.power_type == "Motor"):
                pump_index = network.pn.motor[
                    network.pn.motor.name == row.power_id
                ].index.item()
                if network.pn.res_motor.iloc[pump_index].p_mw == 0:
                    if (
                        f"{row.water_id}_power_off_{time_stamp}"
                        in network.wn.control_name_list
                    ):
                        network.wn.remove_control(
                            f"{row.water_id}_power_off_{time_stamp}"
                        )
                    if (
                        f"{row.water_id}_power_on_{next_time_stamp}"
                        in network.wn.control_name_list
                    ):
                        network.wn.remove_control(
                            f"{row.water_id}_power_on_{next_time_stamp}"
                        )
                    # pump = network.wn.get_link(row.water_id)
                    # pump.add_outage(
                    #     network.wn,
                    #     time_stamp,
                    #     next_time_stamp,
                    # )
                    network_recovery.pump_outage_event(
                        network.wn,
                        row.water_id,
                        time_stamp,
                        next_time_stamp,
                    )
                    # print(
                    #     f"Pump outage resulting from electrical motor failure is added for {row.water_id} between {time_stamp} s and {next_time_stamp} s"
                    # )


# ---------------------------------------------------------------------------- #
#                            MISCELLANEOUS FUNCTIONS                           #
# ---------------------------------------------------------------------------- #
def get_compon_details(compon_name):
    """Fetches the infrastructure type, component type, component code and component actual name.

    :param compon_name: Name of the component.
    :type compon_name: string
    :return: Infrastructure type, component type, component code and component actual name.
    :rtype: list
    """
    compon_details_dict = {}
    compon_infra, compon_id = compon_name.split("_")
    id = re.findall("\d+", compon_name)[0]

    compon_type = ""
    for char in compon_id:
        if char.isalpha():
            compon_type = "".join([compon_type, char])
    if compon_infra == "P":
        if compon_type in power_dict.keys():
            compon_details_dict["infra"] = "power"
            compon_details_dict["infra_code"] = "P"
            compon_details_dict["type_code"] = compon_type
            compon_details_dict["type"] = power_dict[compon_type]["code"]
            compon_details_dict["name"] = power_dict[compon_type]["name"]
            compon_details_dict["id"] = id
            return compon_details_dict
        else:
            print(
                "The naming convention suggests that {} belongs to power network. However, the element {} does not exist in the power component dictionary.".format(
                    compon_name,
                    compon_type,
                )
            )
    elif compon_infra == "W":
        if compon_type in water_dict.keys():
            compon_details_dict["infra"] = "water"
            compon_details_dict["infra_code"] = "W"
            compon_details_dict["type_code"] = compon_type
            compon_details_dict["type"] = water_dict[compon_type]["code"]
            compon_details_dict["name"] = water_dict[compon_type]["name"]
            compon_details_dict["id"] = id
            return compon_details_dict
        else:
            print(
                "The naming convention suggests that {} belongs to water network. However, the element {} does not exist in the water component dictionary.".format(
                    compon_name,
                    compon_type,
                )
            )
    elif compon_infra == "T":
        if compon_type in transpo_dict.keys():
            compon_details_dict["infra"] = "transpo"
            compon_details_dict["infra_code"] = "T"
            compon_details_dict["type_code"] = compon_type
            compon_details_dict["type"] = transpo_dict[compon_type]["code"]
            compon_details_dict["name"] = transpo_dict[compon_type]["name"]
            compon_details_dict["id"] = id
            return compon_details_dict
    else:
        print(
            "Component does not belong to water, power, or transportation networks. Please check the name."
        )


def get_nearest_node(integrated_graph, connected_node, target_type):
    """Finds the nearest node belonging to a specific family from a given node and the distance between the two.

    :param integrated_graph: The integrated network in networkx format.
    :type integrated_graph: netwrokx.Graph
    :param connected_node: Name of the node for which the nearest node has to be identified.
    :type connected_node: string/integer
    :param target_type: The type of the target node (power, transpo, water)
    :type target_type: string
    :return: Nearest node belonging to target type and the distance in meters.
    :rtype: list
    """
    compon_details = get_compon_details(connected_node)
    if compon_details["infra"] == "target_type":
        return connected_node, 0
    else:
        if compon_details["infra"] in ["power", "water"]:
            curr_node_loc = integrated_graph.nodes[connected_node]["coord"]
            nodes_of_interest = [
                x
                for x, y in integrated_graph.nodes(data=True)
                if y["node_type"] == target_type
            ]
            coords_of_interest = [
                y["coord"]
                for x, y in integrated_graph.nodes(data=True)
                if y["node_type"] == target_type
            ]

            tree = spatial.KDTree(coords_of_interest)
            dist_nearest = tree.query([curr_node_loc])[0][0]
            nearest_node = nodes_of_interest[tree.query([curr_node_loc])[1][0]]
        else:
            nearest_node = connected_node
            dist_nearest = 0

        return nearest_node, round(dist_nearest, 2)


def find_connected_nodes(component, integrated_network):
    """Finds the nodes to which the given component is connected to.

    :param component: Name of the component.
    :type component: string
    :param integrated_network: The integrated network in networkx format.
    :type integrated_network: networkx.Graph
    :return: List of connected nodes.
    :rtype: list
    """
    if component.startswith("P_"):
        connected_nodes = find_connected_power_node(component, integrated_network.pn)
    elif component.startswith("W_"):
        connected_nodes = find_connected_water_node(component, integrated_network.wn)
    elif component.startswith("T_"):
        connected_nodes = find_connected_transpo_node(component, integrated_network.tn)
    return connected_nodes


def find_connected_power_node(component, pn):
    """Finds the bus to which the given power systems component is connected to. For elements which are connected to two buses, the start bus is returned.

    :param component: Name of the power systems component.
    :type component: string
    :param pn: The power network the origin node belongs to.
    :type pn: pandaPowerNet
    :return: Name of the connected bus.
    :rtype: string
    """
    compon_details = get_compon_details(component)

    if compon_details["type"] == "bus":
        connected_buses = list(component)
    else:
        near_node_fields = power_dict[compon_details["type_code"]]["connect_field"]
        connected_buses = []
        for near_node_field in near_node_fields:
            bus_index = (
                pn[compon_details["type"]]
                .query('name == "{}"'.format(component))[near_node_field]
                .item()
            )
            connected_buses.append(pn.bus.iloc[bus_index]["name"])
    return connected_buses


def find_connected_water_node(component, wn):
    """Finds the water network node to which the water component is connected to.

    :param component: Name of the water network component.
    :type component: string
    :param wn: The water distribution network the origin node belongs to.
    :type wn: wntr.network.WaterNetworkModel
    :return: Name of the water network node.
    :rtype: string
    """
    compon_details = get_compon_details(component)
    near_node_fields = water_dict[compon_details["type_code"]]["connect_field"]

    connected_nodes = []
    if compon_details["type_code"] in ["P", "PMA", "PSC", "PV", "MP", "PHC", "WP"]:
        for near_node_field in near_node_fields:
            connected_node = getattr(wn.get_link(component), near_node_field)
            if connected_node in wn.original_node_list:
                connected_nodes.append(connected_node)
    elif compon_details["type_code"] in ["R", "J", "JIN", "JVN", "JTN", "JHY", "T"]:
        for near_node_field in near_node_fields:
            connected_node = getattr(wn.get_node(component), near_node_field)
            if connected_node in wn.original_node_list:
                connected_nodes.append(connected_node)
    # print(connected_nodes)
    return connected_nodes


def find_connected_transpo_node(component, tn):
    """Finds the bus to which the given power systems component is connected to. For elements which are connected to two buses, the start bus is returned.

    :param component: Name of the power systems component.
    :type component: string
    :param pn: The power network the origin node belongs to.
    :type pn: pandaPowerNet
    :return: Name of the connected bus.
    :rtype: string
    """
    compon_details = get_compon_details(component)
    near_node_fields = transpo_dict[compon_details["type_code"]]["connect_field"]

    connected_junctions = []

    for near_node_field in near_node_fields:
        if compon_details["type_code"] == "J":
            connected_junctions.append(getattr(tn.node[component], near_node_field))
        elif compon_details["type_code"] == "L":
            connected_junctions.append(getattr(tn.link[component], near_node_field))

    return connected_junctions


# def get_power_repair_time(component):
#     """Returns the repair time of the given power network component.

#     :param component: Name of the component.
#     :type component: string
#     :return: Repair time of the component in hours.
#     :rtype: float
#     """
#     compon_details = get_compon_details(component)
#     repair_time = power_dict[compon_details["type_code"]]["repair_time"]
#     return repair_time


# def get_transpo_repair_time(component):
#     """Returns the repair time of the given component.

#     :param component: Name of the transport network component.
#     :type component: string
#     :return: Repair time of the component in hours.
#     :rtype: float
#     """
#     compon_details = get_compon_details(component)
#     repair_time = transpo_dict[compon_details["type_ciode"]]["repair_time"]
#     return repair_time


def get_compon_repair_time(component):
    """Returns the repair time of the given component.

    :param component: Name of the component.
    :type component: string
    :return: Repair time of the component in hours.
    :rtype: float

    """
    compon_details = get_compon_details(component)
    if compon_details["infra"] == "power":
        repair_time = power_dict[compon_details["type_code"]]["repair_time"]
    elif compon_details["infra"] == "transpo":
        repair_time = transpo_dict[compon_details["type_code"]]["repair_time"]
    elif compon_details["infra"] == "water":
        repair_time = water_dict[compon_details["type_code"]]["repair_time"]

    return repair_time
