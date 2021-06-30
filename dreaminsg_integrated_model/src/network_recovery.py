"""Functions to generate and save disruptive scenarios."""

import pandas as pd
import math
import copy
import wntr
from wntr.network.controls import ControlPriority
import dreaminsg_integrated_model.src.network_sim_models.interdependencies as interdependencies


class NetworkRecovery:
    """Generate a disaster and recovery object for storing simulation-related information and settings."""

    def __init__(self, network, sim_step):
        """Initiates the NetworkRecovery object.

        :param network: An integrated network object
        :type network: IntegratedNetwork object
        :param sim_step: Initial simulation time step in seconds.
        :type sim_step: integer
        """
        self.base_network = network
        self.network = copy.deepcopy(self.base_network)
        self.sim_step = sim_step

    def set_initial_crew_start(self, repair_order):
        """Sets the initial start times at which the respective infrastructure crews start from their locations post-disaster.

        :param repair_order: The repair order considered in the current simulation.
        :type repair_order: list of strings.
        """
        disruptive_events = self.network.disruptive_events[
            self.network.disruptive_events.components.isin(repair_order)
        ]
        disrupted_infra_dict = self.network.disrupted_infra_dict

        # power
        disrupt_events_power = disruptive_events[
            disruptive_events.components.isin(disrupted_infra_dict["power"])
        ]
        print(disrupt_events_power)
        if disrupt_events_power.shape[0] > 0:
            self.next_power_crew_trip_start = list(disrupt_events_power.time_stamp)[0]
            # print("First power failure at ", self.next_power_crew_trip_start)

        # water
        disrupt_events_water = disruptive_events[
            disruptive_events.components.isin(disrupted_infra_dict["water"])
        ]
        print(disrupt_events_water)
        if disrupt_events_water.shape[0] > 0:
            self.next_water_crew_trip_start = list(disrupt_events_water.time_stamp)[0]
            # print("First water failure at ", self.next_water_crew_trip_start)

        # transportation
        disrupt_events_transpo = disruptive_events[
            disruptive_events.components.isin(disrupted_infra_dict["transpo"])
        ]
        print(disrupt_events_transpo)
        if disrupt_events_transpo.shape[0] > 0:
            self.next_transpo_crew_trip_start = list(disrupt_events_transpo.time_stamp)[
                0
            ]
            # print("First transportation failure at ", self.next_transpo_crew_trip_start)

    def schedule_recovery(self, repair_order):
        """Generates the unexpanded event table consisting of disruptions and repair actions.

        :param repair_order: The repair order considered in the current simulation.
        :type repair_order: list of strings.
        """
        if len(list(repair_order)) > 0:

            self.initiate_next_recov_scheduled()
            self.set_initial_crew_start(repair_order)

            column_list = ["time_stamp", "components", "perf_level", "component_state"]
            self.event_table = pd.DataFrame(columns=column_list)

            # disuptive_events_permut = self.network.disruptive_events[
            #     self.network.disruptive_events.components.isin(repair_order)
            # ]

            for index, component in enumerate(self.network.get_disrupted_components()):
                self.event_table = self.event_table.append(
                    {
                        "time_stamp": 0,
                        "components": component,
                        "perf_level": 100,
                        "component_state": "Functional",
                    },
                    ignore_index=True,
                )

            for index, row in self.network.disruptive_events.iterrows():
                self.event_table = self.event_table.append(
                    {
                        "time_stamp": row[0],
                        "components": row[1],
                        "perf_level": 100 - row[2],
                        "component_state": "Service Disrupted",
                    },
                    ignore_index=True,
                )

            for index, node in enumerate(repair_order):
                origin_node = node
                (
                    compon_infra,
                    compon_notation,
                    compon_code,
                    compon_full,
                ) = interdependencies.get_compon_details(origin_node)
                # print(compon_infra, compon_notation, compon_code, compon_full)

                if compon_infra == "power":
                    recovery_time = (
                        interdependencies.power_dict[compon_notation]["repair_time"]
                        * 3600
                    )
                    connected_bus = interdependencies.find_connected_power_node(
                        origin_node, self.network.pn
                    )
                    nearest_node, near_dist = interdependencies.get_nearest_node(
                        self.network.integrated_graph, connected_bus, "transpo_node"
                    )
                    travel_time = int(
                        round(
                            self.network.tn.calculateShortestTravelTime(
                                self.network.get_power_crew_loc(), nearest_node
                            ),
                            0,
                        )
                    )
                    # print(
                    #     f"The power crew is at {self.network.get_power_crew_loc()} at t = {self.next_power_crew_trip_start / 60} minutes. It takes {travel_time} minutes to reach nearest node {nearest_node}, the nearest transportation node from {node}."
                    # )
                    recovery_start = self.next_power_crew_trip_start + travel_time * 60
                    self.network.set_power_crew_loc(nearest_node)
                    self.next_power_crew_trip_start = recovery_start + recovery_time

                elif compon_infra == "water":
                    recovery_time = (
                        interdependencies.water_dict[compon_notation]["repair_time"]
                        * 3600
                    )
                    connected_node = interdependencies.find_connected_water_node(
                        origin_node, self.network.wn
                    )
                    # print(f"Connected node: {connected_node}")
                    nearest_node, near_dist = interdependencies.get_nearest_node(
                        self.network.integrated_graph, connected_node, "transpo_node"
                    )
                    # print(f"Nearest node: {nearest_node}")
                    travel_time = int(
                        round(
                            self.network.tn.calculateShortestTravelTime(
                                self.network.get_power_crew_loc(), nearest_node
                            ),
                            0,
                        )
                    )
                    # print(
                    #     f"The water crew is at {self.network.get_water_crew_loc()} at t = {self.next_water_crew_trip_start / 60} minutes. It takes {travel_time} minutes to reach nearest node {nearest_node}, the nearest transportation node from {node}."
                    # )
                    recovery_start = self.next_power_crew_trip_start + travel_time * 60
                    self.network.set_water_crew_loc(nearest_node)
                    self.next_water_crew_trip_start = recovery_start + recovery_time

                elif compon_infra == "transpo":
                    recovery_time = (
                        interdependencies.transpo_dict[compon_notation]["repair_time"]
                        * 3600
                    )
                    connected_bus = interdependencies.find_connected_power_node(
                        origin_node, self.network.pn
                    )
                    nearest_node, near_dist = interdependencies.get_nearest_node(
                        self.network.integrated_graph, connected_bus, "transpo_node"
                    )
                    travel_time = int(
                        round(
                            self.network.tn.calculateShortestTravelTime(
                                self.network.get_power_crew_loc(), nearest_node
                            ),
                            0,
                        )
                    )
                    # print(
                    #     f"The power crew is at {self.network.get_power_crew_loc()} at t = {self.next_power_crew_trip_start / 60} minutes. It takes {travel_time} minutes to reach nearest node {nearest_node}, the nearest transportation node from {node}."
                    # )
                    recovery_start = self.next_power_crew_trip_start + travel_time * 60
                    self.network.set_transpo_crew_loc(nearest_node)
                    self.next_transpo_crew_trip_start = recovery_start + recovery_time

                # Schedule the recovery action
                self.event_table = self.event_table.append(
                    {
                        "time_stamp": recovery_start,
                        "components": node,
                        "perf_level": 100
                        - self.network.disruptive_events[
                            self.network.disruptive_events.components == node
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
                        - self.network.disruptive_events[
                            self.network.disruptive_events.components == node
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
                # self.event_table = self.event_table.append(
                #     {
                #         "time_stamp": recovery_start + recovery_time + 7200,
                #         "components": node,
                #         "perf_level": 100,
                #         "component_state": "Service Restored",
                #     },
                #     ignore_index=True,
                # )

                self.event_table.sort_values(by=["time_stamp"], inplace=True)
            self.network.reset_crew_locs()
            # print("All restoration actions are successfully scheduled.")
        else:
            print("No repair action to schedule.")

    def get_event_table(self):
        """Returns the event table."""
        return self.event_table

    def initiate_next_recov_scheduled(self):
        """
        Flag to identify when the crew must stop at a point and schedule next recovery
        """
        self.power_next_scheduled = False
        self.water_next_scheduled = False
        self.transpo_next_scheduled = False

    def update_directly_affected_components(self, time_stamp, next_sim_time):
        """Updates the operational performance of directly impacted infrastructure components by the external event.

        :param time_stamp: Current time stamp in the event table in seconds.
        :type time_stamp: integer
        :param next_sim_time: Next time stamp in the event table in seconds.
        :type next_sim_time: integer
        """
        curr_event_table = self.event_table[self.event_table.time_stamp == time_stamp]
        # print(curr_event_table)
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
                    self.network.pn[compon_code]
                    .query('name == "{}"'.format(component))
                    .index.item()
                )
                if perf_level < 100:
                    self.network.pn[compon_code].at[compon_index, "in_service"] = False
                else:
                    self.network.pn[compon_code].at[compon_index, "in_service"] = True

            elif compon_infra == "water":

                if compon_full == "Pump":
                    if perf_level < 100:
                        self.networkwn.get_link(component).add_outage(
                            self.networkwn, time_stamp, next_sim_time
                        )
                        # print(
                        #     f"The pump outage is added between {time_stamp} s and {next_sim_time} s"
                        # )

                if compon_full == "Pipe":
                    if component_state == "Service Disrupted":
                        leak_node = self.network.wn.get_node(f"{component}_leak_node")
                        leak_node.remove_leak(self.network.wn)
                        leak_node.add_leak(
                            self.network.wn,
                            area=0.005
                            * (100 - perf_level)
                            * (
                                math.pi
                                * (self.network.wn.get_link(f"{component}_B").diameter)
                                ** 2
                            )
                            / 4,
                            start_time=time_stamp,
                            end_time=next_sim_time,
                        )
                        # print(
                        #     f"The pipe leak control is added between {time_stamp} s and {next_sim_time} s"
                        # )
                    elif component_state == "Repairing":
                        self.network.wn.get_link(f"{component}_B").status = 0
                    elif component_state == "Service Restored":
                        self.network.wn.get_link(f"{component}_B").status = 1

                if compon_full == "Tank":
                    if perf_level < 100:
                        pipes_to_tank = self.network.wn.get_links_for_node(component)
                        for pipe_name in pipes_to_tank:
                            pipe = self.network.wn.get_link(pipe_name)
                            act_close = wntr.network.controls.ControlAction(
                                pipe, "status", wntr.network.LinkStatus.Closed
                            )
                            cond_close = wntr.network.controls.SimTimeCondition(
                                self.network.wn, "=", time_stamp
                            )
                            ctrl_close = wntr.network.controls.Control(
                                cond_close, act_close
                            )

                            act_open = wntr.network.controls.ControlAction(
                                pipe, "status", wntr.network.LinkStatus.Open
                            )
                            cond_open = wntr.network.controls.SimTimeCondition(
                                self.network.wn, "=", next_sim_time
                            )
                            ctrl_open = wntr.network.controls.Control(
                                cond_open, act_open
                            )

                            self.network.wn.add_control(
                                f"close_pipe_{pipe_name}", ctrl_close
                            )
                            self.network.wn.add_control(
                                f"open_pipe_{pipe_name}", ctrl_open
                            )
                    else:
                        pipes_to_tank = self.network.wn.get_links_for_node(component)
                        for pipe_name in pipes_to_tank:
                            self.network.wn.get_link(pipe_name).status = 1

    def reset_networks(self):
        """Resets the IntegratedNetwork object within NetworkRecovery object."""
        self.network = copy.deepcopy(self.base_network)


def pipe_leak_node_generator(network):
    """Splits the directly affected pipes to induce leak during simulations.

    :param wn: Water network object.
    :type wn: wntr network object
    :param disaster_recovery_object: The object in which all disaster and repair related information are stored.
    :type disaster_recovery_object: DisasterAndRecovery object
    :return: The modified wntr network object after pipe splits.
    :rtype: wntr network object
    """
    for index, component in enumerate(network.get_disrupted_components()):
        (
            compon_infra,
            compon_notation,
            compon_code,
            compon_full,
        ) = interdependencies.get_compon_details(component)
        if compon_full == "Pipe":
            network.wn = wntr.morph.split_pipe(
                network.wn, component, f"{component}_B", f"{component}_leak_node"
            )


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
