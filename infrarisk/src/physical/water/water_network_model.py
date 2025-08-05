"""Functions to implement water network simulations."""

from pathlib import Path
import copy
import wntr

from infrarisk.src.cyber.sensor import WaterTankLevelSensor
from infrarisk.src.cyber.actuator import WaterPumpActuator, DischargePipeActuator
from infrarisk.src.cyber.controller import WaterController


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
        "PTV": {
            "code": "pipes",
            "name": "Tank Valve converted to Pipe",
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
        "JDP": {
            "code": "junctions",
            "name": "Discharge Pipe End Junction",
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


def get_water_control_dict():
    """Creates a dictionary of major water distribution system contol components.

    :return:  Mapping of control component abbreviations to names.
    :rtype: dictionary of string: string
    """
    water_control_dict = {
        "AWP": {
            "code": "pump",
            "name": "Pump Actuator",
            "repair_time": 5,
        },
        "AP": {
            "code": "pipe",
            "name": "Pipe Actuator",
            "repair_time": 5,
        },
        "ATDP": {
            "code": "tank discharge pipe",
            "name": "Tank Discharge Pipe Actuator",
            "repair_time": 5,
        },
        "SP": {
            "code": "pipe",
            "name": "Pipe Sensor",
            "repair_time": 5,
        },
        "SJ": {
            "code": "junction",
            "name": "Junction Sensor",
            "repair_time": 5,
        },
        "ST": {
            "code": "tank",
            "name": "Tank Level Sensor",
            "repair_time": 5,
        },
        "C": {
            "code": "controller",
            "name": "Water Controller",
            "repair_time": 5,
        },
    }

    return water_control_dict


def generate_pattern_interval_dict(wn):
    """_summary_

    :param wn: _description_
    :type wn: _type_
    """
    pattern_intervals = dict()
    for pattern in wn.pattern_name_list:
        pattern_intervals[pattern] = len(wn.get_pattern(pattern).multipliers)


def load_water_network(
    network_inp, water_sim_type, initial_sim_step, cyber_layer=False
):
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
        # wn.options.hydraulic.threshold_pressure = 20
        wn.options.time.duration = initial_sim_step
        wn.options.time.report_timestep = initial_sim_step
        wn.options.time.hydraulic_timestep = initial_sim_step
        wn.options.hydraulic.demand_model = water_sim_type

        wn.original_node_list = wn.node_name_list

        if water_sim_type not in ["DDA", "PDA"]:
            print("The given simulation type is not valid!")

        print(
            f"Water network successfully loaded from {network_inp}. The analysis type is set to {water_sim_type}."
        )
        print(
            f"initial simulation duration: {initial_sim_step}s; hydraulic time step: {initial_sim_step}s; pattern time step: 3600s\n"
        )

        if cyber_layer:
            wn.tank_level_dict = {tank_id: {} for tank_id in wn.tank_name_list}

            # set tank levels and add discharge pipes to tanks
            for tank in wn.tank_name_list:
                set_tank_levels(
                    wn,
                    tank,
                    tolerance=0.15  # assume 15% tolerance for tank levels on the lower and upper ends
                    * (wn.get_node(tank).max_level - wn.get_node(tank).min_level),
                )
                add_discharge_pipe(
                    wn, tank, elevation=wn.tank_level_dict[tank]["allow_capacity"][1]
                )

            # Initiate cyber systems
            wn.control_systems = {}
            wn.control_system_map = {}
            wn.tank_sensor_map = {}
            wn.pump_actuator_map = {}
            wn.tank_discharge_actuator_map = {}

        return wn
    except FileNotFoundError:
        print(
            "Error: The water network file does not exist. No such file or directory: ",
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


def add_discharge_pipe(wn, tank_id, elevation):
    """Adds a discharge pipe to the tank of interest.

    :param wn: Water network model object.
    :type wn: wntr water network object
    :param tank_id: The ID of the tank to which the discharge pipe is to be added.
    :type tank_id: string
    :param elevation: The elevation of the discharge pipe.
    :type elevation: float
    """
    tank = wn.get_node(tank_id)
    # x, y = tank.coordinates
    dp_index = tank_id.split("W_T")[1]

    wn.add_junction(
        f"W_JDP{dp_index}",
        base_demand=0.01,
        demand_pattern=None,
        elevation=elevation,
        coordinates=tank.coordinates,
        demand_category=None,
    )

    wn.add_pipe(
        f"W_PDP{dp_index}",
        tank_id,
        f"W_JDP{dp_index}",
        length=0.001,
        diameter=0.3048,
        roughness=0.001,
        minor_loss=0.0,
        status="OPEN",
    )


def set_tank_levels(wn, tank_id, tolerance, print_levels=False):
    """Sets the maximum and allowable range of water levels for the tank.

    :param wn: water network model object.
    :type wn: wntr water network object
    :param tank_id: Name of the tank (id).
    :type tank_id: string
    :param tolerance: The difference between maximum and allowable tank levels in meters.
    :type tolerance: float
    """

    tank_obj = wn.get_node(tank_id)

    abs_capacity = [
        round(tank_obj.elevation + tank_obj.min_level, 2),
        round(tank_obj.elevation + tank_obj.max_level, 2),
    ]
    wn.tank_level_dict[tank_id]["abs_capacity"] = abs_capacity

    allow_capacity = [
        abs_capacity[0] + tolerance,
        abs_capacity[1] - tolerance,
    ]
    wn.tank_level_dict[tank_id]["allow_capacity"] = allow_capacity
    wn.tank_level_dict[tank_id]["tank_level_tolerance"] = tolerance

    initial_level = round(tank_obj.elevation, 2) + tank_obj.min_level
    wn.tank_level_dict[tank_id]["initial_level"] = initial_level

    if print_levels:
        print(f"Tank {tank_id} maximum range of levels: ", abs_capacity)
        print(f"Tank {tank_id} allowable range of levels: ", allow_capacity)
        print(f"Tank {tank_id} initial level: ", initial_level)


def add_tank_level_sensor_system(wn, controller_id, list_of_tanks):
    """Adds a sensor system to the water network.

    :param wn: Water network model object.
    :type wn: wntr water network object
    :param controller_id: The ID of the controller to which the sensor system is to be added.
    :type controller_id: string
    :param list_of_tanks: List of tank IDs for which tank level sensors are to be assigned.
    :type list_of_tanks: list
    """

    # add tank level sensors to check over-flow or under-flow
    if controller_id in wn.control_systems.keys():
        for tank in list_of_tanks:
            tank_obj = wn.get_node(tank)
            wn.control_systems[controller_id]._tank_level_sensors[
                tank
            ] = WaterTankLevelSensor(
                tank_id=tank,
                controller_id=controller_id,
                name=f"Tank Level Sensor {tank}",
                status=1,
            )
            wn.control_systems[controller_id]._tank_level_sensors[
                tank
            ].set_tank_thresholds(
                min_level=tank_obj.min_level
                + wn.tank_level_dict[tank]["tank_level_tolerance"],
                max_level=tank_obj.max_level
                - wn.tank_level_dict[tank]["tank_level_tolerance"],
            )

            wn.tank_sensor_map[tank] = controller_id
    else:
        print("The control system does not exist!")


def add_pump_actuator_system(wn, controller_id, list_of_pumps):
    """Adds a pump actuator system to the water network.

    :param wn: Water network model object.
    :type wn: wntr water network object
    """

    if controller_id in wn.control_systems.keys():
        for pump in list_of_pumps:
            wn.control_systems[controller_id]._pump_actuators[pump] = WaterPumpActuator(
                pump_id=pump,
                controller_id=controller_id,
                name=f"Pump Actuator {pump}",
                status=1,
            )
            wn.control_systems[controller_id]._pump_actuators[pump].turn_off_pump(wn, 0)

            wn.pump_actuator_map[pump] = controller_id
    else:
        print("The control system does not exist!")


def add_discharge_pipe_actuator_system(wn, controller_id, list_of_tanks):
    """Adds a discharge pipe actuator system to the water network.

    :param wn: Water network model object.
    :type wn: wntr water network object
    """

    if controller_id in wn.control_systems.keys():
        for tank in list_of_tanks:
            wn.control_systems[controller_id]._tank_discharge_actuators[
                tank
            ] = DischargePipeActuator(
                tank_id=tank,
                controller_id=controller_id,
                name=f"Discharge Pipe Actuator {tank}",
                status=1,
            )
        wn.control_systems[controller_id]._tank_discharge_actuators[
            tank
        ].turn_off_discharge(wn, 0)
        wn.tank_discharge_actuator_map[tank] = controller_id
    else:
        print("The control system does not exist!")


def add_control_system(wn, list_of_tanks, list_of_pumps, controller_id=None):
    """Adds a controller system to the water network.

    :param wn: Water network model object.
    :type wn: wntr water network object
    :param list_of_tanks: List of tanks controlled by the controller system.
    :type list_of_tanks: list
    :param list_of_pumps: List of pumps controlled by the controller system.
    :type list_of_pumps: list
    :param id: The ID of the controller to be added.
    :type id: integer
    """
    for control in wn.control_name_list:
        wn.remove_control(control)

    if controller_id is None:
        id = "W_CS" + str(wn.control_systems.keys().__len__())
    else:
        id = controller_id

    print(f"Adding control system {id}")
    wn.control_systems[id] = WaterController(id=id, name="Controller")

    print("Adding tank level sensor system...")
    add_tank_level_sensor_system(wn, controller_id=id, list_of_tanks=list_of_tanks)

    print("Adding pump actuator system...")
    add_pump_actuator_system(wn, controller_id=id, list_of_pumps=list_of_pumps)

    print("Adding tank discharge pipe actuator system...")
    add_discharge_pipe_actuator_system(
        wn, controller_id=id, list_of_tanks=list_of_tanks
    )


def add_universal_control_system(wn, controller_id=None):
    """Adds single control system to the water network.

    :param wn: Water network model object.
    :type wn: wntr water network object
    """
    for control in wn.control_name_list:
        wn.remove_control(control)

    if wn.control_systems.keys().__len__() == 0:
        if controller_id is None:
            id = "W_CS" + str(wn.control_systems.keys().__len__())
        else:
            id = controller_id

        print(f"Adding universal control system {id}")
        wn.control_systems[id] = WaterController(id=id, name="Controller")

        print("Adding tank level sensor system...")
        add_tank_level_sensor_system(
            wn, controller_id=id, list_of_tanks=wn.tank_name_list
        )
        print("Adding pump actuator system...")
        add_pump_actuator_system(wn, controller_id=id, list_of_pumps=wn.pump_name_list)
        print("Adding tank discharge pipe actuator system...")
        add_discharge_pipe_actuator_system(
            wn, controller_id=id, list_of_tanks=wn.tank_name_list
        )
        print("Successfully added universal control system!")
    else:
        print(
            "Control system already exists! Please remove the controllers first and try again."
        )


def set_initial_control_system_status(
    wn, actuator_status=1, sensor_status=1, controller_status=1
):
    """Sets the initial status of the control system components (sensors, actuators, and sensors).

    :param wn: Water network model object.
    :type wn: wntr water network object
    :param actuator_status: Initial status of the actuators, defaults to 1
    :type actuator_status: int, optional
    :param sensor_status: Initial status of the sensors, defaults to 1
    :type sensor_status: int, optional
    :param controller_status: Initial status of the controller, defaults to 1
    :type controller_status: int, optional
    """
    for cs_id in wn.control_systems:
        wn.control_systems[cs_id]._status = controller_status
        for sensor_id in wn.control_systems[cs_id]._tank_level_sensors:
            wn.control_systems[cs_id]._tank_level_sensors[
                sensor_id
            ]._status = sensor_status
        for actuator_id in wn.control_systems[cs_id]._pump_actuators:
            wn.control_systems[cs_id]._pump_actuators[
                actuator_id
            ]._status = actuator_status
        for actuator_id in wn.control_systems[cs_id]._tank_discharge_actuators:
            wn.control_systems[cs_id]._tank_discharge_actuators[
                actuator_id
            ]._status = actuator_status


def set_tl_sensor_ef(wn, tank_id, error_factor):
    """Sets the error factor for the tank level sensor. A value of 1 means no error.

    :param wn: Water network model object.
    :type wn: wntr water network object
    :param tank_id: Tank ID.
    :type tank_id: str
    :param error_factor: Error factor.
    :type error_factor: float
    """
    controller_id = wn.tank_sensor_map[tank_id]

    wn.control_systems[controller_id]._tank_level_sensors[
        tank_id
    ]._error_factor = error_factor


def get_valves_to_isolate_water_node(integrated_network, node):
    # The function 'valve_identification' identifies all the valves that need to be closed in order to isolate a given NODE
    segment, explored_nodes = [], []
    explored_nodes.append(node)
    if node in [
        y[0] for y in valves_se
    ]:  # if the node is the start node of a valve, add that valve to the segment
        j = [y[0] for y in valves_se].index(node)
        segment.append(valves[j])
    else:
        if node in [
            y[1] for y in valves_se
        ]:  # if the node is the end node of a valve, add that valve to the segment
            j = [y[1] for y in valves_se].index(node)
            segment.append(valves[j])
        else:
            connected_pipes = [x for x in G_water.edges(node)]
            connected_nodes = []
            for c in connected_pipes:
                unexplored_node = list(filter(lambda x: x not in explored_nodes, c))
                if unexplored_node != []:
                    connected_nodes.append(
                        unexplored_node[0]
                    )  # consider all nodes connected to the node by a pipe (but not that node)
            if (
                connected_nodes != []
            ):  # if connected_nodes == 0, then the node is a peripheral node
                for k in connected_nodes:
                    valve_identification(k, segment, explored_nodes)
