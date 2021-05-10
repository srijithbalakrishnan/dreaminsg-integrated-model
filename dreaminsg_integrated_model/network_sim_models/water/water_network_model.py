import wntr


# ---------------------------------------------------------#
#              Water network simulation functions         #
# ---------------------------------------------------------#


def get_water_dict():
    """Creates a dictionary of major water distribution system components.
    Used for naming automatically generated networks.

    Returns:
        [dictionary of string: string] -- Mapping of infrastructure component abbreviations to names.
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
        "J": {
            "code": "junctions",
            "name": "Junction",
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


def load_water_network(network_inp, initial_sim_step):
    """Loads the water network model from an *.inp file.

    Arguments:
        network_inp {string} -- Location of the *.inp water network file.

    Returns:
        object -- The loaded water network model object
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

    Arguments:
        wn {object} -- A water network model object
        hydraulic_timestep {integer} -- Length of one timestep in the water network simulation in seconds.

    Returns:
        object -- Collection of simulation result tables.
    """
    wn_sim = wntr.sim.WNTRSimulator(wn)
    wn_results = wn_sim.run_sim(
        convergence_error=True, solver_options={"MAXITER": 10000}
    )

    return wn_results
