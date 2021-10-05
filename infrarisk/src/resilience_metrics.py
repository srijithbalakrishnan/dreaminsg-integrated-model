"""Resilience metric classes to be used for optimizing recovery actions."""

from abc import ABC, abstractmethod
import math
from sklearn import metrics
import numpy as np
from statistics import mean
import pandas as pd
from wntr import network


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
        self.water_loss_tracker = []
        self.water_pump_flow_df = None
        self.water_node_head_df = None

    def calculate_water_lost(self, network_recovery, wn_results):

        disrupted_pipes = [
            compon
            for compon in network_recovery.network.get_disrupted_components()
            if compon in network_recovery.network.wn.pipe_name_list
        ]
        total_leak_at_t = sum(
            wn_results.node["leak_demand"][
                [f"{component}_leak_node" for component in disrupted_pipes]
            ]
            .iloc[[-1]]
            .values
        )
        return total_leak_at_t

    def calculate_node_head(self, network_recovery, wn_results):
        node_list = network_recovery.network.wn.node_name_list
        if self.water_node_head_df is None:
            self.water_node_head_df = pd.DataFrame(
                columns=[node for node in node_list],
                data=wn_results.node["head"].iloc[[-1]],
            )
        else:
            self.water_node_head_df = pd.concat(
                [self.water_node_head_df, wn_results.node["head"].iloc[[-1]]],
                ignore_index=True,
            )

    def calculate_pump_flow(self, network_recovery, wn_results):
        pump_list = network_recovery.network.wn.pump_name_list
        if self.water_pump_flow_df is None:
            self.water_pump_flow_df = pd.DataFrame(
                columns=[pump for pump in pump_list],
                data=wn_results.link["flowrate"][pump_list].iloc[[-1]],
            )
        else:
            self.water_pump_flow_df = pd.concat(
                [
                    self.water_pump_flow_df,
                    wn_results.link["flowrate"][pump_list].iloc[[-1]],
                ],
                ignore_index=True,
            )

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

        water_supplied_at_t = []
        base_supply_at_t = []
        supply_ratio_at_t = []

        for junc in network_recovery.network.wn.junction_name_list:
            if junc in network_recovery.network.base_water_node_supply.columns:
                # base supply
                base_supply_df = network_recovery.network.base_water_node_supply
                base_junc_supply_at_t = base_supply_df[
                    base_supply_df.time == int(sim_time % (24 * 3600))
                ][junc].item()
                base_supply_at_t.append(base_junc_supply_at_t)

                # actual supply
                if (
                    node_pressure[junc]
                    >= network_recovery.network.wn.options.hydraulic.threshold_pressure
                ):
                    actual_junc_supply_at_t = node_demand[junc]
                    water_supplied_at_t.append(actual_junc_supply_at_t)
                    # supply ratio
                    if base_junc_supply_at_t > 0:
                        supply_ratio_at_t.append(
                            min(1, actual_junc_supply_at_t / base_junc_supply_at_t)
                        )
                elif (
                    0
                    <= node_pressure[junc]
                    < network_recovery.network.wn.options.hydraulic.threshold_pressure
                ):
                    actual_junc_supply_at_t = node_demand[junc] * math.sqrt(
                        node_pressure[junc]
                        / network_recovery.network.wn.options.hydraulic.threshold_pressure
                    )
                    water_supplied_at_t.append(actual_junc_supply_at_t)
                    # supply ratio
                    if base_junc_supply_at_t > 0:
                        supply_ratio_at_t.append(
                            min(1, actual_junc_supply_at_t / base_junc_supply_at_t)
                        )

        print(
            "Supply: ",
            round(sum(water_supplied_at_t), 3),
            "Base demand: ",
            round(sum(base_supply_at_t), 3),
            "Supply ratio: ",
            round(mean(supply_ratio_at_t), 3),
        )
        water_resmetric = min(1, mean(supply_ratio_at_t))
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
