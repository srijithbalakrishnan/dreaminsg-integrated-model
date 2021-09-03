"""Functions to implement power systems simulations."""

import pandapower as pp


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
        },
        "BL": {
            "code": "bus",
            "name": "Bus connected to load",
            "connect_field": ["name"],
            "repair_time": 3,
        },
        "BS": {
            "code": "bus",
            "name": "Bus connected to switch",
            "connect_field": ["name"],
            "repair_time": 3,
        },
        "LO": {
            "code": "load",
            "name": "Load",
            "connect_field": ["bus"],
            "repair_time": 3,
        },
        "LOA": {
            "code": "asymmetric_load",
            "name": "Asymmetric Load",
            "connect_field": ["bus"],
            "repair_time": 3,
        },
        # Three phase electric motor is not compatible with pandapower, hence it is modeled as a load
        "LOMP": {
            "code": "load",
            "name": "Motor as Load",
            "connect_field": ["bus"],
            "repair_time": 3,
        },
        "SG": {
            "code": "sgen",
            "name": "Static Generator",
            "connect_field": ["bus"],
            "repair_time": 24,
        },
        "MP": {
            "code": "motor",
            "name": "Motor",
            "connect_field": ["bus"],
            "repair_time": 24,
        },
        "AL": {
            "code": "asymmetric_load",
            "name": "Asymmetric Load",
            "connect_field": ["bus"],
            "repair_time": 10,
        },
        "AS": {
            "code": "asymmetric_sgen",
            "name": "Asymmetric Static Generator",
            "connect_field": ["bus"],
            "repair_time": 10,
        },
        "ST": {
            "code": "storage",
            "name": "Storage",
            "connect_field": ["bus"],
            "repair_time": 5,
        },
        "G": {
            "code": "gen",
            "name": "Generator",
            "connect_field": ["bus"],
            "repair_time": 24,
        },
        "S": {
            "code": "switch",
            "name": "Switch",
            "connect_field": ["bus", "element"],
            "repair_time": 4,
        },
        "SH": {
            "code": "shunt",
            "name": "Shunt",
            "connect_field": ["bus"],
            "repair_time": 3,
        },
        "EG": {
            "code": "ext_grid",
            "name": "External Grid",
            "connect_field": ["bus"],
            "repair_time": 10,
        },
        "L": {
            "code": "line",
            "name": "Line",
            "connect_field": ["from_bus", "to_bus"],
            "repair_time": 3,
        },
        "LS": {
            "code": "line",
            "name": "Line",
            "connect_field": "from_bus",
            "repair_time": 3,
        },
        "TF": {
            "code": "trafo",
            "name": "Transformer",
            "connect_field": ["hv_bus", "lv_bus"],
            "repair_time": 10,
        },
        "TH": {
            "code": "trafo3w",
            "name": "Three Phase Transformer",
            "connect_field": ["hv_bus", "lv_bus"],
            "repair_time": 10,
        },
        "I": {
            "code": "impedance",
            "name": "Impedance",
            "connect_field": ["from_bus", "to_bus"],
            "repair_time": 5,
        },
        "DL": {
            "code": "dcline",
            "name": "DCLine",
            "connect_field": ["from_bus", "to_bus"],
            "repair_time": 3,
        },
    }
    return power_dict


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
    if pn.sim_type == "1ph":
        pn_sim = pp.runpp(pn)
    elif pn.sim_type == "3ph":
        pp.add_zero_impedance_parameters(pn)
        pn_sim = pp.runpp_3ph(pn)
