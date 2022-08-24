"""Functions to implement power systems simulations."""

import pandapower as pp
import infrarisk.src.physical.interdependencies as interdependencies
import copy


def get_power_dict():
    """Creates a dictionary of major power system components in a network. Used for naming automatically generated networks.

    :return: Mapping of infrastructure component abbreviations to names.
    :rtype: dictionary of string: dictionary of string: string
    """
    power_dict = {
        "B": {
            "code": "bus",
            "name": "Bus",
            "connect_field": ["name"],
            "repair_time": 3,
            "results": "res_bus",
            "capacity_fields": ["p_mw"],
        },
        "BL": {
            "code": "bus",
            "name": "Bus connected to load",
            "connect_field": ["name"],
            "repair_time": 3,
            "results": "res_bus",
            "capacity_fields": ["p_mw"],
        },
        "BLO": {
            "code": "bus",
            "name": "Bus connected to load",
            "connect_field": ["name"],
            "repair_time": 3,
            "results": "res_bus",
            "capacity_fields": ["p_mw"],
        },
        "BS": {
            "code": "bus",
            "name": "Bus connected to switch",
            "connect_field": ["name"],
            "repair_time": 3,
            "results": "res_bus",
            "capacity_fields": ["p_mw"],
        },
        "BG": {
            "code": "bus",
            "name": "Bus connected to gate station",
            "connect_field": ["name"],
            "repair_time": 3,
            "results": "res_bus",
            "capacity_fields": ["p_mw"],
        },
        "BEG": {
            "code": "bus",
            "name": "Bus connected to external grid connection",
            "connect_field": ["name"],
            "repair_time": 3,
            "results": "res_bus",
            "capacity_fields": ["p_mw"],
        },
        "LO": {
            "code": "load",
            "name": "Load",
            "connect_field": ["bus"],
            "repair_time": 3,
            "results": "res_load",
            "capacity_fields": ["p_mw"],
        },
        "LOA": {
            "code": "asymmetric_load",
            "name": "Asymmetric Load",
            "connect_field": ["bus"],
            "repair_time": 3,
            "results": "res_asymmetric_load_3ph",
            "capacity_fields": ["p_a_mw", "p_b_mw", "p_c_mw"],
        },
        "SG": {
            "code": "sgen",
            "name": "Static Generator",
            "connect_field": ["bus"],
            "repair_time": 24,
            "results": "res_sgen",
            "capacity_fields": ["p_mw"],
        },
        "MP": {
            "code": "motor",
            "name": "Motor",
            "connect_field": ["bus"],
            "repair_time": 24,
            "results": "res_motor",
            "capacity_fields": ["p_mw"],
        },
        "AS": {
            "code": "asymmetric_sgen",
            "name": "Asymmetric Static Generator",
            "connect_field": ["bus"],
            "repair_time": 10,
            "results": "res_asymmetric_sgen_3ph",
            "capacity_fields": ["p_a_mw", "p_b_mw", "p_c_mw"],
        },
        "ST": {
            "code": "storage",
            "name": "Storage",
            "connect_field": ["bus"],
            "repair_time": 5,
            "results": "res_storage",
            "capacity_fields": ["p_mw"],
        },
        "G": {
            "code": "gen",
            "name": "Generator",
            "connect_field": ["bus"],
            "repair_time": 24,
            "results": "res_gen",
            "capacity_fields": ["p_mw"],
        },
        "S": {
            "code": "switch",
            "name": "Switch",
            "connect_field": ["bus", "element"],
            "repair_time": 4,
            "results": None,
            "capacity_fields": None,
        },
        "SH": {
            "code": "shunt",
            "name": "Shunt",
            "connect_field": ["bus"],
            "repair_time": 3,
            "results": "res_shunt",
            "capacity_fields": ["p_mw"],
        },
        "EG": {
            "code": "ext_grid",
            "name": "External Grid",
            "connect_field": ["bus"],
            "repair_time": 10,
            "results": "res_ext_grid",
            "capacity_fields": ["p_mw"],
        },
        "L": {
            "code": "line",
            "name": "Line",
            "connect_field": ["from_bus", "to_bus"],
            "repair_time": 5,
            "results": "res_line",
            "capacity_fields": ["p_from_mw"],
        },
        "LS": {
            "code": "line",
            "name": "Line",
            "connect_field": "from_bus",
            "repair_time": 5,
            "results": "res_line",
            "capacity_fields": ["p_from_mw"],
        },
        "TF": {
            "code": "trafo",
            "name": "Transformer",
            "connect_field": ["hv_bus", "lv_bus"],
            "repair_time": 10,
            "results": "res_trafo",
            "capacity_fields": ["p_hv_mw"],
        },
        "I": {
            "code": "impedance",
            "name": "Impedance",
            "connect_field": ["from_bus", "to_bus"],
            "repair_time": 5,
            "results": "res_impedance",
            "capacity_fields": ["p_from_mw"],
        },
        "DL": {
            "code": "dcline",
            "name": "DCLine",
            "connect_field": ["from_bus", "to_bus"],
            "repair_time": 3,
            "results": "res_dcline",
            "capacity_fields": ["p_from_mw"],
        },
    }
    return power_dict

def get_power_control_dict():
    pass

def load_power_network(network_json, sim_type="1ph"):
    """Loads the power system model from a json file.

    :param network_json: Location of the json power system file generated by pandapower package.
    :type network_json: string
    :param sim_type: Type of power flow simulation: '1ph': single phase, '3ph': three phase.
    :type sim_type: string
    :return: The loaded power system model object.
    :rtype: pandapower network object
    """
    pn = pp.from_json(network_json, convert=True)
    pn.sim_type = sim_type
    if sim_type == "1ph":
        print(
            "Power system successfully loaded from {}. Single phase power flow simulation will be used.\n".format(
                network_json
            )
        )
    elif sim_type == "3ph":
        print(
            "Power system successfully loaded from {}. Three phase power flow simulation will be used.\n".format(
                network_json
            )
        )
    return pn


def run_power_simulation(pn):
    """Runs the power flow model for an instance.

    :param pn: A power system model object generated by pandapower package.
    :type pn: pandapower network object
    """
    pp.runpp(pn)


def generate_base_supply(pn):
    pn_base = copy.deepcopy(pn)
    run_power_simulation(pn_base)
    return pn_base

    