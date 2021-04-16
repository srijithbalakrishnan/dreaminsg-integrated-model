import pandas as pd
import re
from scipy import spatial

import dreaminsg_integrated_model.network_sim_models.water.water_network_model as water
import dreaminsg_integrated_model.network_sim_models.power.power_system_model as power
import dreaminsg_integrated_model.network_sim_models.transportation.network as transpo

water_dict = water.get_water_dict()
power_dict = power.get_power_dict()

#-------------------------------------------------------------------------------------------------#
#                               DEPENDENCY TABLE CLASS AND METHODS                                #
#-------------------------------------------------------------------------------------------------#
class DependencyTable:
    def __init__(self):
        """Initiates an empty dataframe to store node-to-node dependencies.

        Arguments:
            table_type {string} -- The type of the table (wp_table - water-power interdependencies, transpo_access_table -- transportation access table)
        """
        self.wp_table = pd.DataFrame(
            columns=['water_id', 'power_id', 'water_type', 'power_type'])
        self.access_table = pd.DataFrame(
            columns=['origin_id', 'transp_id', 'origin_cat', 'origin_type', "access_dist"])

    #Water-Power interdependencies
    def add_pump_motor_coupling(self, water_id, power_id, motor_mw, pm_efficiency=1):
        """Creates a pump-on-motor dependency entry in the dependency table.

        Arguments:
            water_id {string} -- The name of the pump in the water network model.
            power_id {string} -- The name of the motor in the power systems model.
            motor_mw {float} -- The rated power of the motor in MegaWatts.
            pm_efficiency {float} -- Motor-to-pump efficiency.

        Returns:
            pandas dataframe -- The modified power-water dependency table.
        """
        water_code, water_type = get_water_type(water_id)
        power_code, power_type, power_name = get_power_type(power_id)
        #PumpOnMotorDep(name, water_id, power_id, motor_mw, pm_efficiency)
        self.wp_table = self.wp_table.append({
            'water_id': water_id,
            'power_id': power_id,
            'water_type': water_type,
            'power_type': power_name},
            ignore_index=True)

    def add_gen_reserv_coupling(self, water_id, power_id, gen_mw, gr_efficiency):
        """Creates a generator-on-reservoir dependency entry in the dependency table.

        Arguments:
            name {string} -- The user-defined name of the dependency. This name will be used to call the dependency objects during simulation.
            water_id {string} -- The name of the reservoir in the water network model.
            power_id {string} -- The name of the generator in the power systems model.
            gen_mw {float} -- The generator capacity in megawatts.
            gr_efficiency {float} -- Generator efficiency in fractions.
        """
        water_code, water_type = get_water_type(water_id)
        power_code,power_type, power_name = get_power_type(power_id)
        #GeneratorOnReservoirDep(name = name, water_id, pump_id, gen_mw, gr_efficiency)
        self.wp_table = self.wp_table.append({
            'water_id': water_id,
            'power_id': power_id,
            'water_type': water_type,
            'power_type': power_name},
            ignore_index=True)

    #Power-Transportation and  Interdependencies
    def add_transpo_access(self, integrated_graph):
        """Create a mapping to nearest road link from every water/power network component.

        Arguments:
            component {string} -- The name of the water/power network component.
        """
        nodes_of_interest = [x for x, y in integrated_graph.nodes(
            data=True) if y['type'] == "power_node" or y['type'] == 'water_node']
        for node in nodes_of_interest:
            name = '{}'
            compon_cat = get_infra_type(node)
            compon_type = get_power_type(node) if compon_cat == "power" else get_water_type(node)
            near_node, near_dist = get_nearest_node(integrated_graph, node, "transpo_node")
            self.access_table = self.access_table.append({
                'origin_id': node, 
                'transp_id': near_node, 
                'origin_cat': compon_cat, 
                'origin_type': compon_type[1], 
                'access_dist': near_dist},
            ignore_index = True)
    
    def update_dependencies(self, pn, wn):
        for index, row in self.wp_table.iterrows():
            if (row.water_type == "Pump") & (row.power_type == "Motor"):
                if (pn.motor[pn.motor.name == row.power_id].in_service.item() == True):
                    wn.get_link(row.water_id).power = pn.res_motor.p_mw[pn.motor.index[pn.motor.name == row.power_id].item()]*1000
                else:
                    wn.get_link(row.water_id).power = 0

#-------------------------------------------------------------------------------------------------#
#                                           DEPENDENCY CLASSES                                    #
#-------------------------------------------------------------------------------------------------#

class Dependency:
    """A class of infrastructure dependencies.
    """

    def __init__(self, name):
        self.name = name


class PumpOnMotorDep(Dependency):
    """A class of pump-on-motor dependencies. Inherited from the Dependency superclass.

    Arguments:
        Dependency {class} -- Dependency class.
    """

    def __init__(self, name, start_id, end_id, motor_mw, pm_efficiency=1):
        self.name = name
        self.pump_id = start_id
        self.motor_id = end_id
        self.pm_efficiency = pm_efficiency

        def modify_pump_power(self, motor_mw):
            self.pump_power = motor_mw*1000*pm_efficiency


class GeneratorOnReservoirDep(Dependency):
    """A class of generator-on-reservoir dependencies. Inherited from the Dependency superclass.

    Arguments:
        Dependency {class} -- Dependency class.
    """

    def __init__(self, name, start_id, end_id, reserv_head, flowrate, gen_efficiency=1):
        self.name = name
        self.generator_id = start_id
        self.reservoir_id = end_id
        self.generator_power = 10*gen_efficiency*reserv_head*flowrate

#-------------------------------------------------------------------------------------------------#
#                                   MISCELLANEOUS FUNCTIONS                                       #
#-------------------------------------------------------------------------------------------------#


def get_water_type(compon_name):
    """Returns type of water network component

    Arguments:
        compon_name {string} -- Name of the infrastructure component in the respective infrastructure network model.

    Returns:
        string -- The type of the water network component.
    """
    water_type = ""
    for char in compon_name[0:2]:
        if char.isalpha():
            water_type = "".join([water_type, char])
    return water_type, water_dict[water_type][0]


def get_power_type(compon_name):
    """Returns the type of power systems component

    Arguments:
        compon_name {string} -- The name of the power systems component in the network.

    Returns:
        string -- The type of the power systems component.
    """
    power_type = ""
    for char in compon_name[0:2]:
        if char.isalpha():
            power_type = "".join([power_type, char])
    return power_type, power_dict[power_type][0], power_dict[power_type][1]

def get_near_node_field(compon_name):
    power_type = ""
    for char in compon_name[0:2]:
        if char.isalpha():
            power_type = "".join([power_type, char])
    return power_dict[power_type][2]

def get_infra_type(compon_name):
    type = ""
    for char in compon_name[0:2]:
        if char.isalpha():
            type = "".join([type, char])
    if type in power_dict.keys():
        return "power"
    elif type in water_dict.keys():
        return "water"
    else:
        print("Component does not belong to either water or power component dictionary.")

def get_nearest_node(integrated_graph, connected_node, target_type):
    """Finds the nearest node belonging to a specific family from a given node and the distance between the two.

    Arguments:
        integrated_graph {netwrokx integrated network object} -- [description]
        origin_node {string/integer} -- Name of the node for which the nearest node has to be identified.
        target_type {string} -- The type of the target node (power_node, transpo_node, water_node)
    """
    curr_node_loc = integrated_graph.nodes[connected_node]['coord']
    nodes_of_interest = [x for x, y in integrated_graph.nodes(
        data=True) if y['type'] == target_type]
    coords_of_interest = [y['coord'] for x, y in integrated_graph.nodes(
        data=True) if y['type'] == target_type]

    tree = spatial.KDTree(coords_of_interest)
    dist_nearest = tree.query([curr_node_loc])[0][0]
    nearest_node = nodes_of_interest[tree.query([curr_node_loc])[1][0]]

    return nearest_node, round(dist_nearest, 2)

def find_connected_power_node(origin_node, pn):
    origin_code, origin_type, origin_name = get_power_type(origin_node)
    near_node_field = power_dict[origin_code][2]
    near_node_field = get_near_node_field(origin_node)
    bus_index = pn[origin_type].query('name == "{}"'.format(origin_node))[
        near_node_field].item()
    connected_bus = pn.bus.iloc[bus_index]['name']
    return connected_bus

def find_connected_water_node(origin_node, wn):
    origin_code, origin_name = get_water_type(origin_node)
    near_node_field = water_dict[origin_code][1]
    if origin_code in ['WP', 'P']:
        connected_node = getattr(wn.get_link(origin_node), near_node_field)
    elif origin_code in ["R", "J", "T"]:
        connected_node = getattr(wn.get_node(origin_node), near_node_field)
    return connected_node
