"""Resilience metric classes to be used for optimizing recovery actions."""

from sklearn import metrics
from statistics import mean
import pandas as pd
import wntr
import copy


class WeightedResilienceMetric:
    """A class that consists of methods to calculate and store weighted ILOS estimates without"""

    def __init__(self):
        """Initiates the WeightedResilienceMetric object."""
        self.water_leak_loss_df = None
        self.water_pump_flow_df = None
        self.water_node_head_df = None
        self.water_junc_demand_df = None
        self.water_node_pressure_df = None
        self.power_load_df = None

        self.sim_times = []

    def calculate_water_lost(self, network_recovery, wn_results):
        """Calculates the flows through pipe leaks and stores it to a table.

        :param network_recovery: The network recovery object
        :type network_recovery: NetworkRecovery object
        :param wn_results: The water network simulation results for the current time interval
        :type wn_results: wntr object
        """
        node_list = network_recovery.network.wn.node_name_list
        if self.water_leak_loss_df is None:
            self.water_leak_loss_df = wn_results.node["leak_demand"][node_list]
            self.water_leak_loss_df["time"] = wn_results.node["leak_demand"].index
        else:
            water_leak_loss_df_new = wn_results.node["leak_demand"][node_list]
            water_leak_loss_df_new["time"] = wn_results.node["leak_demand"].index
            self.water_leak_loss_df = pd.concat(
                [self.water_leak_loss_df, water_leak_loss_df_new],
                ignore_index=True,
            )

    def calculate_node_details(self, network_recovery, wn_results):
        """Calculates the node head, deamand and pressure and stores them to respective tables.

        :param network_recovery: The network recovery object
        :type network_recovery: NetworkRecovery object
        :param wn_results: The water network simulation results for the current time interval
        :type wn_results: wntr object
        """
        node_list = network_recovery.network.wn.node_name_list
        if self.water_node_head_df is None:
            self.water_node_head_df = wn_results.node["head"][node_list]
            self.water_node_head_df["time"] = wn_results.node["head"].index
        else:
            water_node_head_df_new = wn_results.node["head"][node_list]
            water_node_head_df_new["time"] = wn_results.node["head"].index
            self.water_node_head_df = pd.concat(
                [self.water_node_head_df, water_node_head_df_new],
                ignore_index=True,
            )

        if self.water_junc_demand_df is None:
            self.water_junc_demand_df = wn_results.node["demand"][node_list]
            self.water_junc_demand_df["time"] = wn_results.node["demand"].index
        else:
            water_junc_demand_df_new = wn_results.node["demand"][node_list]
            water_junc_demand_df_new["time"] = wn_results.node["demand"].index
            self.water_junc_demand_df = pd.concat(
                [self.water_junc_demand_df, water_junc_demand_df_new],
                ignore_index=True,
            )

        if self.water_node_pressure_df is None:
            self.water_node_pressure_df = wn_results.node["pressure"][node_list]
            self.water_node_pressure_df["time"] = wn_results.node["pressure"].index
        else:
            water_node_pressure_df_new = wn_results.node["pressure"][node_list]
            water_node_pressure_df_new["time"] = wn_results.node["pressure"].index
            self.water_node_pressure_df = pd.concat(
                [self.water_node_pressure_df, water_node_pressure_df_new],
                ignore_index=True,
            )

    def calculate_pump_flow(self, network_recovery, wn_results):
        """Calculates the flowrates in pumps and stores the values to a table.

        :param network_recovery: The network recovery object.
        :type network_recovery: NetworkRecovery object
        :param wn_results: The water network simulation results for the current time interval
        :type wn_results: wntr object
        """
        pump_list = network_recovery.network.wn.pump_name_list
        if self.water_pump_flow_df is None:
            self.water_pump_flow_df = wn_results.link["flowrate"][pump_list]
            self.water_pump_flow_df["time"] = wn_results.link["flowrate"].index
        else:
            water_pump_flow_df_new = wn_results.link["flowrate"][pump_list]
            water_pump_flow_df_new["time"] = wn_results.link["flowrate"].index
            self.water_pump_flow_df = pd.concat(
                [self.water_pump_flow_df, water_pump_flow_df_new],
                ignore_index=True,
            )

    def calculate_power_load(self, network_recovery, sim_time):
        """Calculates the power flow in loads and motor pumps.

        :param network_recovery: The network recovery object.
        :type network_recovery: NetworkRecovery object
        :param sim_time: The simulation time when the data is collected.
        :type sim_time: integer
        """
        self.sim_times.append(sim_time)
        pn = network_recovery.network.pn
        if self.power_load_df is None:
            self.power_load_df = pd.DataFrame(
                columns=["time"] + list(pn.load.name) + list(pn.motor.name)
            )
            self.power_load_df.loc[len(self.power_load_df)] = (
                [sim_time] + list(pn.res_load.p_mw) + list(pn.res_motor.p_mw)
            )
        else:
            self.power_load_df.loc[len(self.power_load_df)] = (
                [sim_time] + list(pn.res_load.p_mw) + list(pn.res_motor.p_mw)
            )

    def calculate_pump_energy(self, wn_object):
        """Calculates the energy consumed by each pump in kWhr in the network and stores the values in a dictionary.

        :param wn_object: The water network model.
        :type wn_object: wntr water network object
        """
        pump_flows = self.water_pump_flow_df
        pump_flows = pump_flows.set_index("time", drop=True)

        node_heads = self.water_node_head_df
        node_heads = node_heads.set_index("time", drop=True)

        pump_energy = wntr.metrics.economic.pump_energy(
            pump_flows, node_heads, wn_object
        )

        pump_energy_dict = dict()
        for pump in pump_energy.columns:
            pump_energy_dict[pump] = round(
                metrics.auc(pump_energy.index, pump_energy[pump]) / (3600 * 1000), 3
            )
        self.pump_energy_consumed = pump_energy_dict

    def calculate_water_resmetrics(self, network_recovery):
        """Calculates the water network performance timelines (pcs and ecs).

        :param network_recovery: The network recovery object
        :type network_recovery: NetworkRecovery object
        """
        junc_list = network_recovery.network.wn.junction_name_list

        water_demands = self.water_junc_demand_df
        water_pressures = self.water_node_pressure_df

        water_time_list = water_demands.time / 60
        self.water_time_list = water_time_list.tolist()
        rel_time_list = water_demands["time"] % (24 * 3600)
        index_list = [int(x / 60) for x in rel_time_list]
        water_demands = water_demands[junc_list]

        base_water_demands = network_recovery.network.base_water_node_supply

        water_pressures = water_pressures[junc_list]
        water_press_corrections = copy.deepcopy(water_pressures)

        if network_recovery.network.water_sim_type == "DDA":
            for _, column in enumerate(water_pressures.columns):
                water_press_corrections[column] = water_pressures[column].apply(
                    lambda x: 0
                    if x <= 0
                    else (
                        (
                            x
                            / network_recovery.network.wn.options.hydraulic.threshold_pressure
                        )
                        ** 0.5
                        if x
                        <= network_recovery.network.wn.options.hydraulic.threshold_pressure
                        else x
                    )
                )
            water_demands = water_demands * water_press_corrections

        base_water_demands_new = base_water_demands.iloc[index_list].reset_index(
            drop=True
        )
        base_water_demands_new = base_water_demands_new[junc_list]

        water_demands_ratio = water_demands / base_water_demands_new
        water_demands_ratio = water_demands_ratio.clip(upper=1)

        self.water_ecs_list = water_demands_ratio.mean(axis=1, skipna=True).tolist()
        water_pcs_list = pd.concat([water_demands, base_water_demands_new]).min(
            level=0
        ).sum(axis=1, skipna=True) / base_water_demands_new.sum(axis=1, skipna=True)
        self.water_pcs_list = water_pcs_list.tolist()

    def calculate_power_resmetric(self, network_recovery):
        """Calculates the power network performance timelines (pcs and ecs).

        :param network_recovery: The network recovery object
        :type network_recovery: NetworkRecovery object
        """
        power_demands = self.power_load_df
        power_time_list = power_demands.time / 60
        self.power_time_list = power_time_list.tolist()

        base_power_demands = network_recovery.network.base_power_demands

        base_load_demands = pd.DataFrame(
            base_power_demands.load.p_mw.tolist()
            + base_power_demands.motor.pn_mech_mw.tolist()
        ).transpose()
        base_load_demands.columns = (
            base_power_demands.load.name.tolist()
            + base_power_demands.motor.name.tolist()
        )
        base_load_demands = pd.concat(
            [base_load_demands] * (power_demands.shape[0])
        ).reset_index(drop=True)

        power_demand_ratio = power_demands.iloc[:, 1:] / base_load_demands
        power_demand_ratio = power_demand_ratio.clip(upper=1)

        self.power_ecs_list = power_demand_ratio.mean(axis=1, skipna=True).tolist()
        power_pcs_list = pd.concat([power_demands.iloc[:, 1:], base_load_demands]).min(
            level=0
        ).sum(axis=1, skipna=True) / base_load_demands.sum(axis=1, skipna=True)
        self.power_pcs_list = power_pcs_list.tolist()

    def calculate_transpo_resmetric(self, tn):
        pass

    def set_weighted_auc_metrics(self):
        """Calculates the water, power, and weighted auc values."""
        self.power_ecs_auc = round(
            metrics.auc(self.power_time_list, self.power_ecs_list), 3
        )
        self.power_pcs_auc = round(
            metrics.auc(self.power_time_list, self.power_pcs_list), 3
        )

        self.water_ecs_auc = round(
            metrics.auc(self.water_time_list, self.water_ecs_list), 3
        )
        self.water_pcs_auc = round(
            metrics.auc(self.water_time_list, self.water_pcs_list), 3
        )

        self.weighed_ecs_auc = 0.5 * self.power_ecs_auc + 0.5 * self.water_ecs_auc
        self.weighed_pcs_auc = 0.5 * self.power_pcs_auc + 0.5 * self.water_pcs_auc

    def get_weighted_auc_metrics(self):
        """Returns the weighted auc metrics.

        :return: list of acs and pcs weighted auc values
        :rtype: list
        """
        return (
            round(self.weighed_ecs_auc, 3),
            round(self.weighed_pcs_auc, 3),
        )
