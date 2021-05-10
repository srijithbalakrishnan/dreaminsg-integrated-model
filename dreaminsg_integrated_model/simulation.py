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
    dependency_table.add_transpo_access(integrated_graph)
    return dependency_table


def schedule_component_repair(disaster_recovery_object, integrated_graph, pn, wn, tn):
    repair_order = disaster_recovery_object.optimze_recovery_strategy()
    print(
        f"The optimised repair strategy is to schedule repair of failed components in the following order: {repair_order}\n"
    )

    if len(repair_order) > 0:
        for index, node in enumerate(repair_order):
            origin_node = node
            (
                compon_infra,
                compon_notation,
                compon_code,
                compon_full,
            ) = interdependencies.get_compon_details(origin_node)

            if compon_infra == "power":
                recovery_time = power_dict[compon_notation]["repair_time"] * 3600
                connected_bus = find_connected_power_node(origin_node, pn)
                nearest_node, near_dist = get_nearest_node(
                    integrated_graph, connected_bus, "transpo_node"
                )
                travel_time = int(
                    round(
                        tn.calculateShortestTravelTime(
                            disaster_recovery_object.curr_loc_crew, nearest_node
                        ),
                        0,
                    )
                )
            elif compon_infra == "water":
                recovery_time = water_dict[compon_notation]["repair_time"] * 3600
                connected_node = find_connected_water_node(origin_node, wn)
                nearest_node, near_dist = get_nearest_node(
                    disaster_recovery_object, connected_node, "transpo_node"
                )
                travel_time = int(
                    round(
                        tn.calculateShortestTravelTime(
                            disaster_recovery_object.curr_loc_crew, nearest_node
                        ),
                        0,
                    )
                )

            print(
                f"The crew is at {disaster_recovery_object.curr_loc_crew} at t = {disaster_recovery_object.next_crew_trip_start / disaster_recovery_object.sim_step} minutes. It takes {travel_time} minutes to reach nearest node {nearest_node}, the nearest transportation node from {node}."
            )
            recovery_start = (
                disaster_recovery_object.next_crew_trip_start + travel_time * 60
            )

            # Schedule the recovery action
            recovery_start = (
                disaster_recovery_object.next_crew_trip_start + travel_time * 60
            )
            disaster_recovery_object.event_table = (
                disaster_recovery_object.event_table.append(
                    {
                        "time_stamp": recovery_start,
                        "components": node,
                        "perf_level": 100
                        - disaster_recovery_object.disruptive_events[
                            disaster_recovery_object.disruptive_events.components
                            == node
                        ].fail_perc.item(),
                    },
                    ignore_index=True,
                )
            )
            disaster_recovery_object.event_table = (
                disaster_recovery_object.event_table.append(
                    {
                        "time_stamp": recovery_start + recovery_time - 60,
                        "components": node,
                        "perf_level": 100
                        - disaster_recovery_object.disruptive_events[
                            disaster_recovery_object.disruptive_events.components
                            == node
                        ].fail_perc.item(),
                    },
                    ignore_index=True,
                )
            )
            disaster_recovery_object.event_table = (
                disaster_recovery_object.event_table.append(
                    {
                        "time_stamp": recovery_start + recovery_time,
                        "components": node,
                        "perf_level": 100,
                    },
                    ignore_index=True,
                )
            )
            disaster_recovery_object.event_table = (
                disaster_recovery_object.event_table.append(
                    {
                        "time_stamp": recovery_start + recovery_time + 7200,
                        "components": node,
                        "perf_level": 100,
                    },
                    ignore_index=True,
                )
            )

            disaster_recovery_object.event_table.sort_values(
                by=["time_stamp"], inplace=True
            )
            # motor_failure.schedule_recovery(origin_node, recovery_start, recovery_rate)
            disaster_recovery_object.curr_loc_crew = nearest_node
            disaster_recovery_object.next_crew_trip_start = (
                recovery_start + recovery_time
            )
        print("All restoration actions are successfully scheduled.")
    else:
        print("No repair action to schedule. All components functioning perfectly.")


def simulate_interdependent_effects(
    disaster_recovery_object, dependency_table, pn, wn, tn
):
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
