"""Functions to implement water network simulations."""

import wntr


def get_water_dict():
    """Creates a dictionary of major water distribution system components. Used for naming automatically generated networks.

    :return:  Mapping of infrastructure component abbreviations to names.
    :rtype: dictionary of string: string
    """
    water_dict = {
        "WP": {
            "code": "pumps",
            "name": "Pump",
            "connect_field": "start_node_name",
            "repair_time": 10,
        },
        "R": {
            "code": "reservoirs",
            "name": "Reservoir",
            "connect_field": "name",
            "repair_time": 24,
        },
        "P": {
            "code": "pipes",
            "name": "Pipe",
            "connect_field": "start_node_name",
            "repair_time": 12,
        },
        "PSC": {
            "code": "pipes",
            "name": "Service Connection Pipe",
            "connect_field": "start_node_name",
            "repair_time": 4,
        },
        "PMA": {
            "code": "pipes",
            "name": "Main Pipe",
            "connect_field": "start_node_name",
            "repair_time": 2,
        },
        "PHC": {
            "code": "pipes",
            "name": "Hydrant Connection Pipe",
            "connect_field": "start_node_name",
            "repair_time": 4,
        },
        "PV": {
            "code": "pipes",
            "name": "Valve converted to Pipe",
            "connect_field": "start_node_name",
            "repair_time": 2,
        },
        "J": {
            "code": "junctions",
            "name": "Junction",
            "connect_field": "name",
            "repair_time": 5,
        },
        "JIN": {
            "code": "junctions",
            "name": "Intermmediate Junction",
            "connect_field": "name",
            "repair_time": 5,
        },
        "JVN": {
            "code": "junctions",
            "name": "Valve Junction",
            "connect_field": "name",
            "repair_time": 5,
        },
        "JTN": {
            "code": "junctions",
            "name": "Terminal Junction",
            "connect_field": "name",
            "repair_time": 5,
        },
        "JHY": {
            "code": "junctions",
            "name": "Hydrant Junction",
            "connect_field": "name",
            "repair_time": 5,
        },
        "T": {
            "code": "tanks",
            "name": "Tank",
            "connect_field": "name",
            "repair_time": 24,
        },
    }
    return water_dict


def generate_pattern_interval_dict(wn):
    pattern_intervals = dict()
    for pattern in wn.pattern_name_list:
        pattern_intervals[pattern] = len(wn.get_pattern(pattern).multipliers)


def load_water_network(network_inp, initial_sim_step):
    """Loads the water network model from an inp file.

    :param network_inp: Location of the inp water network file.
    :type network_inp: string
    :param initial_sim_step: The initial iteration step size in seconds.
    :type initial_sim_step: integer
    :return: The loaded water wntr network object.
    :rtype: wntr network object
    """
    wn = wntr.network.WaterNetworkModel(network_inp)
    wn.options.time.duration = initial_sim_step
    wn.options.time.report_timestep = initial_sim_step
    wn.options.time.hydraulic_timestep = initial_sim_step
    wn.options.hydraulic.demand_model = "PDA"
    print(
        "Water network successfully loaded from {}. The analysis type is set to Pressure Dependent Demand Analysis.".format(
            network_inp
        )
    )
    print(
        "initial simulation duration: {0}s; hydraulic time step: {0}s; pattern time step: 3600s\n".format(
            initial_sim_step
        )
    )
    return wn


def run_water_simulation(wn):
    """Runs the simulation for one time step.

    :param wn: Water network model object.
    :type wn: wntr water network object
    :return: Simulation results in pandas tables.
    :rtype: ordered dictionary of string: pandas table
    """
    wn_sim = wntr.sim.WNTRSimulator(wn)
    wn_results = wn_sim.run_sim(
        convergence_error=True, solver_options={"MAXITER": 10000}
    )

    return wn_results
