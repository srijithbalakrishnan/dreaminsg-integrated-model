"""Functions to implement the various steps of the interdependent infrastructure network simulations."""

import pandas as pd
from pathlib import Path
import os

import dreaminsg_integrated_model.src.network_sim_models.interdependencies as interdependencies
import dreaminsg_integrated_model.src.disrupt_generator as disrupt_generator
import dreaminsg_integrated_model.src.network_sim_models.water.water_network_model as water
import dreaminsg_integrated_model.src.network_sim_models.power.power_system_model as power
import dreaminsg_integrated_model.src.network_sim_models.transportation.network as transpo
import dreaminsg_integrated_model.src.plots as model_plots


def load_networks(water_file, power_file, transp_folder):
    """Loads the water, power and transportation networks.

    :param water_file: The water network file (*.inp).
    :type water_file: string
    :param power_file: The power systems file (*.json).
    :type power_file: string
    :param transp_folder: The local directory that consists of required transportation network files.
    :type transp_folder: string
    :return: The water, powrr and transportation networks ready for simulation.
    :rtype: objects
    """
    # load water_network model
    try:
        initial_sim_step = 60
        wn = water.load_water_network(water_file, initial_sim_step)
        wn.total_base_water_demand = sum(
            [wn.get_node(node).base_demand for node in wn.junction_name_list]
        )
    except FileNotFoundError:
        print(
            "Error: The water network file does not exist. No such file or directory: ",
            water_file,
        )

    # load power systems network
    try:
        pn = power.load_power_network(power_file)
        power.run_power_simulation(pn)
        pn.total_base_power_demand = pn.res_load.p_mw.sum() + pn.res_motor.p_mw.sum()
    except UserWarning:
        print(
            "Error: The power systems file does not exist. No such file or directory: ",
            power_file,
        )

    # load dynamic traffic assignment model
    try:
        tn = transpo.Network(
            f"{transp_folder}/example_net.tntp",
            f"{transp_folder}/example_trips.tntp",
            f"{transp_folder}/example_node.tntp",
        )
        print(
            f"Transportation network successfully loaded from {transp_folder}. Static traffic assignment method will be used to calculate travel times."
        )
        tn.userEquilibrium("FW", 400, 1e-4, tn.averageExcessCost)

        return wn, pn, tn
    except FileNotFoundError:
        print(
            f"Error: The transportation network folder does not exist. No such directory: {transp_folder}."
        )
    except AttributeError:
        print("Error: Some required network files not found.")


def build_power_water_dependencies(dependency_table, dependency_file):
    """Adds the power-water dependency table to the DependencyTable object.

    :param dependency_table: The object that contains information related to the dependencies in the network.
    :type dependency_table: DependencyTable object
    :param dependency_file: The location of the dependency file containing dependency information.
    :type dependency_file: string
    :return: The modified dependency table object.
    :rtype: DependencyTable object
    """
    try:
        dependency_data = pd.read_csv(dependency_file, sep=",")
        for index, row in dependency_data.iterrows():
            water_id = row["water_id"]
            power_id = row["power_id"]
            (
                water_infra,
                water_notation,
                water_code,
                water_full,
            ) = interdependencies.get_compon_details(water_id)
            (
                power_infra,
                power_notation,
                power_code,
                power_full,
            ) = interdependencies.get_compon_details(power_id)
            if (water_full == "Pump") & (power_full == "Motor"):
                dependency_table.add_pump_motor_coupling(
                    water_id=water_id, power_id=power_id
                )
            elif (water_full == "Reservoir") & (power_full == "Generator"):
                dependency_table.add_gen_reserv_coupling(
                    water_id=water_id, power_id=power_id
                )
            else:
                print(
                    f"Cannot create dependency between {water_id} and {power_id}. Check the component names and types."
                )
        return dependency_table
    except FileNotFoundError:
        print(
            "Error: The infrastructure dependency data file does not exist. No such file or directory: ",
            dependency_file,
        )


def build_transportation_access(dependency_table, integrated_graph):
    """Adds the transportatio naccess table to the DependencyTabl object.

    :param dependency_table: The object that contains information related to the dependencies in the network.
    :type dependency_table: DependencyTable object
    :param integrated_graph: The integrated network as networkx object.
    :type integrated_graph: nextworkx object
    :return: The modified dependency table object.
    :rtype: DependencyTable object
    """
    dependency_table.add_transpo_access(integrated_graph)
    return dependency_table


def schedule_component_repair(disaster_recovery_object, integrated_graph, pn, wn, tn):
    """Optimizes the repair action order and schedules the actions in the event table.

    :param disaster_recovery_object: The object that consists of information related to disruptions and repair actions.
    :type disaster_recovery_object: DisasterAndRecovery object
    :param integrated_graph: The integrated network as networkx object.
    :type integrated_graph: nextworkx object
    :param pn: Power systems object.
    :type pn: pandapower network object
    :param wn: Water network object.
    :type wn: wntr network object
    :param tn: Transportation network object.
    :type tn: traffic network object
    """
    repair_order = disaster_recovery_object.optimze_recovery_strategy()
    print(
        f"The optimised repair strategy is to schedule repair of failed components in the following order: {repair_order}\n"
    )
    disaster_recovery_object.schedule_recovery(
        integrated_graph, wn, pn, tn, repair_order
    )


def expand_event_table(disaster_recovery_object, initial_sim_step, add_points):
    """Expands the event table with additional time_stamps for simulation.

    :param disaster_recovery_object: The object that consists of information related to disruptions and repair actions.
    :type disaster_recovery_object: DisasterAndRecovery object
    :param initial_sim_step: The initial size of time_step in seconds.
    :type initial_sim_step: integer
    :param add_points: A positive integer denoting the number of extra time-stamps to be added to the simulation.
    :type add_points: integer
    """
    compon_list = disaster_recovery_object.event_table.components.unique()
    full_time_list = disaster_recovery_object.event_table.time_stamp.unique()
    interval_approx = (full_time_list[-1] - full_time_list[0]) / add_points
    act_interval = int(initial_sim_step * round(interval_approx / initial_sim_step))

    new_range = range(full_time_list[0], full_time_list[-1], act_interval)
    new_time_stamps = [time_stamp for time_stamp in new_range]

    for time in full_time_list:
        disrupt_components = list(disaster_recovery_object.disrupted_components)
        curr_components = list(
            disaster_recovery_object.event_table[
                disaster_recovery_object.event_table.time_stamp == time
            ].components
        )
        components_to_add = [
            i
            for i in disrupt_components + curr_components
            if i not in disrupt_components or i not in curr_components
        ]
        for i, compon in enumerate(components_to_add):
            compon_time_list = disaster_recovery_object.event_table[
                disaster_recovery_object.event_table.components == compon
            ].time_stamp.unique()
            maxless = max(compon_time_list[compon_time_list <= time])
            perf_level = disaster_recovery_object.event_table[
                (disaster_recovery_object.event_table.components == compon)
                & (disaster_recovery_object.event_table.time_stamp == maxless)
            ].perf_level.values[0]
            perf_state = disaster_recovery_object.event_table[
                (disaster_recovery_object.event_table.components == compon)
                & (disaster_recovery_object.event_table.time_stamp == maxless)
            ].component_state.values[0]
            disaster_recovery_object.event_table = (
                disaster_recovery_object.event_table.append(
                    {
                        "time_stamp": time,
                        "components": compon,
                        "perf_level": perf_level,
                        "component_state": perf_state,
                    },
                    ignore_index=True,
                )
            )

    for compon in compon_list:
        compon_time_list = disaster_recovery_object.event_table[
            disaster_recovery_object.event_table.components == compon
        ].time_stamp.unique()
        for time in new_time_stamps:
            if time not in compon_time_list:
                maxless = max(compon_time_list[compon_time_list <= time])
                perf_level = disaster_recovery_object.event_table[
                    (disaster_recovery_object.event_table.components == compon)
                    & (disaster_recovery_object.event_table.time_stamp == maxless)
                ].perf_level.values[0]
                perf_state = disaster_recovery_object.event_table[
                    (disaster_recovery_object.event_table.components == compon)
                    & (disaster_recovery_object.event_table.time_stamp == maxless)
                ].component_state.values[0]
                disaster_recovery_object.event_table = (
                    disaster_recovery_object.event_table.append(
                        {
                            "time_stamp": time,
                            "components": compon,
                            "perf_level": perf_level,
                            "component_state": perf_state,
                        },
                        ignore_index=True,
                    )
                )
    disaster_recovery_object.event_table.sort_values(by=["time_stamp"], inplace=True)
    disaster_recovery_object.event_table["time_stamp"] = (
        disaster_recovery_object.event_table["time_stamp"]
        + disaster_recovery_object.sim_step
    )


def simulate_interdependent_effects(
    disaster_recovery_object, dependency_table, pn, wn, tn
):
    """Simulates the interdependent effect based on the initial disruptions and subsequent repair actions.

    :param disaster_recovery_object: The object that consists of information related to disruptions and repair actions.
    :type disaster_recovery_object: DisasterAndRecovery object
    :param dependency_table: The object that contains information related to the dependencies in the network.
    :type dependency_table: DependencyTable object
    :param pn: Power systems object.
    :type pn: pandapower network object
    :param wn: Water network object.
    :type wn: wntr network object
    :param tn: Transportation network object.
    :type tn: traffic network object
    :return: lists of time stamps and resilience values of power and water supply.
    :rtype: lists
    """
    # modify water network to induce leaks
    wn = disrupt_generator.pipe_leak_node_generator(wn, disaster_recovery_object)

    power_consump_tracker = []
    water_consump_tracker = []
    time_tracker = []

    unique_time_stamps = sorted(
        list(disaster_recovery_object.event_table.time_stamp.unique())
    )
    print(unique_time_stamps)

    unique_time_differences = [
        x - unique_time_stamps[i - 1] for i, x in enumerate(unique_time_stamps)
    ][1:]

    for index, time_stamp in enumerate(unique_time_stamps[:-1]):
        print(f"\nSimulating network conditions at {time_stamp} s")

        print(
            "Simulation time: ",
            wn.options.time.duration,
            "; Hydraulic time step: ",
            wn.options.time.hydraulic_timestep,
            "; Report time step: ",
            wn.options.time.report_timestep,
        )

        # update performance of directly affected components
        disaster_recovery_object.update_directly_affected_components(
            pn,
            wn,
            wn.options.time.duration,
            wn.options.time.duration + unique_time_differences[index],
        )

        # run power systems model
        power.run_power_simulation(pn)

        # update networkwide effects
        dependency_table.update_dependencies(
            pn,
            wn,
            wn.options.time.duration,
            wn.options.time.duration + unique_time_differences[index],
        )

        # run water network model and print results
        wn_results = water.run_water_simulation(wn)
        print(wn_results.link["status"])
        print(wn_results.node["demand"])
        print(wn_results.node["leak_demand"])

        print(
            "Pump: ",
            "\t\tstatus = ",
            wn_results.link["status"]["W_WP9"].values,
            "\tflowrate = ",
            wn_results.link["flowrate"]["W_WP9"].values,
        )
        print(
            "Tank: ",
            "\t\tdemand",
            wn_results.node["demand"]["W_T2"].values,
            "\thead = ",
            wn_results.node["head"]["W_T2"].values,
        )
        print(
            "Pipe from Tank: ",
            "status",
            wn_results.link["status"]["W_P110"].values,
            "\tflowrate = ",
            wn_results.link["flowrate"]["W_P110"].values,
        )
        print("******************\n")

        # track results
        time_tracker.append((time_stamp) / 60)  # minutes
        power_consump_tracker.append(
            (pn.res_load.p_mw.sum() + pn.res_motor.p_mw.sum())
            / pn.total_base_power_demand
        )
        water_consump_tracker.append(
            sum(
                [
                    list(wn_results.node["demand"][node])[0]
                    for node in wn.junction_name_list
                ]
            )
            / wn.total_base_water_demand
        )

        # Fix the time until which the wntr model should run in this iteration
        if index < len(unique_time_stamps) - 1:
            wn.options.time.duration += unique_time_differences[index]
            wn.options.time.report_timestep += unique_time_differences[index]

        print(f"Simulation for time {time_stamp / 60} minutes completed successfully")
    return time_tracker, power_consump_tracker, water_consump_tracker


def write_results(
    time_tracker, power_consump_tracker, water_consump_tracker, location, plotting=False
):
    """Write the results to local directory.

    :param time_tracker: List of time stamps.
    :type time_tracker: list of integers
    :param power_consump_tracker: List of corresponding power resilience metric value.
    :type power_consump_tracker: list of floats
    :param water_consump_tracker: List of corresponding water resilience metric value.
    :type water_consump_tracker: list of floats
    :param location: The location to which the results are to be saved.
    :type location: string
    :param plotting: True if the plots are to be generated., defaults to False
    :type plotting: bool, optional
    """
    results_df = pd.DataFrame(
        {
            "time_min": time_tracker,
            "power_perf": power_consump_tracker,
            "water_perf": water_consump_tracker,
        }
    )
    if not os.path.exists(f"{location}/results"):
        os.makedirs(f"{location}/results")

    results_df.to_csv(Path(location) / "results/network_performance.csv", sep="\t")
    print(f"The simulation results successfully saved to {Path(location)}")

    if plotting == True:
        model_plots.plot_interdependent_effects(
            power_consump_tracker, water_consump_tracker, time_tracker
        )
