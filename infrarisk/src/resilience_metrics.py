"""Resilience metric classes to be used for optimizing recovery actions."""

from abc import ABC, abstractmethod
import math
from sklearn import metrics


class ResilienceMetric(ABC):
    """The ResilienceMetric class defines an interface to a resilience metric."""

    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def calculate_water_resmetric(self, wn, wn_results):
        pass

    @abstractmethod
    def calculate_power_resmetric(self, pn):
        pass

    @abstractmethod
    def calculate_transpo_resmetric(self, tn):
        pass


class WeightedResilienceMetric(ResilienceMetric):
    """A class that consists of methods to calculate and store weighted ILOS estimates without"""

    def __init__(self):
        """Initiates the WeightedResilienceMetric object."""
        self.time_tracker = []
        self.power_consump_tracker = []
        self.water_consump_tracker = []
        self.transpo_tracker = []

    def calculate_water_resmetric(self, network_recovery, wn_results):
        """Calculates and returns the water resilience metric.

        :param network_recovery: The network recovery object
        :type network_recovery: NetworkRecovery object
        :param wn_results: The water network simulation results for the current time interval
        :type wn_results: wntr object
        :return: water resilience metric value
        :rtype: float
        """
        sim_time = network_recovery.network.wn.options.time.duration
        node_demand = wn_results.node["demand"].iloc[-1]
        node_pressure = wn_results.node["pressure"].iloc[-1]

        water_supplied_at_t = sum(
            [
                node_demand[junc]
                for junc in network_recovery.network.wn.junction_name_list
                if node_pressure[junc]
                > network_recovery.network.wn.options.hydraulic.threshold_pressure
            ]
        )

        base_demands_at_t = []

        for junc in network_recovery.network.wn.junction_name_list:
            base_demand = network_recovery.network.wn.get_node(junc).base_demand

            if base_demand != 0:
                pattern = (
                    network_recovery.network.wn.get_node(junc)
                    .demand_timeseries_list[0]
                    .pattern.multipliers
                )
                pattern_size = len(pattern)
                pattern_interval = 24 / pattern_size
                pattern_index = math.floor(
                    (((sim_time) / 3600) % 24) / pattern_interval
                )

                multiplier = pattern[pattern_index]
                base_demands_at_t.append(multiplier * base_demand)

        print("Supply: ", water_supplied_at_t, "Base demand: ", sum(base_demands_at_t))
        water_resmetric = water_supplied_at_t / sum(base_demands_at_t)
        return water_resmetric

    def calculate_power_resmetric(self, network_recovery):
        """Calcualtes the power resilience metric.

        :param network_recovery: The network recovery object
        :type network_recovery: NetworkRecovery object
        :return: Power resilience metric value
        :rtype: float
        """
        if network_recovery.network.pn.sim_type == "1ph":
            base_demand = (
                network_recovery.network.pn.load["p_mw"].sum()
                + network_recovery.network.pn.motor["pn_mech_mw"].sum()
            )
            power_resmetric = (
                network_recovery.network.pn.res_load["p_mw"].sum()
                + network_recovery.network.pn.res_motor["p_mw"].sum()
            ) / base_demand

        elif network_recovery.network.pn.sim_type == "3ph":
            base_demand = (
                network_recovery.network.pn.asymmetric_load[
                    ["p_a_mw", "p_b_mw", "p_c_mw"]
                ]
                .sum()
                .sum()
            )
            power_resmetric = (
                network_recovery.network.pn.res_asymmetric_load_3ph.sum().sum()
            ) / base_demand

        return power_resmetric

    def calculate_transpo_resmetric(self, tn):
        pass

    def set_weighted_auc_metrics(self):
        """Calculates the water, power, and weighted auc values."""
        self.water_auc = metrics.auc(
            self.time_tracker, self.water_consump_tracker
        )  # / max(self.time_tracker)
        self.power_auc = metrics.auc(
            self.time_tracker, self.power_consump_tracker
        )  # / max(self.time_tracker)

        self.weighed_auc = 0.5 * self.water_auc + 0.5 * self.power_auc

    def get_weighted_auc_metrics(self):
        """Returns the weighted auc metrics.

        :return: list of power, water and weighted auc values
        :rtype: list
        """
        return (
            round(self.power_auc, 3),
            round(self.water_auc, 3),
            round(self.weighed_auc, 3),
        )

    def get_time_tracker(self):
        """Returns the time tracker list with time in minutes.

        :return: time tracker
        :rtype: list
        """
        return self.time_tracker

    def get_power_consump_tracker(self):
        """Returns the power consumption ratio list.

        :return: power consumption ratio values
        :rtype: list
        """
        return self.power_consump_tracker

    def get_water_consump_tracker(self):
        """Returns the water consumption ratio list.

        :return: water consumption ratio values
        :rtype: list
        """
        return self.water_consump_tracker
