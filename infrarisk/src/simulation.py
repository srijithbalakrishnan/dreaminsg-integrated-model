"""Functions to implement the various steps of the interdependent infrastructure network simulations."""

import copy
from pathlib import Path
import time

import infrarisk.src.physical.interdependencies as interdependencies
import infrarisk.src.physical.power.power_system_model as power
import infrarisk.src.physical.water.water_network_model as water
import infrarisk.src.resilience_metrics as resm


class NetworkSimulation:
    """A class to perform simulation of interdependent effects."""

    def __init__(self, network_recovery):
        """Initates a NetworkSimulation object

        :param network_recovery: A integrated infrastructure network recovery object.
        :type network_recovery: infrarisk.src.network_recovery.NetworkRecovery
        """
        self.network_recovery = network_recovery
        self.components_to_repair = network_recovery.network.get_disrupted_components()
        self.components_repaired = []

    def expand_event_table(self):
        """Creates the pivot tables (for functional state and performance level) corresponding to the event table."""

        self.network_recovery.event_table.reset_index(drop=True, inplace=True)
        self.network_recovery.event_table.time_stamp = (
            self.network_recovery.event_table.time_stamp
            + self.network_recovery.network.time_step
        )
        state_pivot_table = self.network_recovery.event_table.pivot(
            index="time_stamp", columns="components", values="component_state"
        )
        state_pivot_table = state_pivot_table.fillna(method="ffill").reset_index()
        # state_pivot_table["time_stamp"] = (
        #     state_pivot_table["time_stamp"] + self.network_recovery.network.time_step
        # )
        self.network_recovery.state_pivot_table = state_pivot_table

        perf_pivot_table = self.network_recovery.event_table.pivot(
            index="time_stamp", columns="components", values="perf_level"
        )
        perf_pivot_table = perf_pivot_table.fillna(method="ffill").reset_index()
        # perf_pivot_table["time_stamp"] = (
        #     perf_pivot_table["time_stamp"] + self.network_recovery.network.time_step
        # )
        self.network_recovery.perf_pivot_table = perf_pivot_table

    def get_components_to_repair(self):
        """Returns the remaining components to be repaired.

        :return: The list of components
        :rtype: list
        """
        return self.components_to_repair

    def get_components_repaired(self):
        """Returns the list of components that are already repaired.

        :return: list of components which are already repaired.
        :rtype: list
        """
        return self.components_repaired

    def update_repaired_components(self, component):
        """Update the lists of repaired and to be repaired components.

        :param component: The name of the component that was recently repaired.
        :type component: string
        """
        self.components_to_repair.remove(component)
        self.components_repaired.append(component)

    def get_sim_times(self, network_recovery):
        """Returns the unique simulation times scheduled by the event table.

        :param network_recovery: A integrated infrastructure network recovery object.
        :type network_recovery: infrarisk.src.network_recovery.NetworkRecovery
        :return: Unique simulation time stamps
        :rtype: list
        """
        simtime_max = 0

        for _, row in network_recovery.event_table_wide.iterrows():
            compon_details = interdependencies.get_compon_details(row["component"])
            if compon_details["infra"] in ["water", "power"]:
                if row["functional_start"] > simtime_max:
                    simtime_max = row["functional_start"]

        unique_time_stamps = network_recovery.event_table.time_stamp.unique()
        maxtime_index = min(
            len(unique_time_stamps),
            len(unique_time_stamps[unique_time_stamps < (simtime_max + 5 * 3600)]) + 3,
        )
        unique_sim_times = unique_time_stamps[0:maxtime_index]
        return unique_sim_times

    def simulate_interdependent_effects(self, network_recovery_original):
        """Simulates the interdependent effect based on the initial disruptions and subsequent repair actions.

        :param network_recovery_original: A integrated infrastructure network recovery object.
        :type network_recovery_original: infrarisk.src.network_recovery.NetworkRecovery
        :return: lists of time stamps and resilience values of power and water supply.
        :rtype: infrarisk.src.resilience_metrics.WeightedResilienceMetric
        """
        start_time = time.time()
        network_recovery = copy.deepcopy(network_recovery_original)
        resilience_metrics = resm.WeightedResilienceMetric()

        water_control_dict = {
            "base": network_recovery.network.wn.control_name_list,
            "curr": [],
            "future": [],
        }

        unique_time_stamps = (
            self.network_recovery.state_pivot_table.time_stamp.unique().tolist()
        )

        # consider only time until water and power are restored
        event_table = self.network_recovery.event_table
        event_table_reduced = event_table[
            event_table.apply(
                lambda x: x["components"].startswith("W_")
                or x["components"].startswith("P_"),
                axis=1,
            )
        ]
        event_table_reduced = event_table_reduced[
            event_table_reduced["component_state"] == "Service Restored"
        ]
        time_stamp_max_needed = (
            event_table_reduced[
                [
                    "components",
                    "time_stamp",
                ]
            ]
            .groupby("components")
            .min()  # minimum of every failed component
            .max()  # maximum of all minimum times to restore completelyu\
        )
        time_index = (
            event_table.time_stamp.sort_values()
            .unique()
            .tolist()
            .index(time_stamp_max_needed[0])
        )
        if len(unique_time_stamps) >= time_index + 3:
            sim_time_max = (
                event_table.time_stamp.sort_values().unique().tolist()[time_index + 2]
            )
        else:
            sim_time_max = (
                event_table.time_stamp.sort_values().unique().tolist()[time_index]
            )

        unique_time_stamps = [
            time for time in unique_time_stamps if time <= sim_time_max
        ]

        print(
            "Time instances for which simulations will be performed:\n",
            unique_time_stamps,
        )

        unique_time_differences = [
            x - unique_time_stamps[i - 1] for i, x in enumerate(unique_time_stamps)
        ][1:]
        # print(unique_time_differences)

        stop_counter = None
        last_five_pcs_list = []

        for index, time_stamp in enumerate(unique_time_stamps[:-1]):
            print(
                f"Simulating network conditions at {time_stamp}/{unique_time_stamps[-1]} s..."
            )

            print(
                "Simulation time: ",
                network_recovery.network.wn.options.time.duration,
                "; Hydraulic time step: ",
                network_recovery.network.wn.options.time.hydraulic_timestep,
                "; Report time step: ",
                network_recovery.network.wn.options.time.report_timestep,
            )

            # Remove unnecessary controls from previous iterations
            for control in water_control_dict["curr"]:
                network_recovery.network.wn.remove_control(control)
            water_control_dict["curr"] = water_control_dict["future"]

            # update performance of directly affected components

            network_recovery.update_directly_affected_components(
                network_recovery.network.wn.options.time.duration,
                network_recovery.network.wn.options.time.duration
                + unique_time_differences[index],
            )

            # run power systems model
            power.run_power_simulation(network_recovery.network.pn)

            # update networkwide effects
            network_recovery.network.dependency_table.update_dependencies(
                network_recovery.network,
                network_recovery.network.wn.options.time.duration,
                network_recovery.network.wn.options.time.duration
                + unique_time_differences[index],
            )

            # run water network model and print results
            print(network_recovery.network.wn.control_name_list)

            wn_results = water.run_water_simulation(network_recovery.network.wn)

            water_control_dict["future"] = list(
                set(network_recovery.network.wn.control_name_list)
                - set(water_control_dict["base"])
                - set(water_control_dict["curr"])
            )
            print("\nFuture: ", water_control_dict["future"], "\n")

            # print(
            #     "Pumps: ",
            #     # "\t\tstatus = \n",
            #     # wn_results.link["status"][
            #     #     network_recovery.network.wn.pump_name_list
            #     # ].round(decimals=4),
            #     "\tflowrate = \n",
            #     wn_results.link["flowrate"][network_recovery.network.wn.pump_name_list]
            #     .round(decimals=4)
            #     .iloc[-1]
            #     .tolist(),
            # )
            # print(
            #     "Tank: ",
            #     "\t\tdemand\n",
            #     wn_results.node["demand"][network_recovery.network.wn.tank_name_list]
            #     .round(decimals=4)
            #     .iloc[-1]
            #     .tolist(),
            #     # "\thead = \n",
            #     # wn_results.node["head"][network_recovery.network.wn.tank_name_list].round(decimals=4).iloc[-1].tolist(),
            # )
            # print(
            #     "Pipe from Tank: ",
            #     "status",
            #     wn_results.link["status"]["W_PMA2000"].round(decimals=4).values,
            #     "\tflowrate = ",
            #     wn_results.link["flowrate"]["W_PMA2000"].round(decimals=4).values,
            # )
            # print(
            #     "Total leak: ",
            #     wn_results.node["leak_demand"][["W_PMA44_leak_node"]].iloc[-1].tolist(),
            # )

            # track results
            resilience_metrics.calculate_node_details(network_recovery, wn_results)
            # resilience_metrics.calculate_water_lost(network_recovery, wn_results)
            resilience_metrics.calculate_pump_flow(network_recovery, wn_results)
            resilience_metrics.calculate_power_load(network_recovery, time_stamp)
            resilience_metrics.calculate_pump_status(network_recovery, wn_results)

            if index > 0:
                resilience_metrics.calculate_power_resmetric(network_recovery)
                resilience_metrics.calculate_water_resmetrics(network_recovery)
                resilience_metrics.set_weighted_auc_metrics()

                if len(last_five_pcs_list) == 3:
                    del last_five_pcs_list[0]
                last_five_pcs_list.append(
                    resilience_metrics.power_pcs_list[-1]
                    * resilience_metrics.water_pcs_list[-1]
                )

                if resilience_metrics.power_pcs_list[-1] > 0.99:
                    if resilience_metrics.water_pcs_list[-1] > 0.99:
                        stop_counter = 0

            if stop_counter is not None:
                stop_counter += 1
                if stop_counter == 2:
                    break

            if len(last_five_pcs_list) == 3:
                if all(x >= 0.98 for x in last_five_pcs_list):
                    break

            # # Fix the time until which the wntr model should run in this iteration
            if index < len(unique_time_stamps) - 1:
                network_recovery.network.wn.options.time.duration += int(
                    unique_time_differences[index]
                )
            print("******************\n")

        end_time = time.time()

        time_taken = round(end_time) - round(start_time)
        print(f"Simulation completed in {time_taken} s")
        return resilience_metrics

    def write_results(self, file_dir, resilience_metrics):
        """Writes the results to csv files.

        :param file_dir: The directory in which the simulation contents are to be saved.
        :type file_dir: string
        :param resilience_metrics: The object in which simulation related data are stored.
        :type resilience_metrics: infrarisk.src.resilience_metrics.WeightedResilienceMetric
        """
        sim_times = resilience_metrics.power_load_df.time.astype("int32").to_list()

        water_demand = resilience_metrics.water_junc_demand_df
        add_times = [time for time in water_demand.time if time % 600 == 0]

        subset_times = sorted(list(set(sim_times + add_times)))

        # leak_loss = resilience_metrics.water_leak_loss_df
        # if leak_loss is not None:
        #     leak_loss[leak_loss.time.isin(subset_times)].to_csv(
        #         Path(file_dir) / "water_loss.csv", sep="\t", index=False
        #     )

        pump_flow = resilience_metrics.water_pump_flow_df
        if pump_flow is not None:
            pump_flow[pump_flow.time.isin(subset_times)].to_csv(
                f"{file_dir}/water_pump_flow.csv", sep="\t", index=False
            )

        pump_status = resilience_metrics.water_pump_status_df
        if pump_status is not None:
            pump_status[pump_status.time.isin(subset_times)].to_csv(
                f"{file_dir}/water_pump_status.csv", sep="\t", index=False
            )

        water_head = resilience_metrics.water_node_head_df
        if water_head is not None:
            water_head[water_head.time.isin(subset_times)].to_csv(
                f"{file_dir}/water_node_head.csv", sep="\t", index=False
            )

        water_demand = resilience_metrics.water_junc_demand_df
        if water_demand is not None:
            water_demand[water_demand.time.isin(subset_times)].to_csv(
                f"{file_dir}/water_junc_demand.csv", sep="\t", index=False
            )

        # water_pressure = resilience_metrics.water_node_pressure_df
        # if water_pressure is not None:
        #     water_pressure[water_pressure.time.isin(subset_times)].to_csv(
        #         f"{file_dir}/water_node_pressure.csv", sep="\t", index=False
        #     )

        if resilience_metrics.power_load_df is not None:
            resilience_metrics.power_load_df.to_csv(
                f"{file_dir}/power_load_demand.csv", sep="\t", index=False
            )

        print(f"The simulation results successfully saved to {Path(file_dir)}")
