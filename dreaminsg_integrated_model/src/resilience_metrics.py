"""Functions to calculate the resilience metrics used for optimizing recovery actions."""

from dreaminsg_integrated_model.src.network_sim_models.interdependencies import *
from dreaminsg_integrated_model.src.network_recovery import *


def calculate_base_demand_metrics(network):
    """Calculates the base netwok demands for water, power and traffic.

    :param wn: Water network object.
    :type wn: wntr network object.
    :param pn: Power network object.
    :type pn: pandapower network object.
    :param tn: Traffic network object.
    :type tn: STA object
    :return: list of total base water demand, total base power demand, and total base system travel time.
    :rtype: list of floats.
    """
    total_base_water_demand = sum(
        [network.wn.get_node(node).base_demand for node in network.wn.junction_name_list]
    )

    total_base_power_demand = network.pn.res_load.p_mw.sum() + network.pn.res_motor.p_mw.sum()

    total_base_travel_time = 0
    total_base_travel_time = sum(
        total_base_travel_time + network.tn.link[i].flow * network.tn.link[i].cost
        for i in network.tn.link
    )


    return total_base_water_demand, total_base_power_demand, total_base_travel_time
