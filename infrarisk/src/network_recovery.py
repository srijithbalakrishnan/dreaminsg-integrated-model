"""Functions to generate and save disruptive scenarios."""

import math
import copy
import pandas as pd
import wntr
from wntr.network.controls import ControlPriority
from infrarisk.src.physical import interdependencies as interdependencies


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
        self._tn_update_flag = True

        self._pipe_close_policy = pipe_close_policy
        self._pipe_closure_delay = pipe_closure_delay

        self._line_close_policy = line_close_policy
        self._line_closure_delay = line_closure_delay

        self.transpo_updated_model_dict = dict()
        self.transpo_updated_model_dict[0] = copy.deepcopy(network.tn)

        self.water_crew_total_tt = 0
        self.power_crew_total_tt = 0
        self.transpo_crew_total_tt = 0

        self.water_access_no_redundancy = []
        self.power_access_no_redundancy = []

        self.transpo_access_no_redundancy = dict()

        self.total_water_recovery_time = 0
        self.total_power_recovery_time = 0
        self.total_transpo_recovery_time = 0

        self.repairs_to_simulate = self.network.disrupted_components.tolist()

        self.network.pipe_leak_node_generator()

    def set_initial_crew_start(self):
        """Sets the initial start times at which the respective infrastructure crews start from their locations post-disaster.

        :param repair_order: The repair order considered in the current simulation.
        :type repair_order: list of strings.
        """
        crew_types = [
            self.network.power_crews,
            self.network.water_crews,
            self.network.transpo_crews,
        ]
        for crew_type in crew_types:
            for crew in crew_type.keys():
                crew_type[crew].set_next_trip_start(
                    list(self.network.get_disruptive_events().time_stamp)[0]
                )

    def schedule_recovery(self, repair_order):
        """Generates the unexpanded event table consisting of disruptions and repair actions.

        :param repair_order: The repair order considered in the current simulation.
        :type repair_order: list of strings.
        """
        self.repair_time_dict = {component: None for component in repair_order}

        if len(list(repair_order)) > 0:

            # self.initiate_next_recov_scheduled()
            # self.set_initial_crew_start()

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
                self.event_table = self.event_table.append(
                    {
                        "time_stamp": row[0],
                        "components": row[1],
                        "perf_level": 100 - row[2],
                        "component_state": "Service Disrupted",
                    },
                    ignore_index=True,
                )

                compon_details = interdependencies.get_compon_details(component)
                if compon_details[0] == "transpo":
                    self.fail_transpo_link(component)

            # update transportation link flows and costs only if there is any change to transportation network due to the event
            disrupted_infra_dict = self.network.get_disrupted_infra_dict()
            if len(disrupted_infra_dict["transpo"]) > 0:
                self.update_traffic_model()
                self.transpo_updated_model_dict[
                    self.network.disruption_time
                ] = copy.deepcopy(self.network.tn)

            # Compute time of recovery actions
            components_to_repair = copy.deepcopy(repair_order)

            # repair transportation links first
            transpo_links_to_repair = [
                x for x in components_to_repair if x.startswith("T_L")
            ]
            skipped_transpo_links = []

            while len(transpo_links_to_repair) > 0:
                recovery_start = None
                for _, component in enumerate(transpo_links_to_repair):
                    compon_details = interdependencies.get_compon_details(component)

                    if compon_details[0] == "transpo":
                        transpo_crew = self.network.get_idle_crew("transpo")
                        recovery_time = (
                            interdependencies.get_transpo_repair_time(component) * 3600
                        )
                        connected_junctions = (
                            interdependencies.find_connected_transpo_node(
                                component, self.network.tn
                            )
                        )
                        nearest_nodes = []
                        for connected_junction in connected_junctions:
                            nearest_node = connected_junction
                            nearest_nodes.append(nearest_node)
                        travel_time = 1e10
                        update_times = list(self.transpo_updated_model_dict.keys())
                        curr_update_time = max(
                            [
                                x
                                for x in update_times
                                if x <= transpo_crew.get_next_trip_start()
                            ]
                        )
                        tn = self.transpo_updated_model_dict[curr_update_time]
                        for nearest_node in nearest_nodes:
                            (
                                curr_path,
                                curr_travel_time,
                            ) = tn.calculateShortestTravelTime(
                                transpo_crew.get_crew_loc(), nearest_node
                            )

                            if curr_travel_time < travel_time:
                                path = curr_path
                                travel_time = curr_travel_time
                        actual_travel_time = 10 + int(round(travel_time, 0))
                        # 10 minutes for preparations
                        failed_transpo_link_en_route = [
                            link for link in path if link in repair_order
                        ]
                        accessible, possible_start = self.check_route_accessibility(
                            failed_transpo_link_en_route
                        )
                        # print(accessible, possible_start)

                        if not failed_transpo_link_en_route:
                            recovery_start = (
                                transpo_crew.get_next_trip_start()
                                + actual_travel_time * 60
                            )

                            print(
                                f"Repair {component}: The transpo crew {transpo_crew._name} is at {transpo_crew.get_crew_loc()} at t = {transpo_crew.get_next_trip_start() / 60} minutes. It takes {actual_travel_time} minutes to reach nearest node {nearest_node}, the nearest transportation node from {component}."
                            )

                            self.restore_transpo_link(component)
                            transpo_crew.set_crew_loc(nearest_node)
                            transpo_crew.set_next_trip_start(
                                recovery_start + recovery_time
                            )

                            # modification needed. transport model should be updated only when the repair is complete.
                            self.update_traffic_model()
                            self.transpo_updated_model_dict[
                                int(recovery_start + recovery_time)
                            ] = copy.deepcopy(self.network.tn)

                            self.repair_time_dict[component] = (
                                recovery_start + recovery_time
                            )
                            components_to_repair.remove(component)
                            transpo_links_to_repair.remove(component)
                            skipped_transpo_links = []
                            self.transpo_crew_total_tt += actual_travel_time
                            break
                        elif accessible is True:
                            no_other_transpo_repairs = len(transpo_links_to_repair) <= 1
                            print(
                                transpo_crew.get_next_trip_start(),
                                possible_start,
                                possible_start > transpo_crew.get_next_trip_start(),
                            )

                            if (
                                possible_start <= transpo_crew.get_next_trip_start()
                                or no_other_transpo_repairs is True
                                or component in skipped_transpo_links
                            ):
                                recovery_start = (
                                    transpo_crew.get_next_trip_start()
                                    + actual_travel_time * 60
                                )
                                idle_time = round(
                                    (
                                        recovery_start
                                        - transpo_crew.get_next_trip_start()
                                    )
                                    / 60,
                                    0,
                                )
                                print(
                                    f"Repair {component}: The transpo crew {transpo_crew._name} is at {transpo_crew.get_crew_loc()} at t = {transpo_crew.get_next_trip_start() / 60} minutes. It takes {idle_time} minutes to reach nearest node {nearest_node}, the nearest transportation  node from {component}  considering time for road link repair.."
                                )

                                self.restore_transpo_link(component)
                                transpo_crew.set_crew_loc(nearest_node)
                                transpo_crew.set_next_trip_start(
                                    recovery_start + recovery_time
                                )

                                # modification needed. transport model should be updated only when the repair is complete.
                                self.update_traffic_model()
                                self.transpo_updated_model_dict[
                                    int(recovery_start + recovery_time)
                                ] = copy.deepcopy(self.network.tn)

                                self.repair_time_dict[component] = (
                                    recovery_start + recovery_time
                                )
                                components_to_repair.remove(component)
                                transpo_links_to_repair.remove(component)
                                skipped_transpo_links = []
                                self.transpo_crew_total_tt += actual_travel_time
                                break
                            elif possible_start > transpo_crew.get_next_trip_start():
                                # recovery_start = (
                                #     possible_start + actual_travel_time * 60
                                # )
                                print(
                                    f"The transportation repair crew {transpo_crew._name} is available for service at time = {transpo_crew.get_next_trip_start() / 60} minutes, much before the possible repair start of {component} at {possible_start/60} minutes. Hence the simulation will check if there are other components, whose repair can be initiated at the earliest."
                                )
                                skipped_transpo_links.append(component)
                        else:
                            print(
                                f"The transportation crew {transpo_crew._name} cannot reach the destination {nearest_node} from {transpo_crew.get_crew_loc()} since there are failed transportation component(s) {failed_transpo_link_en_route} in its possible route. The simulation will defer the repair of {component} and try to repair other failed components."
                            )
                            if component not in self.transpo_access_no_redundancy:
                                self.transpo_access_no_redundancy[component] = 1e10
                # Schedule the recovery action
                if recovery_start is not None:
                    recovery_start = int(120 * round(float(recovery_start) / 120))

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

                    recovery_end = int(
                        120 * round(float(recovery_start + recovery_time) / 120)
                    )
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

                    # -----------------------------------------------
                    self.event_table_wide = self.event_table_wide.append(
                        {
                            "component": component,
                            "disrupt_time": self.network.disruption_time,
                            "repair_start": recovery_start,
                            "functional_start": recovery_end,
                        },
                        ignore_index=True,
                    )

                    # -----------------------------------------------

                    if compon_details[0] == "water":
                        self.total_water_recovery_time = recovery_start + recovery_time
                    elif compon_details[0] == "power":
                        self.total_power_recovery_time = recovery_start + recovery_time
                    elif compon_details[0] == "transpo":
                        self.total_transpo_recovery_time = (
                            recovery_start + recovery_time
                        )

                    self.event_table = self.event_table.append(
                        {
                            "time_stamp": recovery_start
                            + recovery_time
                            + self.sim_step * 2,
                            "components": component,
                            "perf_level": 100,
                            "component_state": "Service Restored",
                        },
                        ignore_index=True,
                    )
                    self.event_table = self.event_table.append(
                        {
                            "time_stamp": recovery_start + recovery_time + 10 * 3600,
                            "components": component,
                            "perf_level": 100,
                            "component_state": "Service Restored",
                        },
                        ignore_index=True,
                    )

            while len(components_to_repair) > 0:
                recovery_start = None
                for _, component in enumerate(components_to_repair):
                    compon_details = interdependencies.get_compon_details(component)

                    if compon_details[0] == "power":
                        power_crew = self.network.get_idle_crew("power")

                        recovery_time = (
                            interdependencies.get_power_repair_time(component) * 3600
                        )

                        connected_buses = interdependencies.find_connected_power_node(
                            component, self.network.pn
                        )

                        nearest_nodes = []
                        for connected_bus in connected_buses:
                            nearest_node, _ = interdependencies.get_nearest_node(
                                self.network.integrated_graph,
                                connected_bus,
                                "transpo_node",
                            )
                            nearest_nodes.append(nearest_node)

                        travel_time = 1e10
                        update_times = list(self.transpo_updated_model_dict.keys())
                        curr_update_time = max(
                            [
                                x
                                for x in update_times
                                if x <= power_crew.get_next_trip_start()
                            ]
                        )
                        tn = self.transpo_updated_model_dict[curr_update_time]
                        for nearest_node in nearest_nodes:
                            (
                                curr_path,
                                curr_travel_time,
                            ) = tn.calculateShortestTravelTime(
                                power_crew.get_crew_loc(), nearest_node
                            )

                            if curr_travel_time < travel_time:
                                path = curr_path
                                travel_time = curr_travel_time
                        actual_travel_time = 10 + int(round(travel_time, 0))
                        # 10 minutes for preparations

                        failed_transpo_link_en_route = [
                            link for link in path if link in repair_order
                        ]

                        accessible, possible_start = self.check_route_accessibility(
                            failed_transpo_link_en_route
                        )

                        if not failed_transpo_link_en_route:
                            recovery_start = (
                                power_crew.get_next_trip_start()
                                + actual_travel_time * 60
                            )

                            print(
                                f"Repair {component}: The power crew {power_crew._name} is at {power_crew.get_crew_loc()} at t = {power_crew.get_next_trip_start() / 60} minutes. It takes {actual_travel_time} minutes to reach nearest node {nearest_node},  the nearest transportation node from {component}."
                            )

                            power_crew.set_crew_loc(nearest_node)
                            power_crew.set_next_trip_start(
                                recovery_start + recovery_time
                            )

                            self.repair_time_dict[component] = (
                                recovery_start + recovery_time
                            )
                            components_to_repair.remove(component)
                            self.power_crew_total_tt += actual_travel_time
                            break
                        elif accessible is True:
                            if possible_start >= power_crew.get_next_trip_start():
                                recovery_start = (
                                    possible_start + actual_travel_time * 60
                                )
                            else:
                                recovery_start = (
                                    power_crew.get_next_trip_start()
                                    + actual_travel_time * 60
                                )

                            idle_time = round(
                                (recovery_start - power_crew.get_next_trip_start())
                                / 60,
                                0,
                            )

                            print(
                                f"Repair {component}: The power crew {power_crew._name} is at {power_crew.get_crew_loc()} at t = {power_crew.get_next_trip_start() / 60}  minutes. It takes {round(idle_time,2)} minutes to reach nearest node {nearest_node}, the nearest transportation  node from {component} considering time for road link repair."
                            )

                            power_crew.set_crew_loc(nearest_node)
                            power_crew.set_next_trip_start(
                                recovery_start + recovery_time
                            )

                            self.repair_time_dict[component] = (
                                recovery_start + recovery_time
                            )
                            components_to_repair.remove(component)
                            self.power_crew_total_tt += actual_travel_time
                            break
                        else:
                            print(
                                f"The power crew {power_crew._name} cannot reach the destination {nearest_node} from {power_crew.get_crew_loc()}  since there are failed transportation component(s) {failed_transpo_link_en_route} in its possible  route. The simulation will defer the repair of {component} and try to repair other failed components."
                            )
                            if component not in self.power_access_no_redundancy:
                                self.power_access_no_redundancy.append(component)

                    elif compon_details[0] == "water":

                        # select an available power repair crew
                        water_crew = self.network.get_idle_crew("water")

                        recovery_time = (
                            interdependencies.get_water_repair_time(
                                component, self.network.wn
                            )
                            * 3600
                        )

                        connected_nodes = interdependencies.find_connected_water_node(
                            component, self.network.wn
                        )
                        nearest_nodes = []
                        for connected_node in connected_nodes:
                            nearest_node, _ = interdependencies.get_nearest_node(
                                self.network.integrated_graph,
                                connected_node,
                                "transpo_node",
                            )
                            nearest_nodes.append(nearest_node)

                        travel_time = 1e10
                        update_times = list(self.transpo_updated_model_dict.keys())
                        curr_update_time = max(
                            [
                                x
                                for x in update_times
                                if x <= water_crew.get_next_trip_start()
                            ]
                        )
                        tn = self.transpo_updated_model_dict[curr_update_time]
                        for nearest_node in nearest_nodes:
                            (
                                curr_path,
                                curr_travel_time,
                            ) = tn.calculateShortestTravelTime(
                                water_crew.get_crew_loc(), nearest_node
                            )

                            if curr_travel_time < travel_time:
                                path = curr_path
                                travel_time = curr_travel_time
                        actual_travel_time = 10 + int(round(travel_time, 0))
                        # 10 minutes for preparations

                        failed_transpo_link_en_route = [
                            link for link in path if link in repair_order
                        ]

                        accessible, possible_start = self.check_route_accessibility(
                            failed_transpo_link_en_route
                        )

                        if not failed_transpo_link_en_route:
                            recovery_start = (
                                water_crew.get_next_trip_start()
                                + actual_travel_time * 60
                            )

                            print(
                                f"Repair {component}: The water crew {water_crew._name} is at {water_crew.get_crew_loc()} at t = {water_crew.get_next_trip_start() / 60}  minutes. It takes {actual_travel_time} minutes to reach nearest node {nearest_node}, the nearest transportation  node from {component}."
                            )

                            water_crew.set_crew_loc(nearest_node)
                            water_crew.set_next_trip_start(
                                recovery_start + recovery_time
                            )

                            self.repair_time_dict[component] = (
                                recovery_start + recovery_time
                            )
                            components_to_repair.remove(component)
                            self.water_crew_total_tt += actual_travel_time
                            break
                        elif accessible is True:
                            if possible_start >= water_crew.get_next_trip_start():
                                recovery_start = (
                                    possible_start + actual_travel_time * 60
                                )
                            else:
                                recovery_start = (
                                    water_crew.get_next_trip_start()
                                    + actual_travel_time * 60
                                )

                            idle_time = round(
                                (recovery_start - water_crew.get_next_trip_start())
                                / 60,
                                0,
                            )
                            print(
                                f"Repair {component}: The water crew {water_crew._name} is at {water_crew.get_crew_loc()} at t = {water_crew.get_next_trip_start() / 60}  minutes. It takes {idle_time} minutes to reach nearest node {nearest_node}, the nearest transportation  node from {component} considering time for road link repair."
                            )

                            water_crew.set_crew_loc(nearest_node)
                            water_crew.set_next_trip_start(
                                recovery_start + recovery_time
                            )

                            self.repair_time_dict[component] = (
                                recovery_start + recovery_time
                            )
                            components_to_repair.remove(component)
                            self.water_crew_total_tt += actual_travel_time
                            break
                        else:
                            print(
                                f"The water crew {water_crew._name} cannot reach the destination {nearest_node} from {water_crew.get_crew_loc()}  since there are failed transportation component(s) {failed_transpo_link_en_route} in its  possible route. The simulation will will defer the repair of {component} and try to repair other failed components."
                            )
                            if component not in self.water_access_no_redundancy:
                                self.water_access_no_redundancy.append(component)

                # Schedule the recovery action
                if recovery_start is not None:
                    recovery_start = int(120 * round(float(recovery_start) / 120))

                    if compon_details[0] == "power":
                        if compon_details[1] in ["L"]:
                            if self._line_close_policy == "sensor_based_line_isolation":
                                if (
                                    recovery_start
                                    > self.network.disruption_time
                                    + 60 * self._pipe_closure_delay
                                ):
                                    self.network.disruption_time = recovery_start
                                    self.event_table = self.event_table.append(
                                        {
                                            "time_stamp": self.network.disruption_time
                                            + 60
                                            * self._line_closure_delay,  # Leaks closed within 10 mins
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
                            elif (
                                self._line_close_policy
                                == "sensor_based_cluster_isolation"
                            ):
                                if (
                                    recovery_start
                                    > self.network.disruption_time
                                    + 60 * self._pipe_closure_delay
                                ):
                                    self.event_table = self.event_table.append(
                                        {
                                            "time_stamp": self.network.disruption_time
                                            + 60
                                            * self._line_closure_delay,  # Leaks closed within 10 mins
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

                    elif compon_details[0] == "water":
                        if compon_details[1] in ["PMA", "P", "T"]:
                            if self._pipe_close_policy == "sensor_based_pipe_isolation":
                                if (
                                    recovery_start
                                    > self.network.disruption_time
                                    + 60 * self._pipe_closure_delay
                                ):
                                    self.network.disruption_time = recovery_start
                                    self.event_table = self.event_table.append(
                                        {
                                            "time_stamp": self.network.disruption_time
                                            + 60
                                            * self._pipe_closure_delay,  # Leaks closed within 10 mins
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
                            elif (
                                self._pipe_close_policy
                                == "sensor_based_cluster_isolation"
                            ):
                                if (
                                    recovery_start
                                    > self.network.disruption_time
                                    + 60 * self._pipe_closure_delay
                                ):
                                    self.event_table = self.event_table.append(
                                        {
                                            "time_stamp": self.network.disruption_time
                                            + 60
                                            * self._pipe_closure_delay,  # Leaks closed within 10 mins
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

                    recovery_end = int(
                        120 * round(float(recovery_start + recovery_time) / 120)
                    )
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

                    # -----------------------------------------------
                    self.event_table_wide = self.event_table_wide.append(
                        {
                            "component": component,
                            "disrupt_time": self.network.disruption_time,
                            "repair_start": recovery_start,
                            "functional_start": recovery_end,
                        },
                        ignore_index=True,
                    )

                    # -----------------------------------------------

                    if compon_details[0] == "water":
                        self.total_water_recovery_time = recovery_start + recovery_time
                    elif compon_details[0] == "power":
                        self.total_power_recovery_time = recovery_start + recovery_time
                    elif compon_details[0] == "transpo":
                        self.total_transpo_recovery_time = (
                            recovery_start + recovery_time
                        )

                    self.event_table = self.event_table.append(
                        {
                            "time_stamp": recovery_start
                            + recovery_time
                            + self.sim_step * 2,
                            "components": component,
                            "perf_level": 100,
                            "component_state": "Service Restored",
                        },
                        ignore_index=True,
                    )
                    self.event_table = self.event_table.append(
                        {
                            "time_stamp": recovery_start + recovery_time + 10 * 3600,
                            "components": component,
                            "perf_level": 100,
                            "component_state": "Service Restored",
                        },
                        ignore_index=True,
                    )

            self.event_table.sort_values(by=["time_stamp"], inplace=True)
            self.event_table["time_stamp"] = self.event_table["time_stamp"].astype(int)
            self.network.reset_crew_locs()
            print("All restoration actions are successfully scheduled.")
            self.transpo_updated_model_dict = dict()
        else:
            print("No repair action to schedule.")

    def get_event_table(self):
        """Returns the event table."""
        return self.event_table

    def update_directly_affected_components(self, time_stamp, next_sim_time):
        """Updates the operational performance of directly impacted infrastructure components by the external event.

        :param time_stamp: Current time stamp in the event table in seconds.
        :type time_stamp: integer
        :param next_sim_time: Next time stamp in the event table in seconds.
        :type next_sim_time: integer
        """
        # print(self.network.wn.control_name_list)
        print(
            f"Updating status of directly affected components between {time_stamp} and {next_sim_time}..."
        )
        curr_event_table = self.event_table[self.event_table.time_stamp == time_stamp]

        for _, row in curr_event_table.iterrows():
            component = row["components"]
            time_stamp = row["time_stamp"]
            perf_level = row["perf_level"]
            component_state = row["component_state"]
            compon_details = interdependencies.get_compon_details(component)
            if compon_details[0] == "power":
                compon_index = (
                    self.network.pn[compon_details[2]]
                    .query('name == "{}"'.format(component))
                    .index.item()
                )

                if perf_level < 100:
                    if self._line_close_policy == "sensor_based_line_isolation":
                        self.network.pn[compon_details[2]].at[
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
                        self.network.pn[compon_details[2]].at[
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
                        if component in self.repairs_to_simulate:
                            self.repairs_to_simulate.remove(component)

            elif compon_details[0] == "water":

                if compon_details[3] == "Pump":
                    if perf_level < 100:
                        self.network.wn.get_link(component).add_outage(
                            self.network.wn, time_stamp, next_sim_time
                        )
                        # print(
                        #     f"The pump outage is added between {time_stamp} s and {next_sim_time} s"
                        # )

                elif compon_details[3] in [
                    "Pipe",
                    "Service Connection Pipe",
                    "Main Pipe",
                    "Hydrant Connection Pipe",
                    "Valve converted to Pipe",
                ]:
                    if component_state == "Service Disrupted":
                        leak_node = self.network.wn.get_node(f"{component}_leak_node")
                        leak_node.remove_leak(self.network.wn)
                        leak_node.add_leak(
                            self.network.wn,
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
                            f"close pipe {component}_isolated"
                            not in self.network.wn.control_name_list
                        ):
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
                                f"close pipe {valve}_isolated"
                                not in self.network.wn.control_name_list
                            ):
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

                elif compon_details[3] == "Tank":
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
                    # else:
                    #     pipes_to_tank = self.network.wn.get_links_for_node(component)
                    #     for pipe_name in pipes_to_tank:
                    #         self.network.wn.get_link(pipe_name).status = 1

    def reset_networks(self):
        """Resets the IntegratedNetwork object within NetworkRecovery object."""
        self.network = copy.deepcopy(self.base_network)

    def update_traffic_model(self):
        """Updates the static traffic assignment model based on current network conditions."""
        self.network.tn.userEquilibrium(
            "FW", 400, 1e-4, self.network.tn.averageExcessCost
        )
        pass

    def fail_transpo_link(self, link_compon):
        """Fails the given transportation link by changing the free-flow travel time to a very large value.

        Args:
            link_compon (string): Name of the transportation link.
        """
        self.network.tn.link[link_compon].freeFlowTime = 9999

    def restore_transpo_link(self, link_compon):
        """Restores the disrupted transportation link by changing the free flow travel time to the original value.

        Args:
            link_compon (string): Name of the transportation link.
        """
        self.network.tn.link[link_compon].freeFlowTime = self.network.tn.link[
            link_compon
        ].fft_base

    def check_route_accessibility(self, failed_transpo_link_en_route):
        """Checks when the failed transportation links along a route are repaired and the possible start time.

        :param failed_transpo_link_en_route: [description]
        :type failed_transpo_link_en_route: [type]
        :return: [description]
        :rtype: [type]
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

        :param network_recovery: NetworkRecovery object
        :type network_recovery: NetworkRecovery
        :param compons_to_repair: List of components to be repaired excluding the component under consideration.
        :type compons_to_repair: list
        :param switch: Switch component
        :type switch: string
        """
        allowed = True
        p_compons = [compon for compon in compons_to_repair if compon.startswith("P_")]

        for p_compon in p_compons:
            if switch in self.network.line_switch_dict[p_compon]:
                allowed = False
                break
        return allowed


def pipe_leak_node_generator(network):
    """Splits the directly affected pipes to induce leak during simulations.
    :param wn: Water network object.
    :type wn: wntr network object
    """
    for _, component in enumerate(network.get_disrupted_components()):
        compon_details = interdependencies.get_compon_details(component)
        if compon_details[3] == "Pipe":
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
    wn.add_control("open pipe " + pipe_name + f"_{state}", ctrl_open)
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
    wn.add_control("close pipe " + pipe_name + f"_{state}", ctrl_close)
    return wn
