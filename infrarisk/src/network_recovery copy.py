"""Functions to generate and save disruptive scenarios."""

import math
import copy
import pandas as pd
import wntr
from wntr.network.controls import ControlPriority
from infrarisk.src.network_sim_models import interdependencies as interdependencies


class NetworkRecovery:
    """Generate a disaster and recovery object for storing simulation-related information and settings."""

    def __init__(self, network, sim_step):
        self.base_network = network
        self.network = copy.deepcopy(self.base_network)
        self.sim_step = sim_step

    def schedule_recovery(self, repair_order):

        if len(repair_order) > 0:
            # Schedule component performance at the start and disruption of the simulation.
            self.initiate_schedule_tables()
            for _, row in self.network.disruptive_events.iterrows():
                component = row["component"]
                time_stamp = row["time_stamp"]
                fail_perc = row["fail_perc"]

                self.add_functional_state(component, 0)
                self.add_disrupted_state(component, time_stamp, fail_perc)

                if component.startswith("T_"):
                    self.fail_transpo_link(component)
            
            # update transportation link flows and costs only if there is any change to transportation network due to the event
            disrupted_infra_dict = self.network.get_disrupted_infra_dict()
            if len(disrupted_infra_dict["transpo"]) > 0:
                self.update_traffic_model()
                self.transpo_updated_model_dict[
                    self.network.disruption_time
                ] = copy.deepcopy(self.network.tn)

    def add_functional_state(self, component, time_stamp):
        """Add a row to the event table for a component that is functional or complered repair."""
        self.event_table = self.event_table.append(
            {
                "time_stamp": time_stamp,
                "components": component,
                "perf_level": 100,
                "component_state": "Functional",
            },
            ignore_index=True,
        )

    def add_disrupted_state(self, component, time_stamp, impact_level):
        """Add a row to the event table for a component that is disrupted."""
        self.event_table = self.event_table.append(
            {
                "time_stamp": time_stamp,
                "components": component,
                "perf_level": 100 - impact_level,
                "component_state": "Service Disrupted",
            },
            ignore_index=True,
        )

    def fail_transpo_link(self, link_compon):
        """Fails the given transportation link by changing the free-flow travel time to a very large value.

        Args:
            link_compon (string): Name of the transportation link.
        """
        self.network.tn.link[link_compon].freeFlowTime = 9999

    def initiate_schedule_tables(self):
        columns_list = [
            "time_stamp",
            "component",
            "perf_level",
            "component_state",
            "crew_id",
        ]
        self.event_table = pd.DataFrame(columns=columns_list)

        column_list_et_short = [
            "component",
            "disrupt_level",
            "repair_start",
            "functional_start",
        ]
        self.event_table_wide = pd.DataFrame(columns=column_list_et_short)
