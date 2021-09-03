"""Classes and functions to manage dependencies in the integrated infrastructure network."""

import pandas as pd
from scipy import spatial
import infrarisk.src.network_sim_models.water.water_network_model as water
import infrarisk.src.network_sim_models.power.power_system_model as power
import infrarisk.src.network_sim_models.transportation.transpo_compons as transpo

water_dict = water.get_water_dict()
power_dict = power.get_power_dict()
transpo_dict = transpo.get_transpo_dict()

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

                if (power_details[3] == "Motor") & (water_details[3] == "Pump"):
                    self.add_pump_motor_coupling(
                        water_id=water_id,
                        power_id=power_id,
                    )
                elif (power_details[3] == "Motor as Load") & (
                    water_details[3] == "Pump"
                ):
                    self.add_pump_loadmotor_coupling(
                        water_id=water_id,
                        power_id=power_id,
                    )
                elif (water_details[3] == "Reservoir") & (
                    power_details[3] == "Generator"
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
        :type integrated_graph: Nextworkx object
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
        :type integrated_graph: [networkx object]
        """
        nodes_of_interest = [
            x
            for x, y in integrated_graph.nodes(data=True)
            if y["node_type"] == "power_node" or y["node_type"] == "water_node"
        ]
        for node in nodes_of_interest:
            comp_details = get_compon_details(node)
            near_node, near_dist = get_nearest_node(
                integrated_graph,
                node,
                "transpo_node",
            )
            self.access_table = self.access_table.append(
                {
                    "origin_id": node,
                    "transp_id": near_node,
                    "origin_cat": comp_details[0],
                    "origin_type": comp_details[3],
                    "access_dist": near_dist,
                },
                ignore_index=True,
            )

    def update_dependencies(self, network, time_stamp, next_time_stamp):
        """Updates the operational performance of all the dependent components in the integrated network.

        :param network: The integrated infrastructure network object.
        :type network: An IntegratedNetwork object
        :param time_stamp: The start time of the current iteration in seconds.
        :type time_stamp: integer
        :param next_time_stamp: The end tiem of the iteration.
        :type next_time_stamp: integer
        """
        # print(network.wn.control_name_list)
        for _, row in self.wp_table.iterrows():
            if (row.water_type == "Pump") & (row.power_type == "Motor"):
                # print(
                #     "Motor operational status: ",
                #     network.pn.motor[
                #         network.pn.motor.name == row.power_id
                #     ].in_service.item(),
                # )
                if (
                    network.pn.motor[
                        network.pn.motor.name == row.power_id
                    ].in_service.item()
                    == False
                ):

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
                    pump = network.wn.get_link(row.water_id)
                    pump.add_outage(
                        network.wn,
                        time_stamp,
                        next_time_stamp,
                    )
                    # print(
                    #     f"Pump outage resulting from electrical motor failure is added between {time_stamp} s and {next_time_stamp} s"
                    # )
                else:
                    # pump = network.wn.get_link(row.water_id)
                    # pump.status = 1
                    pass
            elif (row.water_type == "Pump") & (row.power_type == "Motor as Load"):

                if (
                    network.pn.asymmetric_load[
                        network.pn.asymmetric_load.name == row.power_id
                    ].in_service.item()
                    == False
                ):

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
                    pump = network.wn.get_link(row.water_id)
                    pump.add_outage(
                        network.wn,
                        time_stamp,
                        next_time_stamp,
                    )
                    # print(
                    #     f"Pump outage resulting from electrical motor failure is added between {time_stamp} s and {next_time_stamp} s"
                    # )
                else:
                    # pump = network.wn.get_link(row.water_id)
                    # pump.status = 1
                    pass


# ---------------------------------------------------------------------------- #
#                            MISCELLANEOUS FUNCTIONS                           #
# ---------------------------------------------------------------------------- #
def get_compon_details(compon_name):
    """Fetches the infrastructure type, component type, component code and component actual name.

    :param compon_name: Name of the component.
    :type compon_name: string
    :return: Infrastructure type, component type, component code and component actual name.
    :rtype: list of strings
    """
    compon_infra, compon_id = compon_name.split("_")
    # print(compon_infra, compon_id)
    compon_type = ""
    for char in compon_id:
        if char.isalpha():
            compon_type = "".join([compon_type, char])
    if compon_infra == "P":
        if compon_type in power_dict.keys():
            return (
                "power",
                compon_type,
                power_dict[compon_type]["code"],
                power_dict[compon_type]["name"],
            )
        else:
            print(
                "The naming convention suggests that {} belongs to power netwok. However, the element {} does not exist in the power component dictionary.".format(
                    compon_name,
                    compon_type,
                )
            )
    elif compon_infra == "W":
        if compon_type in water_dict.keys():
            return (
                "water",
                compon_type,
                water_dict[compon_type]["code"],
                water_dict[compon_type]["name"],
            )
        else:
            print(
                "The naming convention suggests that {} belongs to water netwok. However, the element {} does not exist in the water component dictionary.".format(
                    compon_name,
                    compon_type,
                )
            )
    elif compon_infra == "T":
        if compon_type in transpo_dict.keys():
            return (
                "transpo",
                compon_type,
                transpo_dict[compon_type]["code"],
                transpo_dict[compon_type]["name"],
            )
    else:
        print(
            "Component does not belong to water, power, or transportation networks. Please check the name."
        )


def get_nearest_node(integrated_graph, connected_node, target_type):
    """Finds the nearest node belonging to a specific family from a given node and the distance between the two.

    :param integrated_graph: The integrated network in networkx format.
    :type integrated_graph: netwrokx object
    :param connected_node: Name of the node for which the nearest node has to be identified.
    :type connected_node: string/integer
    :param target_type: The type of the target node (power_node, transpo_node, water_node)
    :type target_type: string
    :return: Nearest node belonging to target type and the distance in meters.
    :rtype: list
    """
    curr_node_loc = integrated_graph.nodes[connected_node]["coord"]
    nodes_of_interest = [
        x for x, y in integrated_graph.nodes(data=True) if y["node_type"] == target_type
    ]
    coords_of_interest = [
        y["coord"]
        for x, y in integrated_graph.nodes(data=True)
        if y["node_type"] == target_type
    ]

    tree = spatial.KDTree(coords_of_interest)
    dist_nearest = tree.query([curr_node_loc])[0][0]
    nearest_node = nodes_of_interest[tree.query([curr_node_loc])[1][0]]

    return nearest_node, round(dist_nearest, 2)


def find_connected_power_node(component, pn):
    """Finds the bus to which the given power systems component is connected to. For elements which are connected to two buses, the start bus is returned.

    :param component: Name of the power systems component.
    :type component: string
    :param pn: The power network the origin node belongs to.
    :type pn: pandapower network object
    :return: Name of the connected bus.
    :rtype: string
    """
    compon_details = get_compon_details(component)

    if compon_details[2] == "bus":
        connected_buses = list(component)
    else:
        near_node_fields = power_dict[compon_details[1]]["connect_field"]
        connected_buses = []
        for near_node_field in near_node_fields:
            bus_index = (
                pn[compon_details[2]]
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
    :type wn: wntr network object
    :return: Name of the water network node.
    :rtype: string
    """
    compon_details = get_compon_details(component)
    near_node_fields = water_dict[compon_details[1]]["connect_field"]

    connected_nodes = []
    for near_node_field in near_node_fields:
        connected_nodes.append(getattr(wn.get_link(component), near_node_field))

    return connected_nodes


def find_connected_transpo_node(component, tn):
    """Finds the bus to which the given power systems component is connected to. For elements which are connected to two buses, the start bus is returned.

    :param component: Name of the power systems component.
    :type component: string
    :param pn: The power network the origin node belongs to.
    :type pn: pandapower network object
    :return: Name of the connected bus.
    :rtype: string
    """
    compon_details = get_compon_details(component)
    near_node_fields = transpo_dict[compon_details[1]]["connect_field"]

    connected_junctions = []

    for near_node_field in near_node_fields:
        if compon_details[1] == "J":
            connected_junctions.append(getattr(tn.node[component], near_node_field))
        elif compon_details[1] == "L":
            connected_junctions.append(getattr(tn.link[component], near_node_field))

    return connected_junctions


def get_power_repair_time(component):
    compon_details = get_compon_details(component)
    repair_time = power_dict[compon_details[1]]["repair_time"]
    return repair_time


def get_transpo_repair_time(component):
    compon_details = get_compon_details(component)
    repair_time = transpo_dict[compon_details[1]]["repair_time"]
    return repair_time


def get_water_repair_time(component, wn):
    compon_details = get_compon_details(component)
    if compon_details[1] in ["P", "PMA", "PSC", "PV", "PHC"]:
        repair_time = wn.get_link(component).diameter * 10 + 2  # Choi et al. (2018)
        return repair_time
    else:
        repair_time = water_dict[compon_details[1]]["repair_time"]
        return repair_time
