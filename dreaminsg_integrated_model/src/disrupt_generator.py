"""Functions to generate and save disruptive scenarios."""

import pandas as pd
import random
import math
import wntr
from wntr.network.controls import ControlPriority

import dreaminsg_integrated_model.src.network_sim_models.interdependencies as interdependencies
from dreaminsg_integrated_model.src.disrupt_generator import *


class DisruptionAndRecovery:
    """Generate a disaster and recovery object for storing simulation-related information and settings."""

    def __init__(self, scenario_file, sim_step, curr_loc_crew):
        """Initiates the DisruptionAndRecovery object.

        :param scenario_file: The location of the scenario file consisting of disruption information.
        :type scenario_file: string
        :param sim_step: Initial simulation time step in seconds.
        :type sim_step: integer
        :param curr_loc_crew: Name of the transportation node where the repair crew is initially located.
        :type curr_loc_crew: integer/string
        """
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
        """Schedules the recovery actions in the event table of the DisasterAndRecovery object.

        :param integrated_graph: The integrated network as networkx object.
        :type integrated_graph: nextworkx object
        :param wn: Water network object.
        :type wn: wntr network object
        :param pn: Power systems object.
        :type pn: pandapower network object
        :param tn: Transportation network object.
        :type tn: traffic network object
        :param repair_order: The order in which the disrupted components are to be repaired.
        :type repair_order: list of strings
        """
        if len(repair_order) > 0:
            for index, node in enumerate(repair_order):
                origin_node = node
                (
                    compon_infra,
                    compon_notation,
                    compon_code,
                    compon_full,
                ) = interdependencies.get_compon_details(origin_node)
                print(compon_infra, compon_notation, compon_code, compon_full)

                if compon_infra == "power":
                    recovery_time = (
                        interdependencies.power_dict[compon_notation]["repair_time"]
                        * 3600
                    )
                    connected_bus = interdependencies.find_connected_power_node(
                        origin_node, pn
                    )
                    nearest_node, near_dist = interdependencies.get_nearest_node(
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
                    recovery_time = (
                        interdependencies.water_dict[compon_notation]["repair_time"]
                        * 3600
                    )
                    connected_node = interdependencies.find_connected_water_node(
                        origin_node, wn
                    )
                    print(f"Connected node: {connected_node}")
                    nearest_node, near_dist = interdependencies.get_nearest_node(
                        integrated_graph, connected_node, "transpo_node"
                    )
                    print(f"Nearest node: {nearest_node}")
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
                        "time_stamp": recovery_start
                        + recovery_time
                        - self.sim_step * 2,
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
        """Identifies the optimal repair strategy.

        :return: The order in which the repair actions must be executed.
        :rtype: list of strings
        """
        # repair_order = ["P_MP1", "P_L2", "P_LO1", "W_P10"]

        repair_order = list(self.disrupted_components)
        random.shuffle(repair_order)
        self.next_crew_trip_start = self.disruptive_events.time_stamp[
            self.disruptive_events.components == repair_order[0]
        ].item()
        return repair_order

    def update_directly_affected_components(self, pn, wn, time_stamp, next_sim_time):
        """Updates the operational performance of directly impacted infrastructure components by the external event.

        :param pn: Power network object.
        :type pn: pandapower network object
        :param wn: Water network object.
        :type wn: wntr network object
        :param time_stamp: Current time stamp in the event table in seconds.
        :type time_stamp: integer
        :param next_sim_time: Next time stamp in the event table in seconds.
        :type next_sim_time: integer
        """
        curr_event_table = self.event_table[self.event_table.time_stamp == time_stamp]
        print(curr_event_table)
        for i, row in curr_event_table.iterrows():
            component = row["components"]
            time_stamp = row["time_stamp"]
            perf_level = row["perf_level"]
            component_state = row["component_state"]
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
                if perf_level < 100:
                    pn[compon_code].at[compon_index, "in_service"] = False
                else:
                    pn[compon_code].at[compon_index, "in_service"] = True

            elif compon_infra == "water":

                if compon_full == "Pump":
                    if perf_level < 100:
                        wn.get_link(component).add_outage(wn, time_stamp, next_sim_time)
                        print(
                            f"The pump outage is added between {time_stamp} s and {next_sim_time} s"
                        )

                if compon_full == "Pipe":
                    if component_state == "Service Disrupted":
                        leak_node = wn.get_node(f"{component}_leak_node")
                        leak_node.remove_leak(wn)
                        leak_node.add_leak(
                            wn,
                            area=0.005
                            * (100 - perf_level)
                            * (math.pi * (wn.get_link(f"{component}_B").diameter) ** 2)
                            / 4,
                            start_time=time_stamp,
                            end_time=next_sim_time,
                        )
                        print(
                            f"The pipe leak control is added between {time_stamp} s and {next_sim_time} s"
                        )
                    elif component_state == "Repairing":
                        wn.get_link(f"{component}_B").status = 0
                    elif component_state == "Service Restored":
                        wn.get_link(f"{component}_B").status = 1

                if compon_full == "Tank":
                    if perf_level < 100:
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


def pipe_leak_node_generator(wn, disaster_recovery_object):
    """Splits the directly affected pipes to induce leak during simulations.

    :param wn: Water network object.
    :type wn: wntr network object
    :param disaster_recovery_object: The object in which all disaster and repair related information are stored.
    :type disaster_recovery_object: DisasterAndRecovery object
    :return: The modified wntr network object after pipe splits.
    :rtype: wntr network object
    """
    for index, component in enumerate(disaster_recovery_object.disrupted_components):
        (
            compon_infra,
            compon_notation,
            compon_code,
            compon_full,
        ) = interdependencies.get_compon_details(component)
        if compon_full == "Pipe":
            wn = wntr.morph.split_pipe(
                wn, component, f"{component}_B", f"{component}_leak_node"
            )
    return wn


def link_open_event(wn, pipe_name, time_stamp, state):
    """Opens a pipe.

    :param wn: Water network object.
    :type wn: wntr network object
    :param pipe_name:  Name of the pipe.
    :type pipe_name: string
    :param time_stamp: Time stamp at which the pipe must be opened in seconds.
    :type time_stamp: integer
    :param state: The state of the object.
    :type state: string
    :return: The modified wntr network object after pipe splits.
    :rtype: wntr network object
    """
    pipe = wn.get_link(pipe_name)
    act_open = wntr.network.controls.ControlAction(
        pipe, "status", wntr.network.LinkStatus.Open
    )
    cond_open = wntr.network.controls.SimTimeCondition(wn, "=", time_stamp)
    ctrl_open = wntr.network.controls.Control(
        cond_open, act_open, ControlPriority.medium
    )
    wn.add_control("open pipe " + pipe_name + f"{time_stamp}" + f"_{state}", ctrl_open)
    return wn


def link_close_event(wn, pipe_name, time_stamp, state):
    """Closes a pipe.

    :param wn: Water network object.
    :type wn: wntr network object
    :param pipe_name: Name of the pipe.
    :type pipe_name: string
    :param time_stamp: Time stamp at which the pipe must be closed in seconds.
    :type time_stamp: integer
    :param state: The state of the object.
    :type state: string
    :return: The modified wntr network object after pipe splits.
    :rtype: wntr network object
    """
    pipe = wn.get_link(pipe_name)
    act_close = wntr.network.controls.ControlAction(
        pipe, "status", wntr.network.LinkStatus.Closed
    )
    cond_close = wntr.network.controls.SimTimeCondition(wn, "=", time_stamp)
    ctrl_close = wntr.network.controls.Control(
        cond_close, act_close, ControlPriority.medium
    )
    wn.add_control(
        "close pipe " + pipe_name + f"{time_stamp}" + f"_{state}", ctrl_close
    )
    return wn
