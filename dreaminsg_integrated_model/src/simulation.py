"""Functions to implement the various steps of the interdependent infrastructure network simulations."""

import pandas as pd
from pathlib import Path
import os
import dreaminsg_integrated_model.src.network_sim_models.water.water_network_model as water
import dreaminsg_integrated_model.src.network_sim_models.power.power_system_model as power
import dreaminsg_integrated_model.src.network_sim_models.transportation.network as transpo
import dreaminsg_integrated_model.src.plots as model_plots
import dreaminsg_integrated_model.src.resilience_metrics as resm


class NetworkSimulation:
    """Methods to perform simulation of interdependent effects."""

    def __init__(self, network_recovery, sim_step):
        """Initates a NetworkSimulation object

        :param network_recovery: A integrated infrastructure network recovery object.
        :type network_recovery: NetworkRecovery object
        :param sim_step: step size used for simulation in seconds.
        :type sim_step: non-negative integer
        """
        self.network_recovery = network_recovery
        self.sim_step = sim_step
        self.components_to_repair = network_recovery.network.get_disrupted_components()
        self.components_repaired = []

    def expand_event_table(self, add_points):
        """Expands the event table with additional time_stamps for simulation.

        :param add_points: A positive integer denoting the number of extra time-stamps to be added to the simulation.
        :type add_points: integer
        """
        compon_list = list(self.network_recovery.event_table.components.unique())
        full_time_list = self.network_recovery.event_table.time_stamp.unique()

        # print("Prior to expansion: ", full_time_list)  ###

        interval_approx = (full_time_list[-1] - full_time_list[0]) / add_points
        act_interval = int(self.sim_step * round(interval_approx / self.sim_step))

        new_range = range(full_time_list[0], full_time_list[-1], act_interval)

        # print("Additional points that might be added: ", [i for i in new_range])

        new_time_stamps = [time_stamp for time_stamp in new_range]

        for time in full_time_list:
            curr_components = list(
                self.network_recovery.event_table[
                    self.network_recovery.event_table.time_stamp == time
                ].components
            )
            components_to_add = [
                i
                for i in compon_list + curr_components
                if i not in compon_list or i not in curr_components
            ]
            # print("Components to add at {}".format(time), components_to_add)
            for _, compon in enumerate(components_to_add):
                compon_time_list = self.network_recovery.event_table[
                    self.network_recovery.event_table.components == compon
                ].time_stamp.unique()

                maxless = max(compon_time_list[compon_time_list <= time])

                perf_level = self.network_recovery.event_table[
                    (self.network_recovery.event_table.components == compon)
                    & (self.network_recovery.event_table.time_stamp == maxless)
                ].perf_level.values[0]

                perf_state = self.network_recovery.event_table[
                    (self.network_recovery.event_table.components == compon)
                    & (self.network_recovery.event_table.time_stamp == maxless)
                ].component_state.values[0]

                self.network_recovery.event_table = (
                    self.network_recovery.event_table.append(
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
            compon_time_list = self.network_recovery.event_table[
                self.network_recovery.event_table.components == compon
            ].time_stamp.unique()

            for time in new_time_stamps:
                if time not in compon_time_list:
                    if time not in [
                        compon_time - 60 for compon_time in compon_time_list
                    ]:
                        if time not in [
                            compon_time + 60 for compon_time in compon_time_list
                        ]:
                            maxless = max(compon_time_list[compon_time_list <= time])

                            perf_level = self.network_recovery.event_table[
                                (self.network_recovery.event_table.components == compon)
                                & (
                                    self.network_recovery.event_table.time_stamp
                                    == maxless
                                )
                            ].perf_level.values[0]

                            perf_state = self.network_recovery.event_table[
                                (self.network_recovery.event_table.components == compon)
                                & (
                                    self.network_recovery.event_table.time_stamp
                                    == maxless
                                )
                            ].component_state.values[0]

                            self.network_recovery.event_table = (
                                self.network_recovery.event_table.append(
                                    {
                                        "time_stamp": time,
                                        "components": compon,
                                        "perf_level": perf_level,
                                        "component_state": perf_state,
                                    },
                                    ignore_index=True,
                                )
                            )
        self.network_recovery.event_table.sort_values(by=["time_stamp"], inplace=True)
        self.network_recovery.event_table["time_stamp"] = (
            self.network_recovery.event_table["time_stamp"] + 60
        )

    def get_components_to_repair(self):
        """Returns the remaining components to be repaired.

        :return: The list of components
        :rtype: list of strings
        """
        return self.components_to_repair

    def get_components_repaired(self):
        """Returns the list of components that are already repaired.

        :return: list of components which are already repaired.
        :rtype: list of strings
        """
        return self.components_repaired

    def update_repaired_components(self, component):
        """Update the lists of repaired and to be repaired components.

        :param component: The name of the component that was recently repaired.
        :type component: string
        """
        self.components_to_repair.remove(component)
        self.components_repaired.append(component)

    def simulate_interdependent_effects(self, network_recovery):
        """Simulates the interdependent effect based on the initial disruptions and subsequent repair actions.

        :param network_recovery: A integrated infrastructure network recovery object.
        :type network_recovery: NetworkRecovery object
        :return: lists of time stamps and resilience values of power and water supply.
        :rtype: lists
        """
        resilience_metrics = resm.WeightedResilienceMetric()

        unique_time_stamps = sorted(
            list(network_recovery.event_table.time_stamp.unique())
        )
        # print(unique_time_stamps)

        unique_time_differences = [
            x - unique_time_stamps[i - 1] for i, x in enumerate(unique_time_stamps)
        ][1:]

        for index, time_stamp in enumerate(unique_time_stamps[:-1]):
            print(f"\nSimulating network conditions at {time_stamp} s")

            print(
                "Simulation time: ",
                network_recovery.network.wn.options.time.duration,
                "; Hydraulic time step: ",
                network_recovery.network.wn.options.time.hydraulic_timestep,
                "; Report time step: ",
                network_recovery.network.wn.options.time.report_timestep,
            )

            # print(
            #     "Pump status before updating direct effects: ",
            #     [
            #         network_recovery.network.wn.get_link(pump).status
            #         for pump in network_recovery.network.wn.pump_name_list
            #     ],
            # )

            # update performance of directly affected components
            network_recovery.update_directly_affected_components(
                network_recovery.network.wn.options.time.duration,
                network_recovery.network.wn.options.time.duration
                + unique_time_differences[index],
            )

            # run power systems model
            power.run_power_simulation(network_recovery.network.pn)

            # print(
            #     "Pump status before updating interdependent effects: ",
            #     [
            #         network_recovery.network.wn.get_link(pump).status
            #         for pump in network_recovery.network.wn.pump_name_list
            #     ],
            # )

            # update networkwide effects
            network_recovery.network.dependency_table.update_dependencies(
                network_recovery.network,
                network_recovery.network.wn.options.time.duration,
                network_recovery.network.wn.options.time.duration
                + unique_time_differences[index],
            )

            # run water network model and print results

            # print(
            #     "Pump status before simulation: ",
            #     [
            #         network_recovery.network.wn.get_link(pump).status
            #         for pump in network_recovery.network.wn.pump_name_list
            #     ],
            # )
            wn_results = water.run_water_simulation(network_recovery.network.wn)
            # print(wn_results.link["status"])
            # print(wn_results.node["demand"])
            # print(wn_results.node["leak_demand"])
            # failed_pipe = "W_PMA505"
            # print(
            #     "Pumps: ",
            #     "\t\tstatus = ",
            #     wn_results.link["status"][
            #         network_recovery.network.wn.pump_name_list
            #     ].values,
            #     "\tflowrate = ",
            #     wn_results.link["flowrate"][
            #         network_recovery.network.wn.pump_name_list
            #     ].values,
            # )
            # print(
            #     "Failed pipe: ",
            #     "\t\tstatus = ",
            #     wn_results.link["status"][failed_pipe].values,
            #     "\tflowrate = ",
            #     wn_results.link["flowrate"][failed_pipe].values,
            # )
            # print(
            #     "Leaking pipe: ",
            #     "\t\tstatus = ",
            #     wn_results.link["status"][f"{failed_pipe}_B"].values,
            #     "\tflowrate = ",
            #     wn_results.link["flowrate"][f"{failed_pipe}_B"].values,
            #     "\tleak demand = ",
            #     wn_results.node["leak_demand"][f"{failed_pipe}_leak_node"].values,
            # )
            # print(
            #     "Tank: ",
            #     "\t\tdemand",
            #     wn_results.node["demand"]["W_T1"].values,
            #     "\thead = ",
            #     wn_results.node["head"]["W_T1"].values,
            # )
            # print(
            #     "Pipe from Tank: ",
            #     "status",
            #     wn_results.link["status"]["W_PMA2000"].values,
            #     "\tflowrate = ",
            #     wn_results.link["flowrate"]["W_PMA2000"].values,
            # )
            # print("******************\n")

            # track results

            # time_tracker.append((time_stamp) / 60)  # minutes
            resilience_metrics.time_tracker.append((time_stamp) / 60)  # minutes

            resilience_metrics.power_consump_tracker.append(
                resilience_metrics.calculate_power_resmetric(
                    network_recovery,
                )
            )

            resilience_metrics.water_consump_tracker.append(
                resilience_metrics.calculate_water_resmetric(
                    network_recovery,
                    wn_results,
                )
            )

            # Fix the time until which the wntr model should run in this iteration
            if index < len(unique_time_stamps) - 1:
                network_recovery.network.wn.options.time.duration += (
                    unique_time_differences[index]
                )
                network_recovery.network.wn.options.time.report_timestep += (
                    unique_time_differences[index]
                )

            # print(
            #      f"Simulation for time {time_stamp / 60} minutes completed successfully"
            # )
        return resilience_metrics

    def write_results(
        self,
        time_tracker,
        power_consump_tracker,
        water_consump_tracker,
        location,
        plotting=False,
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
