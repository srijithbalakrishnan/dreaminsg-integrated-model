"""Functions to generate and save disruptive scenaios"""

import pandas as pd
import random
import wntr
from dreaminsg_integrated_model.network_sim_models.interdependencies import *
import dreaminsg_integrated_model.network_sim_models.water.water_network_model as water
import dreaminsg_integrated_model.network_sim_models.power.power_system_model as power
import dreaminsg_integrated_model.network_sim_models.transportation.network as transpo
from dreaminsg_integrated_model.data.disruptive_scenarios.disrupt_generator_discrete import *
import dreaminsg_integrated_model.results.figures.plots as plots


class DisruptionAndRecovery:
    """Generate a disaster and recovery object for storing simulation settings."""

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

            column_list = ["time_stamp", "components", "perf_level", "component_state"]
            self.event_table = pd.DataFrame(columns=column_list)

            for index, component in enumerate(self.disrupted_components):
                self.event_table = self.event_table.append(
                    {
                        "time_stamp": 0,
                        "components": component,
                        "perf_level": 100,
                        "component_state": "Functional",
                    },
                    ignore_index=True,
                )

            for index, row in self.disruptive_events.iterrows():
                self.event_table = self.event_table.append(
                    {
                        "time_stamp": row[0],
                        "components": row[1],
                        "perf_level": 100 - row[2],
                        "component_state": "Service Disrupted",
                    },
                    ignore_index=True,
                )

    def schedule_recovery(self, integrated_graph, wn, pn, tn, repair_order):
        """[summary]

        Arguments:
            integrated_graph {[type]} -- [description]
            wn {[type]} -- [description]
            pn {[type]} -- [description]
            tn {[type]} -- [description]
            repair_order {[type]} -- [description]
        """
        if len(repair_order) > 0:
            for index, node in enumerate(repair_order):
                origin_node = node
                (
                    compon_infra,
                    compon_notation,
                    compon_code,
                    compon_full,
                ) = get_compon_details(origin_node)

                if compon_infra == "power":
                    recovery_time = power_dict[compon_notation]["repair_time"] * 3600
                    connected_bus = find_connected_power_node(origin_node, pn)
                    nearest_node, near_dist = get_nearest_node(
                        integrated_graph, connected_bus, "transpo_node"
                    )
                    travel_time = int(
                        round(
                            tn.calculateShortestTravelTime(
                                self.curr_loc_crew, nearest_node
                            ),
                            0,
                        )
                    )
                elif compon_infra == "water":
                    recovery_time = water_dict[compon_notation]["repair_time"] * 3600
                    connected_node = find_connected_water_node(origin_node, wn)
                    nearest_node, near_dist = get_nearest_node(
                        self, connected_node, "transpo_node"
                    )
                    travel_time = int(
                        round(
                            tn.calculateShortestTravelTime(
                                self.curr_loc_crew, nearest_node
                            ),
                            0,
                        )
                    )

                print(
                    f"The crew is at {self.curr_loc_crew} at t = {self.next_crew_trip_start / self.sim_step} minutes. It takes {travel_time} minutes to reach nearest node {nearest_node}, the nearest transportation node from {node}."
                )
                recovery_start = self.next_crew_trip_start + travel_time * 60

                # Schedule the recovery action
                recovery_start = self.next_crew_trip_start + travel_time * 60
                self.event_table = self.event_table.append(
                    {
                        "time_stamp": recovery_start,
                        "components": node,
                        "perf_level": 100
                        - self.disruptive_events[
                            self.disruptive_events.components == node
                        ].fail_perc.item(),
                        "component_state": "Repairing",
                    },
                    ignore_index=True,
                )
                self.event_table = self.event_table.append(
                    {
                        "time_stamp": recovery_start + recovery_time - 60,
                        "components": node,
                        "perf_level": 100
                        - self.disruptive_events[
                            self.disruptive_events.components == node
                        ].fail_perc.item(),
                        "component_state": "Repairing",
                    },
                    ignore_index=True,
                )
                self.event_table = self.event_table.append(
                    {
                        "time_stamp": recovery_start + recovery_time,
                        "components": node,
                        "perf_level": 100,
                        "component_state": "Service Restored",
                    },
                    ignore_index=True,
                )
                self.event_table = self.event_table.append(
                    {
                        "time_stamp": recovery_start + recovery_time + 7200,
                        "components": node,
                        "perf_level": 100,
                        "component_state": "Service Restored",
                    },
                    ignore_index=True,
                )

                self.event_table.sort_values(by=["time_stamp"], inplace=True)
                self.curr_loc_crew = nearest_node
                self.next_crew_trip_start = recovery_start + recovery_time
            print("All restoration actions are successfully scheduled.")
        else:
            print("No repair action to schedule. All components functioning perfectly.")

    def optimze_recovery_strategy(self):
        """[summary]

        Returns:
            [type] -- [description]
        """
        repair_order = list(self.disrupted_components)
        random.shuffle(repair_order)
        self.next_crew_trip_start = self.disruptive_events.time_stamp[
            self.disruptive_events.components == repair_order[0]
        ].item()
        return repair_order

    def update_directly_affected_components(
        self, pn, wn, curr_event_table, next_sim_time
    ):
        """[summary]

        Arguments:
            pn {[type]} -- [description]
            wn {[type]} -- [description]
            curr_event_table {[type]} -- [description]
            next_sim_time {[type]} -- [description]
        """
        for i, row in curr_event_table.iterrows():
            component = row["components"]
            time_stamp = row["time_stamp"]
            perf_level = row["perf_level"]
            (
                compon_infra,
                compon_notation,
                compon_code,
                compon_full,
            ) = get_compon_details(component)

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
