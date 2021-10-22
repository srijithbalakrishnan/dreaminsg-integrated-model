"""Functions to implement the various steps of the interdependent infrastructure network simulations."""

from pathlib import Path
import copy

from wntr import network
import infrarisk.src.network_sim_models.water.water_network_model as water
import infrarisk.src.network_sim_models.power.power_system_model as power
import infrarisk.src.network_sim_models.transportation.network as transpo
import infrarisk.src.network_sim_models.interdependencies as interdependencies
import infrarisk.src.plots as model_plots
import infrarisk.src.resilience_metrics as resm


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

    def get_sim_times(self, network_recovery):
        """Returns the unique simulation times scheduled by the event table.

        :param network_recovery: A integrated infrastructure network recovery object.
        :type network_recovery: NetworkRecovery object
        :return: Unique simulation time stamps
        :rtype: list of integers
        """
        simtime_max = 0

        for _, row in network_recovery.event_table_wide.iterrows():
            compon_details = interdependencies.get_compon_details(row["component"])
            if compon_details[0] in ["water", "power"]:
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
        :type network_recovery_original: NetworkRecovery object
        :return: lists of time stamps and resilience values of power and water supply.
        :rtype: lists
        """
        network_recovery = copy.deepcopy(network_recovery_original)
        resilience_metrics = resm.WeightedResilienceMetric()

        unique_time_stamps = sorted(
            list(network_recovery.event_table.time_stamp.unique())
        )

        unique_sim_times = self.get_sim_times(network_recovery)
        # print(unique_sim_times)

        unique_time_differences = [
            x - unique_time_stamps[i - 1] for i, x in enumerate(unique_sim_times)
        ][1:]
        # print(unique_time_differences)

        for index, time_stamp in enumerate(unique_sim_times[:-1]):
            print(f"Simulating network conditions at {time_stamp} s")

            # network_recovery.remove_previous_water_controls()

            print(
                "Simulation time: ",
                network_recovery.network.wn.options.time.duration,
                "; Hydraulic time step: ",
                network_recovery.network.wn.options.time.hydraulic_timestep,
                "; Report time step: ",
                network_recovery.network.wn.options.time.report_timestep,
            )
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

            # Fix the time until which the wntr model should run in this iteration
            wn_results = water.run_water_simulation(network_recovery.network.wn)

            # print(
            #     "Pumps: ",
            #     "\t\tstatus = \n",
            #     wn_results.link["status"][
            #         network_recovery.network.wn.pump_name_list
            #     ].round(decimals=4),
            #     "\tflowrate = \n",
            #     wn_results.link["flowrate"][
            #         network_recovery.network.wn.pump_name_list
            #     ].round(decimals=4),
            # )
            # print(
            #     "Tank: ",
            #     "\t\tdemand\n",
            #     wn_results.node["demand"]["W_T1"].round(decimals=4),
            #     "\thead = \n",
            #     wn_results.node["head"]["W_T1"].round(decimals=4),
            # )
            # print(
            #     "Pipe from Tank: ",
            #     "status",
            #     wn_results.link["status"]["W_PMA2000"].round(decimals=4).values,
            #     "\tflowrate = ",
            #     wn_results.link["flowrate"]["W_PMA2000"].round(decimals=4).values,
            # )
            # print("Total leak: ", wn_results.node["leak_demand"].sum())

            # track results
            resilience_metrics.calculate_node_details(network_recovery, wn_results)
            resilience_metrics.calculate_water_lost(network_recovery, wn_results)
            resilience_metrics.calculate_pump_flow(network_recovery, wn_results)
            resilience_metrics.calculate_power_load(network_recovery, time_stamp)

            # # Fix the time until which the wntr model should run in this iteration
            if index < len(unique_time_stamps) - 1:
                network_recovery.network.wn.options.time.duration += int(
                    unique_time_differences[index]
                )
            print("******************\n")

        return resilience_metrics

    def write_results(self, file_dir, resilience_metrics, plotting=False):
        """[summary]

        :param file_dir: The directory in which the simulation contents are to be saved.
        :type file_dir: string
        :param resilience_metrics: The object in which simulation related data are stored.
        :type resilience_metrics: The WeightedResilienceMetric object
        :param plotting: [description], defaults to False
        :type plotting: bool, optional
        """
        sim_times = resilience_metrics.power_load_df.time.astype("int32").to_list()

        water_demand = resilience_metrics.water_junc_demand_df
        add_times = [time for time in water_demand.time if time % 600 == 0]

        subset_times = sorted(list(set(sim_times + add_times)))

        leak_loss = resilience_metrics.water_leak_loss_df
        if leak_loss is not None:
            leak_loss[leak_loss.time.isin(subset_times)].to_csv(
                Path(file_dir) / "water_loss.csv", sep="\t", index=False
            )

        pump_flow = resilience_metrics.water_pump_flow_df
        if pump_flow is not None:
            pump_flow[pump_flow.time.isin(subset_times)].to_csv(
                Path(file_dir) / "water_pump_flow.csv", sep="\t", index=False
            )

        water_head = resilience_metrics.water_node_head_df
        if water_head is not None:
            water_head[water_head.time.isin(subset_times)].to_csv(
                Path(file_dir) / "water_node_head.csv", sep="\t", index=False
            )

        water_demand = resilience_metrics.water_junc_demand_df
        if water_demand is not None:
            water_demand[water_demand.time.isin(subset_times)].to_csv(
                Path(file_dir) / "water_junc_demand.csv", sep="\t", index=False
            )

        water_pressure = resilience_metrics.water_node_pressure_df
        if water_pressure is not None:
            water_pressure[water_pressure.time.isin(subset_times)].to_csv(
                Path(file_dir) / "water_node_pressure.csv", sep="\t", index=False
            )

        if resilience_metrics.power_load_df is not None:
            resilience_metrics.power_load_df.to_csv(
                Path(file_dir) / "power_load_demand.csv", sep="\t", index=False
            )

        print(f"The simulation results successfully saved to {Path(file_dir)}")

        # if plotting == True:
        #     model_plots.plot_interdependent_effects(
        #         power_consump_tracker, water_consump_tracker, time_tracker
        #     )
