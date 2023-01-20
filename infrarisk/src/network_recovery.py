import math
import copy
import pandas as pd
import wntr
from wntr.network.controls import ControlAction, Control, ControlPriority
from infrarisk.src.physical import interdependencies as interdependencies
import time


class NetworkRecovery:
    """Generate a disaster and recovery object for storing simulation-related information and settings."""

    def __init__(
        self,
        network,
        sim_step,
        pipe_close_policy="repair",
        pipe_closure_delay=None,
        line_close_policy="sensor_based_line_isolation",
        line_closure_delay=None,
    ):
        """Initiates the NetworkRecovery object.

        :param network: An integrated network object
        :type network: IntegratedNetwork object
        :param sim_step: Initial simulation time step in seconds.
        :type sim_step: integer
        :param pipe_close_policy: The policy to isolating leaking pipes - whether performed by crew during repair ("repair"), sensor triggered isolation of leaking pipes ("sensor_based_pipe_isolation") or sensor triggered isolation of cluster consisting of leaking pipes ("sensor_based_cluster_isolation), defaults to "repair"
        :type pipe_close_policy: str, optional
        :param pipe_closure_delay: If pipe_close_policy is "sensor_based_pipe_isolation" or "sensor_based_cluster_isolation", the delay in minutes for the sensors to detect the leak, defaults to None
        :type pipe_closure_delay: integer, optional
        :param line_close_policy: The policy to isolating leaking lines - whether performed by crew during repair ("repair"), sensor triggered isolation of broken lines ("sensor_based_line_isolation") or sensor triggered isolation of cluster consisting of roken lines ("sensor_based_cluster_isolation"), defaults to "sensor_based_line_isolation"
        :type line_close_policy: str, optional
        :param line_closure_delay: If line_close_policy is "sensor_based_line_isolation" or "sensor_based_cluster_isolation", the delay in minutes for the sensors to detect the leak, defaults to None
        :type line_closure_delay: integer, optional
        """
        self.base_network = network
        self.network = copy.deepcopy(self.base_network)
        self.sim_step = sim_step

        self._pipe_close_policy = pipe_close_policy
        self._pipe_closure_delay = pipe_closure_delay

        self._line_close_policy = line_close_policy
        self._line_closure_delay = line_closure_delay

        self.transpo_updated_model_dict = dict()
        self.transpo_updated_model_dict[0] = copy.deepcopy(network.tn)

        self.crew_total_tt = {"water": 0, "power": 0, "transpo": 0}
        self.total_recovery_time = {"water": 0, "power": 0, "transpo": 0}

        self.water_access_no_redundancy = []
        self.power_access_no_redundancy = []
        self.transpo_access_no_redundancy = dict()

        self.repairs_to_simulate = self.network.disrupted_components.tolist()

        self.network.pipe_leak_node_generator()

    def set_initial_crew_start(self):
        """Sets the initial start times at which the respective infrastructure crews start from their locations post-disaster."""
        crew_groups = [
            self.network.power_crews,
            self.network.water_crews,
            self.network.transpo_crews,
        ]
        for crew_group in crew_groups:
            for crew in crew_group.keys():
                crew_group[crew].set_next_trip_start(
                    list(self.network.get_disruptive_events().time_stamp)[0]
                )

    def add_disruption_to_event_table(self):
        """Schedules the events until the initial disruption events."""
        column_list = [
            "time_stamp",
            "components",
            "perf_level",
            "component_state",
        ]
        self.event_table = pd.DataFrame(columns=column_list)

        # ----------------------------------------------------------
        column_list_et_short = [
            "component",
            "disrupt_time",
            "repair_start",
            "functional_start",
        ]
        self.event_table_wide = pd.DataFrame(columns=column_list_et_short)
        # ----------------------------------------------------------

        # Schedule component performance at the start of the simulation.
        for _, component in enumerate(self.network.get_disrupted_components()):
            self.event_table = self.event_table.append(
                {
                    "time_stamp": 0,
                    "components": component,
                    "perf_level": 100,
                    "component_state": "Functional",
                },
                ignore_index=True,
            )

        # Schedule component disruptions
        for _, row in self.network.disruptive_events.iterrows():
            disrupt_time = get_nearest_time_step(row[0], 2 * self.sim_step)
            self.event_table = self.event_table.append(
                {
                    "time_stamp": disrupt_time,
                    "components": row[1],
                    "perf_level": 100 - row[2],
                    "component_state": "Service Disrupted",
                },
                ignore_index=True,
            )

            compon_details = interdependencies.get_compon_details(component)
            if compon_details["infra"] == "transpo":
                self.fail_transpo_link(component)

    def calculate_travel_time_and_path(self, component, crew):
        """Calculates the travel time and path for a component and crew.

        :param component: The component for which the travel time and path is to be calculated
        :type component: string
        :param crew: The crew for which the travel time and path is to be calculated
        :type crew: crew object
        :return: The nearest node, travel time to that node for the crew and path for the component and crew
        :rtype: list
        """
        connected_nodes = interdependencies.find_connected_nodes(
            component, self.network
        )
        near_nodes = []
        for connected_node in connected_nodes:
            near_node, _ = interdependencies.get_nearest_node(
                self.network.integrated_graph, connected_node, "transpo"
            )
            near_nodes.append(near_node)

        travel_time = 1e10
        update_times = list(self.transpo_updated_model_dict.keys())
        curr_update_time = max(
            [x for x in update_times if x <= crew.get_next_trip_start()]
        )
        tn = self.transpo_updated_model_dict[curr_update_time]
        for near_node in near_nodes:
            (
                curr_path,
                curr_travel_time,
            ) = tn.calculateShortestTravelTime(crew.get_crew_loc(), near_node)

            if curr_travel_time < travel_time:
                nearest_node = near_node
                path = curr_path
                travel_time = curr_travel_time
        return nearest_node, path, travel_time

    def calculate_recovery_start_end(self, links_to_repair, repair_order):
        """Calculates the start and end times for the repair of the links.

        :param links_to_repair: The list of components to be repaired
        :type links_to_repair: list
        :param repair_order: The list of components to be repaired in the order in which they are to be repaired
        :type repair_order: list
        :return: The component name, start time and durationof  the repair of the links
        :rtype: list
        """
        # compon_importance_dict = {
        #     link: {
        #         "crew": None,
        #         "nearest_node": None,
        #         "path": None,
        #         "actual_travel_time": None,
        #         "weight": 0,
        #     }
        #     for link in links_to_repair
        # }

        # for _, component in enumerate(links_to_repair):
        #     compon_details = interdependencies.get_compon_details(component)
        #     crew = self.network.get_idle_crew(compon_details["infra"])
        #     nearest_node, path, travel_time = self.calculate_travel_time_and_path(
        #         component, crew
        #     )
        #     actual_travel_time = 10 + int(
        #         round(travel_time, 0)
        #     )  # 10 minutes preparation
        #     compon_importance_dict[component]["crew"] = crew
        #     compon_importance_dict[component]["nearest_node"] = nearest_node
        #     compon_importance_dict[component]["path"] = path
        #     compon_importance_dict[component]["actual_travel_time"] = actual_travel_time

        #     failed_transpo_link_en_route = [
        #         link for link in path if link in self.transpo_links_to_repair
        #     ]

        #     # Keep track of number of links that are affected due to failure of a transport link
        #     for link in failed_transpo_link_en_route:
        #         if link in compon_importance_dict.keys():
        #             compon_importance_dict[link]["weight"] += 1

        # compon_importance_dict = {
        #     k: v
        #     for k, v in sorted(
        #         compon_importance_dict.items(),
        #         key=lambda item: item[1]["weight"],
        #         reverse=True,
        #     )
        # }

        print("Components yet to repair", len(links_to_repair))

        # for component, _ in compon_importance_dict.items():
        for _, component in enumerate(links_to_repair):
            compon_details = interdependencies.get_compon_details(component)
            # crew = compon_importance_dict[component]["crew"]
            # nearest_node = compon_importance_dict[component]["nearest_node"]
            # path = compon_importance_dict[component]["path"]
            # actual_travel_time = compon_importance_dict[component]["actual_travel_time"]

            crew = self.network.get_idle_crew(compon_details["infra"])
            nearest_node, path, travel_time = self.calculate_travel_time_and_path(
                component, crew
            )
            actual_travel_time = 10 + int(
                round(travel_time, 0)
            )  # 10 minutes preparation

            failed_transpo_link_en_route = [
                link for link in path if link in self.transpo_links_to_repair
            ]

            disruption_time = self.network.disruptive_events[
                self.network.disruptive_events["components"] == component
            ].time_stamp.values[0]
            recovery_time = self.calculate_recovery_time(component)

            already_disrupted = crew.get_next_trip_start() >= disruption_time

            accessible, possible_start = self.check_route_accessibility(
                failed_transpo_link_en_route
            )

            if already_disrupted:
                if not failed_transpo_link_en_route:
                    recovery_start = (
                        crew.get_next_trip_start() + actual_travel_time * 60
                    )

                    print(
                        f"Repair {component}: The {compon_details['infra']} crew {crew._name} is at {crew.get_crew_loc()} at t = {crew.get_next_trip_start() / 60} minutes. It takes {actual_travel_time} minutes to reach nearest node {nearest_node}, the nearest transportation node from {component}."
                    )

                    crew.set_crew_loc(nearest_node)
                    crew.set_next_trip_start(recovery_start + recovery_time)

                    if compon_details["infra"] == "transpo":
                        self.restore_transpo_link(component)
                        self.update_traffic_model()
                        self.transpo_updated_model_dict[
                            int(recovery_start + recovery_time)
                        ] = copy.deepcopy(self.network.tn)
                        self.transpo_links_to_repair.remove(component)

                    self.repair_time_dict[component] = recovery_start + recovery_time
                    self.components_to_repair.remove(component)
                    self.crew_total_tt[compon_details["infra"]] += actual_travel_time
                    break
                elif accessible is True:
                    no_other_transpo_repairs = len(self.transpo_links_to_repair) <= 1

                    if (
                        possible_start <= crew.get_next_trip_start()
                        or no_other_transpo_repairs is True
                        # or component in self.skipped_transpo_links
                    ):
                        recovery_start = (
                            crew.get_next_trip_start() + actual_travel_time * 60
                        )
                        idle_time = round(
                            (recovery_start - crew.get_next_trip_start()) / 60,
                            0,
                        )
                        print(
                            f"Repair {component}: The {compon_details['infra']} crew {crew._name} is at {crew.get_crew_loc()} at t = {crew.get_next_trip_start() / 60} minutes. It takes {idle_time} minutes to reach nearest node {nearest_node}, the nearest transportation  node from {component}  considering time for road link repair.."
                        )

                        crew.set_crew_loc(nearest_node)
                        crew.set_next_trip_start(recovery_start + recovery_time)

                        # modification needed. transport model should be updated only when the repair is complete.
                        if compon_details["infra"] == "transpo":
                            self.restore_transpo_link(component)
                            self.update_traffic_model()
                            self.transpo_updated_model_dict[
                                int(recovery_start + recovery_time)
                            ] = copy.deepcopy(self.network.tn)
                            self.transpo_links_to_repair.remove(component)

                        self.repair_time_dict[component] = (
                            recovery_start + recovery_time
                        )
                        self.components_to_repair.remove(component)

                        self.crew_total_tt[
                            compon_details["infra"]
                        ] += actual_travel_time
                        break
                    elif possible_start > crew.get_next_trip_start():

                        print(
                            f"Attempting repair {component}. The {compon_details['infra']} repair crew {crew._name} is available for service at time = {crew.get_next_trip_start() / 60} minutes, much before the possible repair start of {component} at {possible_start/60} minutes. Hence the simulation will check if there are other components, whose repair can be initiated at the earliest."
                        )
                        if compon_details["infra"] == "transpo":
                            self.skipped_transpo_links.append(component)
                        recovery_start = None
                else:
                    print(
                        f"Attempting repair {component}. The {compon_details['infra']} crew {crew._name} cannot reach the destination {nearest_node} from {crew.get_crew_loc()} since there are failed transportation component(s) {failed_transpo_link_en_route} in its possible route. The simulation will defer the repair of {component} and try to repair other failed components."
                    )
                    recovery_start = None
                    if component not in self.transpo_access_no_redundancy:
                        self.transpo_access_no_redundancy[component] = 1e10
        print("\n")
        return component, recovery_start, recovery_time

    def add_recovery_to_event_table(self, component, recovery_start, recovery_time):
        """Adds the recovery time to the event table.

        :param component: The component name
        :type component: string
        :param recovery_start: The start time of the recovery in seconds
        :type recovery_start: integer
        :param recovery_time: The duration of the recovery in seconds
        :type recovery_time: integer
        """
        if recovery_start is not None:
            compon_details = interdependencies.get_compon_details(component)
            disruption_time = self.network.disruptive_events[
                self.network.disruptive_events.components == component
            ].time_stamp.item()
            disruption_time = get_nearest_time_step(disruption_time, 2 * self.sim_step)
            recovery_start = get_nearest_time_step(recovery_start, 2 * self.sim_step)
            recovery_end = get_nearest_time_step(
                recovery_start + recovery_time, 2 * self.sim_step
            )

            recovery_start = max(recovery_start, disruption_time + 2 * self.sim_step)
            recovery_end = max(recovery_end, recovery_start + 2 * self.sim_step)

            if compon_details["infra"] == "transpo":
                pass

            elif compon_details["infra"] == "water":
                if compon_details["type_code"] in ["PMA", "P", "PSC", "T"]:
                    if self._pipe_close_policy == "sensor_based_pipe_isolation":
                        pipe_isolation_time = get_nearest_time_step(
                            disruption_time + 2 * self._pipe_closure_delay * 60,
                            2 * self.sim_step,
                        )
                        if (
                            disruption_time + 2 * self.sim_step
                            <= pipe_isolation_time
                            <= recovery_start - 2 * self.sim_step
                        ):
                            self.event_table = self.event_table.append(
                                {
                                    "time_stamp": pipe_isolation_time,  # Leaks closed within 10 mins
                                    "components": component,
                                    "perf_level": 100
                                    - self.network.disruptive_events[
                                        self.network.disruptive_events.components
                                        == component
                                    ].fail_perc.item(),
                                    "component_state": "Pipe Isolated",
                                },
                                ignore_index=True,
                            )
                    elif self._pipe_close_policy == "sensor_based_cluster_isolation":
                        cluster_isolation_time = get_nearest_time_step(
                            disruption_time + self._pipe_closure_delay * 60,
                            2 * self.sim_step,
                        )
                        if (
                            disruption_time + 2 * self.sim_step
                            <= pipe_isolation_time
                            <= recovery_start - 2 * self.sim_step
                        ):
                            self.event_table = self.event_table.append(
                                {
                                    "time_stamp": cluster_isolation_time,
                                    "components": component,
                                    "perf_level": 100
                                    - self.network.disruptive_events[
                                        self.network.disruptive_events.components
                                        == component
                                    ].fail_perc.item(),
                                    "component_state": "Valves Isolated",
                                },
                                ignore_index=True,
                            )

            elif compon_details["infra"] == "power":
                if compon_details["type_code"] in ["L"]:
                    if self._line_close_policy == "sensor_based_line_isolation":
                        line_isolation_time = get_nearest_time_step(
                            disruption_time + 2 * self._line_closure_delay * 60,
                            2 * self.sim_step,
                        )
                        if (
                            disruption_time + 2 * self.sim_step
                            <= line_isolation_time
                            <= recovery_start - 2 * self.sim_step
                        ):
                            self.event_table = self.event_table.append(
                                {
                                    "time_stamp": line_isolation_time,
                                    "components": component,
                                    "perf_level": 100
                                    - self.network.disruptive_events[
                                        self.network.disruptive_events.components
                                        == component
                                    ].fail_perc.item(),
                                    "component_state": "Line Isolated",
                                },
                                ignore_index=True,
                            )
                    elif self._line_close_policy == "sensor_based_cluster_isolation":
                        cluster_isolation_time = get_nearest_time_step(
                            disruption_time + 2 * self._line_closure_delay * 60,
                            2 * self.sim_step,
                        )
                        if (
                            disruption_time + 2 * self.sim_step
                            <= cluster_isolation_time
                            <= recovery_start - 2 * self.sim_step
                        ):
                            self.event_table = self.event_table.append(
                                {
                                    "time_stamp": cluster_isolation_time,  # Leaks closed within 10 mins
                                    "components": component,
                                    "perf_level": 100
                                    - self.network.disruptive_events[
                                        self.network.disruptive_events.components
                                        == component
                                    ].fail_perc.item(),
                                    "component_state": "Switches Isolated",
                                },
                                ignore_index=True,
                            )

            self.event_table = self.event_table.append(
                {
                    "time_stamp": recovery_start,
                    "components": component,
                    "perf_level": 100
                    - self.network.disruptive_events[
                        self.network.disruptive_events.components == component
                    ].fail_perc.item(),
                    "component_state": "Repairing",
                },
                ignore_index=True,
            )

            if recovery_end - self.sim_step * 2 > recovery_start:
                self.event_table = self.event_table.append(
                    {
                        "time_stamp": recovery_end - self.sim_step * 2,
                        "components": component,
                        "perf_level": 100
                        - self.network.disruptive_events[
                            self.network.disruptive_events.components == component
                        ].fail_perc.item(),
                        "component_state": "Repairing",
                    },
                    ignore_index=True,
                )

            self.event_table = self.event_table.append(
                {
                    "time_stamp": recovery_end,
                    "components": component,
                    "perf_level": 100,
                    "component_state": "Service Restored",
                },
                ignore_index=True,
            )

            self.event_table = self.event_table.append(
                {
                    "time_stamp": recovery_end + self.sim_step * 2,
                    "components": component,
                    "perf_level": 100,
                    "component_state": "Service Restored",
                },
                ignore_index=True,
            )

            # -----------------------------------------------
            self.event_table_wide = self.event_table_wide.append(
                {
                    "component": component,
                    "disrupt_time": disruption_time,
                    "repair_start": recovery_start,
                    "functional_start": recovery_end,
                },
                ignore_index=True,
            )
            self.total_recovery_time[compon_details["infra"]] += (
                recovery_end - recovery_start
            ) / 60

    def add_additional_end_events(self, repair_order, extra_hours=8):
        """Add events post-recovery to the event table.

        :param repair_order: list of components to be repaired
        :type repair_order: list
        :param extra_hours: Number of hours post-recovery to be added, defaults to 5
        :type extra_hours: integer, optional
        """
        max_event_table_time = self.event_table["time_stamp"].max()
        for component in repair_order:
            self.event_table = self.event_table.append(
                {
                    "time_stamp": max_event_table_time + extra_hours * 3600,
                    "components": component,
                    "perf_level": 100,
                    "component_state": "Service Restored",
                },
                ignore_index=True,
            )

    def schedule_recovery(self, repair_order):
        """Generates the unexpanded event table consisting of disruptions and repair actions.

        :param repair_order: The repair order considered in the current simulation.
        :type repair_order: list of strings.
        """
        start = time.process_time()
        self.repair_time_dict = {component: None for component in repair_order}

        if len(list(repair_order)) > 0:
            # initiates the recovery schedule pandas table and add component performances until the initial failures
            self.add_disruption_to_event_table()

            # update transportation link flows and costs only if there is any change to transportation network due to the event
            disrupted_infra_dict = self.network.get_disrupted_infra_dict()
            if len(disrupted_infra_dict["transpo"]) > 0:
                self.update_traffic_model()
                self.transpo_updated_model_dict[
                    self.network.disruption_time_dict["transpo"]
                ] = copy.deepcopy(self.network.tn)

            # Compute time of recovery actions
            self.components_to_repair = copy.deepcopy(repair_order)

            # repair transportation links first
            self.transpo_links_to_repair = [
                x for x in self.components_to_repair if x.startswith("T_L")
            ]
            self.skipped_transpo_links = []

            while len(self.transpo_links_to_repair) > 0:
                recovery_start = None
                (
                    component,
                    recovery_start,
                    recovery_time,
                ) = self.calculate_recovery_start_end(
                    self.transpo_links_to_repair, repair_order
                )

                # Schedule the recovery action
                self.add_recovery_to_event_table(
                    component, recovery_start, recovery_time
                )

            while len(self.components_to_repair) > 0:
                recovery_start = None
                (
                    component,
                    recovery_start,
                    recovery_time,
                ) = self.calculate_recovery_start_end(
                    self.components_to_repair, repair_order
                )

                # Schedule the recovery action
                self.add_recovery_to_event_table(
                    component, recovery_start, recovery_time
                )

            # self.add_additional_end_events(repair_order=repair_order)

            self.event_table.sort_values(by=["time_stamp"], inplace=True)
            self.event_table["time_stamp"] = self.event_table["time_stamp"].astype(int)
            self.network.reset_crew_locs()
            print("All restoration actions are successfully scheduled.")
            print(
                f"Total travel times: power: {self.crew_total_tt['power']} mins, water: {self.crew_total_tt['water']} min, transportation: {self.crew_total_tt['transpo']} mins"
            )
            print(
                f"Total recovery times: power: {self.total_recovery_time['power']} mins, water: {self.total_recovery_time['water']} min, transportation: {self.total_recovery_time['transpo']} mins"
            )
            self.transpo_updated_model_dict = dict()
        else:
            print("No repair action to schedule.")

        del self.transpo_updated_model_dict
        print(
            f"Scheduling recovery actions completed in {time.process_time() - start} seconds"
        )

    def get_event_table(self):
        """Returns the event table.

        :return: The event table.
        :rtype: pandas.DataFrame
        """
        return self.event_table

    def update_directly_affected_components(self, time_stamp, next_sim_time):
        """Updates the operational performance of directly impacted infrastructure components by the external event.

        :param time_stamp: Current time stamp in the event table in seconds.
        :type time_stamp: integer
        :param next_sim_time: Next time stamp in the event table in seconds.
        :type next_sim_time: integer
        """

        print(
            f"Updating status of directly affected components between {time_stamp} and {next_sim_time}..."
        )
        # print(self.network.wn.control_name_list)
        time_stamp, next_sim_time = int(time_stamp), int(next_sim_time)

        # curr_event_table = self.event_table[self.event_table.time_stamp == time_stamp]
        curr_state_df = self.state_pivot_table[
            self.state_pivot_table.time_stamp == time_stamp
        ]
        curr_perf_df = self.perf_pivot_table[
            self.perf_pivot_table.time_stamp == time_stamp
        ]
        for component in self.network.disrupted_components:
            # component = row["components"]
            # time_stamp = row["time_stamp"]
            perf_level = curr_perf_df[component].values[0]
            component_state = curr_state_df[component].values[0]
            # component_state = row["component_state"]
            compon_details = interdependencies.get_compon_details(component)
            if compon_details["infra"] == "power":
                compon_index = (
                    self.network.pn[compon_details["type"]]
                    .query('name == "{}"'.format(component))
                    .index.item()
                )

                if perf_level < 100:
                    if self._line_close_policy == "sensor_based_line_isolation":
                        self.network.pn[compon_details["type"]].at[
                            compon_index, "in_service"
                        ] = False
                    elif self._line_close_policy == "sensor_based_cluster_isolation":
                        list_of_switches = self.network.line_switch_dict[component]
                        for switch in list_of_switches:
                            switch_index = self.network.pn.switch.query(
                                'name == "{}"'.format(switch)
                            ).index.item()
                            self.network.pn.switch.at[switch_index, "closed"] = False

                else:
                    if self._line_close_policy == "sensor_based_line_isolation":
                        self.network.pn[compon_details["type"]].at[
                            compon_index, "in_service"
                        ] = True
                    elif self._line_close_policy == "sensor_based_cluster_isolation":
                        compons_left_for_repair = copy.deepcopy(
                            self.repairs_to_simulate
                        )
                        if component in compons_left_for_repair:
                            compons_left_for_repair.remove(component)
                        list_of_switches = self.network.line_switch_dict[component]
                        for switch in list_of_switches:
                            if self.switch_closure_allowed(
                                compons_left_for_repair, switch
                            ):
                                switch_index = self.network.pn.switch.query(
                                    'name == "{}"'.format(switch)
                                ).index.item()
                                self.network.pn.switch.at[switch_index, "closed"] = True

                    if component_state == "Service Restored":
                        self.network.pn[compon_details["type"]].at[
                            compon_index, "in_service"
                        ] = True
                        if component in self.repairs_to_simulate:
                            self.repairs_to_simulate.remove(component)

            elif compon_details["infra"] == "water":

                if compon_details["name"] == "Pump":
                    if perf_level < 100:
                        if (
                            f"{component}_power_off_{time_stamp}"
                            in self.network.wn.control_name_list
                        ):
                            self.network.wn.remove_control(
                                f"{component}_power_off_{time_stamp}"
                            )
                        if (
                            f"{component}_power_on_{next_sim_time}"
                            in self.network.wn.control_name_list
                        ):
                            self.network.wn.remove_control(
                                f"{component}_power_on_{next_sim_time}"
                            )
                        self.network.wn.get_link(component).add_outage(
                            self.network.wn, time_stamp, next_sim_time
                        )
                        # print(
                        #     f"The pump outage is added for {component} between {time_stamp} s and {next_sim_time} s"
                        # )

                elif compon_details["name"] in [
                    "Pipe",
                    "Service Connection Pipe",
                    "Main Pipe",
                    "Hydrant Connection Pipe",
                    "Valve converted to Pipe",
                ]:
                    if component_state == "Service Disrupted":
                        leak_node = self.network.wn.get_node(f"{component}_leak_node")
                        leak_node.remove_leak(self.network.wn)
                        add_pipe_leak(
                            self.network.wn,
                            leak_node,
                            area=((100 - perf_level) / 100)
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
                        #     f"The pipe leak control for {component} is added between {time_stamp} s and {next_sim_time} s"
                        # )
                    elif component_state == "Pipe Isolated":
                        if (
                            "close pipe " + component + f"_isolated_{time_stamp}"
                            in self.network.wn.control_name_list
                        ):
                            self.network.wn.remove_control(
                                "close pipe " + component + f"_isolated_{time_stamp}"
                            )
                            self.network.wn.remove_control(
                                "open pipe " + component + f"_isolated_{time_stamp}"
                            )

                        link_close_event(
                            self.network.wn, f"{component}", time_stamp, "isolated"
                        )
                        link_open_event(
                            self.network.wn,
                            f"{component}",
                            next_sim_time,
                            "isolated",
                        )
                        # print(
                        #     f"The valve {component} close control is added between {time_stamp} s and {next_sim_time} s"
                        # )
                    elif component_state == "Valves Isolated":
                        list_of_valves = self.network.pipe_valve_dict[component]
                        for valve in list_of_valves:
                            if (
                                "close pipe " + valve + f"_isolated_{time_stamp}"
                                in self.network.wn.control_name_list
                            ):
                                self.network.wn.remove_control(
                                    "close pipe " + valve + f"_isolated_{time_stamp}"
                                )
                                self.network.wn.remove_control(
                                    "open pipe " + valve + f"_isolated_{next_sim_time}"
                                )

                            link_close_event(
                                self.network.wn, f"{valve}", time_stamp, "isolated"
                            )
                            link_open_event(
                                self.network.wn,
                                f"{valve}",
                                next_sim_time,
                                "isolated",
                            )
                            # print(
                            #     f"The valve {component} close control is added between {time_stamp} s and {next_sim_time} s"
                            # )

                    elif component_state == "Repairing":
                        if self._pipe_close_policy in [
                            "repair",
                            "sensor_based_pipe_isolation",
                        ]:
                            if (
                                "close pipe " + component + f"_repairing_{time_stamp}"
                                in self.network.wn.control_name_list
                            ):
                                self.network.wn.remove_control(
                                    "close pipe "
                                    + component
                                    + f"_repairing_{time_stamp}"
                                )
                                self.network.wn.remove_control(
                                    "open pipe "
                                    + pipe_name
                                    + f"_repairing_{next_sim_time}"
                                )

                            link_close_event(
                                self.network.wn,
                                f"{component}_B",
                                time_stamp,
                                "repairing",
                            )
                            link_open_event(
                                self.network.wn,
                                f"{component}_B",
                                next_sim_time,
                                "repairing",
                            )
                            # print(
                            #     f"The pipe {component} close control is added between {time_stamp} s and {next_sim_time} s"
                            # )
                        elif (
                            self._pipe_close_policy == "sensor_based_cluster_isolation"
                        ):
                            list_of_valves = self.network.pipe_valve_dict[component]
                            for valve in list_of_valves:
                                if (
                                    f"close pipe {valve}_repairing"
                                    not in self.network.wn.control_name_list
                                ):
                                    link_close_event(
                                        self.network.wn,
                                        f"{valve}",
                                        time_stamp,
                                        "repairing",
                                    )
                                    link_open_event(
                                        self.network.wn,
                                        f"{valve}",
                                        next_sim_time,
                                        "repairing",
                                    )

                    elif component_state == "Service Restored":
                        if component in self.repairs_to_simulate:
                            self.repairs_to_simulate.remove(component)

                elif compon_details["name"] == "Tank":
                    if perf_level < 100:
                        pipes_to_tank = self.network.wn.get_links_for_node(component)
                        for pipe_name in pipes_to_tank:
                            if (
                                "close pipe " + pipe_name + f"_repairing_{time_stamp}"
                                in self.network.wn.control_name_list
                            ):
                                self.network.wn.remove_control(
                                    "close pipe " + pipe_name + f"_close_{time_stamp}"
                                )
                                self.network.wn.remove_control(
                                    "open pipe " + pipe_name + f"_open_{next_sim_time}"
                                )

                            link_close_event(
                                self.network.wn,
                                f"{pipe_name}",
                                time_stamp,
                                "close",
                            )
                            link_open_event(
                                self.network.wn,
                                f"{pipe_name}",
                                next_sim_time,
                                "open",
                            )
                    #         act_close = wntr.network.controls.ControlAction(
                    #             pipe, "status", wntr.network.LinkStatus.Closed
                    #         )
                    #         cond_close = wntr.network.controls.SimTimeCondition(
                    #             self.network.wn, "=", time_stamp
                    #         )
                    #         ctrl_close = wntr.network.controls.Control(
                    #             cond_close, act_close
                    #         )

                    #         act_open = wntr.network.controls.ControlAction(
                    #             pipe, "status", wntr.network.LinkStatus.Open
                    #         )
                    #         cond_open = wntr.network.controls.SimTimeCondition(
                    #             self.network.wn, "=", next_sim_time
                    #         )
                    #         ctrl_open = wntr.network.controls.Control(
                    #             cond_open, act_open
                    #         )

                    #         self.network.wn.add_control(
                    #             f"close_pipe_{pipe_name}", ctrl_close
                    #         )
                    #         self.network.wn.add_control(
                    #             f"open_pipe_{pipe_name}", ctrl_open
                    #         )
                    # # else:
                    # #     pipes_to_tank = self.network.wn.get_links_for_node(component)
                    # #     for pipe_name in pipes_to_tank:
                    # #         self.network.wn.get_link(pipe_name).status = 1

    def reset_networks(self):
        """Resets the IntegratedNetwork object within NetworkRecovery object."""
        self.network = copy.deepcopy(self.base_network)

    def update_traffic_model(self):
        """Updates the static traffic assignment model based on current network conditions."""
        # self.network.tn.userEquilibrium(
        #     "FW", 400, 1e-4, self.network.tn.averageExcessCost
        # )
        for link in self.network.tn.link:
            self.network.tn.link[link].updateCost()

    def fail_transpo_link(self, link_compon):
        """Fails the given transportation link by changing the free-flow travel time to a very large value.

        :param link_compon: Name of the transportation link.
        :type link_compon: string
        """
        self.network.tn.link[link_compon].freeFlowTime = 9999

    def restore_transpo_link(self, link_compon):
        """Restores the disrupted transportation link by changing the free flow travel time to the original value.

        :param link_compon: Name of the transportation link.
        :type link_compon: string
        """
        self.network.tn.link[link_compon].freeFlowTime = self.network.tn.link[
            link_compon
        ].fft_base

    def check_route_accessibility(self, failed_transpo_link_en_route):
        """Checks when the failed transportation links along a route are repaired and the possible start time.

        :param failed_transpo_link_en_route: List of transportation links along the route.
        :type failed_transpo_link_en_route: list
        :return: Accessibility and possible start time of the route.
        :rtype: list
        """
        accessible = True
        possible_start_time = 0
        for link in failed_transpo_link_en_route:
            if self.repair_time_dict[link] is None:
                accessible = False
                possible_start_time = None
                break
            elif (self.repair_time_dict[link] > possible_start_time) and (
                accessible is True
            ):
                possible_start_time = self.repair_time_dict[link]
            # else:
            #     accessible = False
            #     possible_start_time = None
        return accessible, possible_start_time

    def remove_previous_water_controls(self):
        """Removes all previous pump controls"""
        pump_list = self.network.wn.pump_name_list
        for pump_name in pump_list:
            pump_close_controls = [
                i
                for i in self.network.wn.control_name_list
                if i.startswith(f"{pump_name}_power_off")
            ]
            pump_open_controls = [
                i
                for i in self.network.wn.control_name_list
                if i.startswith(f"{pump_name}_power_on")
            ]

            pump_controls = pump_close_controls + pump_open_controls
            if len(pump_controls) > 0:
                for control in pump_controls:
                    self.network.wn.remove_control(control)

    def switch_closure_allowed(self, compons_to_repair, switch):
        """Check if a switch closure is possible. Depends on whether a switch needs to be open to isolate any component whose repair is not yet performed

        :param compons_to_repair: List of components to be repaired excluding the component under consideration.
        :type compons_to_repair: list
        :param switch: Switch component
        :type switch: string
        :return: True if switch closure is allowed, False otherwise.
        :rtype: bool
        """
        allowed = True
        p_compons = [compon for compon in compons_to_repair if compon.startswith("P_")]

        for p_compon in p_compons:
            if switch in self.network.line_switch_dict[p_compon]:
                allowed = False
                break
        return allowed

    def calculate_recovery_time(self, component):
        """Calculates the recovery time of the given component.

        :param component: Component whose recovery time is to be calculated.
        :type component: string
        :return: Recovery time of the component in seconds.
        :rtype: float
        """
        disruptive_events = self.network.disruptive_events
        perc_damage = disruptive_events[disruptive_events["components"] == component][
            "fail_perc"
        ].values[0]

        if "recovery_time" in disruptive_events.columns:
            recovery_time = (
                disruptive_events[disruptive_events["components"] == component][
                    "recovery_time"
                ].values[0]
                * 3600
            )
        else:
            recovery_time = (
                interdependencies.get_compon_repair_time(component)
                * 3600
                * perc_damage
                / 100
            )
        return recovery_time


def pipe_leak_node_generator(network):
    """Splits the directly affected pipes to induce leak during simulations.

    :param network: Integrated infrastructure network object
    :type network: IntegratedNetwork object
    
    """

    for _, component in enumerate(network.get_disrupted_components()):
        compon_details = interdependencies.get_compon_details(component)
        if compon_details["name"] == "Pipe":
            network.wn = wntr.morph.split_pipe(
                network.wn, component, f"{component}_B", f"{component}_leak_node"
            )


def link_open_event(wn, pipe_name, time_stamp, state):
    """Opens a pipe.

    :param wn: Water network object.
    :type wn: wntr.network.WaterNetworkModel
    :param pipe_name:  Name of the pipe.
    :type pipe_name: string
    :param time_stamp: Time stamp at which the pipe must be opened in seconds.
    :type time_stamp: integer
    :param state: The state of the object.
    :type state: string
    :return: The modified wntr network object after pipe splits.
    :rtype: wntr.network.WaterNetworkModel

    """

    pipe = wn.get_link(pipe_name)
    act_open = wntr.network.controls.ControlAction(
        pipe, "status", wntr.network.LinkStatus.Open
    )
    cond_open = wntr.network.controls.SimTimeCondition(wn, "=", time_stamp)
    ctrl_open = wntr.network.controls.Control(
        cond_open, act_open, ControlPriority.medium
    )
    wn.add_control("open pipe " + pipe_name + f"_{state}_{time_stamp}", ctrl_open)
    return wn


def link_close_event(wn, pipe_name, time_stamp, state):
    """Closes a pipe.

    :param wn: Water network object.
    :type wn: wntr.network.WaterNetworkModel
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
    wn.add_control("close pipe " + pipe_name + f"_{state}_{time_stamp}", ctrl_close)
    return wn


def add_pipe_leak(
    wn, leak_junc, area, discharge_coeff=0.75, start_time=None, end_time=None
):
    """Adds a leak to a junction.

    :param wn: Water network object.
    :type wn: wntr.network.WaterNetworkModel
    :param leak_junc: Name of the junction where the leak is to be added.
    :type leak_junc: string
    :param area: Area of the leak in m^2.
    :type area: float
    :param discharge_coeff: Discharge coefficient of the leak.
    :type discharge_coeff: float
    :param start_time: Time at which the leak must start in seconds.
    :type start_time: integer
    :param end_time: Time at which the leak must end in seconds.
    :type end_time: integer
    """

    leak_junc._leak = True
    leak_junc.leak_area = area
    leak_junc.leak_discharge_coeff = discharge_coeff

    if start_time is not None:
        start_control_action = ControlAction(leak_junc, "leak_status", True)
        control = Control._time_control(
            wn, start_time, "SIM_TIME", False, start_control_action
        )
        wn.add_control(f"{leak_junc}_leak_start_{start_time}", control)

    if end_time is not None:
        end_control_action = ControlAction(leak_junc, "leak_status", False)
        control = Control._time_control(
            wn, end_time, "SIM_TIME", False, end_control_action
        )
        wn.add_control(f"{leak_junc}_leak_end_{end_time}", control)


def get_nearest_time_step(time_stamp, time_step):
    """Returns the nearest time step to the given time stamp.

    :param time_stamp: Time stamp in seconds.
    :type time_stamp: integer
    :param time_step: Time step in seconds.
    :type time_step: integer
    """
    u = time_stamp % time_step > time_step // 2
    nearest_time = time_stamp + (-1) ** (1 - u) * abs(
        time_step * u - time_stamp % time_step
    )
    return max(nearest_time, time_step)
