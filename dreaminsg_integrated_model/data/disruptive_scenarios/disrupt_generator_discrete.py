"""Functions to generate and save disruptive scenaios"""

import pandas as pd
import numpy as np
import random
import dreaminsg_integrated_model.network_sim_models.interdependencies as interdependencies
import wntr


class DisruptionAndRecovery:
    def __init__(self, scenario_file, sim_step, curr_loc_crew):
        try:
            self.disruptive_events = pd.read_csv(scenario_file, sep=",")
        except FileNotFoundError:
            print(
                "Error: The scenario file does not exist. No such directory: ",
                scenario_file,
            )

        self.disrupted_components = self.disruptive_events.components
        if len(list(self.disrupted_components)) > 0:
            self.sim_step = sim_step
            self.next_recov_scheduled = False  # Flag to identify when the crew must stop at a point and schedule next recovery
            self.curr_loc_crew = curr_loc_crew

            column_list = ["time_stamp", "components", "perf_level"]
            self.event_table = pd.DataFrame(columns=column_list)

            for index, component in enumerate(self.disrupted_components):
                self.event_table = self.event_table.append(
                    {"time_stamp": 0, "components": component, "perf_level": 100},
                    ignore_index=True,
                )

            for index, row in self.disruptive_events.iterrows():
                self.event_table = self.event_table.append(
                    {
                        "time_stamp": row[0],
                        "components": row[1],
                        "perf_level": 100 - row[2],
                    },
                    ignore_index=True,
                )

    def schedule_recovery(self, component, recovery_start, recovery_rate):
        recovery_start_index = self.event_table.time_stamp[
            self.event_table.time_stamp == recovery_start
        ].index.to_list()[0]
        start_perf = self.event_table[component].iloc[recovery_start_index]

        for index, row in self.event_table.iloc[recovery_start_index:].iterrows():
            self.event_table.loc[index, component] = min(
                100, start_perf + recovery_rate * (row["time_stamp"] - recovery_start)
            )
            while (self.event_table.loc[index, component] == 100) & (
                self.next_recov_scheduled == False
            ):
                # self.curr_loc_crew = component
                self.next_crew_trip_start = row["time_stamp"]
                print(
                    f"The repair action at {component} successfuly completed at time {self.next_crew_trip_start/self.sim_step} minutes\n"
                )
                self.next_recov_scheduled = True
        self.next_recov_scheduled = False

    def optimze_recovery_strategy(self):
        repair_order = list(self.disrupted_components)
        random.shuffle(repair_order)
        self.next_crew_trip_start = self.disruptive_events.time_stamp[
            self.disruptive_events.components == repair_order[0]
        ].item()
        return repair_order

    def expand_event_table(self, initial_sim_step, add_points):
        compon_list = self.event_table.components.unique()
        full_time_list = self.event_table.time_stamp.unique()
        interval_approx = (full_time_list[-1] - full_time_list[0]) / add_points
        act_interval = int(initial_sim_step * round(interval_approx / initial_sim_step))

        new_range = range(full_time_list[0], full_time_list[-1], act_interval)
        new_time_stamps = [time_stamp for time_stamp in new_range]

        for time in full_time_list:
            disrupt_components = list(self.disrupted_components)
            curr_components = list(
                self.event_table[self.event_table.time_stamp == time].components
            )
            components_to_add = [
                i
                for i in disrupt_components + curr_components
                if i not in disrupt_components or i not in curr_components
            ]
            for i, compon in enumerate(components_to_add):
                compon_time_list = self.event_table[
                    self.event_table.components == compon
                ].time_stamp.unique()
                maxless = max(compon_time_list[compon_time_list <= time])
                perf_level = self.event_table[
                    (self.event_table.components == compon)
                    & (self.event_table.time_stamp == maxless)
                ].perf_level.values[0]
                self.event_table = self.event_table.append(
                    {
                        "time_stamp": time,
                        "components": compon,
                        "perf_level": perf_level,
                    },
                    ignore_index=True,
                )

        for compon in compon_list:
            compon_time_list = self.event_table[
                self.event_table.components == compon
            ].time_stamp.unique()
            for time in new_time_stamps:
                if time not in compon_time_list:
                    maxless = max(compon_time_list[compon_time_list <= time])
                    perf_level = self.event_table[
                        (self.event_table.components == compon)
                        & (self.event_table.time_stamp == maxless)
                    ].perf_level.values[0]
                    self.event_table = self.event_table.append(
                        {
                            "time_stamp": time,
                            "components": compon,
                            "perf_level": perf_level,
                        },
                        ignore_index=True,
                    )
        self.event_table.sort_values(by=["time_stamp"], inplace=True)

    def update_directly_affected_components(
        self, pn, wn, curr_event_table, next_sim_time
    ):
        for i, row in curr_event_table.iterrows():
            component = row["components"]
            time_stamp = row["time_stamp"]
            perf_level = row["perf_level"]
            (
                compon_infra,
                compon_notation,
                compon_code,
                compon_full,
            ) = interdependencies.get_compon_details(component)

            if compon_infra == "power":
                compon_index = (
                    pn[compon_code].query('name == "{}"'.format(component)).index.item()
                )
                if perf_level != 100:
                    pn[compon_code].at[compon_index, "in_service"] = False
                else:
                    pn[compon_code].at[compon_index, "in_service"] = True

            elif compon_infra == "water":
                if compon_full == "Pump":
                    if perf_level != 100:
                        wn.get_link(component).add_outage(wn, time_stamp, next_sim_time)
                    else:
                        wn.get_link(component).status = 1
                if compon_full == "Pipe":
                    if perf_level != 100:
                        wn = wntr.morph.split_pipe(
                            wn, component, f"{component}_B", f"{component}_leak_node"
                        )
                        leak_node = wn.get_node(f"{component}_leak_node")
                        leak_node.add_leak(
                            wn, area=0.05, start_time=time_stamp, end_time=time_stamp
                        )
                    else:
                        wn.get_link(component).status = 1
                if compon_full == "Tank":
                    if perf_level != 100:
                        pipes_to_tank = wn.get_links_for_node(component)
                        for pipe_name in pipes_to_tank:
                            pipe = wn.get_link(pipe_name)
                            act_close = wntr.network.controls.ControlAction(
                                pipe, "status", wntr.network.LinkStatus.Closed
                            )
                            cond_close = wntr.network.controls.SimTimeCondition(
                                wn, "=", time_stamp
                            )
                            ctrl_close = wntr.network.controls.Control(
                                cond_close, act_close
                            )

                            act_open = wntr.network.controls.ControlAction(
                                pipe, "status", wntr.network.LinkStatus.Open
                            )
                            cond_open = wntr.network.controls.SimTimeCondition(
                                wn, "=", next_sim_time
                            )
                            ctrl_open = wntr.network.controls.Control(
                                cond_open, act_open
                            )

                            wn.add_control(f"close_pipe_{pipe_name}", ctrl_close)
                            wn.add_control(f"open_pipe_{pipe_name}", ctrl_open)
                    else:
                        pipes_to_tank = wn.get_links_for_node(component)
                        for pipe_name in pipes_to_tank:
                            wn.get_link(pipe_name).status = 1
