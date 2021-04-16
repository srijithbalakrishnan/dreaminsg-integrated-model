import wntr

def get_water_dict():
    """Creates a dictionary of major water distribution system components.
    Used for naming automatically generated networks.

    Returns:
        [dictionary of string: string] -- Mapping of infrastructure component abbreviations to names.
    """
    water_dict = {
        "WP": ["Pump", "start_node_name"],
        "R": ["Reservoir", "name"],
        "P": ["Pipe", "start_node_name"],
        "J": ["Juntion", "name"],
        "T": ["Tank", "name"]
    }
    return water_dict

def load_water_network(network_inp):
    """Loads the water network model from an *.inp file.

    Arguments:
        network_inp {string} -- Location of the *.inp water network file.

    Returns:
        object -- The loaded water network model object
    """
    wn = wntr.network.WaterNetworkModel(network_inp)
    wn.options.hydraulic.demand_model = 'PDA' #Pressure dependent demand analysis
    print('Water network successfully loaded from {}. The analysis type is set to Pressure De[endent Demand Analysis.'.format(network_inp))
    return wn

def run_water_simulation(wn, hydraulic_timestep):
    """Runs the simulation for one time step.

    Arguments:
        wn {object} -- A water network model object
        hydraulic_timestep {integer} -- Length of one timestep in the water network simulation in seconds.

    Returns:
        object -- Collection of simulation result tables.
    """
    wn.options.time.hydraulic_timestep = hydraulic_timestep
    wn.options.time.report_timestep = hydraulic_timestep
    wn_sim = wntr.sim.WNTRSimulator(wn)
    wn_results = wn_sim.run_sim()
    return wn_results


