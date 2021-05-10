import pandas as pd
from pathlib import Path

from dreaminsg_integrated_model.network_sim_models.interdependencies import *
import dreaminsg_integrated_model.network_sim_models.water.water_network_model as water
import dreaminsg_integrated_model.network_sim_models.power.power_system_model as power
import dreaminsg_integrated_model.network_sim_models.transportation.network as transpo
from dreaminsg_integrated_model.data.disruptive_scenarios.disrupt_generator_discrete import *
import dreaminsg_integrated_model.results.figures.plots as plots


def load_networks(water_file, power_file, transp_folder):
    """Loads the water, power and transportation networks

    Arguments:
        water_file {string} -- The water network file (*.inp).
        power_file {string} -- The power systems file (*.json).
        transp_folder {string} -- The local directory that consists of required transportation network files.

    Returns:
        objects -- The water, powrr and transportation networks ready for simulation.
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
    """[summary]

    Arguments:
        dependency_table {[type]} -- [description]
        dependency_file {[type]} -- [description]

    Returns:
        [type] -- [description]
    """
    try:
        dependency_data = pd.read_csv(dependency_file, sep=",")
        for index, row in dependency_data.iterrows():
            water_id = row["water_id"]
            power_id = row["power_id"]
            water_infra, water_notation, water_code, water_full = get_compon_details(
                water_id
            )
            power_infra, power_notation, power_code, power_full = get_compon_details(
                power_id
            )
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
    """[summary]

    Arguments:
        dependency_table {[type]} -- [description]
        integrated_graph {[type]} -- [description]

    Returns:
        [type] -- [description]
    """
    dependency_table.add_transpo_access(integrated_graph)
    return dependency_table


def schedule_component_repair(disaster_recovery_object, integrated_graph, pn, wn, tn):
    """[summary]

    Arguments:
        disaster_recovery_object {[type]} -- [description]
        integrated_graph {[type]} -- [description]
        pn {[type]} -- [description]
        wn {[type]} -- [description]
        tn {[type]} -- [description]
    """
    repair_order = disaster_recovery_object.optimze_recovery_strategy()
    print(
        f"The optimised repair strategy is to schedule repair of failed components in the following order: {repair_order}\n"
    )
    disaster_recovery_object.schedule_recovery(
        integrated_graph, wn, pn, tn, repair_order
    )


def expand_event_table(disaster_recovery_object, initial_sim_step, add_points):
    """[summary]

    Arguments:
        disaster_recovery_object {[type]} -- [description]
        initial_sim_step {[type]} -- [description]
        add_points {[type]} -- [description]
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


def simulate_interdependent_effects(
    disaster_recovery_object, dependency_table, pn, wn, tn
):
    """[summary]

    Arguments:
        disaster_recovery_object {[type]} -- [description]
        dependency_table {[type]} -- [description]
        pn {[type]} -- [description]
        wn {[type]} -- [description]
        tn {[type]} -- [description]

    Returns:
        [type] -- [description]
    """
    power_consump_tracker = []
    water_consump_tracker = []
    time_tracker = []

    unique_time_stamps = disaster_recovery_object.event_table.time_stamp.unique()
    print(unique_time_stamps)

    previous_time_stamp = 0
    for index, time_stamp in enumerate(unique_time_stamps):
        print(f"\nSimulating network conditions at {time_stamp} s")
        curr_event_table = disaster_recovery_object.event_table[
            disaster_recovery_object.event_table.time_stamp == time_stamp
        ]
        print(curr_event_table)

        if index != len(unique_time_stamps) - 1:
            next_time_stamp = unique_time_stamps[index + 1]
        disaster_recovery_object.update_directly_affected_components(
            pn, wn, curr_event_table, next_time_stamp
        )

        # run power systems model
        power.run_power_simulation(pn)

        # update all dependencies
        dependency_table.update_dependencies(pn, wn, time_stamp, next_time_stamp)

        # Fix the time until which the wntr model should run in this iteration
        if time_stamp == unique_time_stamps[0]:
            previous_time_stamp = unique_time_stamps[0]
        else:
            wn.options.time.duration += time_stamp - previous_time_stamp
            wn.options.time.report_timestep = time_stamp - previous_time_stamp
            previous_time_stamp = time_stamp

        wn_results = water.run_water_simulation(wn)

        print(
            "Simulation time: ",
            wn.options.time.duration,
            "; Hydraulic time step: ",
            wn.options.time.hydraulic_timestep,
            "; Report time step: ",
            wn.options.time.report_timestep,
        )

        # print(wn_results.link['status'])
        print(wn_results.node["demand"])

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
        time_tracker.append(time_stamp / 60)  # minutes
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

        print(f"Simulation for time {time_stamp / 60} minutes completed successfully")
    return time_tracker, power_consump_tracker, water_consump_tracker


def write_results(
    time_tracker, power_consump_tracker, water_consump_tracker, location, plotting=False
):
    """[summary]

    Arguments:
        time_tracker {[type]} -- [description]
        power_consump_tracker {[type]} -- [description]
        water_consump_tracker {[type]} -- [description]
        location {[type]} -- [description]

    Keyword Arguments:
        plotting {bool} -- [description] (default: {False})
    """
    results_df = pd.DataFrame(
        {
            "time_min": time_tracker,
            "power_perf": power_consump_tracker,
            "water_perf": water_consump_tracker,
        }
    )
    results_df.to_csv(Path(location) / "network_performance.csv", sep="\t")
    print(f"The simulation results successfully saved to {Path(location)}")

    if plotting == True:
        plots.plot_interdependent_effects(
            power_consump_tracker, water_consump_tracker, time_tracker
        )
