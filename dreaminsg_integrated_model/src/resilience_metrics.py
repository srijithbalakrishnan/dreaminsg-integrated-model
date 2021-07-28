"""Resilience metric classes to be used for optimizing recovery actions."""

from abc import ABC, abstractmethod
import math

# from dreaminsg_integrated_model.src.network_sim_models.interdependencies import *
# from dreaminsg_integrated_model.src.network_recovery import *


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
    """Methods to calculated the weighted ILOS estimates without normalization."""

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
        node_results = wn_results.node["demand"].iloc[-1]

        water_supplied_at_t = sum(
            [
                node_results[junc]
                for junc in network_recovery.network.wn.junction_name_list
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
                pattern_index = math.ceil(((sim_time / 3600) % 24) / pattern_interval)

                multiplier = pattern[pattern_index - 1]
                base_demands_at_t.append(multiplier * base_demand)

        water_resmetric = water_supplied_at_t / sum(base_demands_at_t)
        return water_resmetric

    def calculate_power_resmetric(self, network_recovery):
        """Calcualtes the power resilience metric.

        :param network_recovery: The network recovery object
        :type network_recovery: NetworkRecovery object
        :return: Power resilience metric value
        :rtype: float
        """
        power_resmetric = (
            network_recovery.network.pn.res_load.p_mw.sum()
            + network_recovery.network.pn.res_motor.p_mw.sum()
        ) / network_recovery.network.total_base_power_demand

        return power_resmetric

    def calculate_transpo_resmetric(self, tn):
        pass
