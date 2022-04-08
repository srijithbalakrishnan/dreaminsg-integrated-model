"""Functions to implement water network simulations."""

from pathlib import Path
import copy
import wntr


def get_water_dict():
    """Creates a dictionary of major water distribution system components.

    :return:  Mapping of infrastructure component abbreviations to names.
    :rtype: dictionary of string: string
    """
    water_dict = {
        "WP": {
            "code": "pumps",
            "name": "Pump",
            "connect_field": ["start_node_name", "end_node_name"],
            "repair_time": 12,
            "results": "link",
        },
        "R": {
            "code": "reservoirs",
            "name": "Reservoir",
            "connect_field": ["name"],
            "repair_time": 24,
            "results": "node",
        },
        "P": {
            "code": "pipes",
            "name": "Pipe",
            "connect_field": ["start_node_name", "end_node_name"],
            "repair_time": 12,
            "results": "link",
        },
        "PSC": {
            "code": "pipes",
            "name": "Service Connection Pipe",
            "connect_field": ["start_node_name", "end_node_name"],
            "repair_time": 2,
            "results": "link",
        },
        "PMA": {
            "code": "pipes",
            "name": "Main Pipe",
            "connect_field": ["start_node_name", "end_node_name"],
            "repair_time": 12,
            "results": "link",
        },
        "PHC": {
            "code": "pipes",
            "name": "Hydrant Connection Pipe",
            "connect_field": ["start_node_name", "end_node_name"],
            "repair_time": 4,
            "results": "link",
        },
        "PV": {
            "code": "pipes",
            "name": "Valve converted to Pipe",
            "connect_field": ["start_node_name", "end_node_name"],
            "repair_time": 2,
            "results": "link",
        },
        "J": {
            "code": "junctions",
            "name": "Junction",
            "connect_field": ["name"],
            "repair_time": 5,
            "results": "node",
        },
        "JIN": {
            "code": "junctions",
            "name": "Intermmediate Junction",
            "connect_field": ["name"],
            "repair_time": 5,
            "results": "node",
        },
        "JVN": {
            "code": "junctions",
            "name": "Valve Junction",
            "connect_field": ["name"],
            "repair_time": 5,
        },
        "JTN": {
            "code": "junctions",
            "name": "Terminal Junction",
            "connect_field": ["name"],
            "repair_time": 5,
            "results": "node",
        },
        "JHY": {
            "code": "junctions",
            "name": "Hydrant Junction",
            "connect_field": ["name"],
            "repair_time": 5,
            "results": "node",
        },
        "T": {
            "code": "tanks",
            "name": "Tank",
            "connect_field": ["name"],
            "repair_time": 24,
            "results": "node",
        },
    }
    return water_dict


def generate_pattern_interval_dict(wn):
    pattern_intervals = dict()
    for pattern in wn.pattern_name_list:
        pattern_intervals[pattern] = len(wn.get_pattern(pattern).multipliers)


def load_water_network(network_inp, water_sim_type, initial_sim_step):
    """Loads the water network model from an inp file.

    :param network_inp: Location of the inp water network file.
    :type network_inp: string
    :param water_sim_type: The type of water simulation in wntr. Available options are pressure-dependent demand analysis ('PDA') and demand driven analysis ('DDA').
    :type network_inp: string
    :param initial_sim_step: The initial iteration step size in seconds.
    :type initial_sim_step: integer
    :return: The loaded water wntr network object.
    :rtype: wntr network object
    """
    try:
        wn = wntr.network.WaterNetworkModel(network_inp)
        wn.options.hydraulic.required_pressure = 30
        wn.options.hydraulic.minimum_pressure = 0
        wn.options.hydraulic.threshold_pressure = 20
        wn.options.time.duration = initial_sim_step
        wn.options.time.report_timestep = initial_sim_step
        wn.options.time.hydraulic_timestep = initial_sim_step
        wn.options.hydraulic.demand_model = water_sim_type
        if water_sim_type not in ["DDA", "PDA"]:
            print("The given simulation type is not valid!")

        print(
            f"Water network successfully loaded from {network_inp}. The analysis type is set to {water_sim_type}."
        )
        print(
            "initial simulation duration: {0}s; hydraulic time step: {0}s; pattern time step: 3600s\n".format(
                initial_sim_step
            )
        )
        return wn
    except FileNotFoundError:
        print(
            f"Error: The water network file does not exist. No such file or directory: ",
            network_inp,
        )


def run_water_simulation(wn):
    """Runs the simulation for one time step.

    :param wn: Water network model object.
    :type wn: wntr water network object
    :return: Simulation results in pandas tables.
    :rtype: ordered dictionary of string: pandas table
    """
    # print(wn.control_name_list)
    wn_sim = wntr.sim.WNTRSimulator(wn)
    wn_results = wn_sim.run_sim(
        convergence_error=True, solver_options={"MAXITER": 10000}
    )

    return wn_results


def generate_base_supply(wn_original, directory):
    """Runs demand driven simulation (DDA) simulation under normal network conditions and stores the node demands.

    :param wn: Water network model object.
    :type wn: wntr water network object
    :param directory: The directory to which the node demands are to be saved.
    :type directory: string
    """
    wn = copy.deepcopy(wn_original)
    wn.options.time.duration = 3600 * 24
    wn.options.time.report_timestep = 60
    wn.options.time.hydraulic_timestep = 60
    wn.options.hydraulic.demand_model = "DDA"
    wn.options.hydraulic.required_pressure = 30
    wn.options.hydraulic.minimum_pressure = 0

    wn_sim = wntr.sim.WNTRSimulator(wn)
    wn_results = wn_sim.run_sim(
        convergence_error=True, solver_options={"MAXITER": 10000}
    )
    base_node_supply_df = wn_results.node["demand"][wn.node_name_list]
    base_node_supply_df["time"] = base_node_supply_df.index
    base_node_supply_df["time"] = base_node_supply_df["time"].astype(int)
    base_node_supply_df.to_csv(
        Path(directory) / "base_water_node_supply.csv", index=False
    )

    base_link_flow_df = wn_results.link["flowrate"][wn.link_name_list]
    base_link_flow_df["time"] = base_link_flow_df.index
    base_link_flow_df["time"] = base_link_flow_df["time"].astype(int)
    base_link_flow_df.to_csv(Path(directory) / "base_water_link_flow.csv", index=False)


def generate_base_supply_pda(wn_original, dir):
    """Runs pressure-dependent demand simulation (PDA) simulation under normal network conditions and stores the node demands.

    :param wn: Water network model object.
    :type wn: wntr water network object
    :param dir: The directory to which the node demands are to be saved.
    :type dir: string
    """
    wn = copy.deepcopy(wn_original)
    wn.options.time.duration = 3600 * 24
    wn.options.time.report_timestep = 60
    wn.options.time.hydraulic_timestep = 60
    wn.options.hydraulic.demand_model = "PDA"
    wn.options.hydraulic.required_pressure = 30
    wn.options.hydraulic.minimum_pressure = 0

    wn_sim = wntr.sim.WNTRSimulator(wn)
    wn_results = wn_sim.run_sim(
        convergence_error=True, solver_options={"MAXITER": 10000}
    )
    base_node_supply_df = wn_results.node["demand"][wn.node_name_list]
    base_node_supply_df["time"] = base_node_supply_df.index
    base_node_supply_df["time"] = base_node_supply_df["time"].astype(int)
    base_node_supply_df.to_csv(
        Path(dir) / "base_water_node_supply_pda.csv",
        index=False,
    )

    base_link_flow_df = wn_results.link["flowrate"][wn.link_name_list]
    base_link_flow_df["time"] = base_link_flow_df.index
    base_link_flow_df["time"] = base_link_flow_df["time"].astype(int)
    base_link_flow_df.to_csv(
        Path(dir) / "base_water_link_flow_pda.csv",
        index=False,
    )


# def get_valves_to_isolate_water_node(integrated_network, node):
#     # The function 'valve_identification' identifies all the valves that need to be closed in order to isolate a given NODE
#     segment, explored_nodes = [], []
#     explored_nodes.append(node)
#     if node in [
#         y[0] for y in valves_se
#     ]:  # if the node is the start node of a valve, add that valve to the segment
#         j = [y[0] for y in valves_se].index(node)
#         segment.append(valves[j])
#     else:
#         if node in [
#             y[1] for y in valves_se
#         ]:  # if the node is the end node of a valve, add that valve to the segment
#             j = [y[1] for y in valves_se].index(node)
#             segment.append(valves[j])
#         else:
#             connected_pipes = [x for x in G_water.edges(node)]
#             connected_nodes = []
#             for c in connected_pipes:
#                 unexplored_node = list(filter(lambda x: x not in explored_nodes, c))
#                 if unexplored_node != []:
#                     connected_nodes.append(
#                         unexplored_node[0]
#                     )  # consider all nodes connected to the node by a pipe (but not that node)
#             if (
#                 connected_nodes != []
#             ):  # if connected_nodes == 0, then the node is a peripheral node
#                 for k in connected_nodes:
#                     valve_identification(k, segment, explored_nodes)
